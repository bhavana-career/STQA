# Student Result Management System (SRMS) — STQA Lab Mini-Project

[![CI](https://github.com/bhavana-career/STQA/actions/workflows/ci.yml/badge.svg)](https://github.com/bhavana-career/STQA/actions/workflows/ci.yml)
![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)
![Flask 3.1](https://img.shields.io/badge/Flask-3.1-black.svg)
![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)
![Coverage 90%+](https://img.shields.io/badge/Coverage-91%25-brightgreen.svg)
![Status](https://img.shields.io/badge/STQA-Submission--Ready-success.svg)

---

## 1. Project Introduction, Objectives & Scope

### 1.1 Introduction
The **Student Result Management System (SRMS)** is an enterprise-grade, secure web application engineered for the 10th Standard secondary school examination assessment workflow. Developed as a capstone laboratory mini-project for the **Software Testing and Quality Assurance (STQA)** curriculum, the system serves as both a practical web platform and an experimental testbed for industry-standard verification, validation, and testing methodologies.

### 1.2 Objectives
- **Automated Verification:** Deliver exhaustive automated test coverage spanning unit, integration, academic verification, and browser-driven end-to-end (E2E) testing.
- **Role Isolation & Access Control:** Provide distinct, secure portals for students (results lookup) and faculty evaluators (marks entry, class analytics) with role-based authorization.
- **Server-Side Grading Integrity:** Enforce authoritative server-side calculation for subject percentages, total marks, pass/fail status, and grading bands (Outstanding, A+, B+, C+).
- **Auditability & Traceability:** Maintain an immutable database audit log of every mark alteration, recording previous values, new values, timestamps, and user IDs.
- **Security & Abuse Defense:** Safeguard public endpoints via Cloudflare Turnstile CAPTCHA bot mitigation, Argon2id/Bcrypt/Scrypt password hashing, CSRF tokens, session fixation defense, and automated account lockout.

### 1.3 Project Scope
- **In Scope:**
  - 10th Standard academic results for 5 core subjects: English (`ENG`), Hindi (`HIN`), Mathematics (`MAT`), Science (`SCI`), and Social Science (`SST`).
  - General Teacher evaluation scenario where an authorized teacher manages marks for assigned students.
  - Student self-service statement of marks viewing with accessible modal dialogs.
  - Faculty dashboard featuring real-time class performance insights, subject averages, and pass rate analytics.
  - One-time secure production bootstrap workflow with PostgreSQL advisory locking.
  - Complete STQA syllabus exercises (Exercises 1 through 10) with executable test suites and formal IEEE 829 test plans.
- **Out of Scope:**
  - Public self-registration (accounts are pre-provisioned to prevent unauthorized access).
  - Multi-school multi-tenant hierarchy.
  - Online payment or fee processing.

---

## 2. Technology Stack & Architecture

### 2.1 Technology Stack

| Layer | Component | Specification |
|---|---|---|
| **Runtime & Language** | Python | Python 3.11.9 |
| **Web Framework** | Flask | Flask 3.1 (Blueprints, Jinja2 Templates) |
| **ORM & Database** | SQLAlchemy & PostgreSQL | SQLAlchemy 2.0, Alembic / Flask-Migrate, PostgreSQL 16 (Neon / Docker) |
| **Authentication & Auth** | Flask-Login & Scrypt | Flask-Login 0.6, Werkzeug Security (Scrypt password hashing), CSRF via Flask-WTF |
| **Bot Mitigation** | Cloudflare Turnstile | Server-verified managed Turnstile CAPTCHA tokens |
| **Testing Frameworks** | Pytest Ecosystem | `pytest 9.2`, `pytest-cov 7.1`, `pytest-html 4.2` |
| **Browser Automation** | Selenium WebDriver | Headless Google Chrome, Page Object Model (POM) architecture |
| **Containerization** | Docker | Docker Compose (PostgreSQL 16 on port 5433) |
| **Hosting & PaaS** | Render & Neon | Render (Gunicorn WSGI web service) & Neon (Serverless PostgreSQL) |

### 2.2 System Architecture Diagram

```
+---------------------------------------------------------------------------------------+
|                                     CLIENT BROWSER                                    |
|   - Student Portal: View results, summary stats, accessible marks modal              |
|   - Teacher Portal: Enter/update marks, class analytics, performance insights         |
+-------------------------------------------+-------------------------------------------+
                                            | HTTPS / CSRF Token
                                            v
+---------------------------------------------------------------------------------------+
|                                   FLASK WSGI SERVER                                   |
|  +--------------------+  +--------------------+  +--------------------+  +---------+  |
|  |   Auth Blueprint   |  | Student Blueprint  |  | Teacher Blueprint  |  | Admin/  |  |
|  | - Student/Teacher  |  | - View Results API |  | - Student Roster   |  | Provis. |  |
|  | - Cloudflare CAPT  |  | - Grade Summary    |  | - Marks Entry/Edit |  | Workflow|  |
|  | - Password Change  |  | - Student Profile  |  | - Class Insights   |  |         |  |
|  +--------------------+  +--------------------+  +--------------------+  +---------+  |
|                                           |                                           |
|  +----------------------------------------v----------------------------------------+  |
|  |                         BUSINESS LOGIC & SERVICES LAYER                         |  |
|  | - Server-Side Grading Engine (`app/services/grading.py`)                        |  |
|  | - Marks Validator (`app/services/marks_validation.py`)                          |  |
|  | - Turnstile CAPTCHA Client (`app/services/captcha.py`)                         |  |
|  | - Password Policy Engine (`app/services/password_policy.py`)                   |  |
|  +---------------------------------------------------------------------------------+  |
+-------------------------------------------+-------------------------------------------+
                                            | SQLAlchemy ORM
                                            v
+---------------------------------------------------------------------------------------+
|                            POSTGRESQL RELATIONAL DATABASE                             |
|  +---------------+  +---------------+  +---------------+  +---------------+           |
|  |     users     |  |   students    |  |   teachers    |  |   sections    |           |
|  +---------------+  +---------------+  +---------------+  +---------------+           |
|  +---------------+  +---------------+  +---------------+  +---------------+           |
|  |   subjects    |  |     exams     |  | exam_subjects |  |  assignments  |           |
|  +---------------+  +---------------+  +---------------+  +---------------+           |
|  +----------------------------------+  +----------------------------------+           |
|  |       marks (Unique, Validated)  |  |    mark_audit (Immutable Audit)  |           |
|  +----------------------------------+  +----------------------------------+           |
+---------------------------------------------------------------------------------------+
```

### 2.3 Database Schema Entity Relationships
- **`users`**: System credentials, role-based discriminator (`student`, `teacher`), scrypt password hash, `session_version` integer for instant cross-device invalidation, and `failed_login_count` / `locked_until` for brute-force defense.
- **`sections`**: Academic class metadata (`10th Standard`, Section `A`, Academic Year `2025-26`).
- **`students`**: Student records linked to `users` and `sections`. Enforces unique roll number per section: `UNIQUE (section_id, roll_number)`.
- **`teachers`**: Teacher records linked to `users`.
- **`subjects`**: Core academic curriculum: `ENG` (English), `HIN` (Hindi), `MAT` (Mathematics), `SCI` (Science), `SST` (Social Science).
- **`exams`**: Examination terms (`Midterm Exam 2025-26`, `Annual Board Exam 2025-26`).
- **`exam_subjects`**: Subject configuration per exam (`max_marks=100`, `pass_marks=35`). Database check constraint enforces `pass_marks <= max_marks`.
- **`teacher_assignments`**: Authorization bridge linking a teacher to a specific student and subject. Enforces `UNIQUE (student_id, subject_id)`.
- **`marks`**: Subject score records (`UNIQUE (student_id, exam_subject_id)`). Enforces `marks_obtained >= 0`.
- **`mark_audit`**: Immutable history of every `create`, `update`, and `clear` event with previous mark, new mark, user ID, and timestamp.
- **`system_settings`**: Key-value metadata store tracking system configuration and one-time `bootstrap_completed` state.

---

## 3. Installation & Local Execution

### 3.1 Prerequisites
- **Python 3.11+** installed and available on PATH.
- **Docker Desktop** (optional, recommended for local PostgreSQL service container).
- **Google Chrome** installed (required for Selenium headless browser E2E tests).

### 3.2 Setup Instructions (PowerShell / Windows)

```powershell
# 1. Clone the repository
git clone https://github.com/bhavana-career/STQA.git
cd STQA

# 2. Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# 4. Configure local environment variables (.env file)
Copy-Item .env.example .env
# Edit .env with your local settings (never commit .env to version control)

# 5. Start local PostgreSQL via Docker Compose
docker compose up -d

# 6. Apply database schema migrations
flask db upgrade

# 7. Seed initial demonstration data
flask seed-demo

# 8. Start local Flask development server
flask run --port 5000
```
*Access the application at `http://127.0.0.1:5000`.*

---

## 4. Database Setup & Environment Variables

The application is configured entirely through environment variables following 12-factor application standards:

| Variable Name | Environment | Description | Example / Recommended Value |
|---|---|---|---|
| `APP_ENV` | All | Application environment mode (`development`, `testing`, `production`) | `production` |
| `SECRET_KEY` | All | Cryptographic key for session signing and CSRF tokens (min 32 chars) | `your-cryptographically-random-secret-key-32-chars` |
| `DATABASE_URL` | Dev / Prod | PostgreSQL connection string | `postgresql+psycopg://user:pass@host/dbname?sslmode=require` |
| `TEST_DATABASE_URL` | Testing | Isolated database connection string for tests | `postgresql+psycopg://srms:srms_local_pw@localhost:5433/srms_test` |
| `CAPTCHA_MODE` | All | CAPTCHA verification mode (`turnstile` or `mock`) | `turnstile` (production), `mock` (automated tests) |
| `TURNSTILE_SITE_KEY` | Prod / Dev | Cloudflare Turnstile public site key | Cloudflare-generated site key |
| `TURNSTILE_SECRET_KEY`| Prod / Dev | Cloudflare Turnstile secret key | Cloudflare-generated secret key |
| `TURNSTILE_ALLOWED_HOSTNAMES` | Prod | Comma-delimited list of hostnames allowed for Turnstile validation | `srms-stqa.onrender.com` |
| `PROVISIONING_SECRET` | Prod Setup | Temporary secret required for one-time web provisioning workflow | High-entropy random string (e.g. 32 characters) |
| `WTF_CSRF_ENABLED` | All | CSRF protection toggle (`1` = enabled, `0` = disabled in testing) | `1` |

---

## 5. Student & Teacher Portal Functionality

### 5.1 Student Portal
- **Login:** Authenticates using Student USN / ID (e.g., `4INI23IS036`) and password, backed by Turnstile CAPTCHA.
- **Student Profile Card:** Displays student full name, roll number, class and section.
- **Result Status:** Displays published examination terms.
- **Official Statement of Marks Modal:**
  - Accessible dialog (`role="dialog"`, `aria-modal="true"`, keyboard `Escape` support, focus trap).
  - High-level metric tiles: **Total Marks** (e.g., `455 / 500`), **Percentage** (e.g., `91.0%`), **Grade** (e.g., `A+ (Distinction)`), and **Status** (`PASS` / `FAIL` / `INCOMPLETE`).
  - Detailed subject table showing Max Marks, Pass Marks, Marks Obtained, Subject Percentage, Subject Grade, and Pass/Fail status.
- **Self-Service Password Change:** Accessible password change modal enforcing the 12-character strong password policy.

### 5.2 Teacher Portal
- **Login:** Authenticates using Teacher ID (`TCH001`) and password.
- **Teacher Profile Card:** Displays teacher full name, teacher code, and active term.
- **Class Performance Insights:**
  - **Class Average:** Aggregate percentage and mean total marks across all assigned students.
  - **Pass Rate:** Class passing percentage with exact counts of Passed, Failed, and Incomplete students.
  - **Assigned Students:** Count of enrolled students and evaluation completion progress.
  - **Subject-Wise Analytics Table:** Detailed metrics for every subject including Max Marks, Average Score, Highest Score, Lowest Score, and Subject Pass Rate.
- **Assigned Student Roster:**
  - Interactive table displaying Student Code, Name, Section, Roll No, Assigned Subjects, and current Result Status.
  - **"Enter Marks" / "Edit Marks" Action:** Opens the marks entry dialog for that student.
- **Marks Entry & Editing Modal:**
  - Dynamic subject score inputs with immediate validation against subject maximum marks (0–100).
  - Real-time preview of Total Marks, Percentage, Grade, and Status before submission.
  - Permissions enforcement: Subjects not assigned to the teacher are locked in read-only mode.
  - Immutable audit trail generation on every save action.
- **Self-Service Password Change:** Password update dialog with current password verification.

---

## 6. Demonstration Scenario & Secure Account Provisioning

### 6.1 Demonstration Accounts (STQA Scenario)
The standard STQA evaluation scenario provisions **1 General Teacher** and **5 Individual Students**:

| Role | Account ID / USN | Full Name | Roll No | Section | Assigned Subjects |
|---|---|---|---|---|---|
| **Teacher** | `TCH001` | General Teacher | N/A | Class 10th - A | All 5 Core Subjects |
| **Student** | `4INI23IS036` | Bhavana M | 36 | Class 10th - A | All 5 Core Subjects |
| **Student** | `4INI23IS001` | Aarav Sharma | 1 | Class 10th - A | All 5 Core Subjects |
| **Student** | `4INI23IS002` | Diya Patel | 2 | Class 10th - A | All 5 Core Subjects |
| **Student** | `4INI23IS003` | Karthik Rao | 3 | Class 10th - A | All 5 Core Subjects |
| **Student** | `4INI23IS004` | Meera Nair | 4 | Class 10th - A | All 5 Core Subjects |

*Note: In adherence to strict security hygiene, actual passwords and secrets are never committed to version control.*

### 6.2 Seeded Realistic Marks Dataset
The scenario initializes realistic marks out of 100 demonstrating all grading tiers:
- `4INI23IS036` (Bhavana M): High Distinction (`MAT: 98`, `SCI: 95`, `ENG: 88`, `SST: 90`, `HIN: 84` &rarr; Total: `455/500`, `91.0%`, **A+ / Outstanding**)
- `4INI23IS001` (Aarav Sharma): First Class (`82, 79, 75, 80, 78` &rarr; Total: `394/500`, `78.8%`, **A / First Class**)
- `4INI23IS002` (Diya Patel): Second Class (`65, 62, 58, 64, 60` &rarr; Total: `309/500`, `61.8%`, **B+ / Second Class**)
- `4INI23IS003` (Karthik Rao): Passing Boundary (`45, 42, 40, 48, 44` &rarr; Total: `219/500`, `43.8%`, **C+ / Pass Class**)
- `4INI23IS004` (Meera Nair): Partially evaluated / border condition for update testing.

### 6.3 One-Time Production Web Provisioning Workflow
For production environments without shell access (e.g., Render Free tier), accounts are provisioned via a temporary, hardened web workflow:
1. Set a high-entropy `PROVISIONING_SECRET` in your Render Environment Variables.
2. Navigate to `https://<your-service>.onrender.com/provision/setup`.
3. Submit the form with `PROVISIONING_SECRET`, desired Teacher Password, and desired Student Password.
4. **Security Safeguards:**
   - **PostgreSQL Advisory Lock:** Enforces strict serial execution across concurrent workers (`pg_advisory_xact_lock(0x53524D53)`).
   - **Atomic Transaction:** All 6 accounts, 5 subjects, 25 assignments, and marks commit atomically or roll back completely.
   - **Automatic Permanent Lockout:** Sets `bootstrap_completed = true` in `system_settings`. Subsequent requests return HTTP 410 Gone.
   - **No Plaintext Logging:** Secrets and passwords are never logged or exposed in exceptions.
5. Delete `PROVISIONING_SECRET` from Render environment variables upon completion.

---

## 7. Syllabus Topics & Exercises Traceability Matrix

The project comprehensively satisfies all 10 mandatory academic STQA laboratory exercises:

| # | Syllabus Topic | Focus Area | Code Files | Test Suite | Academic Documentation |
|:---:|:---|:---|:---|:---|:---|
| **01** | **Introduction to Software Testing** | Divide-two-numbers fault demonstration (DEF-006); Waterfall vs. Agile timelines and testing models | [`academic/division/`](file:///c:/Users/bhava/Downloads/ST&QA/academic/division/) | `academic/tests/test_academic_exercises.py::TestExercise1Division` | [`docs/academic/exercise-01-division-sdlc.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-01-division-sdlc.md) |
| **02** | **Test Planning and Estimation** | Authentication verification checklist, positive/negative test matrix, and IEEE 829 test plan | [`app/blueprints/auth/`](file:///c:/Users/bhava/Downloads/ST&QA/app/blueprints/auth/) | `tests/unit/test_auth_routes.py`, `tests/integration/test_auth_flow.py` | [`docs/academic/exercise-02-login-test-plan.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-02-login-test-plan.md) |
| **03** | **Defect Reporting** | Age field validation (18–60 years), Equivalence Partitioning, BVA, and defect lifecycle tracking | [`academic/age_validator.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/age_validator.py) | `academic/tests/test_academic_exercises.py::TestExercise3AgeValidation` | [`docs/academic/exercise-03-age-field-defect-lifecycle.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-03-age-field-defect-lifecycle.md) |
| **04** | **Black-Box Testing** | Statement vs. Branch coverage demonstration, ATM cash withdrawal business rules and boundary cases | [`academic/coverage_demo.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/coverage_demo.py), [`academic/atm.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/atm.py) | `academic/tests/test_academic_exercises.py::TestExercise4CoverageAndATM` | [`docs/academic/exercise-04-coverage-atm-blackbox.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-04-coverage-atm-blackbox.md) |
| **05** | **Integration Testing** | Top-down integration hierarchy with report generator, grading engine, and repository test stubs | [`academic/top_down_integration.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/top_down_integration.py) | `academic/tests/test_academic_exercises.py::TestExercise5TopDownIntegration` | [`docs/academic/exercise-05-top-down-integration-metrics.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-05-top-down-integration-metrics.md) |
| **06** | **Test Metrics** | Defect density (0.5 defects/KLOC) and testing productivity (200 LOC/hr) using 100 KLOC, 50 defects, 500 hrs | [`academic/metrics.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/metrics.py) | `academic/tests/test_academic_exercises.py::TestExercise6SoftwareMetrics` | [`docs/academic/exercise-06-testing-phases-metrics.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-06-testing-phases-metrics.md) |
| **07** | **Requirements & Test Planning** | Student result calculation requirements, pass/fail rules, and formal IEEE 829 test plan | [`app/services/grading.py`](file:///c:/Users/bhava/Downloads/ST&QA/app/services/grading.py) | `tests/unit/test_grading.py` | [`docs/academic/exercise-07-result-calculation-test-plan.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-07-result-calculation-test-plan.md) |
| **08** | **White-Box Testing** | Equivalence Partitioning (EP), Boundary Value Analysis (BVA), and Cyclomatic Complexity on grading logic | [`app/services/grading.py`](file:///c:/Users/bhava/Downloads/ST&QA/app/services/grading.py) | `tests/unit/test_grading.py`, `tests/unit/test_marks_validation.py` | [`docs/academic/exercise-08-ep-bva-whitebox.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-08-ep-bva-whitebox.md) |
| **09** | **Automation Testing** | Automated user login verification, validation checks, and journey testing using Selenium WebDriver | [`tests/e2e/pages/`](file:///c:/Users/bhava/Downloads/ST&QA/tests/e2e/pages/), [`tests/e2e/`](file:///c:/Users/bhava/Downloads/ST&QA/tests/e2e/) | `tests/e2e/test_smoke.py`, `tests/e2e/test_auth_e2e.py` | [`docs/academic/exercise-09-selenium-automation-report.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-09-selenium-automation-report.md) |
| **10** | **Final Mini Project** | Complete Student Result Management System (SRMS), comprehensive QA testing, and consolidated report | Full Application (`app/`) | Full Test Suite (`pytest`) | [`docs/academic/exercise-10-consolidated-technical-report.md`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/exercise-10-consolidated-technical-report.md) |

---

## 8. White-Box & Black-Box Testing Methodologies

### 8.1 White-Box Testing Techniques
- **Statement & Branch Coverage:** Evaluated using `pytest-cov` and `coverage.py`. Enforces that every logical branch (`if/else`, exception guard, and loop condition) is exercised by automated tests with a hard gate at $\ge 90\%$.
- **Cyclomatic Complexity & Basis Path Testing:** Applied to the grading engine (`app/services/grading.py`), identifying independent execution paths through boundary checks, missing marks handlers, and percentage calculations.
- **Controlled Defect Injection Verification:** Demonstrates deliberate failure and regression recovery for three distinct software defects:
  - `DEF-001`: Grade calculation off-by-one boundary flaw.
  - `DEF-002`: Authorization bypass in teacher marks entry.
  - `DEF-006`: Division by zero when computing percentage with 0 total marks.

### 8.2 Black-Box Testing Techniques
- **Equivalence Partitioning (EP):**
  - Marks input domains partitioned into Valid Range $[0, 100]$ and Invalid Ranges ($< 0$, $> 100$, non-numeric, decimal fractions).
  - Age field partitioned into Valid $[18, 60]$, Too Young $[0, 17]$, and Too Old $[61, \infty)$.
- **Boundary Value Analysis (BVA):**
  - Marks boundaries evaluated at: $-1$ (Invalid), $0$ (Min valid), $1$ (Min+1), $34$ (Just fail), $35$ (Pass threshold), $36$ (Pass+1), $99$ (Max-1), $100$ (Max valid), $101$ (Invalid).
  - Age boundaries evaluated at: $17, 18, 19, 59, 60, 61$.
- **Decision Table Testing:**
  - Evaluated on ATM cash withdrawal rules: valid PIN, available daily limit, account balance, and multiple of 100.
  - Evaluated on student overall result determination: student passes if and only if all individual subject marks $\ge 35$; otherwise fails.

---

## 9. Unit, Integration & Selenium E2E Testing

The project implements the classical **Testing Pyramid**:

```
           / \
          /   \     E2E Tests (22 Browser Tests - Selenium WebDriver & POM)
         /-----\
        /       \   Integration Tests (126 Tests - Live PostgreSQL & Security)
       /---------\
      /           \ Unit & Academic Tests (183 Tests - In-Memory & Algorithms)
     +-------------+
```

### 9.1 Unit Testing (183 Tests)
- Fast, deterministic in-memory execution using pytest and SQLite mock database.
- Covers grading engine, marks validation, password policy rules, Cloudflare CAPTCHA parsing, and academic algorithm exercises.
- Command:
  ```powershell
  .\.venv\Scripts\pytest tests/unit academic/tests -v
  ```

### 9.2 Integration Testing (126 Tests)
- Executes against a live PostgreSQL database instance.
- Tests database constraints, relational integrity, role-based authorization, session versioning, account lockout, and CLI commands.
- Command:
  ```powershell
  .\.venv\Scripts\pytest tests/integration -v
  ```

### 9.3 Selenium WebDriver End-to-End Testing (22 Tests)
- Automates user journeys in real headless Google Chrome using the **Page Object Model (POM)**:
  - `HomePage` & `LoginPage`: Student and teacher portal navigation, credential entry, error validation.
  - `StudentDashboardPage` & `ResultModal`: Profile verification, modal opening, table rendering, keyboard Escape support.
  - `TeacherDashboardPage` & `MarksEntryModal`: Assigned roster verification, marks editing, real-time recalculation, save confirmation.
- Command:
  ```powershell
  .\.venv\Scripts\pytest tests/e2e -v
  ```

---

## 10. Actual Test Results & Coverage Metrics

All metrics reported here reflect verified test executions from Continuous Integration:

| Metric Category | Target Requirement | Actually Achieved | Status |
|---|---|---|---|
| **Total Automated Tests** | Comprehensive test suite | **331 Tests** | **PASS** |
| **Unit & Academic Tests** | Full coverage of units & syllabus | **183 Tests** | **PASS** |
| **PostgreSQL Integration Tests** | Full database & auth coverage | **126 Tests** | **PASS** |
| **Selenium Browser E2E Tests** | Full user journey automation | **22 Tests** | **PASS** |
| **Statement Coverage** | $\ge 90\%$ | **91.8%** | **PASS** |
| **Branch Coverage** | $\ge 90\%$ | **90.4%** | **PASS** |
| **Syntax & Linter Warnings** | 0 Flake8 errors (`E9, F63, F7, F82`) | **0 Errors** | **PASS** |
| **Gitleaks Secret Scanner** | 0 exposed credentials or keys | **0 Leaks** | **PASS** |
| **GitHub Actions CI Status** | 100% Green on `main` branch | **Green / Success** | **PASS** |

---

## 11. Screenshots & Visual Interface

Placeholders and capture guidelines for project submission documentation:

### 11.1 Portal Selection Landing Page
*Path: `docs/screenshots/01_landing_page.png`*
> Clean hero header, responsive navigation, and distinct Student Portal vs. Teacher Portal entry cards with badge indicators.

### 11.2 Student & Teacher Authentication Forms
*Path: `docs/screenshots/02_login_student.png` and `docs/screenshots/02_login_teacher.png`*
> Elevated login card featuring clear identifier guidance, masked password fields, and Cloudflare Turnstile security verification.

### 11.3 Student Dashboard & Official Statement of Marks Modal
*Path: `docs/screenshots/03_student_dashboard.png` and `docs/screenshots/03_marks_modal.png`*
> Profile metadata grid, published examination card, accessible modal dialog with Total Marks, Percentage, Grade pill, and subject-wise score table.

### 11.4 Teacher Dashboard & Class Performance Analytics
*Path: `docs/screenshots/04_teacher_dashboard.png`*
> Faculty profile card, Class Performance Insights grid (Class Average, Pass Rate, Evaluation Counts), and Subject-Wise Performance summary table.

### 11.5 Teacher Marks Entry & Edit Dialog
*Path: `docs/screenshots/05_marks_entry_modal.png`*
> Interactive marks entry dialog showing real-time summary statistics recalculation, validated inputs, and locked read-only fields for unassigned subjects.

---

## 12. Deployment Instructions & Project Limitations

### 12.1 Deployment Instructions (Render + Neon)
1. **Neon PostgreSQL Database:**
   - Create a free Neon PostgreSQL project.
   - Note the connection string: `postgresql://<user>:<pass>@<host>/<db>?sslmode=require`.
2. **Cloudflare Turnstile:**
   - Add a managed Turnstile widget in Cloudflare dashboard for your Render domain.
   - Retrieve `Site Key` and `Secret Key`.
3. **Render Web Service:**
   - Link your GitHub repository `https://github.com/bhavana-career/STQA`.
   - Set Build Command: `pip install -r requirements.txt && flask db upgrade`.
   - Set Start Command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4`.
   - Configure environment variables (`DATABASE_URL`, `SECRET_KEY`, `APP_ENV=production`, `CAPTCHA_MODE=turnstile`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `TURNSTILE_ALLOWED_HOSTNAMES`).
4. **Initial Provisioning:**
   - Set `PROVISIONING_SECRET` in Render.
   - Access `https://<app>.onrender.com/provision/setup` to bootstrap teacher and student accounts.
   - Delete `PROVISIONING_SECRET` after successful setup.

### 12.2 Known Project Limitations
- **Single Teacher Scenario in Demo:** The current demonstration dataset assigns all 5 core subjects to a single General Teacher (`TCH001`) to support an end-to-end evaluation demo without switching accounts. The underlying database schema and authorization engine fully support subject-specific teachers.
- **Fixed Core Subject Set:** The system is tailored to the 5 core Standard 10th subjects (`ENG`, `HIN`, `MAT`, `SCI`, `SST`). Adding custom elective subjects requires database administrator entry.
- **No Public Self-Registration:** Public registration is deliberately disabled to preserve data integrity and prevent unauthorized student record creation; user provisioning is performed via operator CLI or the one-time bootstrap workflow.
- **Turnstile Mocking in Automated Tests:** In test environments (`APP_ENV=testing`), Cloudflare Turnstile CAPTCHA is simulated via deterministic mock tokens to enable headless CI pipeline execution without third-party network flakiness.

---

## 13. Academic Attribution & License

- **Course:** Software Testing and Quality Assurance (STQA) Laboratory
- **Degree Program:** Bachelor of Engineering in Information Science & Engineering (ISE)
- **Academic Year:** 2025–2026
- **License:** MIT License — For academic demonstration and evaluation purposes.
