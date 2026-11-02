"""Database manager for Academic Deadline Management Assistant.
SQLite database storage and CSV/Excel exports.
"""

from __future__ import annotations
import os
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Generator
import pandas as pd

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "assistant.db")
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")


@contextmanager
def get_connection(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize all SQLite tables if they do not exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                course TEXT NOT NULL,
                deadline TEXT NOT NULL,
                effort REAL NOT NULL,
                weight REAL NOT NULL,
                difficulty INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                user_priority_override TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 2. Scored tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scored_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                urgency_score REAL NOT NULL,
                weight_score REAL NOT NULL,
                effort_pressure_score REAL NOT NULL,
                difficulty_score REAL NOT NULL,
                priority_score REAL NOT NULL,
                priority_level TEXT NOT NULL,
                rank INTEGER NOT NULL,
                days_left REAL NOT NULL,
                has_conflict INTEGER NOT NULL DEFAULT 0,
                ai_rationale TEXT,
                evaluated_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
        """)

        # 3. Conflicts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conflicts (
                id TEXT PRIMARY KEY,
                conflict_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                task_ids TEXT NOT NULL,
                explanation TEXT NOT NULL,
                suggested_resolution TEXT,
                detected_at TEXT NOT NULL
            );
        """)

        # 4. AI Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_version TEXT NOT NULL,
                input_payload TEXT NOT NULL,
                raw_output TEXT NOT NULL,
                parsed_output TEXT,
                latency_ms REAL NOT NULL,
                model TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # 5. Evaluations table (10-point Rubric)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_run_id INTEGER,
                prompt_version TEXT NOT NULL,
                json_valid INTEGER NOT NULL,
                task_identity_valid INTEGER NOT NULL,
                completeness_valid INTEGER NOT NULL,
                data_accuracy_valid INTEGER NOT NULL,
                ranking_agreement_valid INTEGER NOT NULL,
                conflict_match_valid INTEGER NOT NULL,
                rationale_quality_valid INTEGER NOT NULL,
                total_score REAL NOT NULL,
                passed INTEGER NOT NULL,
                feedback_notes TEXT,
                evaluated_at TEXT NOT NULL,
                FOREIGN KEY (ai_run_id) REFERENCES ai_runs(id) ON DELETE SET NULL
            );
        """)

        # 6. Test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                test_name TEXT NOT NULL,
                status TEXT NOT NULL,
                expected_summary TEXT,
                actual_summary TEXT,
                latency_ms REAL,
                run_mode TEXT NOT NULL,
                executed_at TEXT NOT NULL
            );
        """)

        # 7. Automation log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trigger_name TEXT NOT NULL,
                condition_matched TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT
            );
        """)

        conn.commit()


# ==================== Task Operations ====================

def add_task(
    title: str,
    course: str,
    deadline: str,
    effort: float,
    weight: float,
    difficulty: int,
    status: str = "pending",
    user_priority_override: Optional[str] = None,
    db_path: str = DB_PATH
) -> int:
    """Insert a single validated task."""
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, course, deadline, effort, weight, difficulty, status, user_priority_override, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title.strip(), course.strip().upper(), deadline.strip(), float(effort), float(weight), int(difficulty), status, user_priority_override, now, now))
        conn.commit()
        return cursor.lastrowid


def get_all_tasks(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Retrieve all tasks."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]


def get_task_by_id(task_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_task_status(task_id: int, status: str, db_path: str = DB_PATH) -> None:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))
        conn.commit()


def update_task_priority_override(task_id: int, override: Optional[str], db_path: str = DB_PATH) -> None:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET user_priority_override = ?, updated_at = ? WHERE id = ?", (override, now, task_id))
        conn.commit()


def update_task(
    task_id: int,
    title: str,
    course: str,
    deadline: str,
    effort: float,
    weight: float,
    difficulty: int,
    status: str,
    user_priority_override: Optional[str] = None,
    db_path: str = DB_PATH
) -> None:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks
            SET title = ?, course = ?, deadline = ?, effort = ?, weight = ?, difficulty = ?, status = ?, user_priority_override = ?, updated_at = ?
            WHERE id = ?
        """, (title.strip(), course.strip().upper(), deadline.strip(), float(effort), float(weight), int(difficulty), status, user_priority_override, now, task_id))
        conn.commit()


