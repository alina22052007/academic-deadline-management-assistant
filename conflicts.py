"""Algorithmic Conflict Detection Engine for Academic Deadlines.
Detects:
  (a) Same-day and same-hour deadline clashes
  (b) Workload overload via greedy backward capacity analysis
  (c) Cluster conflicts (3+ deadlines within 48 hours)
  (d) Overdue unfinished tasks
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from dateutil import parser as date_parser


def parse_datetime(dt_str: str | datetime) -> datetime:
    if isinstance(dt_str, datetime):
        return dt_str
    try:
        return date_parser.parse(dt_str)
    except Exception:
        return datetime.fromisoformat(dt_str)


def detect_conflicts(
    tasks: List[Dict[str, Any]],
    daily_capacity: float = 4.0,
    reference_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Inspect all active (non-completed) tasks and return structured conflict items."""
    if reference_date is None:
        reference_date = datetime.now()

    conflicts: List[Dict[str, Any]] = []
    conflict_counter = 1

    # Filter out completed tasks
    active_tasks = [t for t in tasks if t.get("status", "pending").lower() != "completed"]
    if not active_tasks:
        return conflicts

    # Parse deadlines and compute days_left
    parsed_tasks = []
    for t in active_tasks:
        try:
            dt = parse_datetime(t["deadline"])
            days_left = (dt - reference_date).total_seconds() / 86400.0
            parsed_tasks.append({**t, "_dt": dt, "_days_left": days_left})
        except Exception:
            continue

    # -------------------------------------------------------------
    # (d) OVERDUE UNFINISHED TASKS
    # -------------------------------------------------------------
    for t in parsed_tasks:
        if t["_days_left"] < 0:
            conflicts.append({
                "id": f"C{conflict_counter}",
                "conflict_type": "OVERDUE_UNFINISHED",
                "severity": "CRITICAL",
                "task_ids": [t.get("id") or t.get("task_id")],
                "explanation": f"Task '{t.get('title')}' ({t.get('course')}) is overdue since {t['_dt'].strftime('%Y-%m-%d %H:%M')}.",
                "suggested_resolution": "Submit immediately or email the instructor to request grace period / penalty mitigation."
            })
            conflict_counter += 1

    # Upcoming active tasks only for schedule conflicts
    upcoming_tasks = [t for t in parsed_tasks if t["_days_left"] >= 0]
    upcoming_tasks.sort(key=lambda x: x["_dt"])

    # -------------------------------------------------------------
    # (a) SAME-DAY / SAME-HOUR CLASHES
    # -------------------------------------------------------------
    # Group tasks by date string (YYYY-MM-DD)
    date_groups: Dict[str, List[Dict[str, Any]]] = {}
    for t in upcoming_tasks:
        day_key = t["_dt"].strftime("%Y-%m-%d")
        date_groups.setdefault(day_key, []).append(t)

    for day_key, group in date_groups.items():
        if len(group) >= 2:
            task_ids = [t.get("id") or t.get("task_id") or t.get("title") for t in group]
            titles = [f"'{t.get('title')}'" for t in group]
            exact_hour_match = len(set(t["_dt"].strftime("%Y-%m-%d %H") for t in group)) < len(group)

            severity = "CRITICAL" if exact_hour_match else "HIGH"
            timing_note = "exact same hour" if exact_hour_match else "same day"
            conflicts.append({
                "id": f"C{conflict_counter}",
                "conflict_type": "SAME_DAY_CLASH",
                "severity": severity,
                "task_ids": task_ids,
                "explanation": f"{len(group)} deliverables due on {timing_note} ({day_key}): {', '.join(titles)}.",
                "suggested_resolution": f"Complete {titles[0]} at least 24 hours in advance to avoid last-minute bottleneck on {day_key}."
            })
            conflict_counter += 1

    # -------------------------------------------------------------
    # (c) CLUSTER CONFLICTS (3+ deadlines within 48 hours)
    # -------------------------------------------------------------
    # Sliding window of 48 hours (2.0 days)
    reported_cluster_signatures = set()
    for i in range(len(upcoming_tasks)):
        cluster = [upcoming_tasks[i]]
        for j in range(i + 1, len(upcoming_tasks)):
            delta_hours = (upcoming_tasks[j]["_dt"] - upcoming_tasks[i]["_dt"]).total_seconds() / 3600.0
            if delta_hours <= 48.0:
                cluster.append(upcoming_tasks[j])
            else:
                break

        if len(cluster) >= 3:
            cluster_ids = tuple(sorted([str(t.get("id") or t.get("task_id") or t.get("title")) for t in cluster]))
            if cluster_ids not in reported_cluster_signatures:
                reported_cluster_signatures.add(cluster_ids)
                titles = [t.get("title") for t in cluster]
                conflicts.append({
                    "id": f"C{conflict_counter}",
                    "conflict_type": "CLUSTER_CONFLICT",
                    "severity": "HIGH",
                    "task_ids": list(cluster_ids),
                    "explanation": f"High density cluster: {len(cluster)} deadlines within 48 hours ({', '.join(titles)}).",
                    "suggested_resolution": "Stagger preparation across the preceding week; draft deliverables early to leave exam days clear."
                })
                conflict_counter += 1

    # -------------------------------------------------------------
    # (b) WORKLOAD OVERLOAD (Backward cumulative capacity check)
    # -------------------------------------------------------------
    # For every task, calculate cumulative effort required up to its deadline
    # vs available capacity (days_left * daily_capacity)
    cumulative_effort = 0.0
    for t in upcoming_tasks:
        effort = float(t.get("effort", 0.0))
        cumulative_effort += effort
        days_avail = max(t["_days_left"], 0.25)
        capacity_avail = days_avail * daily_capacity

        # Check individual overload or cumulative overload
        is_single_overload = effort > capacity_avail
        is_cumul_overload = cumulative_effort > capacity_avail

        if is_single_overload or (is_cumul_overload and effort >= daily_capacity):
            task_id = t.get("id") or t.get("task_id") or t.get("title")
            # Avoid duplicate overload logging for the same single task
            existing_overloads = [c for c in conflicts if c["conflict_type"] == "WORKLOAD_OVERLOAD" and task_id in c["task_ids"]]
            if not existing_overloads:
                deficit = round((cumulative_effort if is_cumul_overload else effort) - capacity_avail, 1)
                conflicts.append({
                    "id": f"C{conflict_counter}",
                    "conflict_type": "WORKLOAD_OVERLOAD",
                    "severity": "CRITICAL",
                    "task_ids": [task_id],
                    "explanation": f"Task '{t.get('title')}' requires {effort:.1f}h, exceeding available capacity ({capacity_avail:.1f}h across {days_avail:.1f} days). Capacity deficit: {deficit:.1f}h.",
                    "suggested_resolution": "Front-load work into preceding days immediately, divide task into milestones, or seek an extension."
                })
                conflict_counter += 1

    return conflicts


def annotate_tasks_with_conflicts(
    scored_tasks: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Mark has_conflict = True on any scored task implicated in one or more conflicts."""
    conflict_task_ids = set()
    for c in conflicts:
        for tid in c.get("task_ids", []):
            if tid is not None:
                conflict_task_ids.add(tid)

    for item in scored_tasks:
        tid = item.get("task_id") or item.get("id")
        item["has_conflict"] = tid in conflict_task_ids

    return scored_tasks

