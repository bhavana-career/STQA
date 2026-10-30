# API & Route Design — SRMS

> Phase 1 draft. HTML pages are server-rendered; JSON APIs are used by the dashboards' JavaScript. All JSON APIs are same-origin, session-cookie authenticated and CSRF-protected for unsafe methods.

## 1. Conventions

* **Content type:** `application/json; charset=utf-8` for `/api/*`.
* **Auth:** Flask session cookie (`srms_session`), `HttpOnly`, `SameSite=Lax`, `Secure` in production.
* **CSRF:** unsafe methods (`POST`, `PUT`, `DELETE`) require `csrf_token` form field or `X-CSRFToken` header. The token is rendered in `<meta name="csrf-token">`.
* **Error envelope (APIs):**

```json
{ "error": { "code": "validation_error", "message": "Some marks are invalid.",
             "details": { "fields": { "MAT": "Must be between 0 and 100." } } } }
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `bad_request` / `csrf_failed` | Malformed JSON, missing CSRF token |
| 401 | `unauthenticated` | No/expired/revoked session |
| 403 | `forbidden` | Wrong role, or subject not assigned to this teacher |
| 404 | `not_found` | Unknown resource **or** student not assigned to this teacher (non-disclosure) |
| 405 | `method_not_allowed` | |
| 409 | `conflict` | DB integrity conflict |
| 422 | `validation_error` | Marks failed validation / unknown exam or subject |
| 429 | `locked` | Account locked (login page) |
| 500 | `internal_error` | Unexpected error — generic message, details only in server logs |
| 503 | `captcha_unavailable` / `db_unavailable` | Dependency failure |

## 2. Public / operational

### `GET /health`
* 200 `{"status":"ok","database":"ok","version":"<git sha or app version>"}`
* 503 `{"status":"degraded","database":"error"}` (no exception text).

### `GET /`
Landing page with links to Student login and Teacher login; demo-data disclaimer.

## 3. Authentication (HTML forms)

### `GET /student/login`, `GET /teacher/login`
Renders login form with Turnstile widget (`data-sitekey`, `data-action="login"`). Already-authenticated users are redirected to their dashboard.

### `POST /student/login`, `POST /teacher/login`
Form fields: `login_id`, `password`, `cf-turnstile-response`, `csrf_token`.

Processing order (fail fast): CSRF → required fields → length limits (`login_id` ≤ 32, `password` ≤ 128) → CAPTCHA verify → lockout check → credential + role check → session regeneration.

| Outcome | Status | Response |
|---|---|---|
| Success | 302 | → `/student/dashboard` or `/teacher/dashboard` |
| Empty field(s) | 400 | Form re-rendered, field errors |
| CAPTCHA missing | 400 | "Please complete the CAPTCHA." |
| CAPTCHA invalid / expired / failed | 400 | "CAPTCHA verification failed. Please try again." |
| CAPTCHA provider unreachable | 503 | "Verification service unavailable. Please try again shortly." |
| Wrong ID / password / role | 401 | "Invalid ID or password." |
| Account locked | 429 | "Too many failed attempts. Try again later." |
| Inactive account | 401 | "Invalid ID or password." |

### `POST /logout`
Authenticated; CSRF required. Increments `session_version`, clears session, 302 → `/` with flash "You have been logged out."

## 4. Student

### `GET /student/dashboard` — role `student`
HTML dashboard: profile card + result summary + "View detailed result" button (opens modal populated from the API below). Non-students: 403 page; anonymous: 302 → `/student/login?next=…` (only same-site relative `next` accepted).

### `GET /api/student/result?exam_id=<int>` — role `student`
* `exam_id` optional (defaults to latest exam). **No student ID parameter.** Any `student_id` query parameter is ignored.
* 200:

```json
{
  "demo_data": true,
  "student": { "student_code": "STU2026001", "full_name": "Demo Student One",
               "class_name": "10th Standard", "section": "A", "roll_number": 1 },
  "exam": { "id": 1, "name": "Annual Examination 2025-26 (Demo)", "academic_year": "2025-26" },
  "subjects": [
    { "code": "ENG", "name": "English", "marks_obtained": "78.00", "max_marks": "100.00",
      "pass_marks": "35.00", "percentage": "78.00", "grade": "B1", "passed": true }
  ],
  "summary": { "status": "PASS", "total_obtained": "401.50", "total_max": "500.00",
               "percentage": "80.30", "grade": "A2" }
}
```
* For `INCOMPLETE`: missing subjects have `marks_obtained: null, grade: null, passed: null`; `summary` = `{"status":"INCOMPLETE","total_obtained":null,"total_max":"500.00","percentage":null,"grade":null}`.
* Decimals serialised as strings to avoid float rounding.
* 404 if `exam_id` unknown.

## 5. Teacher

### `GET /teacher/dashboard` — role `teacher`
HTML: list of assigned students; selecting one opens a marks editor (assigned subjects editable, others read-only/hidden).

### `GET /api/teacher/students?exam_id=<int>` — role `teacher`
200:
```json
{ "exam": { "id": 1, "name": "…" },
  "students": [ { "id": 3, "student_code": "STU2026001", "full_name": "Demo Student One",
                  "section": "A", "roll_number": 1,
                  "assigned_subjects": ["ENG", "MAT"], "result_status": "PASS" } ] }
