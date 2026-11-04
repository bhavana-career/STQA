# Software Testing Metrics Report — Student Result Management System (SRMS)

All metrics reported below are recorded directly from the latest automated test execution (`pytest -v --cov=app --cov-report=term-missing --cov-report=html:reports/coverage --html=reports/test-report.html --self-contained-html`).

---

## 1. Test Execution Summary Metrics

| Metric Name | Formula / Calculation | Actual Value |
|---|---|---|
| **Total Test Cases** | Count of all collected Pytest test items across 6 test suites | **170** |
| **Executed Test Cases** | Count of test cases executed in the latest run | **170** |
| **Passed Test Cases** | Count of test cases with `PASSED` status | **170** |
| **Failed Test Cases** | Count of test cases with `FAILED` status in final run | **0** |
| **Blocked / Skipped Test Cases** | Count of test cases skipped or blocked | **0** |
| **Test Execution Percentage** | `(Executed Test Cases / Total Test Cases) × 100` | **100.00%** |
| **Test Pass Percentage** | `(Passed Test Cases / Executed Test Cases) × 100` | **100.00%** |
| **Automation Coverage** | `(Automated Test Cases / Total Test Cases) × 100` | **100.00%** |
| **Total Suite Execution Time** | Wall-clock time including 3 live Headless Chrome Selenium sessions | **41.68 seconds** |

---

## 2. Test Suite Distribution by Testing Level

| Test Category | Directory | Automated Tests | Passed | Pass % |
|---|---|---|---|---|
| **Unit Testing** | `tests/unit/test_core_logic.py` | 85 | 85 | 100% |
| **Black-Box Testing (EP, BVA, Decision Table)** | `tests/blackbox/test_blackbox_techniques.py` | 65 | 65 | 100% |
| **White-Box Testing (Statement, Branch, Path)** | `tests/whitebox/test_whitebox_coverage.py` | 6 | 6 | 100% |
| **Functional Testing (Routes, Auth, CRUD)** | `tests/functional/test_functional_routes.py` | 8 | 8 | 100% |
| **Integration Testing (End-to-End Workflows)** | `tests/integration/test_integration_workflows.py` | 3 | 3 | 100% |
| **Selenium E2E Browser Automation (POM)** | `tests/e2e/test_teacher_journey.py` & `test_student_journey.py` | 3 | 3 | 100% |
| **TOTAL** | **`tests/`** | **170** | **170** | **100%** |

---

## 3. Code Coverage Metrics (`pytest-cov` / `coverage.py`)

- **Core Grading & Calculation Logic Target:** $\ge 90\%$ $\rightarrow$ **Actual: 99.2% (`grading.py`: 100%, `result_service.py`: 100%, `marks_service.py`: 98%, `analytics_service.py`: 100%)**
- **Overall Application Logic Target:** $\ge 80\%$ $\rightarrow$ **Actual: 96% (`667 / 696` statements covered)**

| Module Path | Statements | Missed | Coverage % | Missing Lines |
|---|---|---|---|---|
| `app/__init__.py` | 21 | 0 | **100%** | — |
| `app/config.py` | 19 | 0 | **100%** | — |
| `app/models.py` | 41 | 0 | **100%** | — |
| `app/services/grading.py` | 32 | 0 | **100%** | — |
| `app/services/result_service.py` | 41 | 0 | **100%** | — |
| `app/services/analytics_service.py` | 59 | 0 | **100%** | — |
| `app/services/marks_service.py` | 53 | 1 | **98%** | `95` |
| `app/services/student_service.py` | 189 | 7 | **96%** | `55-58, 163, 170, 198` |
| `app/routes/login.py` | 43 | 0 | **100%** | — |
| `app/routes/student.py` | 42 | 1 | **98%** | `19` |
| `app/routes/teacher.py` | 117 | 6 | **95%** | `128-129, 137, 156-158` |
| `app/routes/__init__.py` | 32 | 7 | **78%** | `9-15` |
| `app/main.py` | 7 | 7 | **0%** | `3-11` (CLI server bootstrap) |
| **TOTAL (`app/`)** | **696** | **29** | **96%** | — |

---

## 4. Defect Metrics & Severity Distribution

Across the development and STQA lifecycle (`docs/defect-report.md`), 5 defects (4 illustrative domain/prototype defects + 1 actual E2E harness defect) were tracked and resolved:

- **Application Code Size:** `0.696` KLOC (`696` executable Python statements in `app/`)
- **Defect Density:** $\frac{5 \text{ defects}}{0.696 \text{ KLOC}} \approx 7.18 \text{ defects / KLOC}$ (all resolved prior to final sign-off; post-release residual defect density = `0.00`).

| Severity Level | Count | Percentage | Current Status |
|---|---|---|---|
| **S1 — Critical** (`DEF-SRMS-001`) | 1 | 20% | Closed (Verified) |
| **S2 — Major** (`DEF-SRMS-002`, `DEF-SRMS-003`) | 2 | 40% | Closed (Verified) |
| **S3 — Minor** (`DEF-SRMS-004`, `DEF-SRMS-005`) | 2 | 40% | Closed (Verified) |
| **S4 — Trivial** | 0 | 0% | — |
| **Total** | **5** | **100%** | **100% Closed** |
