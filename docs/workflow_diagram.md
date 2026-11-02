# Academic Deadline Management Assistant - Workflow Architecture

The system processes student workload through a 6-stage end-to-end pipeline designed for mathematical rigor, deterministic explainability, and intelligent contextual assistance.

```mermaid
flowchart TD
    subgraph S1["Stage 1: Intake & Extraction"]
        UI_Form["Structured Form"] --> Validator["Input Validator & Pydantic Sanitizer"]
        UI_CSV["CSV Upload"] --> Validator
        UI_Text["Natural Language Free Text"] --> LLM_Extract["Gemini Flash Parser / Fallback Regex"]
        LLM_Extract --> Validator
    end

    subgraph S2["Stage 2: Deterministic Priority Scoring"]
        Validator --> Scoring["Multi-Factor Scoring Formula<br/>0.40*Urgency + 0.25*Weight + 0.20*Effort + 0.15*Difficulty"]
        Scoring --> PriorityLevels["Priority Levels:<br/>Critical (>=75) | High (55-74) | Medium (35-54) | Low (<35)"]
    end

    subgraph S3["Stage 3: Algorithmic Conflict Detection"]
        PriorityLevels --> ConflictEngine["Deterministic Conflict Engine"]
        ConflictEngine --> Clash["(a) Same-Day/Hour Clash"]
        ConflictEngine --> Overload["(b) Greedy Backward Overload"]
        ConflictEngine --> Cluster["(c) 48h Cluster Conflict (3+ tasks)"]
        ConflictEngine --> Overdue["(d) Overdue Unfinished Tasks"]
    end

    subgraph S4["Stage 4: AI Reasoning & Planning"]
        Clash & Overload & Cluster & Overdue --> LLM_Reasoning["Gemini 2.5 Flash / Fallback Engine<br/>Prompt v3 Final (Few-Shot, Decomposition)"]
        LLM_Reasoning --> AI_Output["Strict JSON:<br/>1. Task Rationales<br/>2. Conflict Resolutions<br/>3. Capacity-Constrained 7-Day Plan"]
    end

    subgraph S5["Stage 5: Rubric Verification"]
        AI_Output --> Rubric["10-Point Verification Rubric (validator.py)"]
        Rubric -- "Score >= 8/10 (Pass)" --> Verified["Verified Output"]
        Rubric -- "Score < 8/10 (Fail)" --> AutoCorrect["Auto-Correct & Deterministic Fallback"]
        AutoCorrect --> Verified
    end

    subgraph S6["Stage 6: Persistence & Automation"]
        Verified --> SQLite["SQLite Database (assistant.db)"]
        SQLite --> Tables["7 Normalized Tables & CSV Exports"]
        Verified --> AutoEngine["Automation Engine (Trigger-Condition-Action)"]
        AutoEngine --> ICS["RFC 5545 iCalendar (.ics)"]
        AutoEngine --> Notification["SMTP Email Dispatch / outbox/*.eml"]
        AutoEngine --> LiveLog["Automation Event Log"]
    end
```

---

## Stage Descriptions
1. **Stage 1 (Intake & Extraction):** Normalizes inputs from interactive form submissions, CSV uploads, or free-text syllabus descriptions. Employs prompt-injection defenses and type constraints.
2. **Stage 2 (Priority Scoring):** Computes normalized 0-100 priority scores deterministically using an explainable mathematical formula combining urgency, grade weight, effort pressure, and course difficulty.
3. **Stage 3 (Conflict Detection):** Algorithmic rules independently evaluate deadlines against student daily study capacity to detect same-day collisions, capacity deficits, deadline clusters, and overdue tasks.
4. **Stage 4 (AI Reasoning):** Generates concise rationales per task, actionable conflict resolutions, and an adaptive 7-day schedule respecting daily study hours.
5. **Stage 5 (Rubric Verification):** Evaluates AI output against 7 rubric checks (10 points total). Guarantees zero task hallucinations and ranking agreement; engages deterministic fallback if score < 8/10.
6. **Stage 6 (Persistence & Automation):** Persists all states to SQLite, generates downloadable iCalendar files, and dispatches automated email alerts or outbox files when urgent conditions are met.

