# Live Demonstration Script & Viva Preparation Guide

**Project:** Academic Deadline Management Assistant  
**Duration:** 4 Minutes Timed Walkthrough + Viva Q&A

---

## 1. Timed 4-Minute Walkthrough

### [0:00 - 0:30] Introduction & Problem Statement
- **Visual:** Open Streamlit dashboard at `http://localhost:8501`. Point out the clean UI, metrics cards, and sidebar settings.
- **Spoken Script:**
  > *"Good morning. University students routinely face multiple competing assignment deadlines across 4 to 6 simultaneous courses. Without intelligent scheduling, students experience last-minute submission panic, overlooked prerequisites, and burnout. Our Academic Deadline Management Assistant solves this by combining deterministic mathematical prioritization and algorithmic conflict detection with Google Gemini AI for contextual study planning and unstructured extraction."*

### [0:30 - 1:15] Tab 1: Intake & Free-Text Extraction
- **Action:** Click sidebar button **"Load Demo"** (or paste free-text: *"DBMS assignment due Friday 5pm, 6 hrs, worth 15%, difficulty 4. ML quiz tomorrow 10am, 2 hrs, worth 10%."* and click **"Extract Tasks"**).
- **Spoken Script:**
  > *"Students can enter tasks manually via a validated form, bulk-import CSVs, or paste unstructured text from a syllabus or syllabus chat. Notice how our extraction engine normalizes the text into structured JSON with course codes, estimated effort, weight, and deadlines, presenting a confirmation preview table before database insertion. Input validation prevents negative hours, invalid dates, and duplicates."*

### [1:15 - 2:00] Tab 2: Prioritized Task Tracker
- **Action:** Navigate to **"2. Prioritized Tracker"**. Point to the color-coded priority levels, scores, days left, and the AI rationale column.
- **Spoken Script:**
  > *"Here is the core deliverable: a dynamically ranked task tracker. Our formula balances urgency, course weight, effort pressure, and difficulty on a transparent 0 to 100 scale. Tasks are categorized into Critical, High, Medium, and Low. Students can filter by course, change status, or exercise human-in-the-loop priority override, ensuring student autonomy."*

### [2:00 - 2:30] Tab 3: Conflicts & Workload Visualization
- **Action:** Switch to **"3. Conflicts"**. Highlight the detected same-day clash, workload overload, and the Plotly Gantt/workload chart.
- **Spoken Script:**
  > *"In Tab 3, our algorithmic conflict detector pinpoints two tasks due on the exact same hour, as well as an overload condition where required effort exceeds the student's daily study capacity. The Plotly chart visualizes required effort versus capacity over a 7-day horizon, while providing practical resolution steps."*

### [2:30 - 3:00] Tab 4 & Tab 5: AI Study Plan & Prompt Lab
- **Action:** Quickly show **"4. AI Study Plan"** (day-by-day table), then click into **"5. Prompt Lab"** and click **"Run Prompt Comparison Experiment"**.
- **Spoken Script:**
  > *"Tab 4 generates a capacity-constrained 7-day schedule allocating study blocks day by day. In Tab 5, our Prompt Lab provides empirical evidence for Criterion 2. We run prompt versions v1, v2, and v3 on identical data. As the bar chart demonstrates, v3 wins with a perfect 10/10 rubric score, eliminating hallucinations through negative constraints and structured schema enforcement."*

### [3:00 - 3:30] Tab 6: Validation & Tests
- **Action:** Switch to **"6. Validation & Tests"** and click **"Run All Tests"**.
- **Spoken Script:**
  > *"Under Tab 6, our 10-point verification rubric runs against our 5 documented test cases (TC1 to TC5), covering normal tasks, clashes, overloads, edge cases, and prompt injection attacks. All 5 test cases pass 100% in both AI mode and deterministic fallback mode, generating auditable evidence in CSV and Markdown."*

### [3:30 - 4:00] Tab 7 & Tab 8: Automation Firing & Wrap-Up
- **Action:** Switch to **"7. Automation & Logs"**, click **"Simulate Urgent Trigger"**, show live log table updating and outbox message, then conclude in **"8. About"**.
- **Spoken Script:**
  > *"Finally, Tab 7 implements trigger-condition-action automation. When a task is due within 48 hours or flagged Critical, the engine automatically generates an RFC 5545 iCalendar (.ics) file and dispatches an alert email to the outbox. The system operates with zero crashes, robust fallback, and zero PII collection. Thank you, and I look forward to your questions."*

