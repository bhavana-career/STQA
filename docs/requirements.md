# Requirements Specification — Student Result Management System (SRMS)

> **Status:** Phase 1 draft — awaiting approval.  
> **Scope:** Fictional 10th Standard result portal built for an STQA (Software Testing & Quality Assurance) laboratory. It is **not** affiliated with, and must not imitate, any real examination board or government portal. All records are **demonstration data**.

---

## 1. Purpose and scope

SRMS lets:

* **Students** sign in (with CAPTCHA) and view **only their own** examination result.
* **Teachers** sign in (with CAPTCHA), see the students/subjects assigned to them, and enter or edit marks for those assignments only.
* The **server** calculate totals, percentages, grades and pass/fail status from stored marks.

Out of scope for this release: self-registration, password reset by e-mail, admin web UI (accounts are created through a CLI), PDF mark-sheets, multi-school tenancy, result publication workflow.

## 2. Actors

| Actor | Description | How the account is created |
|---|---|---|
| Student | 10th-standard learner (fictional) | `flask create-user` CLI or demo seed (non-production only, or explicitly opted-in) |
| Teacher | Subject teacher (fictional) | `flask create-user` CLI or demo seed |
| Operator | Person deploying/maintaining the system | Has shell/CLI access to the host; no web role |
| Anonymous visitor | Not signed in | — |

## 3. Assumptions

| ID | Assumption |
|---|---|
| A-01 | One school, one class level (10th Standard), multiple sections (e.g. 10-A, 10-B). |
| A-02 | Results are per **examination** (e.g. "Annual Examination 2025–26 (Demo)"). The demo has one examination; the schema supports more. |
| A-03 | Each (student, subject) pair has **exactly one** responsible teacher for marks entry. A teacher may teach several subjects/students. |
| A-04 | Marks become visible to the student as soon as they are saved (no publication workflow). If any subject mark is missing the result shows as **INCOMPLETE**. |
| A-05 | Login identifiers: students use their Student ID (e.g. `STU2026001`); teachers use their Teacher ID (e.g. `TCH001`). Identifiers are case-insensitive on input and stored upper-case. |
| A-06 | Demo subjects (all fictional demo data): English, Hindi, Mathematics, Science, Social Science — each max 100, pass mark 35. Schema supports different maxima per subject. |
| A-07 | The deployed demo may be cold-started (free hosting tier) — first request can be slow. |

## 4. Functional requirements

### 4.1 Authentication (FR-AUTH)

| ID | Requirement |
|---|---|
| FR-AUTH-01 | Separate login pages: `/student/login` and `/teacher/login`. A student account cannot log in through the teacher page and vice versa (same generic error as bad credentials). |
| FR-AUTH-02 | Login requires identifier, password, and a CAPTCHA token. Empty fields are rejected with field-level messages (client- and server-side). |
| FR-AUTH-03 | The CAPTCHA token is verified **server-side** with the provider's verification API **before** the password is checked. Missing, invalid, expired/duplicate, wrong-hostname/action or unsuccessful tokens are rejected. |
| FR-AUTH-04 | If the CAPTCHA provider is unreachable, times out, or returns a malformed response, login **fails closed** with a "verification service unavailable" message (HTTP 503). |
| FR-AUTH-05 | Passwords are hashed with Werkzeug `scrypt` (salted). Plain-text passwords are never stored or logged. |
| FR-AUTH-06 | Invalid identifier and invalid password produce the **same** generic message ("Invalid ID or password") to limit account enumeration. |
| FR-AUTH-07 | **Lockout policy:** 5 consecutive failed password attempts (after a valid CAPTCHA) lock the account for 15 minutes. A successful login resets the counter. Values are configurable (`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`). |
| FR-AUTH-08 | On successful login the session is regenerated (cleared then re-populated) to prevent session fixation. |
| FR-AUTH-09 | Logout (POST, CSRF-protected) clears the session **and** increments the user's `session_version`, invalidating any copied session cookie. |
| FR-AUTH-10 | Sessions expire after 30 minutes of inactivity (`SESSION_LIFETIME_MINUTES`). Expired sessions are redirected to login (pages) or receive 401 (APIs). |
| FR-AUTH-11 | No public self-registration for any role. |

### 4.2 Authorization (FR-AUTHZ)

