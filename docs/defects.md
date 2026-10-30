# STQA Defect Tracking Log & Intentional Fault Records

This document tracks intentional defect injections and fixes for the Student Result Management System (SRMS).
In accordance with STQA laboratory practices, intentional defects are implemented in isolated modules (`fault_injection/`) and never included in production code.

---

## Defect Summary Table

| Defect ID | Summary | Severity | Priority | Status | Detecting Test | Regression Test |
|---|---|---|---|---|---|---|
| **DEF-001** | Incorrect percentage denominator assumption (`count * 100` instead of `sum(max_marks)`) | High | P1 | **Closed** (Verified) | `fault_injection/tests/test_failing_faults.py::test_def_001_failing_on_faulty_percentage` | `tests/unit/test_grading.py::TestPercentageCalculation::test_non_uniform_maxima_percentage` |
| **DEF-002** | Grade boundary off-by-one (`>` instead of `>=` on inclusive lower bounds) | High | P1 | **Closed** (Verified) | `fault_injection/tests/test_failing_faults.py::test_def_002_failing_on_faulty_grade_boundary` | `tests/unit/test_grading.py::TestGradeForPercentage::test_grade_boundaries` |

---

## Defect Records

### Record: DEF-001

- **Defect ID:** DEF-001
- **Title:** Percentage calculation assumes fixed 100-mark denominator per subject instead of summing actual subject maximum marks.
- **Severity:** High
- **Priority:** P1
- **Status Lifecycle:** New -> Assigned -> Open -> Fixed -> Retest -> Verified -> Closed
- **Component:** `app/services/grading.py::percentage`
- **Steps to Reproduce:**
  1. Define an exam with non-uniform subject maxima: Subject 1 (max 100), Subject 2 (max 80), Subject 3 (max 50) -> Actual total max = 230.
  2. Input obtained marks: 80, 40, 25 -> Total obtained = 145.
  3. Execute `fault_injection/tests/test_failing_faults.py::test_def_001_failing_on_faulty_percentage`.
- **Expected Result:** Percentage calculated as `145 / 230 * 100 = 63.04%`.
- **Actual Result (Before Fix):** Faulty function assumed denominator was `3 * 100 = 300`, returning `48.33%`.
- **Failure Evidence:** Recorded in `docs/evidence/faults/DEF-001-before.txt`.
- **Root Cause:** Hardcoded assumption that all examination subjects have maximum marks of 100.
- **Resolution / Fix:** In `app/services/grading.py`, calculate percentage by dividing `total_obtained` by `total_max` (dynamically summed from all subject definitions) and round using `Decimal.quantize(..., rounding=ROUND_HALF_UP)`.
- **Retest Evidence:** `pytest tests/unit/test_fault_demo.py -k test_def_001_corrected_implementation_passes` -> PASSED (recorded in `docs/evidence/faults/DEF-001-after.txt`).
- **Regression Tests:** `tests/unit/test_grading.py::TestPercentageCalculation::test_non_uniform_maxima_percentage` (TC-CALC-10).

---

### Record: DEF-002

- **Defect ID:** DEF-002
- **Title:** Grade assignment boundary condition uses strict greater-than (`>`) instead of greater-than-or-equal (`>=`).
- **Severity:** High
- **Priority:** P1
- **Status Lifecycle:** New -> Assigned -> Open -> Fixed -> Retest -> Verified -> Closed
- **Component:** `app/services/grading.py::grade_for_percentage`
- **Steps to Reproduce:**
  1. Student achieves exactly `90.00%` (the documented lower bound for grade A1).
  2. Student achieves exactly `35.00%` (the documented pass threshold for grade D).
  3. Execute `fault_injection/tests/test_failing_faults.py::test_def_002_failing_on_faulty_grade_boundary`.
- **Expected Result:**
  - `90.00%` receives grade `A1`.
  - `35.00%` receives grade `D` (PASS).
- **Actual Result (Before Fix):**
  - `90.00%` evaluated as `not (90.00 > 90.00)` and was demoted to `A2`.
  - `35.00%` evaluated as `not (35.00 > 35.00)` and was demoted to `E` (FAIL).
- **Failure Evidence:** Recorded in `docs/evidence/faults/DEF-002-before.txt`.
- **Root Cause:** Relational operator error in boundary comparison (`>` instead of `>=`).
- **Resolution / Fix:** In `app/services/grading.py::grade_for_percentage`, iterate grade thresholds using `if pct_dec >= lower_bound: return grade_name`.
- **Retest Evidence:** `pytest tests/unit/test_fault_demo.py -k test_def_002_corrected_implementation_passes` -> PASSED (recorded in `docs/evidence/faults/DEF-002-after.txt`).
- **Regression Tests:** `tests/unit/test_grading.py::TestGradeForPercentage::test_grade_boundaries` (covers all lower and upper bounds for A1, A2, B1, B2, C1, C2, D, E) (TC-CALC-12).
