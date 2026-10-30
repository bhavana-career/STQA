# Exercise 7: Student Result Calculation Test Plan (IEEE 829 Standard)

---

## 1. Exercise Objective

1. Document the complete business and grading rules for the Student Result Management System (SRMS), covering marks validation, complete vs. incomplete states, pass/fail criteria, and grade boundaries.
2. Formulate test cases covering critical edge cases (e.g., student failing one subject despite achieving an overall aggregate percentage of 85%).
3. Author a formal **IEEE 829 Standard Test Plan** specifically governing Result Calculation and Marks Processing.
4. Provide verifiable execution evidence tracing test cases directly to automated unit test suites.

---

## 2. Business & Grading Specification

### 2.1 Grading Scale (Provisional Demo Rules)

| Percentage Range | Assigned Grade | Description | Minimum Passing Status |
|:---:|:---:|:---:|:---:|
| **90.00% – 100.00%** | **A1** | Outstanding / Distinction | Pass |
| **80.00% – 89.99%** | **A2** | Excellent | Pass |
| **70.00% – 79.99%** | **B1** | Very Good | Pass |
| **60.00% – 69.99%** | **B2** | Good | Pass |
| **50.00% – 59.99%** | **C1** | Above Average | Pass |
| **40.00% – 49.99%** | **C2** | Average | Pass |
| **35.00% – 39.99%** | **D** | Minimum Pass | Pass |
| **0.00% – 34.99%** | **E** | Unsatisfactory | **Fail** |

### 2.2 Critical Result Calculation Business Rules

1. **Individual Subject Pass Rule:** A student must secure a minimum of **35% of the maximum marks** in *every single subject* registered for the exam. For a 100-mark paper, the minimum pass threshold is exactly `35.0` marks.
2. **Overall Pass Requirement:** Overall result is **PASS** if and only if:
   - All subjects are evaluated (no missing marks), AND
   - Obtained marks in **every single subject** $\ge 35\%$, AND
   - Overall percentage $\ge 35.00\%$.
3. **The Single-Subject Failure Edge Case:** If a student scores `100/100` in four subjects but `34.5/100` in the fifth subject, their overall percentage is:
   $$\frac{100 + 100 + 100 + 100 + 34.5}{500} \times 100 = 86.90\%$$
   Even though `86.90%` corresponds to Grade `A2`, the overall result status is strictly **FAIL** (or "FAIL (Needs Improvement / Compartment)"), and Grade is assigned as `E` because of the failure in the single subject.
4. **Complete vs. Incomplete State:** If marks for any registered subject are missing or not yet entered by the teacher, the calculation engine does not generate a partial grade. It designates the result status as **INCOMPLETE** with percentage and grade set to `None`.
5. **Precision & Rounding:** All marks are recorded with step increments of `0.5`. Percentages are computed using `Decimal` arithmetic with standard commercial rounding (`ROUND_HALF_UP`) to two decimal places.

---

## 3. IEEE 829 Standard Test Plan: Result Calculation Subsystem

### 1. Test Plan Identifier
`STQA-TP-SRMS-CALC-002` (Version 1.0)

### 2. References
- IEEE Std 829-2008 Standard for Software and System Test Documentation
- SRMS Requirements Specification (`docs/requirements.md#section-4`)
- SRMS Grading Services Implementation (`app/services/grading.py`)

### 3. Introduction
This test plan specifies the testing criteria, test scenarios, and pass/fail thresholds for the core mathematical and business logic engine of SRMS. The engine calculates student totals, determines percentages across non-uniform subject weights, evaluates individual and overall pass criteria, and maps results to letter grades.

### 4. Test Items
- `app/services/grading.py`: Functions `validate_marks_entry()`, `total_obtained()`, `total_max()`, `percentage()`, `grade_for_percentage()`, and `compute_result()`.
- `app/services/marks_service.py`: Service orchestration for marks entry and recalculation.

### 5. Software Risk Issues
- **Risk 1: Floating-point precision inaccuracy.** (Mitigation: Mandate Python `decimal.Decimal` with explicit rounding).
- **Risk 2: Misclassification of failing student as passed due to high aggregate average.** (Mitigation: Strict iterative individual subject pass guard).
- **Risk 3: Unhandled division by zero when total maximum marks is zero.** (Mitigation: Explicit zero divisor guard raising domain `ValueError`).

