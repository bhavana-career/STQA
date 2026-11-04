# Student Result Management System (SRMS) — Software Testing and Quality Assurance (STQA)

**Repository:** [https://github.com/bhavana-career/STQA](https://github.com/bhavana-career/STQA)  
**Subject:** Software Testing and Quality Assurance (STQA)  
**Academic Level:** Class 10 Secondary Board Examination Result & Analytics Portal  
**Execution Mode:** Localhost Web Application (`127.0.0.1:5000`) with JSON File Persistence  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Key Features](#2-key-features)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Installation and Cloning Instructions (Windows PowerShell)](#5-installation-and-cloning-instructions-windows-powershell)
6. [Running the Application Locally](#6-running-the-application-locally)
7. [Automated Testing Using Pytest](#7-automated-testing-using-pytest)
8. [Selenium Web Automation (End-to-End Page Object Model)](#8-selenium-web-automation-end-to-end-page-object-model)
9. [HTML Test Reports](#9-html-test-reports)
10. [Code Coverage and Test Metrics](#10-code-coverage-and-test-metrics)
11. [Software Testing Concepts Demonstrated (STQA Syllabus Mapping)](#11-software-testing-concepts-demonstrated-stqa-syllabus-mapping)
    - [A. Introduction to Software Testing](#a-introduction-to-software-testing)
    - [B. Test Planning and Estimation](#b-test-planning-and-estimation)
    - [C. Defect Reporting and Tracking](#c-defect-reporting-and-tracking)
    - [D. Black-Box Testing Techniques](#d-black-box-testing-techniques)
    - [E. White-Box Testing Techniques](#e-white-box-testing-techniques)
    - [F. Test Metrics and Quality Measurement](#f-test-metrics-and-quality-measurement)
    - [G. Final Case Study / Mini Project Synthesis](#g-final-case-study--mini-project-synthesis)
12. [Intentional Defect Demonstration (`DEF-SRMS-BVA-035`)](#12-intentional-defect-demonstration-def-srms-bva-035)
13. [Application and Testing Screenshots](#13-application-and-testing-screenshots)
14. [Repository and Contribution Information](#14-repository-and-contribution-information)

---

## 1. Project Overview

The **Student Result Management System (SRMS)** is a full-stack, locally hosted web application developed in Python and Flask to manage, compute, analyze, and publish **Class 10 Secondary Board Examination** results.

### Why SRMS Was Developed
In academic institutions, compiling multi-subject examination scores involves strict validation rules, multi-band grading matrices, mandatory per-subject passing thresholds, and cohort-level performance analytics. Manual spreadsheet processing is prone to boundary errors, formula corruption, and unauthorized access. SRMS automates this lifecycle while serving as a comprehensive, testable software engineering artifact for **Software Testing and Quality Assurance (STQA)**.

### Purpose in Demonstrating STQA Concepts
Unlike static prototypes, SRMS was architected with **testability as a primary design requirement**:
- Core business rules—marks validation, total calculation, percentage rounding, letter-grade assignment, overall classification, and section-wise analytics—are decoupled into pure Python service modules (`app/services/`).
- This separation of concerns enables independent verification across six distinct testing levels: **Unit Testing**, **Black-Box Testing** (Equivalence Partitioning, Boundary Value Analysis, Decision Tables), **White-Box Testing** (Statement, Branch, Condition, and Basis Path coverage), **Functional Testing**, **Integration Testing**, and **End-to-End (E2E) Browser Automation** using Selenium WebDriver and the Page Object Model (POM).

### Functional Summary
- **Two User Roles:**
  1. **Teacher (`teacher01`):** Manages student records (Create, Read, Search, Section Filter, Update, Delete), enters or modifies six-subject examination marks, views individual student scorecards, and inspects section-wise class analytics.
  2. **Student (`student01` – `student09`):** Views their personal profile, six-subject marks and letter grades, aggregate score out of `600`, percentage, overall classification, pass/fail status, celebratory pass popup, and the official grading matrix.
- **Six Mandatory Class 10 Subjects:** `Physics`, `Chemistry`, `Mathematics`, `Computer Science`, `Kannada`, and `English` (`100` marks each; `600` maximum total marks).
- **Local JSON Storage (No External Database):** All predefined and newly created records are stored in `app/data/students.json` and `app/data/teachers.json` using atomic temporary-file writes (`tempfile.mkstemp` + `os.fsync` + `os.replace`) so interrupted operations never corrupt application data.

---

## 2. Key Features

1. **Preassigned Role-Based Authentication:** Local credential verification against `teachers.json` and `students.json` with a password visibility toggle (`Show`/`Hide`), session tracking, and flash feedback.
2. **Backend Access Control & Student Isolation:** Custom route decorators (`@teacher_required`, `@student_required`) block unauthenticated users (`302 Redirect` to `/login`), block students from accessing teacher administration pages (`403 Forbidden`), and block students from viewing other students' records (`403 Forbidden`).
3. **Teacher Dashboard Overview:** Displays real-time counters for Total Students, Section A/B/C enrollments, Total Passed Students, Total Failed Students, and Distinction Holders, alongside a complete student summary table.
4. **Student CRUD Management:** Teachers can create new Class 10 students with unique Student IDs, usernames, passwords, sections (`A`, `B`, `C`), roll numbers, and subject marks; search by Name or Student ID; filter by Section; edit student records; and delete records with browser confirmation prompts.
5. **Six-Subject Marks Validation & Calculation Engine:**
   - Validates every subject mark as a whole integer in `[0, 100]`.
   - Rejects negative numbers, values `> 100`, decimal floats, booleans, non-numeric strings, and empty inputs (empty marks never silently become zero).
   - Automatically calculates `Total Marks` out of `600` and `Percentage` rounded to two decimal places (`0.00%` – `100.00%`).
6. **Individual Subject Grading Matrix:** Automatically assigns letter grades (`O`, `A+`, `A`, `B+`, `B`, `C+`, `C`, `F`) and subject pass/fail statuses (`>= 35` Pass, `< 35` Fail).
7. **Overall Classification & Critical Single-Subject Fail Rule:**
   - Awards `Distinction` ($\ge 75\%$), `First Class` ($60\%–74.99\%$), `Second Class` ($50\%–59.99\%$), `Pass` ($35\%–49.99\%$), or `Fail` ($< 35\%$).
   - Enforces the **Critical Board Examination Rule**: a student must score at least `35` marks in all six subjects to pass overall. If even one subject has `< 35` marks, the overall status is forced to `FAIL` and classification is forced to `Fail`, even if the aggregate percentage is $\ge 75\%$.
8. **One-Time Celebratory Result Announcement Popup:** Passing students receive a congratulatory modal popup on their dashboard showing their name, classification, and percentage once per login session (`session["popup_shown"]`). Failing students do not receive the popup and instead see an alert identifying their failed subject(s).
9. **Section-Isolated Class Analytics:** Teachers can select `Section A`, `Section B`, or `Section C` to compute section-specific student counts, average total marks, average percentage, subject-wise averages, pass/fail counts, distinction counts, and visual bar charts without cross-section data contamination.
10. **Persistent Atomic JSON Storage:** All CRUD and marks updates persist across server restarts in `app/data/students.json`.

---

## 3. Technology Stack

All dependencies are defined in `requirements.txt` and verified against the project source code:

| Category | Technology / Library | Version / Specification | Purpose in SRMS |
|---|---|---|---|
| **Programming Language** | Python | `3.11+` | Core application logic, data models, and test automation scripts |
| **Backend Web Framework** | Flask (`Flask`, `Werkzeug`, `Jinja2`) | `>= 3.0.0` (`3.1.3`) | HTTP routing, session management, HTML templating, and WSGI test client |
| **Frontend Technologies** | HTML5, CSS3, Vanilla JavaScript | Standard Web APIs | Responsive dashboard layout, CSS bar charts, password toggle, delete confirmation, and modal popup |
| **Data Persistence** | JSON (`json`, `tempfile`, `os.replace`) | Python Standard Library | Atomic local file persistence (`students.json`, `teachers.json`) without external databases |
| **Testing Framework** | Pytest (`pytest`) | `>= 8.0.0` (`9.1.1`) | Test discovery, parameterization, fixture management, and assertion reporting |
| **Browser Automation** | Selenium WebDriver (`selenium`) | `>= 4.20.0` (`4.52.0`) | Automated End-to-End (E2E) Google Chrome browser testing via Page Object Model |
| **Code Coverage** | `pytest-cov` & `coverage` | `>= 5.0.0` / `>= 7.5.0` | Statement and branch execution tracking and interactive HTML coverage reports |
| **Test Reporting** | `pytest-html` | `>= 4.1.0` (`4.2.0`) | Self-contained HTML test execution report generation |

---

## 4. Project Structure

```text
STQA/
│
├── app/                                      # Main Flask application package
│   ├── __init__.py                           # Application factory (create_app) & 403/404 error handlers
│   ├── main.py                               # Localhost server entry point (127.0.0.1:5000)
│   ├── config.py                             # Subjects list, grading matrix, classification thresholds, paths
│   ├── models.py                             # Dataclasses: StudentRecord, SubjectResult, OverallResult
│   │
│   ├── data/                                 # Persistent JSON data store
│   │   ├── students.json                     # Predefined Class 10 student records (STU001–STU009 across Sec A, B, C)
│   │   └── teachers.json                     # Predefined teacher credentials (teacher01)
│   │
│   ├── services/                             # Pure Python business logic layer
│   │   ├── __init__.py
│   │   ├── marks_service.py                  # Marks validation (0–100 int), total calculation, percentage rounding
│   │   ├── grading.py                        # Individual subject grading (O, A+, A, B+, B, C+, C, F) & pass check
│   │   ├── result_service.py                 # Overall classification, critical single-subject fail rule, popup rule
│   │   ├── student_service.py                # Atomic JSON I/O, student CRUD validation, search/filter, authentication
│   │   └── analytics_service.py              # Teacher overview stats & strictly isolated section-wise analytics
│   │
│   ├── routes/                               # Flask Blueprints & role-based access control
│   │   ├── __init__.py                       # Access decorators (@login_required, @teacher_required, @student_required)
│   │   ├── login.py                          # Root redirect, /login authentication, and /logout session clearing
│   │   ├── teacher.py                        # Teacher routes: /dashboard, /students CRUD, /marks, /analytics
│   │   └── student.py                        # Student routes: /dashboard, /results, /grading-matrix, /view/<id>
│   │
│   ├── templates/                            # Jinja2 HTML5 templates
│   │   ├── base.html                         # Shared sidebar layout, topbar, and flash message container
│   │   ├── login.html                        # Academic login portal with demo credentials & password toggle
│   │   ├── teacher_dashboard.html            # Teacher KPI cards and full student summary table
│   │   ├── students.html                     # Student CRUD form, search bar, section filter, and directory table
│   │   ├── marks.html                        # Student selector, 6-subject marks entry table, and live result banner
│   │   ├── analytics.html                    # Section A/B/C selector, KPI cards, and CSS performance bar charts
│   │   ├── student_dashboard.html            # Student scorecard, celebratory popup modal, and grading matrix
│   │   └── error.html                        # Custom 403 Forbidden and 404 Not Found error page
│   │
│   └── static/                               # Static frontend assets
│       ├── css/
│       │   └── style.css                     # Modern navy/slate/blue academic dashboard stylesheet
│       └── js/
│           └── main.js                       # Password visibility toggle, delete confirmation, popup dismissal
│
├── tests/                                    # Multi-layered automated STQA test suite
│   ├── conftest.py                           # Fixtures: temp_data_files, test_app, client, live_server_url, browser
│   ├── unit/
│   │   └── test_core_logic.py                # 85 unit tests for marks validation, totals, percentages, grades, classification
│   ├── blackbox/
│   │   └── test_blackbox_techniques.py       # 66 black-box tests: EP, 34-point BVA, Decision Tables, & BVA defect test
│   ├── whitebox/
│   │   └── test_whitebox_coverage.py         # 6 white-box test suites covering all branches, conditions, & basis paths
│   ├── functional/
│   │   └── test_functional_routes.py         # 8 functional route tests for auth, RBAC, CRUD, marks, and analytics
│   ├── integration/
│   │   └── test_integration_workflows.py     # 3 integration workflows: marks-to-result, restart persistence, section isolation
│   └── e2e/
│       ├── pages/
│       │   └── __init__.py                   # Selenium Page Object Model (BasePage, LoginPage, Teacher/Student pages)
│       ├── test_teacher_journey.py           # 15-step Selenium E2E Teacher workflow + invalid input browser tests
│       └── test_student_journey.py           # 14-step Selenium E2E Student workflow (passing & failing students)
│
├── docs/                                     # Formal STQA academic documentation deliverables
│   ├── requirements.md                       # Software Requirements Specification (SRS)
│   ├── test-plan.md                          # IEEE 829-inspired Software Test Plan
│   ├── test-cases.md                         # Master Test Case Specification Table (TC-001 to TC-025)
│   ├── defect-report.md                      # Structured Defect Report Log
│   ├── defect-lifecycle.md                   # Defect Lifecycle state machine & severity/priority matrix
│   ├── black-box-testing.md                  # Equivalence Partitioning, BVA, and Decision Table documentation
│   ├── white-box-testing.md                  # Statement, Branch, Condition, and Cyclomatic Complexity analysis
│   ├── test-metrics.md                       # Test execution, pass rate, defect density, and coverage metrics
│   └── estimation.md                         # Work Breakdown Structure (WBS), effort estimation, and risk analysis
│
├── reports/                                  # Generated test execution & code coverage artifacts
│   ├── test-report.html                      # Self-contained Pytest HTML test report
│   └── coverage/                             # Interactive HTML code coverage report (index.html)
│
├── requirements.txt                          # Python package dependencies
├── pytest.ini                                # Pytest configuration, pythonpath, and custom test markers
├── .gitignore                                # Git ignore rules for virtual environments and caches
└── README.md                                 # Project documentation (this file)
```

---

## 5. Installation and Cloning Instructions (Windows PowerShell)

Follow these step-by-step instructions to set up and run the project on a Windows machine from scratch.

### Prerequisites
1. **Git:** Install from [https://git-scm.com/download/win](https://git-scm.com/download/win).
2. **Python (3.11 or newer):** Install from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/). During installation, check **"Add python.exe to PATH"**.
3. **Google Chrome:** Installed for running Selenium WebDriver browser tests.
4. **Visual Studio Code (VS Code):** Recommended for inspecting code and running integrated PowerShell terminals.

### Step-by-Step Setup in Windows PowerShell

**Step 1: Clone the GitHub Repository**
```powershell
git clone https://github.com/bhavana-career/STQA.git
```

**Step 2: Navigate into the Project Directory**
```powershell
cd STQA
```

**Step 3: Open the Project in VS Code (Optional)**
```powershell
code .
```

**Step 4: Verify Your Python Installation**
```powershell
py --version
```

**Step 5: Create an Isolated Virtual Environment (`.venv`)**
```powershell
py -m venv .venv
```

**Step 6: Activate the Virtual Environment**
```powershell
.venv\Scripts\Activate.ps1
```
*(Note: If PowerShell displays an ExecutionPolicy warning, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, then run `.venv\Scripts\Activate.ps1` again.)*

**Step 7: Install Required Dependencies**
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Understanding `python` vs `py` on Windows
On Windows systems with multiple Python versions installed, typing `py` invokes the global Windows Python Launcher (which may point to a system-wide Python installation that does not have project packages installed), whereas typing `python` inside an activated `.venv` uses the isolated virtual environment where `Flask`, `pytest`, and `selenium` are installed.  
**Recommendation:** Always activate `.venv` first (`.venv\Scripts\Activate.ps1`) and run commands using `python -m ...` so that the exact virtual environment interpreter is used consistently.

---

## 6. Running the Application Locally

### Start the Local Flask Server
Inspecting `app/main.py` confirms that the application binds to `127.0.0.1` on port `5000`. Run the following command from the project root directory:

```powershell
python -m app.main
```

You will see the following output in PowerShell:
```text
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### Access the Application in Your Browser
Open any web browser and navigate to:
```text
http://127.0.0.1:5000
```

### Predefined Demonstration Credentials
The repository includes predefined demonstration accounts in `app/data/teachers.json` and `app/data/students.json` covering all sections and result classifications:

| Role | Username | Password | Student ID / Section | Marks & Result Profile |
|---|---|---|---|---|
| **Teacher** | `teacher01` | `Teacher@123` | `TCH001` (Coordinator) | Full access to Teacher Dashboard, Student CRUD, Marks Management, and Class Analytics |
| **Student** | `student01` | `Student@123` | `STU001` (Section A, Roll 101) | **Aarav Kulkarni** — `546 / 600` (`91.00%`) — **Distinction (`PASS`)** + Celebratory Popup |
| **Student** | `student02` | `Student@123` | `STU002` (Section B, Roll 201) | **Diya Nair** — `412 / 600` (`68.67%`) — **First Class (`PASS`)** + Celebratory Popup |
| **Student** | `student03` | `Student@123` | `STU003` (Section C, Roll 301) | **Rohan Deshmukh** — `426 / 600` (`71.00%`), Mathematics `= 28` — **`FAIL` (Single-Subject Fail Override, No Popup)** |
| **Student** | `student04` | `Student@123` | `STU004` (Section A, Roll 102) | **Sneha Hegde** — `336 / 600` (`56.00%`) — **Second Class (`PASS`)** |
| **Student** | `student05` | `Student@123` | `STU005` (Section A, Roll 103) | **Karthik Gowda** — `255 / 600` (`42.50%`) — **Pass Class (`PASS`)** |
| **Student** | `student06` | `Student@123` | `STU006` (Section B, Roll 202) | **Ananya Rao** — `504 / 600` (`84.00%`) — **Distinction (`PASS`)** |
| **Student** | `student07` | `Student@123` | `STU007` (Section B, Roll 203) | **Vikram Patil** — `177 / 600` (`29.50%`), Kannada `= 35` — **`FAIL` (Multi-Subject Fail)** |
| **Student** | `student08` | `Student@123` | `STU008` (Section C, Roll 302) | **Meera Joshi** — `472 / 600` (`78.67%`) — **Distinction (`PASS`)** |
| **Student** | `student09` | `Student@123` | `STU009` (Section C, Roll 303) | **Pranav Shetty** — `378 / 600` (`63.00%`) — **First Class (`PASS`)** |

### Stopping the Server
In the PowerShell terminal where the server is running, press **`Ctrl + C`** to stop the Flask development server.

---

## 7. Automated Testing Using Pytest

### Role of Pytest in SRMS
**Pytest** is the primary automated testing framework used in this project. It automatically discovers test modules matching `test_*.py` inside `tests/`, injects isolated test environments using **fixtures** (`tests/conftest.py`), executes test functions, and evaluates `assert` statements comparing **Actual Output** against **Expected Output**.

### How Test Isolation Prevents Data Corruption
In `tests/conftest.py`, the `temp_data_files` fixture uses Pytest's built-in `tmp_path` directory to create fresh, temporary copies of `students.json` and `teachers.json` for every test function. This guarantees that running CRUD, marks modification, or deletion tests never alters or corrupts the real demonstration data in `app/data/students.json`.

### Pytest Execution Commands

Run these commands from the project root directory (`STQA/`):

**1. Run the Complete Automated Test Suite (All 171 Tests):**
```powershell
python -m pytest -v
```

**2. Run Unit Tests (`tests/unit/`):**
```powershell
python -m pytest tests/unit -v
```

**3. Run Black-Box Tests — EP, BVA, and Decision Tables (`tests/blackbox/`):**
```powershell
python -m pytest tests/blackbox -v
```

**4. Run White-Box Tests — Statement, Branch, Condition, and Path Coverage (`tests/whitebox/`):**
```powershell
python -m pytest tests/whitebox -v
```

**5. Run Functional Route & Access Control Tests (`tests/functional/`):**
```powershell
python -m pytest tests/functional -v
```

**6. Run Service & Persistence Integration Tests (`tests/integration/`):**
```powershell
python -m pytest tests/integration -v
```

### Understanding Pytest Outcomes
- **`PASSED` (`.`):** The test executed completely and all `assert` conditions evaluated to `True`.
- **`FAILED` (`F`):** An `AssertionError` occurred because the software's actual output differed from the expected specification (e.g., the intentional boundary value defect at `mark = 35`).
- **`ERROR` (`E`):** An unexpected exception occurred during fixture setup/teardown or module import outside the test assertion itself.
- **`SKIPPED` (`s`):** The test was intentionally bypassed due to a conditional marker or platform rule.

---

## 8. Selenium Web Automation (End-to-End Page Object Model)

### Why Browser Automation is Required
While Unit and Functional tests verify Python functions and HTTP responses, they do not execute client-side JavaScript, CSS layout rendering, DOM events, or browser alert dialogs. **Selenium WebDriver** launches a real Google Chrome browser instance, connects to a live background Flask server started by the `live_server_url` fixture, and simulates real human interactions (typing, clicking buttons, toggling password visibility, selecting dropdowns, and dismissing modal popups).

### Page Object Model (POM) Architecture
To keep E2E tests maintainable and eliminate duplicated DOM locators, `tests/e2e/pages/__init__.py` implements the **Page Object Model (POM)** pattern:

| Page Object Class | Responsibility & Encapsulated UI Interactions |
|---|---|
| `BasePage` | Explicit `WebDriverWait` synchronization, URL navigation, form input handling, flash text extraction, and logout |
| `LoginPage` | Opening `/login`, entering username/password, toggling password visibility (`#togglePasswordBtn`), and reading error alerts |
| `TeacherDashboardPage` | Verifying teacher KPI overview cards (`#dashboardOverviewGrid`) and sidebar navigation |
| `StudentManagementPage` | Adding new students (`#studentCrudForm`), searching by name/ID, editing student details, and confirming deletion dialogs |
| `MarksEntryPage` | Selecting a student (`#marksStudentSelect`), submitting 6 subject marks, and reading calculated total, percentage, grades, and classification |
| `ResultPage` / `StudentDashboardPage` | Reading candidate scorecard metrics, subject rows, grading matrix visibility, and celebratory popup dismissal (`#resultSuccessPopup`) |
| `AnalyticsPage` | Switching between Section `A`, `B`, and `C` tabs and extracting section-specific averages and pass/fail counts |

### Commands to Run Selenium E2E Tests

**Run Selenium E2E Tests in Headless Chrome (Default Fast Mode):**
```powershell
python -m pytest tests/e2e -v
```

**Run Selenium E2E Tests in Visible Chrome Window (For Live Classroom Demonstrations):**
```powershell
$env:SRMS_HEADLESS="false"
python -m pytest tests/e2e -v
```

### Automated End-to-End User Journeys

1. **Teacher E2E Journey (`tests/e2e/test_teacher_journey.py`):**
   - Opens localhost login page $\rightarrow$ verifies password visibility toggle $\rightarrow$ logs in as `teacher01` $\rightarrow$ verifies initial student count on Teacher Dashboard $\rightarrow$ navigates to Student Management $\rightarrow$ adds new student `Siddharth Menon (STU888)` in Section B $\rightarrow$ searches for `"Siddharth"` $\rightarrow$ edits name and roll number $\rightarrow$ navigates to Marks Management $\rightarrow$ enters 6 subject marks (`92, 86, 81, 75, 65, 81`) $\rightarrow$ verifies automatic calculation of `480 / 600`, `80.00%`, individual grades (`O, A+, A, B+, B, A`), and `Distinction` classification $\rightarrow$ navigates to Class Analytics and verifies independent averages for Section A (`63.17%`) and Section B (`74.34%`) $\rightarrow$ deletes `STU888` $\rightarrow$ logs out.
   - Also tests invalid login credentials and backend rejection of out-of-range marks (`145`) in the browser.
2. **Student E2E Journey (`tests/e2e/test_student_journey.py`):**
   - **Passing Student (`student01` / Aarav Kulkarni):** Logs in $\rightarrow$ verifies celebratory popup `#resultSuccessPopup` is displayed $\rightarrow$ dismisses popup $\rightarrow$ verifies personal details (`STU001`), all 6 subject marks and grades, total (`546 / 600`), percentage (`91.00%`), and `Distinction (PASS)` status $\rightarrow$ verifies official grading matrix table $\rightarrow$ navigates across student tabs to confirm the popup does not repeat $\rightarrow$ attempts to access `/teacher/dashboard` and `/student/view/STU002` and verifies `403 Access Denied` enforcement $\rightarrow$ logs out.
   - **Failing Student (`student03` / Rohan Deshmukh):** Logs in $\rightarrow$ verifies celebratory popup is **not** shown $\rightarrow$ verifies `426 / 600` (`71.00%`) is overridden to `Fail (FAIL)` due to `Mathematics = 28 (F)` $\rightarrow$ logs out.

---

## 9. HTML Test Reports

SRMS uses `pytest-html` to generate a standalone, single-file HTML report suitable for academic submission and examiner review.

### Command to Generate the HTML Test Report
```powershell
python -m pytest -v --html=reports/test-report.html --self-contained-html
```

### Opening the Report
Run the following command in PowerShell to open the generated report in your default browser:
```powershell
Start-Process "reports\test-report.html"
```

### What the Report Displays
- **Environment Metadata:** Python version, OS platform, and installed Pytest plugins.
- **Summary Counts:** Total tests collected (`171`), Passed (`168`), Failed (`3` — corresponding to the intentional `mark = 35` boundary defect demonstration), Skipped (`0`), Errors (`0`), and total execution duration.
- **Interactive Traceback Inspector:** Expandable stack traces and assertion diffs for any failing test case, along with captured HTTP server logs.

---

## 10. Code Coverage and Test Metrics

### What Code Coverage Measures
**Code Coverage** measures the percentage of application source code (`app/`) executed during automated testing. Using `pytest-cov` and `coverage.py`, SRMS tracks which Python statements and decision branches are exercised and identifies any unexecuted lines.

### Command to Generate Terminal and HTML Coverage Reports
```powershell
python -m pytest --cov=app --cov-report=term-missing --cov-report=html:reports/coverage
```

To view the interactive line-by-line HTML coverage report in your browser:
```powershell
Start-Process "reports\coverage\index.html"
```

### Actual Measured Coverage Results (`app/` Package)

| Module | Statements | Missed | Coverage % | Notes |
|---|---|---|---|---|
| `app/__init__.py` | 21 | 0 | **100%** | Application factory & error handlers |
| `app/config.py` | 19 | 0 | **100%** | Configuration & grading matrices |
| `app/models.py` | 41 | 0 | **100%** | Data models & serialization |
| `app/services/grading.py` | 32 | 0 | **100%** | Subject grading service |
| `app/services/result_service.py` | 41 | 0 | **100%** | Overall classification & critical fail rule |
| `app/services/analytics_service.py` | 59 | 0 | **100%** | Dashboard & section analytics engine |
| `app/services/marks_service.py` | 53 | 1 | **98%** | Marks validation & calculation service |
| `app/services/student_service.py` | 189 | 7 | **96%** | Atomic JSON storage & CRUD validation |
| `app/routes/login.py` | 43 | 0 | **100%** | Authentication routes |
| `app/routes/student.py` | 42 | 1 | **98%** | Student portal routes |
| `app/routes/teacher.py` | 117 | 6 | **95%** | Teacher portal & CRUD routes |
| `app/routes/__init__.py` | 32 | 7 | **78%** | Route access guard decorators |
| `app/main.py` | 7 | 7 | **0%** | CLI bootstrap (`if __name__ == "__main__":`) |
| **TOTAL (`app/`)** | **696** | **29** | **96%** | **Exceeds 90% core & 80% overall targets** |

### Why High Code Coverage Alone Does Not Guarantee Defect-Free Software
A critical lesson demonstrated by this project is that **100% statement coverage of `app/services/grading.py` is achieved even when the intentional off-by-one defect (`validated_mark > 35` instead of `>= 35`) is present!** Why? Because testing `mark = 42` executes the `return "C"` statement, and testing `mark = 20` executes the `return "F"` statement—achieving 100% statement and branch coverage without ever testing the exact boundary value `35`. Only combining White-Box coverage with rigorous Black-Box **Boundary Value Analysis (BVA)** exposes the off-by-one defect.

---

## 11. Software Testing Concepts Demonstrated (STQA Syllabus Mapping)

Full formal deliverables for each topic below are available in the `docs/` directory.

### A. Introduction to Software Testing
- **Definition & Objectives:** Software testing is the systematic process of executing a program with the intent of finding defects and verifying that the software meets its specified functional and non-functional requirements (`docs/requirements.md`).
- **Verification vs. Validation:**
  - *Verification ("Are we building the product right?"):* Confirming that `marks_service.py`, `grading.py`, and `result_service.py` conform to exact mathematical formulas and grading tables through unit and white-box tests.
  - *Validation ("Are we building the right product?"):* Confirming through Selenium E2E user journeys that teachers and students can accomplish their real-world academic tasks intuitively and securely.

### B. Test Planning and Estimation
- Guided by the IEEE 829 standard (`docs/test-plan.md` and `docs/estimation.md`), testing was organized around defined **Scope**, **Test Environment**, **Entry Criteria**, **Exit Criteria**, **Suspension/Resumption Criteria**, **Work Breakdown Structure (WBS)** effort estimates (`40.0` estimated hours vs. `37.0` actual hours), and **Risk Mitigation** (such as using `tmp_path` fixtures to prevent test data corruption).

### C. Defect Reporting and Tracking
- A **Software Defect (Bug)** occurs whenever the actual behavior of the application deviates from its expected specification (`docs/defect-report.md`).
- Each defect is classified by **Severity** (technical impact on the system: `S1 Critical`, `S2 Major`, `S3 Minor`) and **Priority** (urgency of scheduling a fix: `P1 High`, `P2 Medium`, `P3 Low`).
- **Defect Lifecycle (`docs/defect-lifecycle.md`):**
  ```text
  New → Assigned → Open → Fixed → Retest → Closed
                                    │
                                    └──► Reopened (if defect persists during Retest) ──► Open
  ```

### D. Black-Box Testing Techniques
Documented in `docs/black-box-testing.md` and automated in `tests/blackbox/test_blackbox_techniques.py`:
1. **Equivalence Partitioning (EP):** Divides the subject mark input domain into 8 valid grade partitions (`90–100`, `85–89`, `80–84`, `70–79`, `60–69`, `50–59`, `35–49`, `0–34`) and 3 invalid partitions (`< 0`, `> 100`, non-integer/empty).
2. **Boundary Value Analysis (BVA):** Tests all 34 exact edge points across the 9 boundary clusters: `[-1, 0, 1]`, `[33, 34, 35, 36]`, `[48, 49, 50, 51]`, `[58, 59, 60, 61]`, `[68, 69, 70, 71]`, `[78, 79, 80, 81]`, `[83, 84, 85, 86]`, `[88, 89, 90, 91]`, and `[99, 100, 101]`.
3. **Decision Table Testing:** Evaluates multi-condition business rules across 4 decision tables: Login Validation, Subject Pass/Fail & Critical Overall Override Rule, Celebratory Popup Session Suppression, and Role-Based Access Permissions.

### E. White-Box Testing Techniques
Documented in `docs/white-box-testing.md` and automated in `tests/whitebox/test_whitebox_coverage.py`:
1. **Statement Coverage ($C_0$):** Ensures every line of code in core services is executed.
2. **Branch / Decision Coverage ($C_1$):** Ensures every `if/elif/else` and `try/except` block evaluates to both `True` and `False`.
3. **Condition Testing:** Evaluates atomic boolean sub-expressions in compound conditions (e.g., `if mark is None or isinstance(mark, bool)`).
4. **Basis Path Testing (Cyclomatic Complexity $V(G)$):** Both `calculate_subject_grade()` and `determine_classification()` have a Cyclomatic Complexity of $V(G) = 7 + 1 = 8$, and all 8 independent execution paths are explicitly tested.

### F. Test Metrics and Quality Measurement
Documented in `docs/test-metrics.md`:
- **Test Execution Percentage:**
  $$\text{Test Execution \%} = \left( \frac{\text{Executed Test Cases}}{\text{Total Test Cases}} \right) \times 100 = \left( \frac{171}{171} \right) \times 100 = 100\%$$
- **Test Pass Percentage:**
  $$\text{Test Pass \%} = \left( \frac{\text{Passed Test Cases}}{\text{Executed Test Cases}} \right) \times 100$$
  *(100% when all rules are intact; 98.25% [`168 / 171`] when the intentional BVA defect `DEF-SRMS-BVA-035` is active).*
- **Defect Density:**
  $$\text{Defect Density} = \frac{\text{Total Confirmed Defects}}{\text{Size in KLOC}} = \frac{5}{0.696 \text{ KLOC}} \approx 7.18 \text{ defects/KLOC}$$
- **Automation Coverage:** $100\%$ (`171 / 171` test cases automated in Pytest).

### G. Final Case Study / Mini Project Synthesis
SRMS integrates requirements engineering, defensive software architecture, UI/UX design, multi-tier test automation, defect tracking, and empirical quality measurement into a single cohesive repository.

---

## 12. Intentional Defect Demonstration (`DEF-SRMS-BVA-035`)

> **IMPORTANT — INTENTIONAL ACADEMIC DEFECT DEMONSTRATION:**  
> This repository currently contains **one deliberately introduced off-by-one boundary defect** in `app/services/grading.py` to provide a live, reproducible failure for college STQA evaluation and defect-reporting demonstrations.

### 1. What the Defect Is
In `app/services/grading.py` (lines 35–39), the function `calculate_subject_grade(mark)` determines the letter grade for a single subject. For Grade `C` (defined in the grading matrix as `35–49` marks), the relational operator was intentionally changed from `>=` to `>`:

```python
# Correct Condition (Specification):
if validated_mark >= 35:
    return "C"

# Intentionally Defective Condition Currently in app/services/grading.py:
if validated_mark > 35:
    return "C"
return "F"
```

### 2. Why `35` Is a Critical Boundary Value
In the Class 10 examination scheme, `35` is the **minimum passing mark** and the **lower inclusive boundary** of the Grade `C` partition (`35–49`), directly adjacent to the upper boundary of the failing Grade `F` partition (`0–34`). Off-by-one errors (`>` instead of `>=`) at partition boundaries are among the most common logic bugs in real-world software.

### 3. Expected vs. Actual Behaviour for `mark = 35`
- **Input:** `mark = 35`
- **Expected Result:** Grade `"C"`
- **Actual Result:** Grade `"F"`

### 4. How the Automated Tests Detect the Defect
A dedicated Boundary Value Analysis test—`test_bva_minimum_passing_mark_35_grade_c_defect_demo`—was added in `tests/blackbox/test_blackbox_techniques.py` (lines 139–152). When executed, Pytest calls `calculate_subject_grade(35, subject_name="Mathematics")` and asserts `actual_grade == "C"`, immediately catching the `"F"` return value and raising an `AssertionError`.

### 5. Exact Command to Reproduce the Failure
Run the following command in PowerShell to execute the dedicated BVA defect demonstration test:

```powershell
python -m pytest tests/blackbox/test_blackbox_techniques.py -k "test_bva_minimum_passing_mark_35_grade_c_defect_demo" -v
```

**Actual Failure Output:**
```text
FAILED tests/blackbox/test_blackbox_techniques.py::TestBoundaryValueAnalysis::test_bva_minimum_passing_mark_35_grade_c_defect_demo
AssertionError: BVA Defect Detected at mark=35: Expected grade 'C' (35-49 band), but calculate_subject_grade(35) returned 'F'.
assert 'F' == 'C'
  - C
  + F
```

*(Note: When running the full test suite via `python -m pytest -v`, `3` test items fail out of `171`—the dedicated BVA defect demo test, the parameterized BVA cluster test at `35`, and the unit grade boundary test at `35`—while all other `168` tests pass.)*

### 6. Structured Defect Record (`DEF-SRMS-BVA-035`)

| Field | Value |
|---|---|
| **Defect ID** | `DEF-SRMS-BVA-035` |
| **Title** | Off-by-one boundary error in `calculate_subject_grade()`: score of `35` returns `"F"` instead of `"C"` |
| **Module** | `app/services/grading.py` (`calculate_subject_grade`) |
| **Testing Technique** | Black-Box Testing — Boundary Value Analysis (BVA) |
| **Expected Result** | `"C"` |
| **Actual Result** | `"F"` |
| **Severity** | **Major / High (S2)** — Misgrades students scoring at the exact passing boundary (`35/100`) |
| **Priority** | **High (P1)** — Must be fixed before final result publication |
| **Current Status** | **Open** (Intentionally active for academic demonstration) |

### 7. How to Fix and Retest the Defect (`Fixed → Retest → Closed`)
To resolve the defect after completing the demonstration:
1. Open `app/services/grading.py` and change line 37 from `if validated_mark > 35:` back to `if validated_mark >= 35:`.
2. Re-run `python -m pytest -v` to verify that all `171` tests pass (`100%` pass rate) and transition `DEF-SRMS-BVA-035` to **Closed**.  
*(This grading rule must be restored before treating the application as a final production-ready result system.)*

---

## 13. Application and Testing Screenshots

> *Note: The placeholders below show key functional screens and test execution evidence from the SRMS project.*

### 1. Application Login Page
Demonstrates the SRMS academic login interface, preassigned demonstration credential guide, and password visibility toggle.
<!-- INSERT SCREENSHOT: Application Login Page -->
![Application Login Page](screenshots/login-page.png)

### 2. Teacher Dashboard
Demonstrates the Teacher Dashboard Overview displaying total students, Section A/B/C counts, passed/failed counts, distinction holders, and the student result summary table.
<!-- INSERT SCREENSHOT: Teacher Dashboard -->
![Teacher Dashboard](screenshots/teacher-dashboard.png)

### 3. Student Management Page (CRUD, Search & Section Filter)
Demonstrates the Teacher Student Management view for creating, searching, filtering by section (`A`, `B`, `C`), editing, and deleting student records.
<!-- INSERT SCREENSHOT: Student Management Page -->
![Student Management Page](screenshots/student-management.png)

### 4. Marks Entry Page
Demonstrates the six-subject Marks Management interface with automatic calculation of total marks out of 600, percentage, individual subject grades, and overall classification.
<!-- INSERT SCREENSHOT: Marks Entry Page -->
![Marks Entry Page](screenshots/marks-entry.png)

### 5. Student Result Page & Celebratory Pass Popup
Demonstrates the Student Dashboard scorecard (`student01`), subject-wise marks and grades, and the one-time celebratory result announcement popup.
<!-- INSERT SCREENSHOT: Student Result Page -->
![Student Result Page](screenshots/student-result-page.png)

### 6. Official Grading Matrix
Demonstrates the Class 10 eight-tier subject grading rubric (`O` through `F`) displayed on the student portal.
<!-- INSERT SCREENSHOT: Grading Matrix -->
![Grading Matrix](screenshots/grading-matrix.png)

### 7. Class Analytics Dashboard
Demonstrates independent section-wise performance metrics, subject average bar charts, and classification distributions for Sections A, B, and C.
<!-- INSERT SCREENSHOT: Class Analytics Dashboard -->
![Class Analytics Dashboard](screenshots/class-analytics.png)

### 8. Pytest Execution in VS Code Terminal
Demonstrates automated execution of Unit, Black-Box, White-Box, Functional, and Integration test suites in the VS Code PowerShell terminal.
<!-- INSERT SCREENSHOT: Pytest Execution in VS Code Terminal -->
![Pytest Execution in VS Code Terminal](screenshots/pytest-terminal.png)

### 9. Selenium Automation Running in Chrome
Demonstrates live End-to-End browser automation executing the Teacher and Student journeys in Google Chrome.
<!-- INSERT SCREENSHOT: Selenium Automation Running in Chrome -->
![Selenium Automation Running in Chrome](screenshots/selenium-chrome-automation.png)

### 10. Pytest HTML Report
Demonstrates the self-contained HTML test execution report (`reports/test-report.html`) generated by `pytest-html`.
<!-- INSERT SCREENSHOT: Pytest HTML Report -->
![Pytest HTML Report](screenshots/pytest-html-report.png)

### 11. Code Coverage Report
Demonstrates the interactive HTML statement and branch coverage report (`reports/coverage/index.html`) generated by `pytest-cov`.
<!-- INSERT SCREENSHOT: Code Coverage Report -->
![Code Coverage Report](screenshots/code-coverage-report.png)

### 12. Intentional Boundary Value Defect — Failed Test Output
Demonstrates the Boundary Value Analysis test failure (`DEF-SRMS-BVA-035`) capturing `AssertionError: assert 'F' == 'C'` for `mark = 35`.
<!-- INSERT SCREENSHOT: Intentional Boundary Value Defect – Failed Test Output -->
![Intentional Boundary Value Defect – Failed Test Output](screenshots/intentional-defect-test-failure.png)

---

## 14. Repository and Contribution Information

- **GitHub Repository:** [https://github.com/bhavana-career/STQA](https://github.com/bhavana-career/STQA)
- **Clone URL:** `https://github.com/bhavana-career/STQA.git`
- **Quick Start Summary:**
  ```powershell
  git clone https://github.com/bhavana-career/STQA.git
  cd STQA
  py -m venv .venv
  .venv\Scripts\Activate.ps1
  python -m pip install -r requirements.txt
  python -m app.main
  ```
- **Quick Test Summary:**
  ```powershell
  python -m pytest -v
  python -m pytest tests/e2e -v
  python -m pytest -v --html=reports/test-report.html --self-contained-html
  python -m pytest --cov=app --cov-report=html:reports/coverage
  ```

### Project Scope and Limitations
This project is an **academic Software Testing and Quality Assurance (STQA) mini project** designed for local execution and automated testing evaluation. It intentionally uses local JSON file persistence rather than an external database, uses predefined demonstration credentials rather than external OAuth/registration workflows, and runs on `localhost` (`127.0.0.1:5000`) rather than a public cloud server.
