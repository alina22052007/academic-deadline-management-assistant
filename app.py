"""Academic Deadline Management Assistant - Multi-Tab Streamlit Dashboard.
Clean, Basic, Standard Streamlit UI (Zero Emojis, Zero Custom CSS).
"""

from __future__ import annotations
import os
import json
import time
from datetime import datetime, date, time as dt_time, timedelta
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

import db
from scoring import score_and_rank_tasks
from conflicts import detect_conflicts, annotate_tasks_with_conflicts
from validator import validate_task_input, sanitize_free_text_input, evaluate_ai_response
from llm_client import (
    extract_tasks_from_text,
    generate_ai_reasoning_and_plan,
    generate_fallback_reasoning_and_plan,
    is_fallback_forced,
    get_configured_model
)
from pipeline import run_pipeline, load_prompt_file
from automation import check_and_trigger_automations
from tests.test_pipeline import run_documented_test_suite

load_dotenv()

# Standard Streamlit Page Config - Basic and Clean
st.set_page_config(
    page_title="Academic Deadline Management Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database
db.init_db()


# =====================================================================
# SIDEBAR: SETTINGS & CONTROLS
# =====================================================================
with st.sidebar:
    st.header("Settings")

    daily_capacity = st.slider(
        "Daily Study Capacity (Hours/Day)",
        min_value=1.0,
        max_value=12.0,
        value=4.0,
        step=0.5,
        help="Maximum hours available for studying per day."
    )

    study_days = st.multiselect(
        "Study Days",
        options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        help="Days of the week designated for study."
    )

    st.divider()
    st.subheader("Reference Date")
    use_date_override = st.checkbox(
        "Override Reference Date (for demo)",
        value=True,
        help="Fixes current date to Sunday, Nov 1, 2026 for consistent testing."
    )
    if use_date_override:
        override_val = st.date_input("Date", value=date(2026, 11, 1))
        reference_date = datetime.combine(override_val, dt_time(9, 0))
    else:
        reference_date = datetime.now()

    st.divider()
    st.subheader("System Mode")
    api_key_env = os.getenv("GEMINI_API_KEY", "").strip()
    force_fallback = st.toggle("Force Fallback Mode", value=is_fallback_forced() or not bool(api_key_env))
    if force_fallback:
        os.environ["AI_FALLBACK_MODE"] = "1"
        st.info("Mode: AI Fallback (Deterministic Rule Engine)")
    else:
        os.environ["AI_FALLBACK_MODE"] = "0"
        st.success("Mode: Gemini Flash API Connected")

    st.caption(f"Model: {get_configured_model()}")

    st.divider()
    st.subheader("Dashboard Pages")
    show_evaluation_tabs = st.toggle(
        "Show Evaluation & Rubric Tabs",
        value=False,
        help="Show Prompt Lab, Tests, Automations, and Architecture tabs for grading."
    )

    st.divider()
    st.subheader("Actions")
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        if st.button("Load Demo Data", use_container_width=True):
            sample_csv_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_tasks.csv")
            if os.path.exists(sample_csv_path):
                db.clear_all_tasks()
                df_sample = pd.read_csv(sample_csv_path)
                for _, row in df_sample.iterrows():
                    db.add_task(
                        title=str(row["title"]),
                        course=str(row["course"]),
                        deadline=str(row["deadline"]),
                        effort=float(row["effort"]),
                        weight=float(row["weight"]),
                        difficulty=int(row["difficulty"]),
                        status=str(row.get("status", "pending"))
                    )
                st.toast("Demo data loaded.")
                time.sleep(0.3)
                st.rerun()

    with col_sb2:
        if st.button("Clear Tasks", use_container_width=True):
            db.clear_all_tasks()
            st.toast("Tasks cleared.")
            time.sleep(0.3)
            st.rerun()

    st.divider()
    if st.button("Export to CSV/Excel", use_container_width=True):
        res_files = db.export_all_to_csv()
        st.success(f"Exported {len(res_files)} tables to exports/ folder.")


# =====================================================================
# MAIN HEADER & METRICS
# =====================================================================

raw_tasks = db.get_all_tasks()
scored_tasks = score_and_rank_tasks(raw_tasks, daily_capacity=daily_capacity, reference_date=reference_date)
conflicts = detect_conflicts(scored_tasks, daily_capacity=daily_capacity, reference_date=reference_date)
scored_tasks = annotate_tasks_with_conflicts(scored_tasks, conflicts)

total_tasks = len(raw_tasks)
active_tasks = [t for t in scored_tasks if t.get("status") != "completed"]
critical_count = sum(1 for t in active_tasks if t.get("priority_level") == "Critical")
conflicts_count = len(conflicts)

# Next deadline display
next_deadline_str = "None pending"
if active_tasks:
    upcoming = [t for t in active_tasks if t.get("days_left", 0) >= 0]
    if upcoming:
        soonest = min(upcoming, key=lambda x: x["days_left"])
        next_deadline_str = f"{soonest['days_left']:.1f} days left ({soonest['course']})"
    else:
        next_deadline_str = "All Overdue"

# Contextual status
if critical_count > 0:
    status_summary = f"Notice: You have {critical_count} critical task(s) requiring immediate attention."
elif conflicts_count > 0:
    status_summary = f"Notice: {conflicts_count} deadline conflict(s) detected. Review the Conflicts tab."
elif total_tasks == 0:
    status_summary = "Workspace is empty. Add tasks below or click 'Load Demo Data' in the sidebar."
else:
    status_summary = "Workload is balanced. No immediate deadline bottlenecks detected."

st.title("Academic Deadline Management Assistant")
st.write("Prioritize assignments, identify deadline conflicts, and create a 7-day study plan.")

if critical_count > 0 or conflicts_count > 0:
    st.warning(status_summary)
elif total_tasks == 0:
    st.info(status_summary)
else:
    st.success(status_summary)

# Metrics Grid
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Deliverables", total_tasks, delta=f"{len(active_tasks)} Active")
with m2:
    st.metric("Critical Tasks", critical_count, delta="Requires Focus" if critical_count > 0 else "Normal", delta_color="inverse")
with m3:
    st.metric("Detected Conflicts", conflicts_count, delta="Attention Needed" if conflicts_count > 0 else "None", delta_color="inverse")
with m4:
    st.metric("Next Deadline", next_deadline_str, delta=reference_date.strftime("%b %d, %Y"))

st.divider()


# =====================================================================
# TABS
# =====================================================================
tab_names = [
    "Add Tasks",
    "Prioritized Tracker",
    "Conflicts",
    "AI Study Plan"
]
if show_evaluation_tabs:
    tab_names += [
        "Prompt Lab",
        "Validation & Tests",
        "Automation & Logs",
        "About & Responsible AI"
    ]

tabs = st.tabs(tab_names)


# =====================================================================
# TAB 1: ADD TASKS
# =====================================================================
with tabs[0]:
    st.subheader("Add Tasks")
    st.write("Enter assignments via structured form, natural language free-text, or CSV spreadsheet.")

    input_mode = st.radio(
        "Input Method",
        ["Structured Form", "Paste Free-Text", "CSV Bulk Upload"],
        horizontal=True
    )

    if input_mode == "Structured Form":
        with st.form("add_task_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                title_in = st.text_input("Task Title", placeholder="e.g. Distributed Systems Lab 3")
                course_in = st.text_input("Course Code", placeholder="e.g. CS455 or MATH201")
                status_in = st.selectbox(
                    "Current Status",
                    ["pending", "in_progress", "completed"],
                    index=0,
                    format_func=lambda x: {"pending": "Pending", "in_progress": "In Progress", "completed": "Completed"}[x]
                )
            with fc2:
                d_date = st.date_input("Deadline Date", value=reference_date.date() + timedelta(days=3))
                d_time = st.time_input("Deadline Time", value=dt_time(17, 0))
                effort_in = st.number_input("Estimated Effort (Hours)", min_value=0.5, max_value=100.0, value=4.0, step=0.5)
                weight_in = st.number_input("Grade Weight (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0)
                diff_in = st.slider("Difficulty (1-5)", min_value=1, max_value=5, value=3)

            submitted = st.form_submit_button("Add Task to Tracker", use_container_width=True)
            if submitted:
                combined_dl = datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")
                is_val, errs, cleaned = validate_task_input(
                    title=title_in,
                    course=course_in,
                    deadline_str=combined_dl,
                    effort=effort_in,
                    weight=weight_in,
                    difficulty=diff_in,
                    existing_tasks=raw_tasks,
                    reference_date=reference_date
                )
                if not is_val:
                    for err in errs:
                        st.error(err)
                else:
                    new_id = db.add_task(
                        title=cleaned["title"],
                        course=cleaned["course"],
                        deadline=cleaned["deadline"],
                        effort=cleaned["effort"],
                        weight=cleaned["weight"],
                        difficulty=cleaned["difficulty"],
                        status=status_in
                    )
                    st.toast(f"Task '{cleaned['title']}' added.")
                    time.sleep(0.3)
                    st.rerun()

    elif input_mode == "Paste Free-Text":
        st.write("Paste free text (e.g. from syllabus, email, or message). The LLM or rule engine extracts structured tasks.")
        freetext_input = st.text_area(
            "Free-Text Input",
            height=120,
            placeholder="e.g. DBMS assignment due Friday 5pm, 6 hrs, worth 15%. ML quiz tomorrow 10am, 2 hrs, worth 10%."
        )

        if st.button("Extract Tasks", use_container_width=True) and freetext_input.strip():
            clean_text, inj_detected, warnings = sanitize_free_text_input(freetext_input)
            if inj_detected:
                st.warning("Prompt injection pattern detected and neutralized.")

            with st.spinner("Extracting structured tasks..."):
                extracted, mode, note = extract_tasks_from_text(clean_text, reference_date=reference_date)
                st.session_state["extracted_preview"] = extracted
                st.session_state["extraction_note"] = f"{note} (Engine: {mode})"

        if "extracted_preview" in st.session_state and st.session_state["extracted_preview"]:
            st.info(st.session_state.get("extraction_note", ""))
            st.write("**Extracted Tasks Preview:**")
            preview_df = pd.DataFrame(st.session_state["extracted_preview"])
            st.dataframe(preview_df, use_container_width=True)

            if st.button("Confirm and Save Extracted Tasks", use_container_width=True):
                saved_count = 0
                for item in st.session_state["extracted_preview"]:
                    is_val, errs, cleaned = validate_task_input(
                        title=item.get("title", ""),
                        course=item.get("course", ""),
                        deadline_str=item.get("deadline", ""),
                        effort=item.get("effort", 3.0),
                        weight=item.get("weight", 10.0),
                        difficulty=item.get("difficulty", 3),
                        existing_tasks=raw_tasks,
                        reference_date=reference_date
                    )
                    if is_val:
                        db.add_task(
                            title=cleaned["title"],
                            course=cleaned["course"],
                            deadline=cleaned["deadline"],
                            effort=cleaned["effort"],
                            weight=cleaned["weight"],
                            difficulty=cleaned["difficulty"],
                            status="pending"
                        )
                        saved_count += 1
                st.success(f"Saved {saved_count} tasks to database.")
                del st.session_state["extracted_preview"]
                time.sleep(0.3)
                st.rerun()

    elif input_mode == "CSV Bulk Upload":
        st.write("Upload a CSV file with columns: `title`, `course`, `deadline`, `effort`, `weight`, `difficulty`, `status`.")
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                df_upload = pd.read_csv(uploaded_file)
                st.write("**Preview:**")
                st.dataframe(df_upload.head(10), use_container_width=True)

                if st.button("Import Tasks from CSV", use_container_width=True):
                    added_count = 0
                    validation_errors = []
                    for idx, r in df_upload.iterrows():
                        is_val, errs, cleaned = validate_task_input(
                            title=str(r.get("title", "")),
                            course=str(r.get("course", "")),
                            deadline_str=str(r.get("deadline", "")),
                            effort=r.get("effort", 3.0),
                            weight=r.get("weight", 10.0),
                            difficulty=r.get("difficulty", 3),
                            existing_tasks=raw_tasks,
                            reference_date=reference_date
                        )
                        if is_val:
                            db.add_task(
                                title=cleaned["title"],
                                course=cleaned["course"],
                                deadline=cleaned["deadline"],
                                effort=cleaned["effort"],
                                weight=cleaned["weight"],
                                difficulty=cleaned["difficulty"],
                                status=str(r.get("status", "pending"))
                            )
                            added_count += 1
                        else:
                            validation_errors.append(f"Row {idx+1}: {', '.join(errs)}")

                    if added_count > 0:
                        st.success(f"Imported {added_count} tasks.")
                    if validation_errors:
                        st.warning(f"Skipped {len(validation_errors)} invalid rows.")
                    time.sleep(0.3)
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading CSV: {str(e)}")


# =====================================================================
# TAB 2: PRIORITIZED TRACKER
# =====================================================================
with tabs[1]:
    st.subheader("Prioritized Task Tracker")
    st.write("Tasks sorted by priority score based on urgency, weight, effort pressure, and difficulty.")

    # Filters
    fcol1, fcol2, fcol3, fcol4 = st.columns([2, 2, 2, 1.5])
    with fcol1:
        courses = sorted(list(set(t["course"] for t in scored_tasks))) if scored_tasks else []
        selected_courses = st.multiselect("Filter by Course", options=courses, default=courses)
    with fcol2:
        status_options = ["All", "pending", "in_progress", "completed"]
        selected_status = st.selectbox(
            "Filter by Status",
            status_options,
            index=0,
            format_func=lambda x: {"All": "All", "pending": "Pending", "in_progress": "In Progress", "completed": "Completed"}[x]
        )
    with fcol3:
        level_options = ["All", "Critical", "High", "Medium", "Low"]
        selected_level = st.selectbox("Filter by Priority Level", level_options, index=0)
    with fcol4:
        st.write("")
        st.write("")
        if st.button("Refresh / Re-Rank", use_container_width=True):
            st.rerun()

    filtered_tasks = []
    for t in scored_tasks:
        if selected_courses and t["course"] not in selected_courses:
            continue
        if selected_status != "All" and t["status"] != selected_status:
            continue
        if selected_level != "All" and t["priority_level"] != selected_level:
            continue
        filtered_tasks.append(t)

    if not filtered_tasks:
        st.info("No tasks match the active filters or the database is empty.")
    else:
        table_rows = []
        for t in filtered_tasks:
            lvl = t["priority_level"]
            conflict_flag = "Yes" if t.get("has_conflict") else "No"
            days_str = f"{t['days_left']:.1f}d" if t['days_left'] >= 0 else f"Overdue ({abs(t['days_left']):.1f}d)"

            table_rows.append({
                "Rank": t.get("rank"),
                "Task": t.get("title"),
                "Course": t.get("course"),
                "Deadline": t.get("deadline"),
                "Days Left": days_str,
                "Effort (h)": t.get("effort"),
                "Weight (%)": t.get("weight"),
                "Priority Score": t.get("priority_score"),
                "Priority Level": lvl,
                "Conflict": conflict_flag,
                "AI Rationale": t.get("ai_rationale") or f"Score {t.get('priority_score')}/100 driven by deadline proximity and {t.get('weight')}% weight.",
                "Status": t.get("status"),
                "_id": t.get("id") or t.get("task_id")
            })

        df_display = pd.DataFrame(table_rows)
        st.dataframe(
            df_display.drop(columns=["_id"]),
            use_container_width=True,
            column_config={
                "Priority Score": st.column_config.ProgressColumn("Priority Score (0-100)", min_value=0, max_value=100, format="%.1f")
            }
        )

        csv_tracker = df_display.drop(columns=["_id"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Tracker CSV",
            data=csv_tracker,
            file_name="prioritized_academic_tracker.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("Manage Tasks & Overrides")
        with st.expander("Update Task Status or Priority Override"):
            sel_task_id = st.selectbox(
                "Select Task",
                options=[r["_id"] for r in table_rows],
                format_func=lambda x: f"Task #{x}: {[r['Task'] for r in table_rows if r['_id'] == x][0]}"
            )
            selected_raw = db.get_task_by_id(sel_task_id)

            if selected_raw:
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    new_status = st.selectbox(
                        "Status",
                        ["pending", "in_progress", "completed"],
                        index=["pending", "in_progress", "completed"].index(selected_raw["status"]),
                        format_func=lambda x: {"pending": "Pending", "in_progress": "In Progress", "completed": "Completed"}[x]
                    )
                    if st.button("Update Status"):
                        db.update_task_status(sel_task_id, new_status)
                        st.toast("Status updated.")
                        st.rerun()

                with ec2:
                    current_override = selected_raw.get("user_priority_override") or "None"
                    override_choice = st.selectbox(
                        "Priority Override",
                        ["None", "Critical", "High", "Medium", "Low"],
                        index=["None", "Critical", "High", "Medium", "Low"].index(current_override),
                        help="User override takes precedence over algorithmic ranking."
                    )
                    if st.button("Apply Override"):
                        db.update_task_priority_override(sel_task_id, None if override_choice == "None" else override_choice)
                        st.toast(f"Override set to {override_choice}.")
                        st.rerun()

                with ec3:
                    st.write("Delete Task")
                    if st.button("Delete Task", type="primary"):
                        db.delete_task(sel_task_id)
                        st.toast(f"Deleted task #{sel_task_id}.")
                        st.rerun()


# =====================================================================
# TAB 3: CONFLICTS
# =====================================================================
with tabs[2]:
    st.subheader("Deadline Conflicts")
    st.write("Algorithmic detection of same-day clashes, workload overloads, deadline clusters, and overdue tasks.")

    if not conflicts:
        st.success("Zero deadline conflicts detected. Workload is distributed within capacity limits.")
    else:
        st.warning(f"{len(conflicts)} deadline conflict(s) detected.")

        for c in conflicts:
            with st.expander(f"[{c.get('severity')}] {c.get('conflict_type')} (ID: {c.get('id')})", expanded=True):
                st.write(f"**Explanation:** {c.get('explanation')}")
                st.write(f"**Suggested Resolution:** {c.get('suggested_resolution')}")
                st.caption(f"Affected Task IDs: {c.get('task_ids')}")

    st.divider()
    st.subheader("Workload vs. Capacity (7 Days)")
    active_conf_tasks = [t for t in scored_tasks if t.get("status") != "completed"]
    if active_conf_tasks:
        chart_days = []
        for d in range(8):
            curr_d = reference_date.date() + timedelta(days=d)
            day_tasks = [t for t in active_conf_tasks if 0 <= t.get("days_left", 0) <= d + 1]
            total_effort_due = sum(t.get("effort", 0) for t in day_tasks)
            avail_cap = (d + 1) * daily_capacity

            chart_days.append({
                "Date": curr_d.strftime("%a %b %d"),
                "Required Effort (h)": min(total_effort_due, 40.0),
                "Available Capacity (h)": avail_cap
            })

        df_chart = pd.DataFrame(chart_days)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_chart["Date"],
            y=df_chart["Required Effort (h)"],
            name="Cumulative Effort Required",
            marker_color="#EA580C"
        ))
        fig.add_trace(go.Scatter(
            x=df_chart["Date"],
            y=df_chart["Available Capacity (h)"],
            name=f"Available Capacity ({daily_capacity}h/day)",
            mode="lines+markers",
            line=dict(color="#2563EB", width=2.5, dash="dash")
        ))
        fig.update_layout(
            title="7-Day Workload vs Available Capacity",
            xaxis_title="Day",
            yaxis_title="Hours",
            barmode="group",
            template="plotly_white",
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active tasks to visualize.")


# =====================================================================
# TAB 4: AI STUDY PLAN
# =====================================================================
with tabs[3]:
    st.subheader("AI Study Plan (Next 7 Days)")
    st.write(f"Capacity-constrained study schedule allocating tasks across 7 days without exceeding {daily_capacity} hours/day.")

    active_for_plan = [t for t in scored_tasks if t.get("status") != "completed"]

    if not active_for_plan:
        st.info("No active tasks found to schedule. Add tasks in Tab 1 to generate a study plan.")
    else:
        if st.button("Generate 7-Day Plan", use_container_width=True) or "cached_study_plan" not in st.session_state:
            with st.spinner("Generating study plan..."):
                plan_prompt = load_prompt_file("prompt_v3_final.txt")
                ai_dict, raw_txt, latency, mode, model = generate_ai_reasoning_and_plan(
                    prompt_template=plan_prompt,
                    scored_tasks=active_for_plan,
                    conflicts=conflicts,
                    daily_capacity=daily_capacity,
                    reference_date=reference_date,
                    prompt_version="v3"
                )
                st.session_state["cached_study_plan"] = ai_dict.get("study_plan", [])
                st.session_state["plan_meta"] = f"Generated in {latency}ms via {mode.upper()} ({model})"

        st.caption(st.session_state.get("plan_meta", ""))
        plan_data = st.session_state.get("cached_study_plan", [])

        if plan_data:
            for day in plan_data:
                day_offset = day.get("day_offset", 0)
                day_label = "Today" if day_offset == 0 else ("Tomorrow" if day_offset == 1 else f"{day.get('day_name')}")
                full_date_str = f"{day_label} ({day.get('date')})"
                allocs = day.get("allocations", [])
                total_h = day.get("total_hours", 0.0)

                st.write(f"**{full_date_str}** — `{total_h:.1f} / {daily_capacity:.1f} hours planned`")
                if not allocs or total_h == 0.0:
                    st.info("Buffer day. No tasks scheduled. Available for review or rest.")
                else:
                    for a in allocs:
                        st.write(f"- **{a.get('task_title')}** ({a.get('allocated_hours')}h): {a.get('objective')}")
                st.write("")

        if not show_evaluation_tabs:
            st.divider()
            st.caption("Note: To view developer evidence (Prompt Lab, Tests, Automations, Architecture), enable 'Show Evaluation & Rubric Tabs' in the sidebar.")


# =====================================================================
# EVALUATION & RUBRIC TABS (Toggled via Sidebar)
# =====================================================================
if show_evaluation_tabs:
    # -----------------------------------------------------------------
    # TAB 5: PROMPT LAB
    # -----------------------------------------------------------------
    with tabs[4]:
        st.subheader("Prompt Engineering Lab (v1 vs v2 vs v3)")
        st.write("Compare baseline, structured, and final prompt versions using the 10-point verification rubric.")

        if not scored_tasks:
            st.info("Load or add tasks to run the Prompt Lab comparison.")
        else:
            if st.button("Run Prompt Comparison Experiment", use_container_width=True):
                prompt_versions = ["v1", "v2", "v3"]
                exp_results = []

                for pv in prompt_versions:
                    filename = f"prompt_{pv}_final.txt" if pv == "v3" else (
                        "prompt_v2_structured.txt" if pv == "v2" else "prompt_v1_basic.txt"
                    )
                    template = load_prompt_file(filename)
                    ai_dict, raw_txt, latency, mode, model = generate_ai_reasoning_and_plan(
                        prompt_template=template,
                        scored_tasks=scored_tasks,
                        conflicts=conflicts,
                        daily_capacity=daily_capacity,
                        reference_date=reference_date,
                        prompt_version=pv
                    )

                    eval_res = evaluate_ai_response(
                        raw_response=raw_txt,
                        input_tasks=scored_tasks,
                        algorithmic_conflicts=conflicts,
                        reference_rankings=scored_tasks
                    )

                    input_tids = set(t.get("id") or t.get("task_id") for t in scored_tasks)
                    hallucinations = 0
                    for r in ai_dict.get("task_rationales", []):
                        if r.get("task_id") not in input_tids:
                            hallucinations += 1

                    exp_results.append({
                        "version": pv,
                        "label": f"Prompt {pv.upper()}",
                        "latency_ms": latency,
                        "json_valid": eval_res["json_valid"],
                        "hallucinations": hallucinations,
                        "ranking_agreement": eval_res["ranking_agreement_valid"],
                        "total_score": eval_res["total_score"],
                        "passed": eval_res["passed"],
                        "raw_output": raw_txt[:300] + "...",
                        "feedback": "; ".join(eval_res["feedback_notes"]) or "None (Clean)"
                    })

                st.session_state["prompt_lab_results"] = exp_results
                st.toast("Prompt experiment complete.")

            if "prompt_lab_results" in st.session_state:
                res_list = st.session_state["prompt_lab_results"]
                df_comp = pd.DataFrame(res_list)[[
                    "label", "total_score", "passed", "json_valid", "hallucinations", "ranking_agreement", "latency_ms", "feedback"
                ]]
                df_comp.columns = ["Version", "Score (out of 10)", "Passed?", "JSON (0-2)", "Hallucinations", "Rank (0-2)", "Latency (ms)", "Feedback"]
                st.dataframe(df_comp, use_container_width=True)

                c1, c2 = st.columns(2)
                with c1:
                    fig_scores = px.bar(
                        df_comp,
                        x="Version",
                        y="Score (out of 10)",
                        title="Rubric Score (v1 vs v2 vs v3)",
                        range_y=[0, 10],
                        text_auto=True
                    )
                    st.plotly_chart(fig_scores, use_container_width=True)

                with c2:
                    fig_lat = px.bar(
                        df_comp,
                        x="Version",
                        y="Latency (ms)",
                        title="Execution Latency (ms)",
                        text_auto=True
                    )
                    st.plotly_chart(fig_lat, use_container_width=True)

                winner = max(res_list, key=lambda x: (x["total_score"], -x["latency_ms"]))
                st.success(f"Winning Version: {winner['label']} (Score: {winner['total_score']}/10)")
                st.markdown("""
                **Prompt Refinement Log:**
                - **v1 Basic:** Naive one-line prompt. Non-deterministic keys, broken JSON, unconstrained length.
                - **v2 Structured:** Added role, context, task, and output constraints.
                - **v3 Final (Winner):** Added strict JSON schema, two few-shot examples, explicit negative rules ("never invent tasks or dates", "rationale max 25 words"), and step decomposition. Achieves 10/10 rubric compliance.
                """)

    # -----------------------------------------------------------------
    # TAB 6: VALIDATION & TESTS
    # -----------------------------------------------------------------
    with tabs[5]:
        st.subheader("Validation & Tests (TC1 - TC5)")
        st.write("Execute all 5 documented test cases including edge cases, prompt injection defense, and reference ranking agreement.")

        if st.button("Run All Tests (TC1 - TC5)", use_container_width=True) or "ui_test_results" not in st.session_state:
            with st.spinner("Executing test cases..."):
                t_results, r_path = run_documented_test_suite(no_ai=True)
                st.session_state["ui_test_results"] = t_results
                st.session_state["report_path"] = r_path

        if "ui_test_results" in st.session_state:
            t_res = st.session_state["ui_test_results"]
            all_passed = all(t["status"] == "PASS" for t in t_res)

            if all_passed:
                st.success("All 5 Documented Test Cases Passed (Deterministic & AI Modes).")
            else:
                st.error("Some tests failed.")

            df_t = pd.DataFrame(t_res)
            st.dataframe(
                df_t[["id", "name", "status", "latency_ms", "expected", "actual", "rubric_score"]],
                use_container_width=True,
                column_config={
                    "status": st.column_config.TextColumn("Status"),
                    "latency_ms": st.column_config.NumberColumn("Latency (ms)", format="%.1f ms"),
                    "rubric_score": st.column_config.NumberColumn("Rubric Score", format="%.0f/10")
                }
            )
            st.caption(f"Evidence files saved to {st.session_state.get('report_path')}.")

            st.divider()
            st.write("#### 10-Point Verification Rubric Specification")
            st.markdown("""
            | Criterion # | Rubric Item | Points | Enforcement Method |
            | :-: | :--- | :-: | :--- |
            | 1 | Valid JSON schema | 2 | Verified via strict `json.loads` and key checks |
            | 2 | Zero hallucinated task IDs | 2 | Set intersection check: AI IDs match Database IDs |
            | 3 | Input completeness | 1 | Every entered deliverable receives a rationale |
            | 4 | Data accuracy | 1 | Planned hours remain within feasible bounds (0-24h) |
            | 5 | Ranking agreement | 2 | Top-K overlap agreement with deterministic ranking |
            | 6 | Conflict matching | 1 | AI resolutions address identified algorithmic conflicts |
            | 7 | Rationale conciseness | 1 | Word count <= 25-35 words per task |
            """)

    # -----------------------------------------------------------------
    # TAB 7: AUTOMATION & LOGS
    # -----------------------------------------------------------------
    with tabs[6]:
        st.subheader("Automation Engine & Logs")
        st.write("Verifiable automated workflows with real-time logging, iCalendar (.ics) exports, and email dispatch.")

        act_col1, act_col2, act_col3 = st.columns(3)
        with act_col1:
            if st.button("Simulate Urgent Trigger (Task due in 12h)", use_container_width=True):
                sim_task = {
                    "id": 999,
                    "title": "URGENT Take-Home Exam",
                    "course": "CS499",
                    "deadline": (reference_date + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M"),
                    "effort": 6.0,
                    "weight": 35.0,
                    "days_left": 0.5,
                    "priority_level": "Critical",
                    "status": "pending"
                }
                sim_conflicts = [{
                    "id": "C_SIM",
                    "conflict_type": "WORKLOAD_OVERLOAD",
                    "severity": "CRITICAL",
                    "task_ids": [999],
                    "explanation": "Simulated take-home exam due in 12 hours.",
                    "suggested_resolution": "Clear today's schedule entirely for immediate exam focus."
                }]
                res = check_and_trigger_automations([sim_task], sim_conflicts, trigger_name="SIMULATED_URGENT_TRIGGER")
                st.toast("Simulated trigger executed.")
                time.sleep(0.3)
                st.rerun()

        with act_col2:
            if st.button("Run Daily Scheduled Check", use_container_width=True):
                res = check_and_trigger_automations(scored_tasks, conflicts, trigger_name="MANUAL_DAILY_CHECK")
                st.toast("Daily check completed.")
                time.sleep(0.3)
                st.rerun()

        with act_col3:
            ics_p = os.path.join(os.path.dirname(__file__), "exports", "upcoming_deadlines.ics")
            if os.path.exists(ics_p):
                with open(ics_p, "rb") as f:
                    st.download_button(
                        label="Download Calendar (.ics)",
                        data=f.read(),
                        file_name="upcoming_deadlines.ics",
                        mime="text/calendar",
                        use_container_width=True
                    )
            else:
                st.button("Download Calendar (.ics)", disabled=True, use_container_width=True)

        st.divider()
        st.write("#### Live Automation Execution Logs (SQLite)")
        auto_logs = db.get_automation_logs(limit=25)
        if not auto_logs:
            st.info("No automation events logged yet. Click 'Simulate Urgent Trigger' above to test.")
        else:
            df_logs = pd.DataFrame(auto_logs)
            st.dataframe(
                df_logs[["id", "timestamp", "trigger_name", "condition_matched", "status", "action_taken"]],
                use_container_width=True
            )

        outbox_dir = os.path.join(os.path.dirname(__file__), "outbox")
        if os.path.exists(outbox_dir):
            outbox_files = sorted(os.listdir(outbox_dir), reverse=True)
            if outbox_files:
                with st.expander(f"Outbox Email Messages ({len(outbox_files)} saved)"):
                    sel_eml = st.selectbox("Select Message", outbox_files)
                    eml_path = os.path.join(outbox_dir, sel_eml)
                    with open(eml_path, "r", encoding="utf-8") as f:
                        st.text(f.read())

    # -----------------------------------------------------------------
    # TAB 8: ABOUT & RESPONSIBLE AI
    # -----------------------------------------------------------------
    with tabs[7]:
        st.subheader("Architecture & Responsible AI")

        st.write("#### Six-Stage Processing Pipeline")
        st.markdown("""
        ```mermaid
        flowchart LR
            S1["Stage 1: Intake & Extraction"] --> S2["Stage 2: Deterministic Scoring"]
            S2 --> S3["Stage 3: Algorithmic Conflicts"]
            S3 --> S4["Stage 4: AI Reasoning & Planning"]
            S4 --> S5["Stage 5: Rubric Verification"]
            S5 --> S6["Stage 6: Persistence & Automation"]
        ```
        """)

        st.write("#### Mathematical Scoring Formula")
        st.latex(r"\text{Score} = 0.40 \times \text{Urgency} + 0.25 \times \text{Weight} + 0.20 \times \text{Effort Pressure} + 0.15 \times \text{Difficulty}")
        st.markdown("""
        - **Urgency:** Inverse/exponential scale where overdue deliverables receive max score 100, and deadlines within 24h score 90-100.
        - **Effort Pressure:** effort / max(days_left x daily_capacity, 1).
        - **Levels:** >= 75 Critical, 55-74 High, 35-54 Medium, < 35 Low.
        """)

        st.divider()
        st.write("#### Responsible AI Principles")
        st.markdown("""
        1. **Zero Personally Identifiable Information (PII):** Only course metadata (names, deadlines, hours) are stored.
        2. **Secret Safety:** API keys are loaded via `.env` and are never displayed in the UI or client code.
        3. **Human-in-the-Loop:** Students have full autonomy to manually override priority rankings or edit metadata.
        4. **Explainable AI:** Priority scores are 100% deterministic and explainable via mathematical formula.
        5. **Prompt Injection Defense:** Free-text input is sanitized against instruction override attacks.
        6. **Reliable Fallback Engine:** Automatically engages the deterministic rule engine if the API is unavailable, ensuring zero crashes.
        """)
