# Academic STQA Exercises Index & Traceability Matrix

This directory contains comprehensive academic documentation, theoretical analyses, IEEE 829-standard test plans, and test case matrices for all 10 Software Testing and Quality Assurance (STQA) laboratory exercises.

---

## 1. Exercises Traceability Matrix

| Exercise # | Topic / Title | Focus Area | Code Implementation | Test Suite | Documentation Guide |
|:---:|:---|:---|:---|:---|:---|
| **01** | Simple Program, Defect Demo & SDLC Comparison | Unit testing, Defect DEF-006, Waterfall vs. Agile | [`academic/division/`](file:///c:/Users/bhava/Downloads/ST&QA/academic/division/) | `academic/tests/test_academic_exercises.py::TestExercise1Division` | [`docs/academic/exercise-01-division-sdlc.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-01-division-sdlc.md) |
| **02** | User Login Test Checklist & IEEE 829 Test Plan | Positive/Negative testing, Security, Turnstile | [`app/blueprints/auth/`](file:///c:/Users/bhava/Downloads/ST&QA/app/blueprints/auth/) | `tests/unit/test_auth_routes.py`, `tests/integration/test_auth_flow.py` | [`docs/academic/exercise-02-login-test-plan.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-02-login-test-plan.md) |
| **03** | Age Validation & Defect Lifecycle | Equivalence Partitioning (EP), BVA, Defect tracking | [`academic/age_validator.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/age_validator.py) | `academic/tests/test_academic_exercises.py::TestExercise3AgeValidation` | [`docs/academic/exercise-03-age-field-defect-lifecycle.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-03-age-field-defect-lifecycle.md) |
| **04** | Coverage Demonstrations & ATM Black-Box Testing | Statement vs. Branch coverage, ATM withdrawal | [`academic/coverage_demo.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/coverage_demo.py), [`academic/atm.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/atm.py) | `academic/tests/test_academic_exercises.py::TestExercise4CoverageAndATM` | [`docs/academic/exercise-04-coverage-atm-blackbox.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-04-coverage-atm-blackbox.md) |
| **05** | Top-Down Integration Testing & Metrics | Top-down integration hierarchy with stubs, Metrics | [`academic/top_down_integration.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/top_down_integration.py) | `academic/tests/test_academic_exercises.py::TestExercise5TopDownIntegration` | [`docs/academic/exercise-05-top-down-integration-metrics.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-05-top-down-integration-metrics.md) |
| **06** | STQA Testing Phases & Defect Metrics | Sample 100 KLOC analysis vs. SRMS Actuals | [`academic/metrics.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/metrics.py) | `academic/tests/test_academic_exercises.py::TestExercise6SoftwareMetrics` | [`docs/academic/exercise-06-testing-phases-metrics.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-06-testing-phases-metrics.md) |
| **07** | Student Result Calculation Test Plan (IEEE 829) | Complete/Incomplete result rules, Edge cases | [`app/services/grading.py`](file:///c:/Users/bhava/Downloads/ST&QA/app/services/grading.py) | `tests/unit/test_grading.py` | [`docs/academic/exercise-07-result-calculation-test-plan.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-07-result-calculation-test-plan.md) |
| **08** | Equivalence Partitioning, BVA & White-Box Testing | Systematic domain partitioning, Basis path testing | [`app/services/grading.py`](file:///c:/Users/bhava/Downloads/ST&QA/app/services/grading.py) | `tests/unit/test_grading.py`, `tests/unit/test_marks_validation.py` | [`docs/academic/exercise-08-ep-bva-whitebox.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-08-ep-bva-whitebox.md) |
| **09** | Selenium E2E Automation for SRMS Login | Automated browser testing, POM, Pass/Fail metrics | [`tests/e2e/pages/`](file:///c:/Users/bhava/Downloads/ST&QA/tests/e2e/pages/), [`tests/e2e/`](file:///c:/Users/bhava/Downloads/ST&QA/tests/e2e/) | `tests/e2e/test_auth_e2e.py` | [`docs/academic/exercise-09-selenium-automation-report.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-09-selenium-automation-report.md) |
| **10** | Consolidated QA & STQA Lab Technical Report | Final technical synthesis, Full test statistics | Full System | Full test suite (`pytest -v`) | [`docs/academic/exercise-10-consolidated-technical-report.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-10-consolidated-technical-report.md) |

---

## 2. Quick Execution Guide

All academic test cases can be executed independently or as part of the unified test suite:

```powershell
# Run all academic exercises (Exercises 1, 3, 4, 5, 6)
.\.venv\Scripts\pytest academic/tests/ -v

# Run fault injection demonstration test (intentional failure)
.\.venv\Scripts\pytest fault_injection/tests/test_failing_faults.py -k test_def_006

# Run fault injection regression verification (corrected implementation passes)
.\.venv\Scripts\pytest tests/unit/test_fault_demo.py -k test_def_006 -v

# Run the complete project test suite with branch coverage report
.\.venv\Scripts\pytest --cov=app --cov-branch --cov-report=term-missing
```
