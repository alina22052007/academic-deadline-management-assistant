"""Unit tests for deterministic priority scoring engine."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from scoring import (
    calculate_days_left,
    compute_urgency_score,
    compute_effort_pressure_score,
    compute_weight_score,
    compute_difficulty_score,
    get_priority_level,
    score_task,
    score_and_rank_tasks
)


def test_calculate_days_left():
    ref = datetime(2026, 11, 1, 12, 0)
    dl = datetime(2026, 11, 3, 12, 0)
    assert calculate_days_left(dl, ref) == pytest.approx(2.0, 0.01)

    dl_past = datetime(2026, 10, 31, 12, 0)
    assert calculate_days_left(dl_past, ref) == pytest.approx(-1.0, 0.01)


def test_urgency_score_scale():
    # Overdue
    assert compute_urgency_score(-0.5) == 100.0
    # Due in 12 hours (0.5 days)
    u_24h = compute_urgency_score(0.5)
    assert 90.0 <= u_24h <= 100.0
    # Due in 2 days
    u_2d = compute_urgency_score(2.0)
    assert 70.0 <= u_2d <= 90.0
    # Due in 5 days
    u_5d = compute_urgency_score(5.0)
    assert 40.0 <= u_5d <= 70.0
    # Due in 20 days
    u_20d = compute_urgency_score(20.0)
    assert u_20d <= 20.0


def test_effort_pressure():
    # 20 hours with 4 hrs/day over 2 days = 8 hrs capacity -> ratio = 2.5 (overload)
    ep = compute_effort_pressure_score(effort_hours=20.0, days_left=2.0, daily_capacity=4.0)
    assert ep >= 75.0

    # 2 hours with 4 hrs/day over 5 days = 20 hrs capacity -> ratio = 0.1 (low pressure)
    ep_low = compute_effort_pressure_score(effort_hours=2.0, days_left=5.0, daily_capacity=4.0)
    assert ep_low < 35.0


def test_weight_and_difficulty():
    assert compute_weight_score(15.0) == 15.0
    assert compute_weight_score(120.0) == 100.0
    assert compute_weight_score(-10.0) == 0.0

    assert compute_difficulty_score(1) == 20.0
    assert compute_difficulty_score(3) == 60.0
    assert compute_difficulty_score(5) == 100.0


def test_priority_levels():
    assert get_priority_level(85.0) == "Critical"
    assert get_priority_level(65.0) == "High"
    assert get_priority_level(45.0) == "Medium"
    assert get_priority_level(25.0) == "Low"


def test_score_and_rank_tasks():
    ref = datetime(2026, 11, 1, 10, 0)
    tasks = [
        {"id": 1, "title": "Urgent Exam", "course": "CS101", "deadline": "2026-11-02 10:00", "effort": 6.0, "weight": 30.0, "difficulty": 5, "status": "pending"},
        {"id": 2, "title": "Casual Reading", "course": "ENG101", "deadline": "2026-11-20 10:00", "effort": 2.0, "weight": 5.0, "difficulty": 1, "status": "pending"},
        {"id": 3, "title": "Completed Lab", "course": "CS102", "deadline": "2026-11-01 18:00", "effort": 3.0, "weight": 10.0, "difficulty": 2, "status": "completed"}
    ]
    ranked = score_and_rank_tasks(tasks, daily_capacity=4.0, reference_date=ref)
    assert ranked[0]["id"] == 1
    assert ranked[0]["rank"] == 1
    assert ranked[0]["priority_level"] in ("Critical", "High")

    # Completed task must be at bottom
    assert ranked[-1]["id"] == 3
    assert ranked[-1]["rank"] == 3

