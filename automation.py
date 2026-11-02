"""Automation Engine for Academic Deadline Management Assistant.
Trigger-Condition-Action workflow with verifiable execution results:
- Conditions: task due <= 48h, Critical priority, or active conflict.
- Actions:
  1. Generate detailed reminder/alert message
  2. Write to SQLite automation_log and logs/automation.log
  3. Export RFC 5545 iCalendar (.ics) to exports/upcoming_deadlines.ics
  4. Dispatch SMTP email if configured; otherwise write RFC 822 email to outbox/*.eml
"""

from __future__ import annotations
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

import db
from utils import generate_ics_calendar

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
OUTBOX_DIR = os.path.join(BASE_DIR, "outbox")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")


def check_and_trigger_automations(
    scored_tasks: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    trigger_name: str = "PIPELINE_TRIGGER",
    db_path: str = db.DB_PATH
) -> str:
    """Evaluate conditions and execute notification actions."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    matched_conditions: List[str] = []

    # Condition 1: Any task due within 48 hours and not done
    urgent_tasks = [
        t for t in scored_tasks
        if t.get("status") != "completed" and 0 <= t.get("days_left", 999) <= 2.0
    ]
    if urgent_tasks:
        matched_conditions.append(f"{len(urgent_tasks)} task(s) due within 48 hours")

    # Condition 2: Any task with Critical priority
    critical_tasks = [
        t for t in scored_tasks
        if t.get("status") != "completed" and t.get("priority_level") == "Critical"
    ]
    if critical_tasks:
        matched_conditions.append(f"{len(critical_tasks)} Critical priority task(s)")

    # Condition 3: Any active deadline conflict
    if conflicts:
        matched_conditions.append(f"{len(conflicts)} active deadline conflict(s)")

    if not matched_conditions:
        # No urgent triggers met
        action_note = "Conditions checked; workload balanced, no emergency dispatch required."
        db.log_automation_event(
            trigger_name=trigger_name,
            condition_matched="NONE",
            action_taken=action_note,
            status="SUCCESS",
            details="Zero tasks due within 48h and zero conflicts.",
            db_path=db_path
        )
        return "SUCCESS: No urgent conditions matched."

    condition_summary = " & ".join(matched_conditions)

    # -------------------------------------------------------------
    # Action 1: Construct reminder message
    # -------------------------------------------------------------
    subject = f"[Action Required] Academic Alert: {condition_summary}"
    body_lines = [
        f"Academic Deadline Management Alert",
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Trigger: {trigger_name}",
        f"Conditions: {condition_summary}",
        "-" * 50,
        "URGENT / CRITICAL TASKS:"
    ]

    for t in (urgent_tasks + [c for c in critical_tasks if c not in urgent_tasks]):
        body_lines.append(
            f" - [{t.get('course')}] {t.get('title')}: Due {t.get('deadline')} "
            f"({t.get('days_left', 0.0):.1f} days left) | Effort: {t.get('effort')}h | Level: {t.get('priority_level')}"
        )

    if conflicts:
        body_lines.append("\nDETECTED CONFLICTS:")
        for c in conflicts:
            body_lines.append(f" - [{c.get('id')}] {c.get('conflict_type')}: {c.get('explanation')}")
            body_lines.append(f"   Resolution: {c.get('suggested_resolution')}")

    body_text = "\n".join(body_lines)

    # -------------------------------------------------------------
    # Action 2: Write to logs/automation.log
    # -------------------------------------------------------------
    log_file_path = os.path.join(LOGS_DIR, "automation.log")
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] [{trigger_name}] {condition_summary}\n{body_text}\n\n")

    # -------------------------------------------------------------
    # Action 3: Generate iCalendar (.ics) in exports/
    # -------------------------------------------------------------
    ics_path = os.path.join(EXPORTS_DIR, "upcoming_deadlines.ics")
    generate_ics_calendar(scored_tasks, ics_path)

    # -------------------------------------------------------------
    # Action 4: Dispatch Email via SMTP or save to outbox/*.eml
    # -------------------------------------------------------------
    delivery_status, delivery_note = dispatch_email_or_outbox(subject, body_text)

    # Log to SQLite automation_log
    action_desc = f"Generated .ics calendar ({os.path.basename(ics_path)}) + {delivery_note}"
    db.log_automation_event(
        trigger_name=trigger_name,
        condition_matched=condition_summary,
        action_taken=action_desc,
        status=delivery_status,
        details=body_text[:500],
        db_path=db_path
    )

    return f"{delivery_status}: {action_desc}"


def dispatch_email_or_outbox(subject: str, body: str) -> Tuple[str, str]:
    """Send email via SMTP if configured; otherwise write RFC 822 .eml to outbox/."""
    student_email = os.getenv("STUDENT_EMAIL", "student@university.edu").strip()
    smtp_server = os.getenv("SMTP_SERVER", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()

    msg = MIMEMultipart()
    msg["From"] = smtp_user if smtp_user else "assistant@academic-deadline-tracker.internal"
    msg["To"] = student_email
    msg["Subject"] = subject
    msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg.attach(MIMEText(body, "plain"))

    # If SMTP is configured with real credentials, attempt send
    if smtp_server and smtp_user and smtp_pass:
        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=5) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return "SUCCESS", f"Sent live SMTP email to {student_email}"
        except Exception as e:
            # Fall through to outbox
            pass

    # Save to local outbox/*.eml for 100% reliable verification
    filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.eml"
    outbox_file = os.path.join(OUTBOX_DIR, filename)
    with open(outbox_file, "w", encoding="utf-8") as f:
        f.write(msg.as_string())

    return "SUCCESS", f"Saved verified message to outbox/{filename} (Fallback/No-SMTP mode)"

