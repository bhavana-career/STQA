# Student Result Management System (SRMS) — Class 10 Secondary Examination

A complete, locally hosted **Student Result Management System (SRMS)** and **Software Testing & Quality Assurance (STQA)** automation framework built with Python, Flask, JSON atomic storage, Pytest, and Selenium WebDriver.

---

## 1. Project Overview

The SRMS application manages Class 10 Secondary Board Examination results across six mandatory subjects (**Physics**, **Chemistry**, **Mathematics**, **Computer Science**, **Kannada**, and **English**; 100 marks each, 600 maximum total marks) and three class sections (**Section A**, **Section B**, and **Section C**).

Designed specifically as a comprehensive academic **Software Testing and Quality Assurance (STQA)** project, the repository demonstrates:
- A polished, responsive web portal with **Teacher** and **Student** role-based dashboards.
- Pure Python service layers for marks validation, total/percentage calculation, individual subject grading (`O` through `F`), overall classification (`Distinction` through `Fail`), and the **Critical Single-Subject Fail Rule**.
- **Zero external database, Docker, or cloud dependencies** — all records and marks persist reliably in local JSON files (`app/data/students.json` and `app/data/teachers.json`) using atomic temporary-file replacement.
- A multi-layered automated test suite (`tests/unit`, `tests/blackbox`, `tests/whitebox`, `tests/functional`, `tests/integration`, and `tests/e2e` with Selenium Page Object Model).

---

## 2. Key Features

### Teacher Portal
- **Dashboard Overview:** Real-time metrics for Total Students, Section A/B/C counts, Total Passed, Total Failed, and Distinction holders.
- **Student Management (CRUD):** Add new students with preassigned credentials, search by Name or Student ID, filter by Section (`A`, `B`, `C`), edit student details/marks, view individual student result cards, and delete student records with confirmation prompts.
- **Marks Management & Calculation Engine:** Enter or modify marks (`0–100` integer validation) with automatic calculation of total out of 600, percentage to two decimal places, subject-wise grades, and overall classification.
- **Section-Wise Class Analytics:** Select Section `A`, `B`, or `C` to compute section-isolated averages, subject-wise averages, pass/fail rates, and visual bar charts.

### Student Portal
- **Personal Scorecard Dashboard:** Displays Student Name, ID, Roll Number, Class, Section, Examination Name, 6 subject marks & grades, Total out of 600, Percentage, Overall Classification, and Pass/Fail status.
- **One-Time Celebratory Result Popup:** Displays a congratulatory popup modal with student name, classification, and percentage **only** if the student passed all six subjects, and only once per login session.
- **Critical Fail Rule Highlight:** If even one subject has `< 35` marks, the overall result is forced to `FAIL` regardless of aggregate percentage, and failed subjects are highlighted clearly.
- **Official Grading Matrix Reference:** Built-in reference table of the 8-tier grading rubric.
- **Strict Backend Access Control:** Students cannot access teacher routes (`403 Forbidden`) or view other students' records (`403 Forbidden`).

---

## 3. Technology Stack & Prerequisites

- **OS:** Windows 10 / 11 (PowerShell)
- **Language:** Python 3.11+
- **Backend Framework:** Flask 3.x
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Data Persistence:** Local JSON files (`students.json`, `teachers.json`)
- **Testing & Automation:** `pytest`, `pytest-cov`, `pytest-html`, `coverage.py`, `selenium` (Chrome WebDriver)

---

## 4. Installation Instructions (Windows PowerShell)

Open PowerShell in the project root directory (`c:\Users\bhava\Downloads\STQA`) and install the dependencies:

```powershell
pip install -r requirements.txt
```

---

## 5. Launching the Application Locally

Run the Flask application on `localhost` (`http://127.0.0.1:5000`):

```powershell
python -m app.main
```

Then open your browser and navigate to:
**http://127.0.0.1:5000**

---

## 6. Default Demonstration Credentials

| Role | Username | Password | Profile / Demonstration Highlight |
|---|---|---|---|
| **Teacher** | `teacher01` | `Teacher@123` | Full access to Teacher Dashboard, Student CRUD, Marks Management, and Class Analytics |
| **Student (Sec A)** | `student01` | `Student@123` | **Aarav Kulkarni (`STU001`)** — `546/600` (`91.00%`) — **Distinction (PASS)** + Celebratory Popup |
| **Student (Sec B)** | `student02` | `Student@123` | **Diya Nair (`STU002`)** — `412/600` (`68.67%`) — **First Class (PASS)** + Celebratory Popup |
| **Student (Sec C)** | `student03` | `Student@123` | **Rohan Deshmukh (`STU003`)** — `426/600` (`71.00%`), Mathematics `= 28` — **FAIL (Critical Rule Override, No Popup)** |
| **Student (Sec A)** | `student04` | `Student@123` | **Sneha Hegde (`STU004`)** — `336/600` (`56.00%`) — **Second Class (PASS)** |
| **Student (Sec A)** | `student05` | `Student@123` | **Karthik Gowda (`STU005`)** — `255/600` (`42.50%`) — **Pass Class (PASS)** |

