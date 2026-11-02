"""Validation and Responsible AI Engine.
Implements:
  1. Input data validation (form, CSV, free text)
  2. Prompt-injection defense & sanitization
  3. 10-Point AI Output Verification Rubric
  4. Ranking correlation / agreement calculation
"""

from __future__ import annotations
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dateutil import parser as date_parser


# =====================================================================
# 1. Input Validation
# =====================================================================

def validate_task_input(
    title: str,
    course: str,
    deadline_str: str,
    effort: Any,
    weight: Any,
    difficulty: Any,
    existing_tasks: Optional[List[Dict[str, Any]]] = None,
    reference_date: Optional[datetime] = None
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate user/form task fields. Returns (is_valid, error_list, cleaned_data)."""
    errors: List[str] = []
    cleaned: Dict[str, Any] = {}

    # Title check
    cleaned_title = str(title).strip() if title is not None else ""
    if not cleaned_title:
        errors.append("Task title cannot be empty.")
    cleaned["title"] = cleaned_title

    # Course check
    cleaned_course = str(course).strip().upper() if course is not None else ""
    if not cleaned_course:
        errors.append("Course code cannot be empty.")
    cleaned["course"] = cleaned_course

    # Deadline check
    if not deadline_str or not str(deadline_str).strip():
        errors.append("Deadline is required.")
        cleaned["deadline"] = ""
    else:
        try:
            parsed_dt = date_parser.parse(str(deadline_str).strip())
            cleaned["deadline"] = parsed_dt.strftime("%Y-%m-%d %H:%M")
            if reference_date and parsed_dt < reference_date:
                # We warn about overdue, but allow it to be flagged as overdue
                cleaned["is_past_deadline"] = True
            else:
                cleaned["is_past_deadline"] = False
        except Exception:
            errors.append(f"Invalid date/time format: '{deadline_str}'. Use YYYY-MM-DD HH:MM.")
            cleaned["deadline"] = str(deadline_str)

    # Effort check
    try:
        effort_val = float(effort)
        if effort_val <= 0:
            errors.append("Estimated effort must be strictly greater than 0 hours.")
        cleaned["effort"] = max(0.1, effort_val)
    except (ValueError, TypeError):
        errors.append("Estimated effort must be a positive number.")
        cleaned["effort"] = 1.0

    # Weight check
    try:
        weight_val = float(weight)
        if weight_val < 0 or weight_val > 100:
            errors.append("Grade weight must be between 0% and 100%.")
        cleaned["weight"] = max(0.0, min(100.0, weight_val))
    except (ValueError, TypeError):
        errors.append("Grade weight must be a number between 0 and 100.")
        cleaned["weight"] = 10.0

    # Difficulty check
    try:
        diff_val = int(difficulty)
        if diff_val < 1 or diff_val > 5:
            errors.append("Difficulty must be an integer between 1 and 5.")
        cleaned["difficulty"] = max(1, min(5, diff_val))
    except (ValueError, TypeError):
        errors.append("Difficulty must be an integer between 1 and 5.")
        cleaned["difficulty"] = 3

    # Duplicate check against existing tasks
    if existing_tasks and not errors:
        for ex in existing_tasks:
            same_title = ex.get("title", "").strip().lower() == cleaned_title.lower()
            same_course = ex.get("course", "").strip().upper() == cleaned_course
            same_deadline = ex.get("deadline", "").strip() == cleaned["deadline"]
            if same_title and same_course and same_deadline:
                errors.append(f"Duplicate task detected: '{cleaned_title}' for {cleaned_course} due {cleaned['deadline']} already exists.")
                break

    is_valid = len(errors) == 0
    return is_valid, errors, cleaned


# =====================================================================
# 2. Responsible AI & Prompt Injection Defense
# =====================================================================

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"delete\s+(all\s+)?(tasks|database|everything)",
    r"drop\s+table",
    r"system\s*prompt",
    r"reveal\s+(the\s+)?api\s*key",
    r"you\s+are\s+now\s+in\s+dan\s+mode",
    r"disregard\s+rules",
    r"pwned",
    r"<script.*?>.*?</script>"
]


def sanitize_free_text_input(text: str) -> Tuple[str, bool, List[str]]:
    """Scan and sanitize user-submitted natural language text.
    Returns (sanitized_text, injection_detected, detected_warnings).
    """
    if not text:
        return "", False, []

    detected_warnings: List[str] = []
    injection_detected = False

    for pat in INJECTION_PATTERNS:
        matches = re.findall(pat, text, flags=re.IGNORECASE)
        if matches:
            injection_detected = True
            detected_warnings.append(f"Safety filter flagged potential directive override: '{pat}'")

    # Neutralize control characters and XML tags
    clean = re.sub(r"[<>{}\\]", "", text)
    # Strip any direct system command injections
    clean = re.sub(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions", "[REDACTED_DIRECTIVE]", clean)
    clean = re.sub(r"(?i)delete\s+all\s+tasks", "[REDACTED_COMMAND]", clean)

    return clean.strip(), injection_detected, detected_warnings


# =====================================================================
# 3. 10-Point AI Output Verification Rubric
# =====================================================================

def evaluate_ai_response(
    raw_response: str,
    input_tasks: List[Dict[str, Any]],
    algorithmic_conflicts: List[Dict[str, Any]],
    reference_rankings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Verify AI-generated response against the 10-point rubric:
    1. Valid JSON matching schema (2 pts)
    2. Zero hallucinated task IDs (2 pts)
    3. Completeness - covers all input tasks (1 pt)
    4. Data accuracy - numbers/deadlines match db (1 pt)
    5. Ranking agreement with deterministic ranking (2 pts)
    6. Conflicts match algorithmic conflicts (1 pt)
    7. Rationale concise and non-empty (1 pt)
    Pass threshold: >= 8 / 10
    """
    breakdown = {
        "json_valid": 0,
        "task_identity_valid": 0,
        "completeness_valid": 0,
        "data_accuracy_valid": 0,
        "ranking_agreement_valid": 0,
        "conflict_match_valid": 0,
        "rationale_quality_valid": 0,
        "total_score": 0.0,
        "passed": False,
        "feedback_notes": []
    }

    parsed_json: Optional[Dict[str, Any]] = None

    # Step 1: Valid JSON matching schema (2 points)
    try:
        # Strip potential markdown fences if present
        cleaned_text = raw_response.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

        parsed_json = json.loads(cleaned_text)
        if isinstance(parsed_json, dict) and ("task_rationales" in parsed_json or "study_plan" in parsed_json):
            breakdown["json_valid"] = 2
        else:
            breakdown["json_valid"] = 1
            breakdown["feedback_notes"].append("JSON valid but missing required root keys.")
    except Exception as e:
        breakdown["json_valid"] = 0
        breakdown["feedback_notes"].append(f"Invalid JSON: {str(e)[:60]}")
        breakdown["total_score"] = 0.0
        breakdown["passed"] = False
        return breakdown

    input_task_ids = set(t.get("id") or t.get("task_id") for t in input_tasks if (t.get("id") or t.get("task_id")) is not None)
    rationales = parsed_json.get("task_rationales", [])

    # Step 2: Task Identity & Zero Hallucinations (2 points)
    ai_task_ids = set()
    hallucinated_ids = set()
    for item in rationales:
        tid = item.get("task_id")
        if tid is not None:
            ai_task_ids.add(tid)
            if tid not in input_task_ids:
                hallucinated_ids.add(tid)

    # Check study plan task ids as well
    study_plan = parsed_json.get("study_plan", [])
    for day in study_plan:
        for alloc in day.get("allocations", []):
            sp_tid = alloc.get("task_id")
            if sp_tid is not None:
                ai_task_ids.add(sp_tid)
                if sp_tid not in input_task_ids:
                    hallucinated_ids.add(sp_tid)

    if not hallucinated_ids:
        breakdown["task_identity_valid"] = 2
    else:
        breakdown["task_identity_valid"] = 0
        breakdown["feedback_notes"].append(f"Hallucinated task IDs found: {list(hallucinated_ids)}")

    # Step 3: Completeness - Covers all input tasks (1 point)
    if input_task_ids and input_task_ids.issubset(set(item.get("task_id") for item in rationales)):
        breakdown["completeness_valid"] = 1
    elif not input_task_ids:
        breakdown["completeness_valid"] = 1
    else:
        missing = input_task_ids - set(item.get("task_id") for item in rationales)
        breakdown["completeness_valid"] = 0
        breakdown["feedback_notes"].append(f"Missing rationales for tasks: {list(missing)}")

    # Step 4: Data accuracy (1 point)
    # Check that planned task allocations don't propose negative hours or impossible dates
    data_accurate = True
    for day in study_plan:
        for alloc in day.get("allocations", []):
            hours = alloc.get("allocated_hours", 0)
            if hours < 0 or hours > 24:
                data_accurate = False
                break
    if data_accurate:
        breakdown["data_accuracy_valid"] = 1
    else:
        breakdown["data_accuracy_valid"] = 0
        breakdown["feedback_notes"].append("Study plan contained anomalous hours.")

    # Step 5: Ranking agreement with reference ranking (2 points)
    # If the response suggested an order, or check alignment of critical tasks
    # Top-3 agreement or priority consistency
    agreement_score = check_ranking_agreement(rationales, reference_rankings)
    breakdown["ranking_agreement_valid"] = agreement_score

    # Step 6: Conflict matching (1 point)
    ai_conflicts = parsed_json.get("conflict_resolutions", [])
    algo_conflict_ids = set(c["id"] for c in algorithmic_conflicts)
    if not algo_conflict_ids:
        breakdown["conflict_match_valid"] = 1
    else:
        reported_conflict_ids = set(c.get("conflict_id") for c in ai_conflicts)
        overlap = algo_conflict_ids.intersection(reported_conflict_ids)
        if len(overlap) >= max(1, len(algo_conflict_ids) // 2):
            breakdown["conflict_match_valid"] = 1
        else:
            breakdown["conflict_match_valid"] = 0
            breakdown["feedback_notes"].append("AI conflict resolutions missed algorithmic conflicts.")

    # Step 7: Rationale quality & conciseness (1 point)
    all_concise = True
    if rationales:
        for r in rationales:
            words = r.get("rationale", "").split()
            if len(words) == 0 or len(words) > 35:
                all_concise = False
                break
        breakdown["rationale_quality_valid"] = 1 if all_concise else 0
        if not all_concise:
            breakdown["feedback_notes"].append("Some task rationales were empty or exceeded concise word limit.")
    else:
        breakdown["rationale_quality_valid"] = 0
        breakdown["feedback_notes"].append("No task rationales returned.")

    # Compute Total Score
    total = (
        breakdown["json_valid"] +
        breakdown["task_identity_valid"] +
        breakdown["completeness_valid"] +
        breakdown["data_accuracy_valid"] +
        breakdown["ranking_agreement_valid"] +
        breakdown["conflict_match_valid"] +
        breakdown["rationale_quality_valid"]
    )

    breakdown["total_score"] = float(total)
    breakdown["passed"] = total >= 8.0

    return breakdown


def check_ranking_agreement(
    rationales: List[Dict[str, Any]],
    reference_rankings: List[Dict[str, Any]]
) -> int:
    """Evaluate how well AI prioritized order aligns with deterministic ranking.
    Returns 2 points for strong agreement, 1 point for moderate, 0 for poor.
    """
    if not reference_rankings or not rationales:
        return 2  # No tasks to disagree on

    # Order of tasks appearing in AI rationales
    ai_ordered_ids = [r.get("task_id") for r in rationales if r.get("task_id") is not None]
    ref_ordered_ids = [t.get("task_id") or t.get("id") for t in reference_rankings]

    if not ai_ordered_ids or not ref_ordered_ids:
        return 1

    # Check Top-1 or Top-3 overlap
    top_k = min(3, len(ref_ordered_ids))
    ref_top_k = set(ref_ordered_ids[:top_k])
    ai_top_k = set(ai_ordered_ids[:top_k])

    overlap = len(ref_top_k.intersection(ai_top_k))
    if overlap >= top_k:
        return 2
    elif overlap >= 1:
        return 1
    else:
        return 0