### 6. Features to be Tested
- Calculation of total marks obtained and total maximum possible marks.
- Accurate percentage calculation rounded to 2 decimal places.
- Grade assignment across all 8 grade intervals and boundaries.
- Individual subject pass threshold verification (`obtained >= 0.35 * max`).
- Handling of incomplete result sets where one or more subjects lack marks.
- Rejection of invalid inputs (negative marks, marks > max, invalid step intervals).

### 7. Features Not to be Tested
- Graphical display and CSS rendering of the result modal (tested in E2E suite).
- Teacher authentication and database connection retries (tested in integration suite).

### 8. Approach (Strategy)
Testing is executed using pytest at the unit test tier. Functions in `app/services/grading.py` are pure functions devoid of side-effects or database I/O, allowing exhaustive parameterized combinatorial testing across:
- All boundary points (0.0, 34.5, 35.0, 89.9, 90.0, 100.0).
- Mixed subject maximum weights (e.g., 50-mark lab + 100-mark theory).
- High-average single-subject failure scenarios.

### 9. Item Pass/Fail Criteria
- **Pass:** 100% of parameterized test cases match expected outputs; zero calculation drift; 100% branch coverage on `app/services/grading.py`.
- **Fail:** Any incorrect grade assignment, failure to flag incomplete state, or improper pass status.

### 10. Suspension Criteria and Resumption Requirements
- **Suspension:** Syntax errors in grading service preventing test suite import.
- **Resumption:** Service code compiles and clean test collection succeeds.

### 11. Test Deliverables
- Unit Test Suite: [`tests/unit/test_grading.py`](file:///c:/Users/bhava/Downloads/ST&QA/tests/unit/test_grading.py).
- Marks Validation Suite: [`tests/unit/test_marks_validation.py`](file:///c:/Users/bhava/Downloads/ST&QA/tests/unit/test_marks_validation.py).
- Test Execution Log and Coverage Artifacts.

### 12. Remaining Test Tasks
- Automated stress test calculating 10,000 student results in a batch job.

### 13. Environmental Needs
- Python 3.11.9, pytest 9.2.0, pytest-cov 7.1.0.

### 14. Staffing and Training Needs
- QA Engineer with knowledge of academic grading systems and Python `decimal` module.

### 15. Responsibilities
- **Test Author:** Bhavya (STQA Lab).
- **Verification:** Continuous Automated pytest runner.

### 16. Schedule
- Milestone M2 (Grading Core TDD): Completed.
- Milestone M8 (Academic Documentation & Sign-off): Completed.

### 17. Approvals
- Approved by QA Lead upon 100% test pass verification.

---

## 4. Test Case Matrix & Actual Test Execution Evidence

| Test Case ID | Test Description | Input Marks | Expected Percentage | Expected Grade | Expected Pass | Automated Test Function |
|---|---|---|:---:|:---:|:---:|---|
| **TC-CALC-01** | All subjects distinction | `[95, 92, 90]` (max 100 each) | `92.33%` | `A1` | `True` | `test_grading.py::test_compute_result_pass_a1` |
| **TC-CALC-02** | Exact minimum pass marks | `[35, 35, 35]` (max 100 each) | `35.00%` | `D` | `True` | `test_grading.py::test_compute_result_pass_minimum_boundary` |
| **TC-CALC-03** | High aggregate with 1 fail | `[100, 100, 34.5]` (max 100 each)| `78.17%` | `E` | `False` | `test_grading.py::test_compute_result_fail_one_subject_high_average` |
| **TC-CALC-04** | Non-uniform subject weights | Sub 1: `40/50`, Sub 2: `75/100` | `76.67%` | `B1` | `True` | `test_grading.py::test_compute_result_non_uniform_maxima` |
| **TC-CALC-05** | Incomplete result set | Sub 1: `80/100`, Sub 2: `None` | `None` | `None` | `False` (`INCOMPLETE`) | `test_grading.py::test_compute_result_incomplete_marks` |
| **TC-CALC-06** | Zero total marks obtained | `[0, 0, 0]` (max 100 each) | `0.00%` | `E` | `False` | `test_grading.py::test_compute_result_all_zeros` |

```text
============================= test session starts =============================
tests/unit/test_grading.py ............................................ [100%]
============================== 44 passed in 0.08s ==============================
```