| ID | Requirement |
|---|---|
| FR-AUTHZ-01 | Role-based access: `student` and `teacher`. Role is stored in the database and never accepted from client input. |
| FR-AUTHZ-02 | Students can only read their own result. Student result endpoints take **no student ID parameter**; the identity comes from the session. |
| FR-AUTHZ-03 | Students cannot call any teacher page or API (HTTP 403). |
| FR-AUTHZ-04 | Teachers can read/write marks only for (student, subject) pairs assigned to them. Requests for unassigned or non-existent students return 404 (no existence disclosure); requests mixing assigned and unassigned subjects return 403 and change nothing. |
| FR-AUTHZ-05 | Client-supplied fields such as `student_id` in the body, `role`, `teacher_id`, `total`, `percentage`, `grade`, `status` are ignored or rejected; the server derives them. |
| FR-AUTHZ-06 | Unauthenticated page requests redirect to the relevant login page; unauthenticated API requests return 401 JSON. |
| FR-AUTHZ-07 | All state-changing requests require a valid CSRF token. |

### 4.3 Marks management (FR-MARK)

| ID | Requirement |
|---|---|
| FR-MARK-01 | Teacher dashboard lists assigned students (ID, name, section, roll no.) and, per student, the assigned subjects with current marks. |
| FR-MARK-02 | A teacher can enter/edit marks for one student and one examination across their assigned subjects and save them in a **single atomic transaction** (all-or-nothing). |
| FR-MARK-03 | Validation (server-side authoritative, mirrored client-side): mark must be a number, `0 ≤ mark ≤ subject.max_marks`, and a multiple of **0.5** (e.g. `78`, `78.5`, `78.50` valid; `78.25`, `78.3` invalid). Blank = "not entered" (stored as no row / NULL — see FR-MARK-05). Malformed values (`"abc"`, `"1e2"`, `"NaN"`, `"Infinity"`, `" "`, booleans, arrays) are rejected. |
| FR-MARK-04 | Unknown/invalid `exam_id`, `subject_id` or student references are rejected (404/422) without partial writes. |
| FR-MARK-05 | Clearing a previously entered mark is allowed (sets it to "not entered") and is audited. |
| FR-MARK-06 | Every create/update/clear writes a `mark_audit` row (old value, new value, changed-by user, timestamp) inside the same transaction. |
| FR-MARK-07 | Students have no write path to marks (no route exists; any attempt to reach teacher write APIs returns 403). |

### 4.4 Result display and calculation (FR-RES)

| ID | Requirement |
|---|---|
| FR-RES-01 | Student dashboard shows: student name, Student ID, class & section, roll number, examination name/year, subject-wise marks (obtained / max / subject grade / subject pass-fail), total obtained, total maximum, percentage, overall grade, overall status. Displayed as a dashboard card with a "View detailed result" modal (popup). |
| FR-RES-02 | All calculations happen on the server in a pure, unit-tested module (`app/services/grading.py`). Browser-supplied values are never used. |
| FR-RES-03 | The page is clearly labelled "Demonstration data — not an official result". |

#### 4.4.1 Calculation rules (configurable in `app/config.py → GRADING`)

1. **Total obtained** = Σ marks_obtained over all subjects of the exam.
2. **Total maximum** = Σ subject.max_marks over all subjects of the exam.
3. **Percentage** = total_obtained ÷ total_maximum × 100, computed with `Decimal`, then **rounded half-up to 2 decimal places**. The rounded value is both displayed and used for grading (what you see is what is graded).
4. **Subject pass** ⇔ marks_obtained ≥ subject.pass_marks (demo: 35 of 100).
5. **Overall PASS** ⇔ every subject passed **and** percentage ≥ 35.00 (`GRADING.min_overall_percentage`).
6. **Overall grade** (from percentage, only when status is PASS):

| Grade | Percentage range (inclusive lower bound) |
|---|---|
| A1 | 90.00 – 100.00 |
| A2 | 80.00 – 89.99 |
| B1 | 70.00 – 79.99 |
| B2 | 60.00 – 69.99 |
| C1 | 50.00 – 59.99 |
| C2 | 40.00 – 49.99 |
| D  | 35.00 – 39.99 |
| E  | below 35.00, **or** overall status FAIL (any subject failed) |

7. **Subject grade** uses the same table applied to (marks_obtained ÷ subject.max_marks × 100), rounded half-up to 2 dp.
8. **INCOMPLETE:** if any subject of the exam has no mark, status = `INCOMPLETE`; total/percentage/grade are **not** shown (partial marks entered so far are listed with "Not entered").
9. Status values: `PASS`, `FAIL`, `INCOMPLETE`.

### 4.5 User interface (FR-UI)

