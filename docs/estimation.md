# Software Testing Effort & Resource Estimation — SRMS

## 1. Overview
This document presents the test effort, time allocation, resource planning, risk contingencies, and comparison between **Estimated Effort** (planned prior to implementation) and **Actual Effort** (recorded upon completion of the SRMS STQA project).

---

## 2. Work Breakdown Structure (WBS) & Effort Estimation

> **Note:** Estimated values represent standard academic STQA project planning estimates (in person-hours), clearly distinguished from the actual automated execution metrics.

| Phase / Testing Activity | Deliverables | Estimated Effort (Hours) | Actual Effort (Hours) | Time Allocation (%) |
|---|---|---|---|---|
| **1. Test Planning & Requirements Analysis** | `docs/requirements.md`, `docs/test-plan.md` | 4.0 hrs | 3.5 hrs | 10% |
| **2. Test Case Design (EP, BVA, Decision Tables)** | `docs/test-cases.md`, `docs/black-box-testing.md` | 6.0 hrs | 5.5 hrs | 15% |
| **3. Unit & White-Box Test Implementation** | `tests/unit/`, `tests/whitebox/`, `docs/white-box-testing.md` | 8.0 hrs | 7.5 hrs | 20% |
| **4. Functional & Integration Test Implementation** | `tests/functional/`, `tests/integration/` | 8.0 hrs | 7.0 hrs | 20% |
| **5. Selenium WebDriver E2E POM Automation** | `tests/e2e/pages/`, `test_teacher_journey.py`, `test_student_journey.py` | 10.0 hrs | 9.5 hrs | 25% |
| **6. Test Execution, Defect Fixing & Reporting** | `reports/test-report.html`, `reports/coverage/`, `docs/test-metrics.md` | 4.0 hrs | 4.0 hrs | 10% |
| **Total Project Testing Effort** | **Complete SRMS STQA Suite** | **40.0 hrs** | **37.0 hrs** | **100%** |

---

## 3. Resource Requirements

### 3.1 Human Resources
- **1 × Senior Python Developer / Software Architect:** Backend Flask services, JSON atomic storage, and UI templates.
- **1 × STQA & Test Automation Engineer:** Pytest test suite, BVA/EP/Decision Table design, White-box coverage analysis, and Selenium POM automation.

### 3.2 Hardware & Software Resources
- **Workstation:** Windows 10/11 (x64), minimum 8 GB RAM.
- **Runtime & Frameworks:** Python 3.11.9, Flask 3.1.3.
- **Testing & Quality Toolchain:**
  - `pytest 9.1.1` (Core test runner)
  - `pytest-cov 7.1.0` & `coverage 7.15.0` (Statement and branch coverage analysis)
  - `pytest-html 4.2.0` (Self-contained HTML test execution report generator)
  - `selenium 4.52.0` & Google Chrome WebDriver (Browser E2E automation)

---

## 4. Risks and Contingency Buffers

| Risk ID | Risk Description | Probability | Impact | Contingency / Mitigation |
|---|---|---|---|---|
| **RSK-01** | Browser driver version mismatch with installed Google Chrome | Low | High | Use Selenium 4+ built-in `Selenium Manager` for automatic driver resolution. |
| **RSK-02** | Test execution corrupts demonstration data in `app/data/students.json` | Medium | Critical | Enforce `temp_data_files` fixture in `tests/conftest.py` using `tmp_path` isolation. |
| **RSK-03** | Boundary rounding discrepancies in percentage calculation | Low | Medium | Include explicit `round(raw_percentage, 2)` and verify repeating decimals (e.g., `412/600 = 68.67%`). |

---

## 5. Estimation Assumptions
1. All six subjects carry equal weight (`100` maximum marks each, `600` total).
2. Localhost network latency is negligible (`< 5 ms` per HTTP request), allowing the complete 170-test suite (including headless Chrome E2E journeys) to execute in under 30 seconds.
3. No external database provisioning or Docker container spin-up overhead is incurred.
