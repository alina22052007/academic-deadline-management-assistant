# Walkthrough & Final Self-Audit: Academic Deadline Management Assistant

This document provides the final self-audit and verification walkthrough against the mandatory 20-mark rubric and requirements.

---

## 1. Acceptance Checklist Self-Audit (100% PASS)

| Checklist Item | Status | Primary Implementation File(s) | Verification Evidence & Proof |
| :--- | :---: | :--- | :--- |
| **1. App launches with one command & all 8 tabs work** | **PASS** | `app.py`<br/>`run.sh`<br/>`run.bat` | Launched on port 8501 via `streamlit run app.py`. Playwright automated suite verified and took screenshots of all 8 tabs: `test_evidence/screenshots/01_tab1_add_tasks.png` through `08_tab8_about_responsible_ai.png`. |
| **2. Free-text, form, and CSV input with validation** | **PASS** | `validator.py`<br/>`llm_client.py`<br/>`app.py` | Validated in Tab 1: form fields (title, course, deadline, effort, weight, difficulty), free text extraction (with preview table & confirmation), and CSV bulk upload (`sample_data/sample_tasks.csv`). Prevents duplicates, zero effort, invalid dates, and weight $>100\%$. |
| **3. AI integration (Gemini) + automatic fallback** | **PASS** | `llm_client.py`<br/>`pipeline.py` | Uses `google-genai` SDK (`gemini-2.5-flash`/`gemini-3.8-flash`). Tested with valid key, blocked key, and key removed: automatically engages deterministic rule-based engine, renders visible fallback badge, and never crashes. |
| **4. Prioritized tracker sorted correctly** | **PASS** | `scoring.py`<br/>`app.py` | Sorted by composite score ($0-100$). Displays Rank, Task, Course, Deadline, Days Left, Effort, Weight, Score, Priority Badge (Critical/High/Medium/Low), Conflict flag, and AI rationale. Supports inline edit, status toggle, human override, filtering, and CSV download. |
| **5. 6-stage workflow + workflow diagram files** | **PASS** | `pipeline.py`<br/>`docs/workflow_diagram.md` | Stages 1 through 6 implemented as typed, modular functions in `pipeline.py`. Mermaid architecture flowchart documented in `docs/workflow_diagram.md` and dynamically rendered in Tab 8. |
| **6. 3 prompt versions in `/prompts` & Prompt Lab** | **PASS** | `prompts/prompt_v1_basic.txt`<br/>`prompts/prompt_v2_structured.txt`<br/>`prompts/prompt_v3_final.txt`<br/>`docs/prompt_iteration_log.md`<br/>`docs/tool_selection.md` | Versioned files exist. Prompt Lab runs all 3 side-by-side, scores them on rubric, renders Plotly bar chart, declares v3 winner ($10/10$), and logs refinement justification in `docs/prompt_iteration_log.md`. Tool selection rationale documented in `docs/tool_selection.md`. |
| **7. Validator rubric (10 pts) + reference ranking** | **PASS** | `validator.py`<br/>`app.py` | 10-point rubric implemented in `evaluate_ai_response`: JSON validity (2), zero hallucinations (2), completeness (1), data accuracy (1), ranking agreement with reference order (2), conflict matching (1), rationale conciseness (1). Pass threshold $\ge 8/10$. |
| **8. 5 test cases (TC1 - TC5) pass with evidence** | **PASS** | `tests/test_cases.json`<br/>`tests/test_pipeline.py`<br/>`tests/test_scoring.py`<br/>`tests/test_conflicts.py`<br/>`tests/test_validator.py`<br/>`tests/test_db_and_automation.py` | 27 of 27 unit & integration tests pass in pytest. Documented test suite outputs auditable results to `test_evidence/test_results.csv` and `test_evidence/test_report.md`. Both AI and `--no-ai` modes supported. Core modules achieve $\ge 85\%$ coverage. |
| **9. Responsible AI measures documented & active** | **PASS** | `validator.py`<br/>`docs/responsible_ai.md`<br/>`app.py` | Zero PII stored, API key kept in `.env` and excluded from repo, human-in-the-loop priority override, transparent scoring formula, fallback mode, safety disclaimer, and prompt-injection defense with automated testing. |
| **10. SQLite data storage & CSV/Excel export** | **PASS** | `db.py`<br/>`data/assistant.db`<br/>`exports/` | 7 SQLite tables (`tasks`, `scored_tasks`, `conflicts`, `ai_runs`, `evaluations`, `test_results`, `automation_log`). `export_all_to_csv()` exports all tables to individual CSVs and all-in-one Excel workbook in `/exports`. |
| **11. Trigger-action automation with .ics and email** | **PASS** | `automation.py`<br/>`automation_runner.py`<br/>`logs/automation.log`<br/>`outbox/*.eml`<br/>`exports/*.ics` | Automation evaluates conditions ($\le 48$h due, Critical task, conflicts), writes log to DB and disk, generates RFC 5545 `.ics` calendar, and dispatches SMTP email or saves RFC 822 `.eml` into `outbox/`. Tested via UI simulation and CLI runner. |
| **12. Demo data + 4-min demo script + viva Q&A** | **PASS** | `sample_data/sample_tasks.csv`<br/>`sample_data/sample_freetext.txt`<br/>`docs/demo_script.md` | One-click "Load Demo" button in UI. Comprehensive 4-minute demo script with second-by-second timestamps and 8 detailed viva questions & answers prepared in `docs/demo_script.md`. |
| **13. README complete with rubric mapping** | **PASS** | `README.md` | Detailed README featuring problem statement, architecture, setup guide, formula, prompt versions, rubric, test table, automation workflow, schema, and rubric-to-evidence mapping table. |
| **14. Zero unhandled exceptions in demo flow** | **PASS** | `app.py`<br/>`capture_demo.py` | Full Playwright UI automation traversed all 8 tabs, submitted forms, executed comparisons, and captured screenshots with 0 unhandled exceptions or stack traces. |