def delete_task(task_id: int, db_path: str = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        cursor.execute("DELETE FROM scored_tasks WHERE task_id = ?", (task_id,))
        conn.commit()


def clear_all_tasks(db_path: str = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM scored_tasks")
        cursor.execute("DELETE FROM conflicts")
        conn.commit()


# ==================== Scored Tasks & Conflicts Operations ====================

def save_scored_tasks(scored_tasks: List[Dict[str, Any]], db_path: str = DB_PATH) -> None:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scored_tasks")
        for item in scored_tasks:
            cursor.execute("""
                INSERT INTO scored_tasks (
                    task_id, urgency_score, weight_score, effort_pressure_score, difficulty_score,
                    priority_score, priority_level, rank, days_left, has_conflict, ai_rationale, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["task_id"],
                item.get("urgency_score", 0.0),
                item.get("weight_score", 0.0),
                item.get("effort_pressure_score", 0.0),
                item.get("difficulty_score", 0.0),
                item.get("priority_score", 0.0),
                item.get("priority_level", "Low"),
                item.get("rank", 999),
                item.get("days_left", 0.0),
                1 if item.get("has_conflict") else 0,
                item.get("ai_rationale", ""),
                now
            ))
        conn.commit()


def get_latest_scored_tasks(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, t.title, t.course, t.deadline, t.effort, t.weight, t.difficulty, t.status, t.user_priority_override
            FROM scored_tasks s
            JOIN tasks t ON s.task_id = t.id
            ORDER BY s.rank ASC
        """)
        return [dict(row) for row in cursor.fetchall()]


def save_conflicts(conflicts: List[Dict[str, Any]], db_path: str = DB_PATH) -> None:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conflicts")
        for c in conflicts:
            task_ids_str = json.dumps(c.get("task_ids", []))
            cursor.execute("""
                INSERT INTO conflicts (id, conflict_type, severity, task_ids, explanation, suggested_resolution, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"],
                c["conflict_type"],
                c.get("severity", "MEDIUM"),
                task_ids_str,
                c.get("explanation", ""),
                c.get("suggested_resolution", ""),
                now
            ))
        conn.commit()


def get_latest_conflicts(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conflicts ORDER BY id ASC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["task_ids"] = json.loads(d["task_ids"])
            except Exception:
                d["task_ids"] = []
            result.append(d)
        return result


# ==================== AI Runs & Evaluations ====================

def log_ai_run(
    prompt_version: str,
    input_payload: str,
    raw_output: str,
    parsed_output: Optional[str],
    latency_ms: float,
    model: str,
    mode: str,
    db_path: str = DB_PATH
) -> int:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_runs (prompt_version, input_payload, raw_output, parsed_output, latency_ms, model, mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (prompt_version, input_payload, raw_output, parsed_output, latency_ms, model, mode, now))
        conn.commit()
        return cursor.lastrowid


def log_evaluation(
    prompt_version: str,
    scores: Dict[str, Any],
    ai_run_id: Optional[int] = None,
    feedback_notes: str = "",
    db_path: str = DB_PATH
) -> int:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluations (
                ai_run_id, prompt_version, json_valid, task_identity_valid, completeness_valid,
                data_accuracy_valid, ranking_agreement_valid, conflict_match_valid,
                rationale_quality_valid, total_score, passed, feedback_notes, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ai_run_id,
            prompt_version,
            scores.get("json_valid", 0),
            scores.get("task_identity_valid", 0),
            scores.get("completeness_valid", 0),
            scores.get("data_accuracy_valid", 0),
            scores.get("ranking_agreement_valid", 0),
            scores.get("conflict_match_valid", 0),
            scores.get("rationale_quality_valid", 0),
            scores.get("total_score", 0.0),
            1 if scores.get("passed") else 0,
            feedback_notes,
            now
        ))
        conn.commit()
        return cursor.lastrowid


def get_all_ai_runs(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ai_runs ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]


def get_all_evaluations(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evaluations ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]


# ==================== Test Results & Automation Logging ====================

def log_test_result(
    test_id: str,
    test_name: str,
    status: str,
    expected_summary: str,
    actual_summary: str,
    latency_ms: float,
    run_mode: str,
    db_path: str = DB_PATH
) -> int:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO test_results (test_id, test_name, status, expected_summary, actual_summary, latency_ms, run_mode, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_id, test_name, status, expected_summary, actual_summary, latency_ms, run_mode, now))
        conn.commit()
        return cursor.lastrowid


def get_test_results(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_results ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]


def log_automation_event(
    trigger_name: str,
    condition_matched: str,
    action_taken: str,
    status: str,
    details: str = "",
    db_path: str = DB_PATH
) -> int:
    now = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO automation_log (timestamp, trigger_name, condition_matched, action_taken, status, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now, trigger_name, condition_matched, action_taken, status, details))
        conn.commit()
        return cursor.lastrowid


def get_automation_logs(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM automation_log ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]


# ==================== CSV & Excel Export ====================

def export_all_to_csv(export_dir: str = EXPORTS_DIR, db_path: str = DB_PATH) -> Dict[str, str]:
    """Export all 7 database tables to individual CSVs and an all-in-one Excel file."""
    os.makedirs(export_dir, exist_ok=True)
    table_names = ["tasks", "scored_tasks", "conflicts", "ai_runs", "evaluations", "test_results", "automation_log"]
    generated_files = {}

    with get_connection(db_path) as conn:
        excel_writer_path = os.path.join(export_dir, "academic_assistant_data.xlsx")
        try:
            with pd.ExcelWriter(excel_writer_path, engine="openpyxl") as excel_writer:
                for table in table_names:
                    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                    csv_path = os.path.join(export_dir, f"{table}.csv")
                    df.to_csv(csv_path, index=False)
                    df.to_excel(excel_writer, sheet_name=table[:31], index=False)
                    generated_files[table] = csv_path
            generated_files["excel_workbook"] = excel_writer_path
        except Exception:
            # If openpyxl has issues, fallback to just CSVs
            for table in table_names:
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                csv_path = os.path.join(export_dir, f"{table}.csv")
                df.to_csv(csv_path, index=False)
                generated_files[table] = csv_path

    return generated_files

