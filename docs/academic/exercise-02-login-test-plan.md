# Exercise 2: User Login Test Checklist & IEEE 829 Test Plan

---

## 1. Exercise Objective

1. Design an exhaustive test checklist for a web application user authentication system covering functional, security, UI/UX, accessibility, and performance dimensions.
2. Develop a comprehensive suite of positive and negative test cases.
3. Produce a formal, IEEE 829-standard Test Plan tailored to the Student Result Management System (SRMS) authentication subsystem, including role-based access control and Cloudflare Turnstile CAPTCHA verification.

---

## 2. Comprehensive Login Testing Checklist

```
+-------------------------------------------------------------------------------+
|                       SRMS AUTHENTICATION CHECKLIST                           |
+-------------------------------------------------------------------------------+
|  1. UI / UX Design & Responsive Layout                                       |
|     [x] Clean form layout with username/role/password fields and submit button|
|     [x] Distinct visual feedback on active focus, hover, and disabled states  |
|     [x] Responsive rendering on mobile (375px), tablet (768px), desktop(1280px)|
|     [x] Semantic labels, aria attributes, and field validation indicators     |
|                                                                               |
|  2. Functional Verification                                                   |
|     [x] Successful login redirects to corresponding role dashboard            |
|     [x] Student credentials route to Student Portal (/student/dashboard)      |
|     [x] Teacher credentials route to Teacher Portal (/teacher/dashboard)      |
|     [x] Password input masked with standard password character masking        |
|     [x] Session persistence across page reloads                               |
|     [x] Explicit logout invalidates session and clears active cookies         |
|                                                                               |
|  3. Security & Abuse Resistance                                               |
|     [x] Password hashed using Argon2id / Bcrypt; never stored in plaintext   |
|     [x] Resistance to SQL injection and script injection payloads             |
|     [x] Cloudflare Turnstile CAPTCHA token required and server-verified       |
|     [x] Generic error messages ("Invalid username or password") to stop enum  |
|     [x] Account lockout after consecutive failed attempts (5 failures = lock) |
|     [x] CSRF protection enabled on login submission                           |
|     [x] HttpOnly, Secure, SameSite=Lax flags on session cookies               |
|                                                                               |
|  4. Performance & Availability                                                |
|     [x] Login response latency under 300ms under standard local load          |
|     [x] Database connection pooling safely handles concurrent auth requests   |
+-------------------------------------------------------------------------------+
```

---

## 3. Systematic Test Case Matrix (Positive & Negative Scenarios)

| Test Case ID | Category | Scenario / Inputs | Pre-conditions | Expected Result | Automated Test Reference |
|---|---|---|---|---|---|
| **TC-AUTH-01** | Positive | Valid Teacher credentials (`teacher1` / valid pass) + valid CAPTCHA | User active, unlocked | 302 Redirect to `/teacher/dashboard`; Session created with `role="teacher"` | `tests/unit/test_auth_routes.py::test_login_teacher_success` |
| **TC-AUTH-02** | Positive | Valid Student credentials (`STU001` / valid pass) + valid CAPTCHA | Student active, unlocked | 302 Redirect to `/student/dashboard`; Session created with `role="student"` | `tests/unit/test_auth_routes.py::test_login_student_success` |
| **TC-AUTH-03** | Negative | Missing username (empty string) | None | Form validation failure, 400 Bad Request or flash error "Username is required" | `tests/unit/test_auth_routes.py::test_login_empty_username` |
| **TC-AUTH-04** | Negative | Missing password (empty string) | None | Form validation failure, flash error "Password is required" | `tests/unit/test_auth_routes.py::test_login_empty_password` |
| **TC-AUTH-05** | Negative | Invalid username (`nonexistent_user`) | User not in database | 401 Unauthorized; Generic error "Invalid username or password" | `tests/unit/test_auth_routes.py::test_login_invalid_credentials` |
| **TC-AUTH-06** | Negative | Incorrect password for existing user | User exists | 401 Unauthorized; Failed attempt count incremented | `tests/unit/test_auth_routes.py::test_login_incorrect_password` |
| **TC-AUTH-07** | Security | SQL Injection payload in username (`' OR '1'='1`) | None | Input safely parameterized by ORM; 401 Unauthorized | `tests/unit/test_auth_routes.py::test_login_sql_injection_resilience` |
| **TC-AUTH-08** | Security | Missing or blank Turnstile CAPTCHA token | Valid user credentials | 400 Bad Request; "CAPTCHA verification failed" | `tests/unit/test_auth_routes.py::test_login_missing_captcha_token` |
| **TC-AUTH-09** | Security | Invalid / spoofed Turnstile CAPTCHA token | Valid user credentials | 400 Bad Request; Server rejects simulated token | `tests/unit/test_auth_routes.py::test_login_invalid_captcha_token` |
| **TC-AUTH-10** | Security | 5 consecutive failed login attempts | User active | Account locked; 403 Forbidden on 6th attempt; `is_locked=True` | `tests/integration/test_auth_flow.py::test_account_lockout_after_consecutive_failures` |
| **TC-AUTH-11** | Functional| Role enforcement: Student attempts accessing `/teacher/dashboard` | Student authenticated | 403 Forbidden; Redirect or error displayed | `tests/integration/test_auth_flow.py::test_role_based_access_control` |
| **TC-AUTH-12** | Functional| Logout workflow | User logged in | Session cleared; Redirect to `/login`; Back-button cannot view private data | `tests/unit/test_auth_routes.py::test_logout_flow` |