---

## 7. Running Automated Tests & Generating Reports

All tests use isolated temporary JSON fixtures (`tmp_path`) and never modify `app/data/students.json`.

### Run All Tests
```powershell
pytest -v
```

### Run Unit Tests
```powershell
pytest tests/unit -v
```

### Run Black-Box & White-Box Tests
```powershell
pytest tests/blackbox tests/whitebox -v
```

### Run Functional & Integration Tests
```powershell
pytest tests/functional tests/integration -v
```

### Run Selenium End-to-End Browser Tests (Headless Chrome)
```powershell
pytest tests/e2e -v
```

### Run Selenium End-to-End Browser Tests in Visible Chrome (For Demonstrations)
```powershell
$env:SRMS_HEADLESS="false"; pytest tests/e2e -v
```

### Generate Self-Contained HTML Test Report
```powershell
pytest -v --html=reports/test-report.html --self-contained-html
```

### Generate Code Coverage Report (Terminal + HTML)
```powershell
pytest --cov=app --cov-report=term-missing --cov-report=html:reports/coverage
```

---

## 8. Project Directory Structure

```text
SRMS/
│
├── app/
│   ├── __init__.py                 # Flask application factory & error handlers
│   ├── main.py                     # Localhost server entry point
│   ├── config.py                   # Subjects, grading matrix, and app configuration
│   ├── models.py                   # Dataclasses for StudentRecord, SubjectResult, OverallResult
│   ├── data/
│   │   ├── students.json           # Predefined Class 10 student records (Sections A, B, C)
│   │   └── teachers.json           # Predefined teacher credentials
│   ├── services/
│   │   ├── marks_service.py        # Marks validation, total calculation, percentage rounding
│   │   ├── grading.py              # Individual subject grading (O, A+, A, B+, B, C+, C, F)
│   │   ├── result_service.py       # Overall classification, critical fail rule, popup logic
│   │   ├── student_service.py      # Atomic JSON read/write, CRUD, search/filter, auth
│   │   └── analytics_service.py    # Dashboard overview & isolated section analytics
│   ├── routes/
│   │   ├── __init__.py             # Role-based access control decorators
│   │   ├── login.py                # Login and logout endpoints
│   │   ├── teacher.py              # Teacher dashboard, CRUD, marks, and analytics routes
│   │   └── student.py              # Student dashboard, result, grading matrix, isolation routes
│   ├── templates/
│   │   ├── base.html               # Master layout with role-aware sidebar
│   │   ├── login.html              # Academic login page with password toggle
│   │   ├── teacher_dashboard.html  # Overview metrics and student summary
│   │   ├── students.html           # Student CRUD, search, and section filter
│   │   ├── marks.html              # Marks entry & automatic calculation view
│   │   ├── analytics.html          # Section analytics & visual performance charts
│   │   ├── student_dashboard.html  # Student scorecard, grading matrix, & celebratory popup
│   │   └── error.html              # 403 / 404 error page
│   └── static/
│       ├── css/style.css           # Modern academic UI stylesheet
│       └── js/main.js              # Password toggle, delete confirmation, popup dismissal
│
├── tests/
│   ├── conftest.py                 # Temporary JSON fixtures, test client, live server, WebDriver
│   ├── unit/
│   │   └── test_core_logic.py      # 85 unit tests for validation, totals, grades, classification
│   ├── blackbox/
│   │   └── test_blackbox_techniques.py # EP, 34-point BVA, and Decision Table tests
│   ├── whitebox/
│   │   └── test_whitebox_coverage.py   # Statement, branch, condition, and basis path tests
│   ├── functional/
│   │   └── test_functional_routes.py   # Route, auth, CRUD, and RBAC functional tests
│   ├── integration/
│   │   └── test_integration_workflows.py # End-to-end service & restart persistence workflows
│   └── e2e/
│       ├── pages/                  # Page Object Model (BasePage, LoginPage, Dashboard, etc.)
│       ├── test_teacher_journey.py # 15-step Selenium Teacher Journey + browser validation
│       └── test_student_journey.py # 14-step Selenium Student Journey (passing & failing)
│
├── docs/
│   ├── requirements.md             # Software Requirements Specification (SRS)
│   ├── test-plan.md                # IEEE 829 Software Test Plan
│   ├── test-cases.md               # Structured Test Case Specification
│   ├── defect-report.md            # Defect Report Log
│   ├── defect-lifecycle.md         # Defect Lifecycle & State Machine
│   ├── black-box-testing.md        # EP, BVA, and Decision Table analysis
│   ├── white-box-testing.md        # Control flow, cyclomatic complexity, and coverage analysis
│   ├── test-metrics.md             # Actual execution metrics & coverage results
│   └── estimation.md               # WBS, effort estimation, and risk analysis
│
├── reports/                        # Generated HTML test reports & coverage reports
├── requirements.txt
├── pytest.ini
├── .gitignore
└── README.md
```
