"""Unit tests for algorithmic conflict detector."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from conflicts import detect_conflicts, annotate_tasks_with_conflicts


def test_detect_same_day_clash():
    ref = datetime(2026, 11, 1, 9, 0)
    tasks = [
        {"id": 10, "title": "Math Assignment", "course": "MATH", "deadline": "2026-11-04 14:00", "effort": 3.0, "status": "pending"},
        {"id": 11, "title": "Physics Quiz", "course": "PHYS", "deadline": "2026-11-04 14:00", "effort": 2.0, "status": "pending"},
    ]
    conflicts = detect_conflicts(tasks, reference_date=ref)
    assert len(conflicts) >= 1
    types = [c["conflict_type"] for c in conflicts]
    assert "SAME_DAY_CLASH" in types

    clash = [c for c in conflicts if c["conflict_type"] == "SAME_DAY_CLASH"][0]
    assert 10 in clash["task_ids"] and 11 in clash["task_ids"]
    assert clash["severity"] == "CRITICAL"  # exact same hour


def test_detect_workload_overload():
    ref = datetime(2026, 11, 1, 9, 0)
    # 20 hours of work in 2 days (Nov 3 9:00 is 2 days away) with 4 hrs/day capacity = 8 hrs max
    tasks = [
        {"id": 20, "title": "Massive Paper", "course": "HIST", "deadline": "2026-11-03 09:00", "effort": 20.0, "status": "pending"}
    ]
    conflicts = detect_conflicts(tasks, daily_capacity=4.0, reference_date=ref)
    types = [c["conflict_type"] for c in conflicts]
    assert "WORKLOAD_OVERLOAD" in types
    overload = [c for c in conflicts if c["conflict_type"] == "WORKLOAD_OVERLOAD"][0]
    assert overload["severity"] == "CRITICAL"


def test_detect_cluster_conflicts():
    ref = datetime(2026, 11, 1, 9, 0)
    # 3 deadlines within 36 hours
    tasks = [
        {"id": 31, "title": "Exam 1", "course": "CS1", "deadline": "2026-11-05 10:00", "effort": 2.0, "status": "pending"},
        {"id": 32, "title": "Exam 2", "course": "CS2", "deadline": "2026-11-05 18:00", "effort": 2.0, "status": "pending"},
        {"id": 33, "title": "Exam 3", "course": "CS3", "deadline": "2026-11-06 14:00", "effort": 2.0, "status": "pending"},
    ]
    conflicts = detect_conflicts(tasks, reference_date=ref)
    types = [c["conflict_type"] for c in conflicts]
    assert "CLUSTER_CONFLICT" in types


def test_detect_overdue_tasks():
    ref = datetime(2026, 11, 1, 9, 0)
    tasks = [
        {"id": 40, "title": "Old Essay", "course": "LIT", "deadline": "2026-10-30 23:59", "effort": 4.0, "status": "pending"},
        {"id": 41, "title": "Done Old Essay", "course": "LIT", "deadline": "2026-10-30 23:59", "effort": 4.0, "status": "completed"}
    ]
    conflicts = detect_conflicts(tasks, reference_date=ref)
    types = [c["conflict_type"] for c in conflicts]
    assert "OVERDUE_UNFINISHED" in types
    # Completed task should NOT trigger overdue conflict
    overdue = [c for c in conflicts if c["conflict_type"] == "OVERDUE_UNFINISHED"][0]
    assert 40 in overdue["task_ids"]
    assert 41 not in overdue["task_ids"]


def test_annotate_tasks():
    tasks = [{"id": 1, "has_conflict": False}, {"id": 2, "has_conflict": False}]
    conflicts = [{"id": "C1", "task_ids": [1]}]
    annotated = annotate_tasks_with_conflicts(tasks, conflicts)
    assert annotated[0]["has_conflict"] is True
    assert annotated[1]["has_conflict"] is False

