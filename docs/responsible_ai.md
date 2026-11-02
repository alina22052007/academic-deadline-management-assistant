# Responsible AI & Safety Framework

The Academic Deadline Management Assistant is engineered adhering to rigorous ethical and safety standards for AI-assisted educational technology.

---

## 1. Principles & Safeguards Implemented

### 1. Privacy by Design & Zero PII Collection
- The application processes strictly task-level academic metadata: task title, course code, deadline timestamp, estimated hours, and grade percentage.
- No personally identifiable information (PII) such as student names, student IDs, GPA records, email credentials, or university IDs are collected, stored, or transmitted to any third-party API.

### 2. Secret Protection & Secure Credential Handling
- API keys are managed exclusively through environment variables loaded via `python-dotenv` from a `.env` file.
- The API key is never hardcoded, never logged to disk, never rendered in the Streamlit UI, and `.env` is explicitly ignored in `.gitignore`.

### 3. Human-in-the-Loop Autonomy & Override
- Automated recommendations must never dictate student decision-making without recourse.
- Students possess complete authority to override computed priority levels (e.g. promoting an assignment from Low to Critical, or demoting a task).
- All human overrides are permanently stored in the `tasks` table (`user_priority_override` column) and directly respected by subsequent scoring and ranking cycles.

### 4. Mathematical Explainability vs. Black-Box Scoring
- Task prioritization is 100% deterministic, explainable, and reproducible through an open mathematical formula.
- The weights ($40\%$ Urgency, $25\%$ Weight, $20\%$ Effort Pressure, $15\%$ Difficulty) are documented in the UI and README, allowing students to understand exactly why tasks are ordered.
- Generative AI is strictly restricted to qualitative rationales and text extraction.

### 5. Prompt-Injection Defense & Input Sanitization
- In the free-text input module, untrusted natural language is pre-processed by `sanitize_free_text_input()` in `validator.py`.
- Known command override signatures (e.g. *"ignore previous instructions"*, *"delete all tasks"*, *"reveal API key"*, *"drop table"*) are intercepted and redacted before model ingestion.
- The system instructions explicitly instruct the language model to treat student text strictly as inert data entities rather than executable system directives.

### 6. Resilience & Deterministic Fallback Mode
- Educational tools must remain reliable regardless of third-party network conditions or quota limitations.
- If the Gemini API call encounters network disconnects, latency timeouts, or authentication errors, the application automatically engages its deterministic rule-based fallback engine.
- A prominent badge (*"AI Fallback Mode"*) notifies the student, ensuring zero application crashes and uninterrupted productivity.

### 7. Clear AI Disclaimer
- A visible notice reminds students:  
  > *"AI-generated recommendations and study schedules are advisory tools. Verify deadlines and requirements against your official course syllabus before making academic decisions."*

---

## 2. Limitations & Ethical Considerations
- **Student-Reported Effort:** Estimated hours are subjective and depend on individual student experience.
- **Cognitive Load:** The system treats hours uniformly; it does not currently model cognitive fatigue across differing course topics.
- **Equitable Access:** Offline deterministic fallback guarantees that students without consistent high-speed internet access or paid API subscriptions maintain access to all core prioritization capabilities.

