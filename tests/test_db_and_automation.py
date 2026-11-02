"""Unit tests for SQLite database manager and trigger-action automation."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import db
import automation
from utils import generate_ics_calendar


def test_db_init_and_crud(tmp_path):
    test_db = str(tmp_path / "test_assistant.db")
    db.init_db(test_db)

    # 1. Add task
    t_id = db.add_task(
        title="Software Testing Lab",
        course="CS350",
        deadline="2026-11-05 17:00",
        effort=4.0,
        weight=15.0,
        difficulty=3,
        status="pending",
        db_path=test_db
    )
    assert t_id > 0

    # 2. Get task
    task = db.get_task_by_id(t_id, db_path=test_db)
    assert task is not None
    assert task["title"] == "Software Testing Lab"
    assert task["course"] == "CS350"

    # 3. Update status
    db.update_task_status(t_id, "in_progress", db_path=test_db)
    updated = db.get_task_by_id(t_id, db_path=test_db)
    assert updated["status"] == "in_progress"

    # 4. Update priority override (Human in the loop)
    db.update_task_priority_override(t_id, "Critical", db_path=test_db)
    overridden = db.get_task_by_id(t_id, db_path=test_db)
    assert overridden["user_priority_override"] == "Critical"

    # 5. Save scored tasks and conflicts
    scored_items = [{
        "task_id": t_id,
        "urgency_score": 80.0,
        "weight_score": 15.0,
        "effort_pressure_score": 60.0,
        "difficulty_score": 60.0,
        "priority_score": 75.0,
        "priority_level": "Critical",
        "rank": 1,
        "days_left": 3.0,
        "has_conflict": True,
        "ai_rationale": "High priority assignment."
    }]
    db.save_scored_tasks(scored_items, db_path=test_db)
    latest_scored = db.get_latest_scored_tasks(db_path=test_db)
    assert len(latest_scored) == 1
    assert latest_scored[0]["priority_score"] == 75.0

    conflicts = [{
        "id": "C1",
        "conflict_type": "SAME_DAY_CLASH",
        "severity": "HIGH",
        "task_ids": [t_id],
        "explanation": "Same day clash test.",
        "suggested_resolution": "Move schedule 1 day forward."
    }]
    db.save_conflicts(conflicts, db_path=test_db)
    latest_conflicts = db.get_latest_conflicts(db_path=test_db)
    assert len(latest_conflicts) == 1
    assert latest_conflicts[0]["id"] == "C1"

    # 6. Log AI run & evaluation
    run_id = db.log_ai_run(
        prompt_version="v3",
        input_payload="{}",
        raw_output="{}",
        parsed_output="{}",
        latency_ms=120.5,
        model="gemini-2.5-flash",
        mode="fallback",
        db_path=test_db
    )
    assert run_id > 0
    runs = db.get_all_ai_runs(db_path=test_db)
    assert len(runs) == 1

    eval_id = db.log_evaluation(
        prompt_version="v3",
        scores={"total_score": 10.0, "passed": True},
        ai_run_id=run_id,
        feedback_notes="All constraints verified.",
        db_path=test_db
    )
    assert eval_id > 0
    evals = db.get_all_evaluations(db_path=test_db)
    assert len(evals) == 1

    # 7. Log test result
    t_res_id = db.log_test_result(
        test_id="TC1",
        test_name="Normal Tasks",
        status="PASS",
        expected_summary="0 conflicts",
        actual_summary="0 conflicts",
        latency_ms=25.0,
        run_mode="fallback",
        db_path=test_db
    )
    assert t_res_id > 0
    test_rows = db.get_test_results(db_path=test_db)
    assert len(test_rows) == 1

    # 8. Log automation event
    auto_id = db.log_automation_event(
        trigger_name="TEST_TRIGGER",
        condition_matched="Task due < 48h",
        action_taken="Sent alert email",
        status="SUCCESS",
        details="Generated email",
        db_path=test_db
    )
    assert auto_id > 0
    auto_logs = db.get_automation_logs(db_path=test_db)
    assert len(auto_logs) == 1

    # 9. Export all to CSV & Excel
    export_dir = str(tmp_path / "exports")
    exported = db.export_all_to_csv(export_dir=export_dir, db_path=test_db)
    assert "tasks" in exported
    assert os.path.exists(exported["tasks"])

    # 10. Delete task
    db.delete_task(t_id, db_path=test_db)
    assert db.get_task_by_id(t_id, db_path=test_db) is None


def test_automation_trigger_and_outbox(tmp_path):
    test_db = str(tmp_path / "test_auto.db")
    db.init_db(test_db)

    # Urgent task due in 1 day (Critical)
    tasks = [{
        "id": 99,
        "title": "Urgent Exam",
        "course": "MATH301",
        "deadline": "2026-11-02 10:00",
        "effort": 8.0,
        "weight": 30.0,
        "days_left": 1.0,
        "priority_level": "Critical",
        "status": "pending"
    }]
    conflicts = [{
        "id": "C1",
        "conflict_type": "WORKLOAD_OVERLOAD",
        "explanation": "High workload before exam",
        "suggested_resolution": "Study early"
    }]

    res_status = automation.check_and_trigger_automations(
        tasks, conflicts, trigger_name="TEST_RUNNER", db_path=test_db
    )
    assert "SUCCESS" in res_status

    # Verify log in DB
    logs = db.get_automation_logs(db_path=test_db)
    assert len(logs) >= 1
    assert logs[0]["status"] == "SUCCESS"
    assert "48 hours" in logs[0]["condition_matched"] or "Critical" in logs[0]["condition_matched"]


def test_calendar_ics_generation(tmp_path):
    ics_file = str(tmp_path / "calendar.ics")
    tasks = [
        {"id": 1, "title": "Lab 1", "course": "CS101", "deadline": "2026-11-05 17:00", "effort": 3.0, "weight": 10.0, "priority_level": "High", "status": "pending"}
    ]
    path = generate_ics_calendar(tasks, ics_file)
    assert os.path.exists(path)
    with open(path, "r") as f:
        content = f.read()
    assert "BEGIN:VCALENDAR" in content
    assert "SUMMARY:[CS101] Lab 1" in content
    assert "END:VCALENDAR" in content

