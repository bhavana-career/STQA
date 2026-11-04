# IEEE 829 Software Test Plan — Student Result Management System (SRMS)

## 1. Test Plan Identifier
`SRMS-TP-2026-V1.0`

## 2. Introduction
This document defines the comprehensive Software Testing and Quality Assurance (STQA) plan for the **Student Result Management System (SRMS)** for Class 10 Secondary Board Examinations. It governs Unit Testing, Black-Box Testing, White-Box Testing, Functional Testing, Integration Testing, and Selenium WebDriver End-to-End (E2E) Browser Automation.

## 3. Test Objectives
1. Verify 100% accuracy of the Marks Calculation Engine, Subject Grading Matrix, and Overall Classification logic.
2. Verify strict enforcement of the **Critical Single-Subject Fail Rule** (any subject `< 35` forces overall `FAIL` regardless of aggregate percentage).
3. Verify JSON data persistence and atomic file integrity across CRUD operations and application restarts.
4. Verify role-based access control and student record isolation at the backend route level.
5. Achieve `>= 90%` code coverage on core grading/calculation modules and `>= 80%` overall application logic coverage.

## 4. Scope

### 4.1 Features to be Tested
- Authentication (`login`, `logout`, session role persistence, invalid credential rejection).
- Role-based access control (`@teacher_required`, `@student_required`, cross-student `403` protection).
- Marks validation (`0–100` integer enforcement, rejection of negatives, `>100`, decimals, booleans, empty strings).
- Total marks (`0–600`) and percentage (`0.00%–100.00%`) calculation.
- Individual subject grading (`O`, `A+`, `A`, `B+`, `B`, `C+`, `C`, `F`).
- Overall classification (`Distinction`, `First Class`, `Second Class`, `Pass`, `Fail`).
- Student Dashboard celebratory popup behavior (passing vs. failing students, once-per-session suppression).
- Teacher CRUD operations (Create, Search, Section Filter, Update, Delete).
- Section-wise Class Analytics isolation (`Section A`, `Section B`, `Section C`).

### 4.2 Features Not to be Tested
- User self-registration and password recovery (explicitly excluded by system specification).
- External database drivers or cloud deployment pipelines (system uses local JSON storage only).
- Multi-node load balancing or distributed concurrency.

## 5. Test Strategy
1. **Unit Testing (`tests/unit/`):** Isolate pure Python functions in `marks_service.py`, `grading.py`, and `result_service.py` using parameterized Pytest assertions.
2. **Black-Box Testing (`tests/blackbox/`):** Apply Equivalence Partitioning (EP), Boundary Value Analysis (BVA) across all 9 boundary clusters, and Decision Table Testing across 6 core rule tables.
3. **White-Box Testing (`tests/whitebox/`):** Exercise all statement, branch, condition, and basis execution paths across validation, grading, classification, JSON I/O, and analytics modules.
4. **Functional Testing (`tests/functional/`):** Verify Flask routes, form submissions, flash notifications, error pages (`403`, `404`), and session management via Flask's test client.
5. **Integration Testing (`tests/integration/`):** Validate multi-service workflows (Marks Entry $\rightarrow$ Calculation $\rightarrow$ JSON Persistence $\rightarrow$ Student Dashboard Display; Student Creation $\rightarrow$ Application Restart $\rightarrow$ Student Login).
6. **End-to-End Automation (`tests/e2e/`):** Automate real Google Chrome browser interactions using Selenium WebDriver and the Page Object Model (POM) pattern.

## 6. Test Environment
- **Operating System:** Windows 10/11 (PowerShell)
- **Runtime:** Python 3.11.9
- **Web Framework:** Flask 3.1.x
- **Test Runner & Plugins:** `pytest`, `pytest-cov`, `pytest-html`, `coverage.py`
- **Browser Automation:** Selenium WebDriver 4.x with Google Chrome (Headless & Visible modes)
- **Data Isolation:** Temporary JSON fixtures (`tmp_path`) ensuring production `app/data/students.json` is never mutated during test runs.

## 7. Entry Criteria
- Source code for `app/` services, routes, and templates compiles without syntax errors.
- Temporary JSON fixtures (`SAMPLE_STUDENTS`, `SAMPLE_TEACHERS`) are initialized.
- Required Python packages (`Flask`, `pytest`, `pytest-cov`, `pytest-html`, `selenium`) are installed.

## 8. Exit Criteria
- 100% of automated test cases execute with `0` failures and `0` errors.
- Core calculation and grading modules achieve `>= 90%` statement/branch coverage.
- Overall `app/` package achieves `>= 80%` code coverage.
- HTML test report (`reports/test-report.html`) and HTML coverage report (`reports/coverage/index.html`) are generated and verified.

## 9. Suspension and Resumption Criteria
- **Suspension:** If the local Flask test server fails to bind to a localhost port or if JSON fixture creation fails due to file system permissions, E2E execution is suspended.
- **Resumption:** Testing resumes once port binding or file permission issues are resolved and verified via smoke test.

## 10. Test Deliverables
- Test Plan (`docs/test-plan.md`)
- Structured Test Cases (`docs/test-cases.md`)
- Black-Box & White-Box Analysis Documents (`docs/black-box-testing.md`, `docs/white-box-testing.md`)
- Defect Report & Lifecycle Documentation (`docs/defect-report.md`, `docs/defect-lifecycle.md`)
- Test Metrics & Effort Estimation (`docs/test-metrics.md`, `docs/estimation.md`)
- Executable Test Suite (`tests/`)
- Automated HTML Test Report (`reports/test-report.html`) & Coverage Report (`reports/coverage/`)

## 11. Roles and Responsibilities
- **Test Architect / QA Lead:** Defines test strategy, BVA/EP partitions, decision tables, and coverage targets.
- **Developer / SDET:** Implements application services, unit/integration tests, and Selenium POM classes.

## 12. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|---|---|---|---|
| Test execution mutates demonstration JSON data | High | Medium | Use Pytest `tmp_path` fixtures (`temp_data_files`) so all tests run against isolated temporary JSON files. |
| Flaky browser synchronization in Selenium E2E tests | Medium | Medium | Use `WebDriverWait` and `expected_conditions` in `BasePage` instead of arbitrary `time.sleep()` calls. |
| Port collisions during live E2E server startup | Medium | Low | Dynamically bind to an ephemeral free port (`socket.bind(('127.0.0.1', 0))`) per E2E test session. |
