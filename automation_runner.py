#!/usr/bin/env python3
"""Standalone Automation Runner CLI for Cron / Task Scheduler.
Usage:
    python automation_runner.py [--capacity 4.0] [--reference-date YYYY-MM-DDTHH:MM]
"""

from __future__ import annotations
import argparse
import sys
from datetime import datetime
from dotenv import load_dotenv

import db
from scoring import score_and_rank_tasks
from conflicts import detect_conflicts, annotate_tasks_with_conflicts
from automation import check_and_trigger_automations

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Academic Deadline Automation Runner")
    parser.add_argument("--capacity", type=float, default=4.0, help="Daily study hours capacity (default: 4.0)")
    parser.add_argument("--reference-date", type=str, default=None, help="Reference date ISO string (optional)")
    args = parser.parse_args()

    ref_date = datetime.fromisoformat(args.reference_date) if args.reference_date else datetime.now()

    print(f"[{datetime.now().isoformat()}] Starting Scheduled Automation Check...")
    print(f"Daily Capacity: {args.capacity} hrs/day | Reference Date: {ref_date.strftime('%Y-%m-%d %H:%M')}")

    db.init_db()
    tasks = db.get_all_tasks()
    if not tasks:
        print("No tasks found in database. Exiting.")
        sys.exit(0)

    scored = score_and_rank_tasks(tasks, daily_capacity=args.capacity, reference_date=ref_date)
    conflicts = detect_conflicts(scored, daily_capacity=args.capacity, reference_date=ref_date)
    annotated = annotate_tasks_with_conflicts(scored, conflicts)

    db.save_scored_tasks(annotated)
    db.save_conflicts(conflicts)

    status_result = check_and_trigger_automations(
        annotated,
        conflicts,
        trigger_name="CLI_CRON_SCHEDULER"
    )

    print(f"Automation Execution Result: {status_result}")
    print(f"[{datetime.now().isoformat()}] Check Complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()