| ID | Requirement |
|---|---|
| FR-UI-01 | Responsive layouts (≥ 320 px wide) for both login pages and both dashboards. |
| FR-UI-02 | Every input has an associated `<label>`; errors are linked via `aria-describedby` and announced via `role="alert"`/`aria-live`. |
| FR-UI-03 | Fully keyboard operable (tab order, visible focus, modal focus trap, Esc closes modal). |
| FR-UI-04 | Loading states: login button shows "Signing in…" and disables during submit; marks save shows a spinner and disables the Save button; the result modal shows "Loading…". |
| FR-UI-05 | Clear success ("Marks saved") and error messages, including network failures. |
| FR-UI-06 | Stable `id`/`data-testid` attributes on interactive elements for Selenium. |

### 4.6 Operations (FR-OPS)

| ID | Requirement |
|---|---|
| FR-OPS-01 | `GET /health` returns 200 `{"status":"ok","database":"ok"}` when the DB is reachable, 503 otherwise. No secrets in the response. |
| FR-OPS-02 | Database schema managed by Flask-Migrate (Alembic) migrations. |
| FR-OPS-03 | `flask seed-demo` creates fictional demo data. It **refuses to run when `APP_ENV=production`** unless `--i-understand-this-is-production` is passed; demo passwords are taken from env vars/prompt, never hard-coded for production. Never runs automatically. |
| FR-OPS-04 | `flask create-user` creates a single student/teacher account interactively (password prompt, hidden). |

## 5. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-SEC-01 | Secrets | All secrets (DB URL, `SECRET_KEY`, CAPTCHA secret) via environment variables. `.env` is git-ignored; `.env.example` contains placeholders only. |
| NFR-SEC-02 | Cookies | Production: `Secure`, `HttpOnly`, `SameSite=Lax` session cookie. |
| NFR-SEC-03 | Debug | `DEBUG=False` in production; app refuses to start in production if `SECRET_KEY` is missing/weak or CAPTCHA is in test/disabled mode. |
| NFR-SEC-04 | Headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, a Content-Security-Policy allowing only self + `challenges.cloudflare.com`; HSTS in production. |
| NFR-SEC-05 | Injection | All DB access via SQLAlchemy ORM / bound parameters; Jinja auto-escaping on. |
| NFR-SEC-06 | Logging | Log auth failures and mark changes without passwords, tokens or secrets. |
| NFR-REL-01 | Persistence | Data stored in managed PostgreSQL; survives restarts/redeploys. |
| NFR-REL-02 | Transactions | Multi-row mark updates are atomic. |
| NFR-PERF-01 | Performance | Dashboard requests < 1 s server time with demo data (excluding cold start). |
| NFR-TEST-01 | Testability | Grading logic is pure and side-effect free; CAPTCHA verifier is injectable/mockable. |
| NFR-TEST-02 | Coverage | Target ≥ 90 % line and branch coverage on `app/services/grading.py` and mark validation (a target, actual figures will be reported from pytest-cov output). |
| NFR-PORT-01 | Portability | Runs on Python 3.11+, PostgreSQL 15+, Windows/macOS/Linux for development. |

## 6. CAPTCHA requirements (summary — details in architecture.md §4)

| ID | Requirement |
|---|---|
| CAP-01 | Provider: **Cloudflare Turnstile** (see architecture.md for rationale). |
| CAP-02 | `TURNSTILE_SITE_KEY` (public) and `TURNSTILE_SECRET_KEY` (server-only) from env vars. |
| CAP-03 | `CAPTCHA_MODE` ∈ {`turnstile`, `mock`}. `mock` is accepted **only** when `APP_ENV=testing`; any other combination aborts startup. |
| CAP-04 | Production startup aborts if Turnstile's documented **test** keys (`1x0000…`, `2x0000…`, `3x0000…`) are configured. |
| CAP-05 | Automated tests use (a) an in-process mocked verifier for unit/integration tests, and (b) Turnstile's official test site/secret keys for E2E browser tests. Selenium never solves a live challenge. |

## 7. Separate academic exercises (not part of the application)

Located under `academic/`, each with its own pytest tests, clearly labelled **"Academic demonstration — not production logic"**:

1. Division program with an intentionally introduced fault (and corrected version).
2. Age-field validation (valid 18–60) — equivalence partitioning & BVA.
3. ATM withdrawal black-box test cases.
4. Statement & branch coverage example (measured with pytest-cov).
5. Top-down integration testing with stubs.
6. Defect life-cycle state machine example.
7. Agile vs Waterfall timeline estimation.
8. Defect density & productivity calculations — **requires the sample data from the syllabus** (pending from user).

## 8. Traceability

Each requirement ID above is referenced by at least one test case in [test-cases.md](test-cases.md). The traceability matrix is in [test-plan.md](test-plan.md#9-requirements-traceability).
