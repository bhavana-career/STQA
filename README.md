# Student Result Management System (SRMS) — STQA Lab

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

### 3. Selenium WebDriver End-to-End (E2E) Smoke Tests
Headless Chrome browser automation using Selenium WebDriver:
```powershell
pytest tests/e2e/test_smoke.py -v
```
*Note: Requires Google Chrome or Chromium installed. Selenium Manager automatically resolves and provisions the matching chromedriver binary. In case of any test assertion or timeout failure, an automated full-page screenshot artifact is automatically saved to `reports/screenshots/<test_name>.png`.*

### 4. Full Automated Test Suite with Statement & Branch Coverage
```powershell
pytest -v --cov=app --cov-branch --cov-report=term-missing --cov-report=html:reports/coverage --html=reports/test_report.html --self-contained-html
```

### 5. Controlled Fault-Injection Defect Demonstrations
```powershell
pytest fault_injection/tests/ -v
```
*(Demonstrates deliberate before-fix defect failures for DEF-001 and DEF-002, isolated outside production logic).*

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