---

## 2. Likely Viva Questions & Answers

### Q1: Why did you use a deterministic mathematical formula for priority scoring instead of letting the LLM decide?
> **Answer:** *"Scoring must be reproducible, explainable, and instantaneous. An LLM is stochastic; the same student checking their dashboard twice could receive different priority rankings, eroding trust. Moreover, mathematical scoring runs in sub-millisecond time at zero API cost. We reserve the LLM for qualitative reasoning, explanation synthesis, and unstructured text parsing where generative capabilities provide the greatest leverage."*

### Q2: How does the priority scoring formula work?
> **Answer:** *"The formula is: $\text{Score} = 0.40 \times \text{Urgency} + 0.25 \times \text{Weight} + 0.20 \times \text{Effort Pressure} + 0.15 \times \text{Difficulty}$, normalized to $0-100$. Urgency uses an exponential/inverse-days scale where overdue tasks receive 100 and deadlines within 24h score 90-100. Effort pressure evaluates effort hours relative to available study hours before the deadline. Tasks scoring $\ge 75$ are flagged Critical."*

### Q3: What specific issues did you identify in Prompt v1, and how did Prompt v3 solve them?
> **Answer:** *"Prompt v1 was a naive zero-shot prompt. It frequently produced unstructured markdown, hallucinated non-existent task IDs, and wrote lengthy paragraphs. Prompt v3 resolved this by defining a strict JSON schema, providing two concrete few-shot examples, enforcing explicit negative constraints ('use ONLY provided task IDs', 'never invent dates'), and decomposing the cognitive process into Analyze -> Rank -> Risk-Detect -> Recommend."*

### Q4: How does the 10-point Verification Rubric in `validator.py` work?
> **Answer:** *"The rubric awards: 2 points for valid JSON matching schema; 2 points for zero hallucinated task IDs (strict subset check); 1 point for complete coverage of all input tasks; 1 point for data accuracy; 2 points for ranking agreement with deterministic reference rankings; 1 point for conflict alignment; and 1 point for concise rationales ($\le 25-35$ words). A score of $\ge 8/10$ is required to pass; otherwise the system auto-corrects or activates deterministic fallback."*

### Q5: How does the system handle API failures, network dropouts, or invalid API keys?
> **Answer:** *"The application features a seamless fallback mode. In `llm_client.py`, every API call is wrapped with error and timeout handling. If the key is invalid, missing, or blocked by billing quotas, the system automatically falls back to our deterministic rule-based engine and marks the UI with a visible 'AI Fallback Mode' badge. The app never crashes and all functionality remains 100% operational."*

### Q6: How is data structured and persisted in SQLite?
> **Answer:** *"We maintain 7 normalized relational tables in `assistant.db`: `tasks` (raw inputs and overrides), `scored_tasks` (computed scores, ranks, and levels), `conflicts` (detected clashes and overload details), `ai_runs` (prompt version, raw output, latency, mode), `evaluations` (rubric breakdown and pass status), `test_results` (documented test execution logs), and `automation_log` (audit trail of triggers and actions). Every table can be exported to CSV or Excel."*

### Q7: Describe your trigger-condition-action automation workflow.
> **Answer:** *"The trigger can be a task database update, a manual click, or our standalone cron CLI script (`automation_runner.py`). The condition checks whether any unfinished task is due within 48 hours, has Critical priority, or has an active conflict. If matched, the action logs the event, exports an RFC 5545 `.ics` calendar to `/exports`, and dispatches an alert email via SMTP or writes an RFC 822 `.eml` message to `/outbox` for offline verification."*

### Q8: What are the key limitations of this system and opportunities for future enhancement?
> **Answer:** *"Currently, effort hours are student-estimated rather than dynamically learned from past task completion times. In future iterations, we could integrate calendar two-way synchronization via Google Calendar/Outlook APIs, incorporate task dependency graphs (e.g. prerequisite milestones), and train personalized effort prediction models based on a student's historical pace."*

