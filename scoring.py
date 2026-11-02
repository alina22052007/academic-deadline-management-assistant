"""Deterministic Priority Scoring Engine for Academic Tasks.
Explainable, mathematical multi-factor scoring normalized to 0-100.
Formula:
  Score = 0.40 * Urgency + 0.25 * Weight + 0.20 * Effort_Pressure + 0.15 * Difficulty
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from dateutil import parser as date_parser


def calculate_days_left(deadline: str | datetime, reference_date: Optional[datetime] = None) -> float:
    """Calculate decimal days remaining until deadline relative to reference_date."""
    if reference_date is None:
        reference_date = datetime.now()

    if isinstance(deadline, str):
        try:
            deadline_dt = date_parser.parse(deadline)
        except Exception:
            deadline_dt = datetime.fromisoformat(deadline)
    else:
        deadline_dt = deadline

    delta = deadline_dt - reference_date
    return delta.total_seconds() / 86400.0


def compute_urgency_score(days_left: float) -> float:
    """Urgency score from 0 to 100 using inverse/exponential urgency scale.
    - Overdue (< 0 days): 100
    - Due in <= 24 hours (<= 1 day): 90 - 100
    - Due in 1-3 days: 70 - 90
    - Due in 3-7 days: 40 - 70
    - Due in 7-14 days: 20 - 40
    - Due > 14 days: < 20
    """
    if days_left < 0:
        return 100.0
    elif days_left <= 1.0:
        return 90.0 + (1.0 - max(0.0, days_left)) * 10.0
    elif days_left <= 3.0:
        return 70.0 + ((3.0 - days_left) / 2.0) * 20.0
    elif days_left <= 7.0:
        return 40.0 + ((7.0 - days_left) / 4.0) * 30.0
    elif days_left <= 14.0:
        return 20.0 + ((14.0 - days_left) / 7.0) * 20.0
    else:
        return max(5.0, 20.0 / (1.0 + (days_left - 14.0) * 0.1))


def compute_effort_pressure_score(effort_hours: float, days_left: float, daily_capacity: float = 4.0) -> float:
    """Effort pressure score from 0 to 100.
    ratio = effort / max(days_left * daily_capacity, 1)
    """
    if days_left < 0:
        return 100.0

    available_capacity = max(days_left * daily_capacity, 1.0)
    ratio = float(effort_hours) / available_capacity

    if ratio >= 1.0:
        # Overload territory
        return min(100.0, 75.0 + 25.0 * min(ratio - 1.0, 1.5) / 1.5)
    else:
        return max(0.0, ratio * 75.0)


def compute_weight_score(weight: float) -> float:
    """Course weight score normalized from 0 to 100."""
    return min(100.0, max(0.0, float(weight)))


def compute_difficulty_score(difficulty: int) -> float:
    """Difficulty score (1 to 5) mapped to 20 - 100."""
    clamped_diff = max(1, min(5, int(difficulty)))
    return (clamped_diff / 5.0) * 100.0


def get_priority_level(score: float) -> str:
    """Determine priority level based on rubric thresholds:
    >= 75: Critical
    55 - 74.9: High
    35 - 54.9: Medium
    < 35: Low
    """
    if score >= 75.0:
        return "Critical"
    elif score >= 55.0:
        return "High"
    elif score >= 35.0:
        return "Medium"
    else:
        return "Low"


def score_task(
    task: Dict[str, Any],
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Calculate deterministic scores and priority level for a single task dictionary."""
    if reference_date is None:
        reference_date = datetime.now()

    days_left = calculate_days_left(task["deadline"], reference_date)
    status = task.get("status", "pending").lower()

    if status == "completed":
        return {
            "task_id": task.get("id"),
            "days_left": round(days_left, 2),
            "urgency_score": 0.0,
            "weight_score": float(task.get("weight", 0.0)),
            "effort_pressure_score": 0.0,
            "difficulty_score": compute_difficulty_score(task.get("difficulty", 3)),
            "priority_score": 0.0,
            "priority_level": "Low",
            "is_completed": True
        }

    urgency = compute_urgency_score(days_left)
    weight_score = compute_weight_score(task.get("weight", 10.0))
    effort_pressure = compute_effort_pressure_score(
        task.get("effort", 2.0),
        days_left,
        daily_capacity
    )
    difficulty_score = compute_difficulty_score(task.get("difficulty", 3))

    # Strict multi-factor weighted sum
    composite = (
        0.40 * urgency +
        0.25 * weight_score +
        0.20 * effort_pressure +
        0.15 * difficulty_score
    )

    score = round(min(100.0, max(0.0, composite)), 1)
    level = get_priority_level(score)

    # Human-in-the-loop override consideration
    override = task.get("user_priority_override")
    if override in ["Critical", "High", "Medium", "Low"]:
        level = override

    tid = task.get("id") if task.get("id") is not None else (task.get("task_id") if task.get("task_id") is not None else task.get("title"))

    return {
        "task_id": tid,
        "days_left": round(days_left, 2),
        "urgency_score": round(urgency, 1),
        "weight_score": round(weight_score, 1),
        "effort_pressure_score": round(effort_pressure, 1),
        "difficulty_score": round(difficulty_score, 1),
        "priority_score": score,
        "priority_level": level,
        "is_completed": False
    }


def score_and_rank_tasks(
    tasks: List[Dict[str, Any]],
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Score all tasks and assign rankings (1 = highest priority)."""
    scored = []
    for idx, t in enumerate(tasks, start=1):
        item_scores = score_task(t, daily_capacity=daily_capacity, reference_date=reference_date)
        merged = {**t, **item_scores}
        if merged.get("id") is None:
            merged["id"] = merged.get("task_id") if merged.get("task_id") is not None else idx
        scored.append(merged)

    # Sort descending by priority_score, then ascending by days_left, then descending by effort
    def sort_key(x):
        # Completed tasks go to the bottom
        if x.get("status", "").lower() == "completed":
            return (-1, 0, 9999)
        return (x["priority_score"], -x["days_left"], x.get("effort", 0))

    scored.sort(key=sort_key, reverse=True)

    for rank, item in enumerate(scored, start=1):
        item["rank"] = rank

    return scored

