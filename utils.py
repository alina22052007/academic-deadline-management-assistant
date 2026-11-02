"""Utility functions for Academic Deadline Management Assistant.
Includes iCalendar (.ics) generation, date parsers, and text helpers.
"""

from __future__ import annotations
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dateutil import parser as date_parser


def parse_flexible_deadline(deadline_str: str, reference_date: Optional[datetime] = None) -> str:
    """Parse various natural or standard deadline strings into 'YYYY-MM-DD HH:MM'.
    Handles expressions like 'tomorrow 10am', 'Friday 5pm', 'in 3 days 2pm'.
    """
    if reference_date is None:
        reference_date = datetime.now()

    text = str(deadline_str).strip().lower()

    # Handle 'tomorrow'
    if "tomorrow" in text:
        target_date = reference_date + timedelta(days=1)
        # Check for time component like '10am', '5pm'
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
        if time_match:
            hr = int(time_match.group(1))
            mn = int(time_match.group(2) or 0)
            meridiem = time_match.group(3)
            if meridiem == "pm" and hr < 12:
                hr += 12
            elif meridiem == "am" and hr == 12:
                hr = 0
            target_date = target_date.replace(hour=hr, minute=mn, second=0)
        else:
            target_date = target_date.replace(hour=23, minute=59, second=0)
        return target_date.strftime("%Y-%m-%d %H:%M")

    # Handle 'in X days'
    in_days_match = re.search(r"in\s+(\d+)\s+days?", text)
    if in_days_match:
        days_offset = int(in_days_match.group(1))
        target_date = reference_date + timedelta(days=days_offset)
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
        if time_match:
            hr = int(time_match.group(1))
            mn = int(time_match.group(2) or 0)
            meridiem = time_match.group(3)
            if meridiem == "pm" and hr < 12:
                hr += 12
            elif meridiem == "am" and hr == 12:
                hr = 0
            target_date = target_date.replace(hour=hr, minute=mn, second=0)
        else:
            target_date = target_date.replace(hour=23, minute=59, second=0)
        return target_date.strftime("%Y-%m-%d %H:%M")

    # Handle weekday like 'friday 5pm', 'next tuesday 2pm'
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for idx, day_name in enumerate(weekdays):
        if day_name in text:
            curr_w = reference_date.weekday()
            days_ahead = (idx - curr_w) % 7
            if days_ahead == 0 and "next" in text:
                days_ahead = 7
            elif days_ahead == 0:
                days_ahead = 7  # Assume coming Friday
            target_date = reference_date + timedelta(days=days_ahead)
            time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
            if time_match:
                hr = int(time_match.group(1))
                mn = int(time_match.group(2) or 0)
                meridiem = time_match.group(3)
                if meridiem == "pm" and hr < 12:
                    hr += 12
                elif meridiem == "am" and hr == 12:
                    hr = 0
                target_date = target_date.replace(hour=hr, minute=mn, second=0)
            else:
                target_date = target_date.replace(hour=23, minute=59, second=0)
            return target_date.strftime("%Y-%m-%d %H:%M")

    # Default to dateutil parser
    try:
        dt = date_parser.parse(text)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        # Fallback to 3 days ahead 23:59
        default_dt = reference_date + timedelta(days=3)
        return default_dt.strftime("%Y-%m-%d 23:59")


def generate_ics_calendar(tasks: List[Dict[str, Any]], output_filepath: str) -> str:
    """Generate a standard RFC 5545 iCalendar (.ics) file from tasks."""
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Academic Deadline Assistant//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Academic Deadlines"
    ]

    now_utc_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for t in tasks:
        try:
            dt = date_parser.parse(t["deadline"])
            dt_start = dt - timedelta(hours=1)
            start_str = dt_start.strftime("%Y%m%dT%H%M%S")
            end_str = dt.strftime("%Y%m%dT%H%M%S")
            uid = f"task-{t.get('id', 0)}-{start_str}@academic-assistant"

            title = str(t.get("title", "Task")).replace(",", "\\,").replace(";", "\\;")
            course = str(t.get("course", "Course")).replace(",", "\\,").replace(";", "\\;")
            desc = (
                f"Course: {course}\\n"
                f"Effort: {t.get('effort', 0)} hrs\\n"
                f"Weight: {t.get('weight', 0)}%\\n"
                f"Priority: {t.get('priority_level', 'Normal')}"
            )

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc_str}",
                f"DTSTART:{start_str}",
                f"DTEND:{end_str}",
                f"SUMMARY:[{course}] {title}",
                f"DESCRIPTION:{desc}",
                f"STATUS:{'COMPLETED' if t.get('status') == 'completed' else 'CONFIRMED'}",
                "PRIORITY:1",
                "END:VEVENT"
            ])
        except Exception:
            continue

    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines) + "\r\n"

    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(ics_content)

    return output_filepath
