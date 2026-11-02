"""Six-Stage Processing Pipeline for Academic Deadline Management Assistant.
Stage 1 - Intake & Extraction
Stage 2 - Priority Scoring (Deterministic)
Stage 3 - Conflict Detection (Algorithmic)
Stage 4 - AI Reasoning & Study Planning
Stage 5 - Rubric Verification & Self-Correction / Fallback
Stage 6 - Persistence & Trigger-Action Automation
"""

from __future__ import annotations
import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from scoring import score_and_rank_tasks
from conflicts import detect_conflicts, annotate_tasks_with_conflicts
from validator import evaluate_ai_response, validate_task_input
from llm_client import (
    extract_tasks_from_text,
    generate_ai_reasoning_and_plan,
    generate_fallback_reasoning_and_plan
)
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Pipeline")

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def load_prompt_file(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


@dataclass
class PipelineResult:
    tasks: List[Dict[str, Any]]
    scored_tasks: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    ai_output: Dict[str, Any]
    evaluation: Dict[str, Any]
    mode: str  # 'gemini' or 'fallback'
    model_name: str
    latency_ms: float
    automation_status: str
    stage_logs: List[str] = field(default_factory=list)


# =====================================================================
# STAGE 1 - INTAKE & EXTRACTION
# =====================================================================

def stage_1_intake_and_extraction(
    raw_input: Any,
    input_type: str = "db",  # "db", "form", "freetext", "csv"
    reference_date: Optional[datetime] = None,
    db_path: str = db.DB_PATH
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Stage 1: Ingest and validate tasks from DB, free-text, CSV, or form."""
    if reference_date is None:
        reference_date = datetime.now()

    logs = []
    tasks: List[Dict[str, Any]] = []

    if input_type == "db":
        tasks = db.get_all_tasks(db_path=db_path)
        logs.append(f"Stage 1 [DB]: Loaded {len(tasks)} tasks from database.")

    elif input_type == "freetext":
        extracted, mode, note = extract_tasks_from_text(str(raw_input), reference_date)
        tasks = extracted
        logs.append(f"Stage 1 [FreeText]: Extracted {len(tasks)} tasks via {mode}. ({note})")

    elif input_type == "form":
        # Form dict
        is_val, errs, cleaned = validate_task_input(
            title=raw_input.get("title", ""),
            course=raw_input.get("course", ""),
            deadline_str=raw_input.get("deadline", ""),
            effort=raw_input.get("effort", 3.0),
            weight=raw_input.get("weight", 10.0),
            difficulty=raw_input.get("difficulty", 3),
            reference_date=reference_date
        )
        if is_val:
            tasks = [cleaned]
            logs.append(f"Stage 1 [Form]: Validated 1 task '{cleaned.get('title')}'.")
        else:
            logs.append(f"Stage 1 [Form Error]: {errs}")

    elif input_type == "list":
        tasks = list(raw_input)
        logs.append(f"Stage 1 [List]: Ingested {len(tasks)} raw task objects.")

    return tasks, logs


# =====================================================================
# STAGE 2 - PRIORITY SCORING (Deterministic)
# =====================================================================

def stage_2_priority_scoring(
    tasks: List[Dict[str, Any]],
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Stage 2: Deterministic, explainable multi-factor scoring formula."""
    if reference_date is None:
        reference_date = datetime.now()

    scored = score_and_rank_tasks(tasks, daily_capacity=daily_capacity, reference_date=reference_date)
    critical_count = sum(1 for s in scored if s.get("priority_level") == "Critical")
    logs = [
        f"Stage 2 [Scoring]: Evaluated {len(scored)} tasks. "
        f"Top score: {scored[0]['priority_score'] if scored else 0.0} (Critical: {critical_count})."
    ]
    return scored, logs


# =====================================================================
# STAGE 3 - CONFLICT DETECTION (Algorithmic)
# =====================================================================

def stage_3_conflict_detection(
    scored_tasks: List[Dict[str, Any]],
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Stage 3: Algorithmic conflict detector (clashes, overload, clusters, overdue)."""
    if reference_date is None:
        reference_date = datetime.now()

    conflicts = detect_conflicts(scored_tasks, daily_capacity=daily_capacity, reference_date=reference_date)
    annotated = annotate_tasks_with_conflicts(scored_tasks, conflicts)
    logs = [
        f"Stage 3 [Conflicts]: Identified {len(conflicts)} deadline conflicts across {len(annotated)} tasks."
    ]
    return annotated, conflicts, logs


# =====================================================================
# STAGE 4 - AI REASONING & PLANNING
# =====================================================================

def stage_4_ai_reasoning(
    scored_tasks: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None,
    prompt_version: str = "v3"
) -> Tuple[Dict[str, Any], str, float, str, str, List[str]]:
    """Stage 4: Synthesize rationales, resolutions, and 7-day plan via Gemini or fallback."""
    if reference_date is None:
        reference_date = datetime.now()

    filename = f"prompt_{prompt_version}_final.txt" if prompt_version == "v3" else (
        "prompt_v2_structured.txt" if prompt_version == "v2" else "prompt_v1_basic.txt"
    )
    prompt_template = load_prompt_file(filename)
    if not prompt_template:
        prompt_template = load_prompt_file("prompt_v3_final.txt")

    ai_dict, raw_text, latency, mode, model = generate_ai_reasoning_and_plan(
        prompt_template=prompt_template,
        scored_tasks=scored_tasks,
        conflicts=conflicts,
        daily_capacity=daily_capacity,
        reference_date=reference_date,
        prompt_version=prompt_version
    )

    logs = [
        f"Stage 4 [Reasoning]: Completed via {mode.upper()} ({model}) in {latency}ms."
    ]
    return ai_dict, raw_text, latency, mode, model, logs


# =====================================================================
# STAGE 5 - VERIFICATION & AUTO-CORRECTION
# =====================================================================

def stage_5_verification(
    ai_dict: Dict[str, Any],
    raw_text: str,
    scored_tasks: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None
) -> Tuple[Dict[str, Any], Dict[str, Any], str, List[str]]:
    """Stage 5: Evaluate AI output against 10-point rubric; fall back to deterministic if failed."""
    if reference_date is None:
        reference_date = datetime.now()

    evaluation = evaluate_ai_response(
        raw_response=raw_text,
        input_tasks=scored_tasks,
        algorithmic_conflicts=conflicts,
        reference_rankings=scored_tasks
    )

    logs = [
        f"Stage 5 [Verification]: Rubric Score {evaluation['total_score']}/10. Passed: {evaluation['passed']}."
    ]

    final_output = ai_dict
    output_mode = "ai_verified"

    if not evaluation["passed"]:
        logs.append("Stage 5 [Auto-Correct]: Verification threshold not reached (<8/10). Engaging deterministic fallback.")
        final_output = generate_fallback_reasoning_and_plan(
            scored_tasks, conflicts, daily_capacity, reference_date
        )
        output_mode = "fallback_engaged"
        # Re-score fallback to verify 10/10 compliance
        evaluation = evaluate_ai_response(
            raw_response=json.dumps(final_output),
            input_tasks=scored_tasks,
            algorithmic_conflicts=conflicts,
            reference_rankings=scored_tasks
        )

    # Attach rationales back to scored tasks
    rationale_map = {r.get("task_id"): r.get("rationale") for r in final_output.get("task_rationales", [])}
    for t in scored_tasks:
        tid = t.get("task_id") or t.get("id")
        t["ai_rationale"] = rationale_map.get(tid, "Prioritized according to urgency and grade impact.")

    return final_output, evaluation, output_mode, logs


# =====================================================================
# STAGE 6 - PERSISTENCE & AUTOMATION
# =====================================================================

def stage_6_persist_and_automate(
    scored_tasks: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    ai_run_metadata: Dict[str, Any],
    evaluation: Dict[str, Any],
    db_path: str = db.DB_PATH
) -> Tuple[str, List[str]]:
    """Stage 6: Save state to SQLite and trigger automated notification workflows."""
    logs = []
    try:
        # Save scored tasks and conflicts
        db.save_scored_tasks(scored_tasks, db_path=db_path)
        db.save_conflicts(conflicts, db_path=db_path)
        logs.append(f"Stage 6 [DB]: Persisted {len(scored_tasks)} scored tasks and {len(conflicts)} conflicts.")

        # Log AI Run
        run_id = db.log_ai_run(
            prompt_version=ai_run_metadata.get("prompt_version", "v3"),
            input_payload=ai_run_metadata.get("input_payload", ""),
            raw_output=ai_run_metadata.get("raw_output", ""),
            parsed_output=json.dumps(ai_run_metadata.get("parsed_output", {})),
            latency_ms=ai_run_metadata.get("latency_ms", 0.0),
            model=ai_run_metadata.get("model", "unknown"),
            mode=ai_run_metadata.get("mode", "fallback"),
            db_path=db_path
        )

        # Log Evaluation
        db.log_evaluation(
            prompt_version=ai_run_metadata.get("prompt_version", "v3"),
            scores=evaluation,
            ai_run_id=run_id,
            feedback_notes="; ".join(evaluation.get("feedback_notes", [])),
            db_path=db_path
        )
        logs.append(f"Stage 6 [DB]: Logged AI run #{run_id} and evaluation score {evaluation.get('total_score')}/10.")

        # Import and execute automation workflow
        from automation import check_and_trigger_automations
        auto_res = check_and_trigger_automations(scored_tasks, conflicts, db_path=db_path)
        logs.append(f"Stage 6 [Automation]: {auto_res}")
        return auto_res, logs

    except Exception as e:
        err = f"Stage 6 [Error]: {str(e)}"
        logs.append(err)
        return err, logs


# =====================================================================
# FULL PIPELINE RUNNER
# =====================================================================

def run_pipeline(
    tasks: Optional[List[Dict[str, Any]]] = None,
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None,
    prompt_version: str = "v3",
    db_path: str = db.DB_PATH
) -> PipelineResult:
    """Execute all six stages sequentially with comprehensive logging."""
    all_logs: List[str] = []

    # Stage 1
    input_tasks, s1_logs = stage_1_intake_and_extraction(
        raw_input=tasks if tasks is not None else "db",
        input_type="list" if tasks is not None else "db",
        reference_date=reference_date,
        db_path=db_path
    )
    all_logs.extend(s1_logs)

    # Stage 2
    scored_tasks, s2_logs = stage_2_priority_scoring(
        input_tasks, daily_capacity=daily_capacity, reference_date=reference_date
    )
    all_logs.extend(s2_logs)

    # Stage 3
    annotated_tasks, conflicts, s3_logs = stage_3_conflict_detection(
        scored_tasks, daily_capacity=daily_capacity, reference_date=reference_date
    )
    all_logs.extend(s3_logs)

    # Stage 4
    ai_dict, raw_text, latency, mode, model, s4_logs = stage_4_ai_reasoning(
        annotated_tasks, conflicts, daily_capacity=daily_capacity,
        reference_date=reference_date, prompt_version=prompt_version
    )
    all_logs.extend(s4_logs)

    # Stage 5
    final_output, evaluation, out_mode, s5_logs = stage_5_verification(
        ai_dict, raw_text, annotated_tasks, conflicts,
        daily_capacity=daily_capacity, reference_date=reference_date
    )
    all_logs.extend(s5_logs)

    # Stage 6
    ai_meta = {
        "prompt_version": prompt_version,
        "input_payload": json.dumps({"tasks_count": len(annotated_tasks), "conflicts_count": len(conflicts)}),
        "raw_output": raw_text,
        "parsed_output": final_output,
        "latency_ms": latency,
        "model": model,
        "mode": mode
    }
    auto_status, s6_logs = stage_6_persist_and_automate(
        annotated_tasks, conflicts, ai_meta, evaluation, db_path=db_path
    )
    all_logs.extend(s6_logs)

    return PipelineResult(
        tasks=input_tasks,
        scored_tasks=annotated_tasks,
        conflicts=conflicts,
        ai_output=final_output,
        evaluation=evaluation,
        mode=mode,
        model_name=model,
        latency_ms=latency,
        automation_status=auto_status,
        stage_logs=all_logs
    )