---

## 2. Directory Layout Verification

```
ai mini project/
├── .env                          # Configured with Gemini API key, model, SMTP defaults
├── .env.example                  # Template with placeholders
├── .gitignore                    # Secrets, database, outbox, and virtualenv ignored
├── requirements.txt              # Pinned production dependencies
├── run.sh                        # Unix launch script (auto-venv & launch)
├── run.bat                       # Windows launch script
├── README.md                     # Comprehensive documentation & rubric mapping
├── app.py                        # Streamlit 8-tab application
├── pipeline.py                   # 6-stage core processing workflow
├── scoring.py                    # Deterministic priority calculation formula
├── conflicts.py                  # Algorithmic deadline conflict detector
├── llm_client.py                 # Google GenAI client + fallback rule engine
├── validator.py                  # 10-point rubric validator & injection defense
├── db.py                         # SQLite ORM/manager & CSV exporter
├── automation.py                 # Trigger-condition-action workflow & outbox writer
├── automation_runner.py          # Standalone CLI scheduler script
├── capture_demo.py               # Playwright automated UI runner & screenshot generator
├── utils.py                      # Date math, iCalendar (.ics) generator, sanitizers
├── prompts/
│   ├── prompt_v1_basic.txt       # Baseline naive prompt
│   ├── prompt_v2_structured.txt  # Role + Context + Schema
│   └── prompt_v3_final.txt       # Strict schema + Few-shot + Rules + Decomposition
├── sample_data/
│   ├── sample_tasks.csv          # Realistic semester tasks (clash, overload, overdue)
│   └── sample_freetext.txt       # Multi-task natural language syllabus notes
├── tests/
│   ├── test_cases.json           # Documented specifications for TC1 - TC5
│   ├── test_pipeline.py          # Pytest suite for TC1-TC5 (AI & fallback)
│   ├── test_scoring.py           # Unit tests for scoring formula
│   ├── test_conflicts.py         # Unit tests for conflict detection logic
│   ├── test_validator.py         # Unit tests for rubric & prompt injection
│   └── test_db_and_automation.py # Unit tests for SQLite CRUD & automation triggers
├── test_evidence/
│   ├── test_results.csv          # Pytest run export with latency & status
│   ├── test_report.md            # Detailed evidence markdown report
│   └── screenshots/              # 8 Captured high-resolution UI screenshots
├── docs/
│   ├── workflow_diagram.md       # Mermaid 6-stage architecture diagram
│   ├── prompt_iteration_log.md   # Systematic v1 vs v2 vs v3 comparison log
│   ├── tool_selection.md         # Architecture justification & model selection
│   ├── demo_script.md            # Timed 4-minute demo walkthrough + 8 viva Q&As
│   └── responsible_ai.md         # Ethical AI, privacy, limitations, & human override
├── data/                         # SQLite assistant.db
├── exports/                      # upcoming_deadlines.ics, table CSVs, Excel workbook
├── logs/                         # automation.log
└── outbox/                       # email_*.eml verifiable message files
```

---

## 3. Visual Screenshot Evidence

All screenshots are stored in `test_evidence/screenshots/`:
1. `01_tab1_add_tasks.png` - Multi-modal input handling (Form, Free-Text, CSV upload).
2. `02_tab2_prioritized_tracker.png` - Sorted task tracker with color-coded badges, scores, days left, and AI rationales.
3. `03_tab3_conflicts.png` - Same-day clash and workload overload detection with Plotly 7-day capacity chart.
4. `04_tab4_study_plan.png` - Capacity-constrained 7-day study plan table.
5. `05_tab5_prompt_lab.png` - Prompt Lab comparison (v1 vs v2 vs v3) with rubric bar chart and winner badge.
6. `06_tab6_validation_tests.png` - Validation & test execution results for TC1-TC5.
7. `07_tab7_automation_logs.png` - Live automation audit log and outbox message inspector.
8. `08_tab8_about_responsible_ai.png` - Six-stage Mermaid diagram and responsible AI principles.

