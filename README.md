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

### 3. Full Test Suite with Statement & Branch Coverage
```powershell
pytest -v --cov=app --cov-branch --cov-report=term-missing --cov-report=html:reports/coverage --html=reports/test_report.html --self-contained-html
```

### 4. Controlled Fault-Injection Defect Demonstrations
```powershell
pytest fault_injection/tests/ -v
```
*(Demonstrates deliberate before-fix defect failures for DEF-001 and DEF-002, isolated outside production logic).*