---

## 4. IEEE 829 Standard Test Plan: SRMS Authentication Subsystem

### 1. Test Plan Identifier
`STQA-TP-SRMS-AUTH-001` (Version 1.0)

### 2. References
- IEEE Std 829-2008: Standard for Software and System Test Documentation
- SRMS Software Requirements Specification (`docs/requirements.md`)
- SRMS Architecture & Security Plan (`docs/architecture.md`)
- SRMS Threat Model & Security Posture (`docs/threat-model.md`)

### 3. Introduction
This test plan defines the scope, strategy, tools, and schedule for validating the Authentication and Authorization Subsystem of the Student Result Management System. The subsystem handles role-based login (Student vs. Teacher), password verification, session cookie management, brute-force protection, and bot defense via Cloudflare Turnstile.

### 4. Test Items
- `app/blueprints/auth/routes.py`: Login, logout, and credential verification endpoints.
- `app/models.py`: `User` entity, password hash comparison, lockout flags, session versioning.
- `app/services/captcha.py`: Cloudflare Turnstile server-side verification client.
- `app/templates/auth/login.html`: Front-end login form and Turnstile client script integration.

### 5. Software Risk Issues
- **Risk 1: Credential stuffing & brute-force attacks.** (Mitigation: Account lockout after 5 failures and Cloudflare Turnstile integration).
- **Risk 2: Session fixation / cookie hijacking.** (Mitigation: Session regeneration upon authentication; `HttpOnly`, `SameSite=Lax`, `Secure` flags).
- **Risk 3: Information leakage via error messages.** (Mitigation: Unified generic error response preventing username enumeration).

### 6. Features to be Tested
- Credential validation against Argon2/Bcrypt password hashes.
- Turnstile CAPTCHA validation (valid test tokens, missing tokens, invalid tokens).
- Account lockout counter and lockout trigger behavior.
- Role-based routing upon successful authentication.
- Session termination upon logout.

### 7. Features Not to be Tested
- Third-party OAuth / Social Login (out of scope for SRMS v1.0).
- Hardware security key / FIDO2 MFA (deferred to future releases).
- Cloudflare Turnstile upstream DNS and network availability (mocked during testing).

### 8. Approach (Strategy)
Testing follows the **Test Pyramid**:
- **Unit Tests:** Direct endpoint testing via Flask test client using parameterized fixtures for edge cases and input variations.
- **Integration Tests:** End-to-end database transactions verifying lockout persistence and session state in PostgreSQL (`srms_test`).
- **End-to-End (E2E) Browser Tests:** Automated Selenium WebDriver tests running in headless Chrome with Page Object Model (`tests/e2e/test_auth_e2e.py`).

### 9. Item Pass/Fail Criteria
- **Pass:** 100% of defined unit, integration, and E2E test cases pass; no unhandled 500 Internal Server Errors; 100% statement and branch coverage on auth business logic.
- **Fail:** Any authentication bypass, unhandled exception, failed lockout trigger, or credential leakage in responses or logs.

### 10. Suspension Criteria and Resumption Requirements
- **Suspension:** Inability to connect to PostgreSQL test database or catastrophic session manager crash.
- **Resumption:** Database container restored, migrations cleanly applied, and baseline smoke tests passing.

### 11. Test Deliverables
- Executable Test Suite (`tests/unit/test_auth_routes.py`, `tests/integration/test_auth_flow.py`, `tests/e2e/test_auth_e2e.py`).
- HTML Test Execution Report (`reports/test_report.html`).
- Code Coverage Report with Branch Analysis (`reports/coverage/index.html`).

### 12. Remaining Test Tasks
- Performance testing under 50 concurrent login requests (scheduled for M10).

### 13. Environmental Needs
- Python 3.11.9 in virtual environment (`.venv`).
- PostgreSQL 16 container running on `localhost:5433` (`srms_test`).
- Google Chrome and matching ChromeDriver for Selenium E2E execution.

### 14. Staffing and Training Needs
- STQA Lab Engineer proficient in Python, Flask, pytest, Selenium, and web application security fundamentals.

### 15. Responsibilities
- **Test Author / Engineer:** Bhavya (STQA Lab).
- **Reviewer / Approver:** Course Instructor & Antigravity STQA Pair Programmer.

### 16. Schedule
- Milestone M4 (Authentication Implementation): Completed.
- Milestone M7 (Selenium POM Automation): Completed.
- Milestone M8 (Academic Documentation & Sign-off): Completed.

### 17. Approvals
- Signed off by STQA QA Lead upon passing all 12 test matrix scenarios.
