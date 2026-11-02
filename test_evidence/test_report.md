# Academic Deadline Management Assistant - Test Verification Report

**Execution Timestamp:** 2026-11-02 01:03:04

**Execution Mode:** Deterministic Fallback Mode (--no-ai)

## Documented Test Cases Summary (TC1 - TC5)

| Test ID | Test Name | Status | Latency | Expected Result | Actual Result | Rubric Score |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **TC1** | Normal Tasks - Distinct Deadlines | ✅ PASS | 0.2 ms | 0 conflicts, top task 'Task A' | 0 conflicts, top task 'Task A' (Score: 53.7) | 10.0/10 |
| **TC2** | Same-Day / Same-Hour Deadline Clash | ✅ PASS | 0.1 ms | At least 1 conflict with type 'SAME_DAY_CLASH' | 1 conflict(s) detected: ['SAME_DAY_CLASH'] | 10.0/10 |
| **TC3** | Workload Overload | ✅ PASS | 0.0 ms | WORKLOAD_OVERLOAD conflict + 'Critical' priority | Conflict: ['WORKLOAD_OVERLOAD'], Priority: 'Critical' (Score: 75.8) | 10.0/10 |
| **TC4** | Edge Cases & Prompt Injection Resilience | ✅ PASS | 0.1 ms | Validation catches invalid inputs, rejects duplicate, flags prompt-injection | Caught 3 validation errors, duplicate rejected, injection flagged: True | 10.0/10 |
| **TC5** | Free-Text Extraction | ✅ PASS | 0.1 ms | Exactly 4 structured tasks extracted | Extracted 4 tasks via fallback. Courses: ['CS340', 'CS470', 'CS350', 'CS301'] | 10.0/10 |

### Overall Verification: 100% ALL TESTS PASSED
