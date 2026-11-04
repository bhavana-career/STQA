# Defect Report Log — Student Result Management System (SRMS)

> **Note:** The defects documented below are **illustrative defect examples** demonstrating standard Software Testing and Quality Assurance (STQA) defect reporting and resolution practices across the development lifecycle. All defects documented here are resolved and verified as `Closed` in the current codebase.

---

## Defect 1 — Critical Rule Override on High Aggregate Percentage (Illustrative Example)

| Field | Details |
|---|---|
| **Defect ID** | `DEF-SRMS-001` |
| **Title** | High aggregate percentage (`>= 75%`) awards "Distinction" even when one subject is failed (`< 35` marks) |
| **Description** | During early prototype verification of `determine_classification()`, if a student scored `95` in five subjects and `28` in Mathematics (Total `= 503/600`, Percentage `= 83.83%`), checking percentage thresholds before checking individual subject pass status caused the student to be awarded `Distinction` instead of `Fail`. |
| **Steps to Reproduce** | 1. Log in as `teacher01`.<br>2. Open Marks Management for `STU003`.<br>3. Enter marks: Physics `82`, Chemistry `78`, Mathematics `28`, Computer Science `85`, Kannada `74`, English `79` (Total `= 426`, `71.00%`).<br>4. Observe computed overall classification. |
| **Expected Result** | Because Mathematics (`28`) is below the minimum passing mark (`35`), Overall Status MUST be `FAIL` and Classification MUST be `Fail`, while still displaying `71.00%`. |
| **Actual Result** | (In unpatched prototype logic) Classification displayed `First Class` based solely on `71.00% >= 60.0%`. |
| **Severity** | **Critical (S1)** — Violates core academic board examination pass rule. |
| **Priority** | **High (P1)** — Immediate fix required before release. |
| **Environment** | Windows 11, Python 3.11.9, Flask 3.1.3 (`app/services/result_service.py`) |
| **Status** | **Closed (Verified via `TC-010` and `test_high_aggregate_with_one_failed_subject_fails_overall`)** |

---

## Defect 2 — Empty Subject Mark Input Coerced to Zero (Illustrative Example)

| Field | Details |
|---|---|
| **Defect ID** | `DEF-SRMS-002` |
| **Title** | Blank subject mark input silently defaults to `0` instead of raising a validation error |
| **Description** | When a teacher accidentally cleared a mark input field and submitted the form using `int(val or 0)`, the empty string `""` was silently converted to `0` marks, causing an unintended `F` grade rather than prompting the teacher to enter the missing mark. |
| **Steps to Reproduce** | 1. Log in as `teacher01`.<br>2. Navigate to Marks Management.<br>3. Clear the `Kannada` mark field (`""`) and click Save. |
| **Expected Result** | Backend `validate_subject_mark()` rejects `""` or `None` with `MarksValidationError("Kannada mark cannot be empty.")`. |
| **Actual Result** | (In naive parsing) `Kannada` was saved as `0`. |
| **Severity** | **Major (S2)** — Corrupts student examination records silently. |
| **Priority** | **High (P1)** |
| **Environment** | Windows 11, Python 3.11.9 (`app/services/marks_service.py`) |
| **Status** | **Closed (Verified via `TC-004` and `test_missing_or_empty_marks_never_become_zero`)** |

---

## Defect 3 — Section Analytics Cross-Contamination (Illustrative Example)

| Field | Details |
|---|---|
| **Defect ID** | `DEF-SRMS-003` |
| **Title** | Section A average percentage calculation divides by total Class 10 student count instead of Section A student count |
| **Description** | When computing section-wise average percentage in `calculate_section_analytics()`, dividing the sum of Section A percentages by `len(all_students)` instead of `len(filtered_section_students)` artificially deflated the section average. |
| **Steps to Reproduce** | 1. Log in as `teacher01`.<br>2. Navigate to Class Analytics (`/teacher/analytics?section=A`).<br>3. Compare displayed Section A average percentage against manual mean of Section A students. |
| **Expected Result** | Section A average percentage equals `Sum(Section A Percentages) / Count(Section A Students)`. |
| **Actual Result** | (In unpatched prototype) Denominator included Section B and Section C students. |
| **Severity** | **Major (S2)** — Produces inaccurate section analytics. |
| **Priority** | **Medium (P2)** |
| **Environment** | Windows 11, Python 3.11.9 (`app/services/analytics_service.py`) |
| **Status** | **Closed (Verified via `TC-023` and `test_workflow_4_section_analytics_strict_isolation`)** |

---

## Defect 4 — Celebratory Popup Repeating on Every Page Refresh (Illustrative Example)

| Field | Details |
|---|---|
| **Defect ID** | `DEF-SRMS-004` |
| **Title** | Student celebratory result popup re-appears on every navigation click within the same login session |
| **Description** | When a passing student (`student01`) clicked between "My Dashboard", "My Results", and "Grading Matrix", the celebratory modal popup appeared repeatedly because `session["popup_shown"]` was not tracked. |
| **Steps to Reproduce** | 1. Log in as `student01`.<br>2. Dismiss the celebratory popup.<br>3. Click "My Dashboard" in the sidebar. |
| **Expected Result** | Popup appears once upon initial login to the Student Dashboard and remains suppressed for the remainder of the session. |
| **Actual Result** | (Before session flag implementation) Popup re-triggered on every dashboard visit. |
| **Severity** | **Minor (S3)** — Degrades student user experience. |
| **Priority** | **Medium (P2)** |
| **Environment** | Windows 11, Chrome Browser, Flask Session (`app/routes/student.py`) |
| **Status** | **Closed (Verified via `TC-021` and `test_student_login_and_popup_session_behavior`)** |

---

## Defect 5 — Scroll-Viewport Click Interception in Headless Selenium E2E (Actual Test Automation Issue Resolved)

| Field | Details |
|---|---|
| **Defect ID** | `DEF-SRMS-005` |
| **Title** | Selenium `ElementClickInterceptedException` when clicking buttons below the fold in headless Chrome |
| **Description** | During the initial execution of `tests/e2e/`, clicking `#saveStudentBtn` and `#logoutBtn` after scrolling or multi-page navigation timed out because `BasePage.click()` invoked `el.click()` without scrolling the element into the viewport center. |
| **Steps to Reproduce** | 1. Run `pytest tests/e2e -v` with unpatched `BasePage.click()`. |
| **Expected Result** | `BasePage.click()` scrolls the target element into center view and dispatches the click reliably. |
| **Actual Result** | `TimeoutException` waiting for post-click navigation. |
| **Severity** | **Minor (S3)** — Test automation harness synchronization issue. |
| **Priority** | **High (P1)** |
| **Environment** | Windows 11, Selenium 4.52.0, Headless Chrome (`tests/e2e/pages/__init__.py`) |
| **Status** | **Closed (Verified by re-running `pytest tests/e2e -v` — 100% pass)** |