```
Only students with ≥ 1 assignment to the current teacher.

### `GET /api/teacher/students/<int:student_id>/marks?exam_id=<int>` — role `teacher`
* 404 if student does not exist **or** has no assignment to this teacher.
* 200: student header, per subject `{subject_id, code, name, max_marks, pass_marks, marks_obtained, editable}` (`editable` = assigned to this teacher), plus server-computed `summary` (same shape as student API).

### `PUT /api/teacher/students/<int:student_id>/marks` — role `teacher`, CSRF
Request:
```json
{ "exam_id": 1,
  "marks": [ { "subject_id": 1, "marks_obtained": "78.5" },
             { "subject_id": 3, "marks_obtained": null } ] }
```
Rules:
* Body must be a JSON object with exactly the keys `exam_id` and `marks`; unknown top-level keys (`total`, `grade`, `student_id`, `role`, …) → 422 `validation_error`.
* `marks`: non-empty list, ≤ 20 items, no duplicate `subject_id`; each item exactly `{subject_id, marks_obtained}`.
* `marks_obtained`: `null` (clear) or a JSON number/string matching `^\d{1,3}(\.\d{1,2})?$`, value 0 ≤ x ≤ max_marks, x×2 integral (0.5 steps). Booleans, `NaN`, `Infinity`, exponents, negatives, blanks rejected.
* `exam_id`/`subject_id` must exist and the subject must belong to the exam → else 422.
* Student must be assigned to teacher (any subject) → else 404; every `subject_id` must be assigned to this teacher for this student → else 403 (nothing saved).
* All-or-nothing transaction; audit rows written.

Responses:
* 200 `{ "message": "Marks saved.", "saved": 2, "summary": {…recomputed…}, "subjects": [...] }`
* 422 with `details.fields` keyed by subject code/index.

## 6. HTML error pages
`400, 403, 404, 405, 429, 500, 503` render friendly templates for page routes; `/api/*` returns the JSON envelope.

## 7. Security headers (all responses)
`Content-Security-Policy: default-src 'self'; script-src 'self' https://challenges.cloudflare.com; frame-src https://challenges.cloudflare.com; connect-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`,
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Strict-Transport-Security: max-age=31536000` (production only), `Cache-Control: no-store` on authenticated pages and APIs.

## 8. CLI commands (operator only, not HTTP)

| Command | Purpose | Production behaviour |
|---|---|---|
| `flask db upgrade` | Apply migrations | Run by start command |
| `flask seed-demo [--reset]` | Create fictional demo data | Blocked unless `--i-understand-this-is-production`; `--reset` always blocked in production |
| `flask create-user --role student\|teacher --login-id … --name … [--section A --roll 7]` | Create one account (password prompted, hidden) | Allowed |
| `flask assign --teacher TCH001 --student STU2026001 --subject MAT` | Create a teacher assignment | Allowed |
| `flask unlock-user LOGIN_ID` | Clear lockout | Allowed |
