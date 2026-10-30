# Student Result Management System (SRMS) — STQA Lab

[![CI](https://github.com/bhavana-career/STQA/actions/workflows/ci.yml/badge.svg)](https://github.com/bhavana-career/STQA/actions/workflows/ci.yml)

A robust, enterprise-grade, publicly deployable Student Result Management System for 10th Standard secondary school results, developed for the Software Testing and Quality Assurance (STQA) academic laboratory.

## Tech Stack

- **Runtime & Language:** Python 3.11
- **Web Framework:** Flask 3.1
- **Database & ORM:** PostgreSQL 16, SQLAlchemy 2.0, Alembic / Flask-Migrate
- **Password Security:** Scrypt hashing via Werkzeug security
- **Authentication & Security:** Flask-Login, Flask-WTF CSRF protection, Cloudflare Turnstile CAPTCHA
- **Testing & QA:** `pytest`, `pytest-cov`, `pytest-html`, Selenium WebDriver
- **Containerization:** Docker & Docker Compose
- **Target Deployment:** Render (Web Service) & Neon (Serverless PostgreSQL)

---

## Architecture & Database Design

### Relational Schema (PostgreSQL)

- **`users`**: System credentials, role-based access (`student`, `teacher`), scrypt password hash, session revocation versioning (`session_version`), and brute-force lockout tracking (`failed_login_count`, `locked_until`).
- **`sections`**: Academic sections (e.g., Class: `10th Standard`, Section: `A`, Academic Year: `2025-26`).
- **`students`**: Student profiles linked to `users` and `sections`. Unique roll number per section (`UNIQUE (section_id, roll_number)`).
- **`teachers`**: Teacher profiles linked to `users`.
- **`subjects`**: Academic subjects (`ENG`, `HIN`, `MAT`, `SCI`, `SST`).
- **`exams`**: Academic examination terms.
- **`exam_subjects`**: Subject configuration per exam (`max_marks`, `pass_marks`). Enforces `pass_marks <= max_marks`.
- **`teacher_assignments`**: Subject-level teacher allocation per student. Enforces `UNIQUE (student_id, subject_id)` so each student-subject pair has exactly one assigned teacher.
- **`marks`**: Normalized marks table (`UNIQUE (student_id, exam_subject_id)`). Enforces non-negative marks via database check constraint.
- **`mark_audit`**: Immutable audit trail capturing every `create`, `update`, or `clear` event with previous value, new value, timestamp, and changing user ID.

---

## Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Docker Desktop (for local PostgreSQL)

### 2. Start PostgreSQL Container
```powershell
docker compose up -d
```
The PostgreSQL container runs on host port `5433` with default credentials:
- Username: `srms`
- Password: `srms_local_pw`
- Databases: `srms_dev`, `srms_test`

### 3. Virtual Environment Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

### 4. Database Migrations
Run schema migrations against the local development database:
```powershell
flask db upgrade
```

### 5. Seed Demonstration Data
Seed fictional demo dataset with realistic students, teachers, subjects, exam, teacher assignments, and sample marks:
```powershell
flask seed-demo
```

### 6. Inspect Database Status
```powershell
flask db-status
```

---

## Safe Operator CLI Commands

The system includes safe CLI administration commands:

- **`flask db-status`**: Check database connectivity and display row counts across all tables.
- **`flask create-user --role [student|teacher] --login-id ID --name "Name" --password "Pass" [--section A --roll 1]`**: Safely provision student or teacher accounts with scrypt password hashing.
- **`flask create-subject --code CODE --name "Subject Name"`**: Provision academic subjects.
- **`flask assign --teacher TCH_CODE --student STU_CODE --subject SUB_CODE`**: Assign teacher permissions per student-subject.
- **`flask unlock-user LOGIN_ID`**: Clear account lockouts after consecutive failed attempts.
- **`flask seed-demo [--reset] [--i-understand-this-is-production]`**: Seed fictional demo data.
  > [!CAUTION]
  > In production (`APP_ENV=production`), `seed-demo` requires explicit `--i-understand-this-is-production` and mandatory `DEMO_STUDENT_PASSWORD` / `DEMO_TEACHER_PASSWORD` environment variables. `--reset` is strictly forbidden in production.

---

## Running the Automated Test Suite

### 1. Fast In-Memory Unit Tests
```powershell
pytest -m unit
```

### 2. Live PostgreSQL Integration Tests
```powershell
pytest -m integration
```

### 3. Selenium WebDriver End-to-End (E2E) Automation (Page Object Model)
Headless Chrome browser automation using Selenium WebDriver and structured Page Objects (`tests/e2e/pages/`):

#### Page Object Model (POM) Architecture:
- `BasePage` (`tests/e2e/pages/base_page.py`): Common driver wrappers, explicit waits (`WebDriverWait`), click/type/text abstractions.
- `HomePage` (`tests/e2e/pages/home_page.py`): Landing page navigation, portal link interactions.
- `LoginPage` (`tests/e2e/pages/login_page.py`): Student and teacher login forms, credential submission, error alerts.
- `StudentDashboardPage` (`tests/e2e/pages/student_dashboard_page.py`): Student profile, exam results view, logout.
- `TeacherDashboardPage` (`tests/e2e/pages/teacher_dashboard_page.py`): Assigned student roster, marks entry trigger, logout.
- `ResultModal` (`tests/e2e/pages/result_modal.py`): Accessible statement of marks dialog, summary statistics, keyboard Esc close.
- `MarksEntryModal` (`tests/e2e/pages/marks_entry_modal.py`): Marks entry form, assigned/read-only validation, save confirmation.

#### Running E2E Test Suites:
```powershell
# Run the complete E2E test suite (22 browser tests)
pytest tests/e2e/ -v

# Run individual user journey suites
pytest tests/e2e/test_smoke.py -v                  # Smoke tests (10 tests)
pytest tests/e2e/test_student_journey.py -v        # Student user journeys (5 tests)
pytest tests/e2e/test_teacher_journey.py -v        # Teacher user journeys & audit verification (3 tests)
pytest tests/e2e/test_boundaries_and_security.py -v # Boundary values, input validation & security (4 tests)
```
*Note: Requires Google Chrome or Chromium installed. Selenium Manager automatically provisions the matching chromedriver. In case of any assertion or timeout failure, automated screenshot artifacts (`reports/screenshots/<test_name>.png`) and browser console logs (`reports/screenshots/<test_name>_browser.log`) are captured automatically.*

### 4. Academic STQA Laboratory Exercises (Exercises 1–10)
Run the academic test suite covering Division, Age Validation (EP/BVA), ATM Black-Box, Coverage demonstrations, Top-Down Integration with Stubs, and Software Engineering Metrics:
```powershell
pytest academic/tests/ -v
```
*(All 10 academic exercises are documented in detail under [`docs/academic/`](file:///c:/Users/bhava/Downloads/ST&QA/docs/academic/README.md)).*

### 5. Full Automated Test Suite with Statement & Branch Coverage
Run the unified 289-test suite (Unit, Integration, Academic, and Headless Chrome E2E):
```powershell
pytest -v --cov=app --cov-branch --cov-report=term-missing --cov-report=html:reports/coverage --html=reports/m8_report.html --self-contained-html
```

### 6. Controlled Fault-Injection Defect Demonstrations
```powershell
pytest fault_injection/tests/ -v
```
*(Demonstrates deliberate before-fix defect failures for DEF-001, DEF-002, and DEF-006, isolated outside production logic).*
- Before/after defect logs: `docs/evidence/faults/`
- Defect tracking and lifecycle: `docs/defects.md`

---

## Continuous Integration (CI) with GitHub Actions

The repository includes a comprehensive, multi-stage automated Continuous Integration pipeline defined in [`.github/workflows/ci.yml`](file:///c:/Users/bhava/Downloads/ST&QA/.github/workflows/ci.yml).

### 1. Trigger Behavior
- **Push:** Automatically triggers on every push to the `main` branch.
- **Pull Request:** Automatically triggers on all pull requests targeting the `main` branch.
- **Manual Execution:** Can be triggered manually on demand via GitHub Actions `workflow_dispatch`.

### 2. CI Verification Stages
Every pipeline run executes sequentially in a clean `ubuntu-latest` environment with Python 3.11:

1. **Environment Setup & Dependency Verification:**
   - Checks out the repository using `actions/checkout@v4`.
   - Sets up Python 3.11 with pip caching using `actions/setup-python@v5`.
   - Installs pinned production and development dependencies (`requirements-dev.txt`).
   - Runs `pip check` to verify zero conflicting dependencies.
2. **Code Quality & Linting:**
   - Bytecode compilation check across all modules (`python -m compileall app tests academic`).
   - Flake8 syntax error, undefined variable, and syntax checks (`flake8 app tests academic --select=E9,F63,F7,F82`).
3. **Security Hygiene & Secret Scanning:**
   - Ensures `.env` files are never tracked or committed.
   - Enforces that no private keys (`*.pem`, `*.key`) or unencrypted private key headers exist in tracked files.
4. **PostgreSQL Service Container & Database Migrations:**
   - Provisions an isolated `postgres:16-alpine` service container with automated health checks on port 5432.
   - Creates the dedicated, isolated `srms_test` database via `psql`.
   - Applies all Alembic schema migrations via `flask db upgrade`.
   - Verifies schema health and table counts via `flask db-status`.
5. **Test Execution & Quality Gates:**
   - **Unit & Academic Tests:** Executes 173 fast in-memory unit and academic syllabus tests with pytest.
   - **Integration Tests:** Executes 94 live PostgreSQL integration tests verifying models, security, and CLI commands.
   - **Headless Chrome E2E Tests:** Executes 22 browser automation tests using Selenium WebDriver and Page Object Model.
6. **Code Coverage Enforcement:**
   - Combines statement and branch coverage across all test tiers (`--cov-append`).
   - Enforces the baseline **90% coverage threshold** via `coverage report -m --fail-under=90`. Builds fail if coverage drops below 90%.
   - Generates interactive HTML coverage reports (`reports/coverage/`).
7. **Artifact Archival:**
   - Automatically uploads HTML test reports, interactive coverage reports, and failure screenshots/logs via `actions/upload-artifact@v4` with a 14-day retention period (`if: always()`).

### 3. How to Inspect CI Test Reports & Artifacts
1. Navigate to the GitHub repository: `https://github.com/bhavana-career/STQA/actions`.
2. Click on the desired workflow run (e.g., from the latest commit).
3. Under the **Artifacts** section at the bottom of the summary page, download `srms-ci-artifacts.zip`.
4. Extract the ZIP archive locally:
   - Open `reports/coverage/index.html` in any browser to inspect line-by-line branch coverage.
   - Open `reports/unit_test_report.html`, `reports/integration_test_report.html`, or `reports/e2e_test_report.html` to view test execution timelines and assertion details.
   - Inspect `reports/screenshots/` for failure screenshots and browser console logs if any test failed.

### 4. Reproducing CI Tests Locally (Windows PowerShell)

Ensure Docker Desktop is running and PostgreSQL container is active (`docker compose up -d`):

```powershell
# 1. Bytecode compilation & linting
.\.venv\Scripts\python -m compileall app tests academic
.\.venv\Scripts\flake8 app tests academic --select=E9,F63,F7,F82 --show-source --statistics

# 2. Database migrations check on local test database
$env:DATABASE_URL = "postgresql+psycopg://srms:srms_local_pw@localhost:5433/srms_test"
flask db upgrade
flask db-status

# 3. Run complete test suite matching CI (Unit, Integration, E2E & Academic)
$env:DATABASE_URL = ""
$env:TEST_DATABASE_URL = "postgresql+psycopg://srms:srms_local_pw@localhost:5433/srms_test"
pytest -v --cov=app --cov-branch --cov-report=term-missing --cov-report=html:reports/coverage --cov-fail-under=90 --html=reports/m9_report.html --self-contained-html
```

---

## Authentication & Security Architecture

### 1. Authentication Flows
- **Student Sign In (`/student/login`)**: Requires Student Login ID (`STU2026001`), password, and Cloudflare Turnstile CAPTCHA.
- **Teacher Sign In (`/teacher/login`)**: Requires Teacher Login ID (`TCH001`), password, and Cloudflare Turnstile CAPTCHA.
- **Role Isolation**: Submitting student credentials on the teacher portal (or vice versa) results in a non-revealing `401 Invalid ID or password.` and increments the failed attempt counter on that account.
- **Non-Revealing Errors**: Non-existent usernames and incorrect passwords return the identical message (`Invalid ID or password.`) with HTTP 401 to prevent user enumeration.

### 2. Session Security & Fixation Protection
- **Session Fixation Prevention**: `session.clear()` is called immediately before `login_user()`, regenerating the session and wiping pre-login cookies.
- **Global Session Revocation**: Every user has a database-backed `session_version` integer. Calling `/logout` increments `session_version` in the database, immediately invalidating all active sessions across all devices and browsers.
- **Idle Expiry**: Sessions are configured with `PERMANENT_SESSION_LIFETIME` (default: 30 minutes) and `SESSION_REFRESH_EACH_REQUEST = True`. Inactive sessions automatically expire.
- **Cookie Flags**:
  - `HttpOnly`: Always enabled (blocks JavaScript access).
  - `SameSite`: Set to `Lax` (protects against CSRF).
  - `Secure`: Enforced in production (`APP_ENV=production`).

### 3. Brute-Force Protection & Account Lockout
- Accounts track `failed_login_count` and `locked_until`.
- After 5 consecutive failed attempts (`LOGIN_MAX_ATTEMPTS`), the account is automatically locked for 15 minutes (`LOGIN_LOCKOUT_MINUTES`), returning HTTP `429 Too Many Requests`.
- Administrators can immediately unlock accounts via `flask unlock-user <LOGIN_ID>`.

### 4. Cloudflare Turnstile Setup & Modes
The application supports three CAPTCHA operating modes:
- **`CAPTCHA_MODE=mock`**: Used during local unit and integration tests. Evaluates tokens offline without external network dependencies. Strictly blocked outside `APP_ENV=testing`.
- **`CAPTCHA_MODE=turnstile` with Test Keys**: Documented Cloudflare test keys for development/staging:
  - Site Key: `1x00000000000000000000AA` (Always passes)
  - Secret Key: `1x0000000000000000000000000000000AA` (Always passes)
- **`CAPTCHA_MODE=turnstile` in Production**:
  - Cloudflare Dashboard -> Turnstile -> Add Site.
  - Set Domain to your Render domain (e.g., `srms-stqa.onrender.com`).
  - Widget Mode: *Managed*.
  - Copy Site Key into Render environment variable `TURNSTILE_SITE_KEY`.
  - Copy Secret Key into Render environment variable `TURNSTILE_SECRET_KEY`.
  - Set `TURNSTILE_ALLOWED_HOSTNAMES=srms-stqa.onrender.com`.
  > [!IMPORTANT]
  > Production interlocks strictly reject dummy tokens and test keys (`1x...`, `2x...`, `3x...`) during `create_app()`, preventing accidental test-mode deployments.
