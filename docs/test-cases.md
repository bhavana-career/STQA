# Test Case Matrix — SRMS (STQA Lab)

> **Status (Milestone M2 Completed):**
> - **M1 & M2 Automated Unit Tests:** 95 tests executed, **95 PASSED** (0 failures, 100% pass rate).
> - **Domain Services Coverage:** `app/services/grading.py` (100% statement, 100% branch), `app/services/marks_service.py` (98% statement, 100% branch).
> - **Fault Injection Evidence:** DEF-001 and DEF-002 before-fix failures and after-fix passes recorded in `docs/evidence/faults/` and logged in `docs/defects.md`.
> - Integration and E2E cases remain planned for subsequent milestones (M3–M7).

## 0. Legend and common preconditions

**Priority:** P1 = critical (must pass for release), P2 = high, P3 = medium.
**Automation:** `Unit`, `Integration`, `E2E` (Selenium), `External` (against deployed URL, opt-in), `Manual`.
**Type:** F = functional, N = negative, B = boundary, S = security, P = persistence, U = UI/usability, R = regression.

**Standard fixture set (FX)** — created by factories in `tests/fixtures/`, truncated after each test:

| Item | Data |
|---|---|
| Exam `E1` | "Test Exam 2025-26"; subjects ENG, HIN, MAT, SCI, SST — max 100, pass 35 each |
| Section `A` | 10th Standard A, 2025-26 |
| Student `S1` | `STU_T001`, "Test Student One", A, roll 1, password `S1-Passw0rd!` (test-only) |
| Student `S2` | `STU_T002`, "Test Student Two", A, roll 2 |
| Teacher `T1` | `TCH_T001`, assigned S1: ENG, MAT |
| Teacher `T2` | `TCH_T002`, assigned S1: HIN, SCI, SST; S2: all 5 |
| Teacher `T3` | `TCH_T003`, no assignments |
| CAPTCHA | `MockVerifier` returning success unless the case states otherwise (Integration); Turnstile test keys `1x…AA` site / `1x…AA` secret (E2E) |

Unless stated, **PC-STD** = "test DB migrated, FX loaded, app in `testing` config".

---

## 1. Authentication (TC-AUTH)

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M4) |
|---|---|---|---|---|---|---|---|---|---|
| TC-AUTH-01 | Valid student login | PC-STD | `STU_T001` / correct pw / valid token | POST `/student/login` | 302 → `/student/dashboard`; session has user S1; `failed_login_count`=0; `last_login_at` set | P1 | F | Integration + E2E (TC-UI-02) | **PASS** (`test_tc_auth_01_valid_student_login`) |
| TC-AUTH-02 | Valid teacher login | PC-STD | `TCH_T001` / correct pw | POST `/teacher/login` | 302 → `/teacher/dashboard` | P1 | F | Integration + E2E (TC-UI-03) | **PASS** (`test_tc_auth_02_valid_teacher_login`) |
| TC-AUTH-03 | Invalid ID or password — same message | PC-STD | (a) `STU_NOPE`/any (b) `STU_T001`/wrong | POST each | 401; identical body message "Invalid ID or password."; no session | P1 | N | Integration | **PASS** (`test_tc_auth_03_invalid_id_or_password_non_revealing`) |
| TC-AUTH-04 | Empty login fields | PC-STD | (a) both empty (b) ID only (c) pw only (d) whitespace-only ID | POST each | 400; field errors; CAPTCHA verifier **not called** | P1 | N | Integration | **PASS** (`test_tc_auth_04_empty_login_fields`) |
| TC-AUTH-05 | Missing CAPTCHA token | PC-STD | valid creds, no `cf-turnstile-response` | POST | 400 "Please complete the CAPTCHA."; no session; failed counter unchanged | P1 | N,S | Integration | **PASS** (`test_tc_auth_05_missing_captcha_token`) |
| TC-AUTH-06 | Invalid CAPTCHA token | Mock returns `success:false, error-codes:[invalid-input-response]` | valid creds | POST | 400 "CAPTCHA verification failed…"; no session | P1 | N,S | Integration | **PASS** (`test_tc_auth_06_invalid_captcha_token`) |
| TC-AUTH-07 | Expired / reused CAPTCHA token | Mock returns `timeout-or-duplicate` | valid creds | POST | 400 CAPTCHA failed; no session | P1 | N,S | Integration | **PASS** (`test_tc_auth_07_expired_captcha_token`) |
| TC-AUTH-08 | CAPTCHA service failure | Mock raises `requests.Timeout` / `ConnectionError` | valid creds | POST | 503 "Verification service unavailable"; no session (fail closed) | P1 | N,S | Integration | **PASS** (`test_tc_auth_08_captcha_service_unavailable`) |
| TC-AUTH-09 | Logout invalidates session | S1 logged in; copy session cookie | — | POST `/logout` with CSRF; then GET `/student/dashboard` with **old** cookie | Logout 302 → `/`; old cookie → 302 to login (session_version mismatch); `session_version` incremented | P1 | S | Integration + E2E (TC-UI-07) | **PASS** (`test_tc_auth_09_logout_invalidates_session`) |
| TC-AUTH-10 | Session idle expiry | `SESSION_LIFETIME_MINUTES` set to 1 in test; S1 logged in | freeze/advance time 61 s | GET dashboard; GET `/api/student/result` | Page 302 → login; API 401 JSON | P2 | S,B | Integration | **PASS** (`test_tc_auth_10_session_idle_expiry`) |
| TC-AUTH-11 | Unauthenticated page access | Anonymous | — | GET `/student/dashboard`, `/teacher/dashboard` | 302 → respective login with safe `next` | P1 | S | Integration + E2E | **PASS** (`test_tc_auth_11_unauthenticated_page_access_redirects`) |
| TC-AUTH-12 | Repeated failed logins → lockout | PC-STD; `LOGIN_MAX_ATTEMPTS=5`, 15 min | wrong pw ×4, ×5, ×6; then correct pw; then advance 15 min + 1 s and correct pw | POST sequentially | Attempts 1–5 → 401 (5th sets `locked_until`); 6th and correct-pw-while-locked → 429; after expiry correct pw → 302 and counter reset | P1 | S,B | Integration | **PASS** (`test_tc_auth_12_account_lockout_policy`, `test_teacher_account_lockout`) |
| TC-AUTH-13 | Role mismatch on login page | PC-STD | S1 creds on `/teacher/login`; T1 creds on `/student/login` | POST | 401 generic message; counts as a failed attempt | P1 | S | Integration | **PASS** (`test_tc_auth_13_role_mismatch_on_login_pages`) |
| TC-AUTH-14 | Inactive account | S1 `is_active=false` | correct pw | POST | 401 generic | P3 | N | Integration | **PASS** (`test_tc_auth_14_inactive_account_rejected`) |
| TC-AUTH-15 | Login ID case-insensitive, trimmed | PC-STD | `  stu_t001 ` | POST | 302 success | P3 | F | Integration | **PASS** (`test_tc_auth_15_case_insensitive_and_trimmed_login_id`) |
| TC-AUTH-16 | Oversized inputs | PC-STD | ID 33 chars; pw 129 chars | POST | 400 validation; no DB lookup error | P3 | N,B | Integration | **PASS** (`test_tc_auth_16_oversized_inputs_rejected`) |

## 2. CAPTCHA (TC-CAP)

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M4) |
|---|---|---|---|---|---|---|---|---|---|
| TC-CAP-01 | Verifier success parsing | `requests.post` mocked → 200 `{"success":true,"hostname":"localhost","action":"login"}` | token `abc` | `TurnstileVerifier.verify("abc", "1.2.3.4")` | Returns `ok=True` | P1 | F | Unit | **PASS** (`test_tc_cap_01_and_09_turnstile_success_and_request_format`) |
| TC-CAP-02 | Missing/blank token short-circuits | — | `None`, `""`, `"   "` | verify | `ok=False, reason="missing-input-response"`; **no HTTP call** | P1 | N | Unit | **PASS** (`test_tc_cap_02_blank_token_short_circuits`) |
| TC-CAP-03 | Invalid token | mocked `success:false, invalid-input-response` | — | verify | `ok=False, reason="invalid-input-response"` | P1 | N | Unit | **PASS** (`test_tc_cap_03_invalid_token`) |
| TC-CAP-04 | Expired/duplicate token | mocked `timeout-or-duplicate` | — | verify | `ok=False` | P1 | N | Unit | **PASS** (`test_tc_cap_04_expired_or_duplicate_token`) |
| TC-CAP-05 | Hostname mismatch | mocked success, hostname `evil.example` | `ALLOWED_HOSTNAMES=localhost` | verify | `ok=False, reason="hostname-mismatch"` | P2 | S | Unit | **PASS** (`test_tc_cap_05_hostname_mismatch`) |
| TC-CAP-06 | Action mismatch | mocked success, action `signup` | — | verify | `ok=False` | P2 | S | Unit | **PASS** (`test_tc_cap_06_action_mismatch`) |
| TC-CAP-07 | Network failure / timeout | mocked raise `Timeout`, `ConnectionError` | — | verify | `ok=False, unavailable=True` (→ 503 at route) | P1 | N | Unit | **PASS** (`test_tc_cap_07_network_failure_or_timeout`) |
| TC-CAP-08 | Non-200 / malformed JSON / missing `success` | mocked 500; 200 with `text/html`; `{}` | — | verify | `ok=False, unavailable=True`; never `ok=True` | P1 | N | Unit | **PASS** (`test_tc_cap_08_malformed_responses`) |
| TC-CAP-09 | Request format | mocked | token `t`, ip `1.2.3.4` | verify | POST to `https://challenges.cloudflare.com/turnstile/v0/siteverify` with `secret`, `response`, `remoteip`, `idempotency_key`; `timeout=5` | P2 | F | Unit | **PASS** (`test_tc_cap_01_and_09_turnstile_success_and_request_format`) |
| TC-CAP-10 | Mock mode blocked outside testing | — | `APP_ENV=production/development`, `CAPTCHA_MODE=mock` | `create_app()` | Raises `ConfigError` | P1 | S | Unit | **PASS** (`test_mock_captcha_blocked_in_non_testing`) |
| TC-CAP-11 | Test keys blocked in production | — | `APP_ENV=production`, site `1x00000000000000000000AA` or secret `1x0000…AA`/`2x…`/`3x…`; missing keys | `create_app()` | Raises `ConfigError` | P1 | S | Unit | **PASS** (`test_turnstile_test_keys_blocked_in_production`) |
| TC-CAP-12 | E2E pass with Turnstile test keys | Live server, site `1x00000000000000000000AA`, secret `1x0000000000000000000000000000000AA`, internet | S1 creds | Open login, wait for widget token, submit | Dashboard shown | P1 | F | E2E (`captcha_live`) | Deferred to M7 (Selenium E2E) |
| TC-CAP-13 | E2E rejection with always-fail secret | secret `2x0000000000000000000000000000000AA` | S1 creds | Same | "CAPTCHA verification failed" shown; still on login page | P1 | N | E2E (`captcha_live`) | Deferred to M7 |
| TC-CAP-14 | E2E spent-token secret | secret `3x0000000000000000000000000000000AA` | S1 creds | Same | CAPTCHA failed message | P2 | N | E2E (`captcha_live`) | Deferred to M7 |
| TC-CAP-15 | E2E blocked widget | site `2x00000000000000000000AB` | S1 creds | Submit | No token → client message "Please complete the CAPTCHA"; server 400 if forced | P2 | N | E2E (`captcha_live`) | Deferred to M7 |
| TC-CAP-16 | Offline E2E with mock widget | `APP_ENV=testing`, `CAPTCHA_MODE=mock`; stub widget sets token `mock-pass` / `mock-fail` | — | Login with each | pass → dashboard, fail → error | P2 | F | E2E | Deferred to M7 |

## 3. Authorization (TC-AUTHZ)

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M4) |
|---|---|---|---|---|---|---|---|---|---|
| TC-AUTHZ-01 | Student → teacher dashboard | S1 logged in | — | GET `/teacher/dashboard`, `/api/teacher/students` | Page 403 template; API 403 JSON | P1 | S | Integration + E2E (TC-UI-08) | **PASS** (`test_tc_authz_01_student_blocked_from_teacher_routes`) |
| TC-AUTHZ-02 | Student attempts to edit marks | S1 logged in | valid PUT body for S1 | PUT `/api/teacher/students/<S1.id>/marks` | 403; marks unchanged; no audit row | P1 | S | Integration | **PASS** (`test_tc_authz_02_and_04_student_cannot_access_or_edit_marks_api`) |
| TC-AUTHZ-03 | Student requests another student's result via param | S1 logged in | `?student_id=<S2.id>`, `?student_code=STU_T002` | GET `/api/student/result…` | 200 with **S1's** data only; no S2 data in body | P1 | S | Integration | **PASS** (`test_tc_authz_03_student_cannot_view_other_student_result`) |
| TC-AUTHZ-04 | Student tries teacher marks URL for other student | S1 logged in | S2 id | GET `/api/teacher/students/<S2.id>/marks` | 403 | P1 | S | Integration | **PASS** (`test_tc_authz_02_and_04_student_cannot_access_or_edit_marks_api`) |
| TC-AUTHZ-05 | Teacher reads unassigned student | T1 logged in | S2 id; non-existent id 999999 | GET marks | 404 for both (identical body) | P1 | S | Integration | **PASS** (`test_tc_authz_05_teacher_reads_unassigned_student_returns_404`) |
| TC-AUTHZ-06 | Teacher edits assigned student/subject | T1 logged in | S1: ENG 78, MAT 91.5 | PUT | 200; DB values updated; 2 audit rows by T1 | P1 | F | Integration + E2E (TC-UI-06) | **PASS** (`test_tc_mark_02_and_08_save_multiple_subjects_atomically_and_audit`) |
| TC-AUTHZ-07 | Teacher edits unassigned student | T1 logged in | S2: ENG 50 | PUT | 404; nothing saved | P1 | S | Integration | **PASS** (`test_tc_authz_07_teacher_edits_unassigned_student_returns_404`) |
| TC-AUTHZ-08 | Teacher mixes assigned + unassigned subjects | T1 logged in | S1: ENG 70, SCI 60 | PUT | 403; **ENG not saved either** (atomic) | P1 | S | Integration | **PASS** (`test_tc_authz_08_teacher_mixes_assigned_and_unassigned_subjects`) |
| TC-AUTHZ-09 | Client tampers protected fields | T1 logged in | body adds `student_id: S2.id`, `total: 500`, `grade: "A1"`, `role: "admin"`, `teacher_id: T2.id` | PUT for S1 | 422 `validation_error` (unknown keys); nothing saved; S2 untouched | P1 | S | Integration | **PASS** (`test_tc_authz_09_tampered_request_body_rejected_with_422`) |
| TC-AUTHZ-10 | Unauthenticated protected APIs | Anonymous | each protected API route/method | request | 401 JSON envelope for every route | P1 | S | Integration (parametrized) | **PASS** (`test_tc_authz_10_unauthenticated_protected_apis_return_401`) |
| TC-AUTHZ-11 | No registration / role escalation | Anonymous | GET/POST `/register`, `/signup`; login POST with extra `role=teacher` for S1 on teacher page | requests | 404 for registration; role field ignored → 401 | P2 | S | Integration | **PASS** (`test_tc_authz_11_no_registration_route_exists`) |
| TC-AUTHZ-12 | Teacher with no assignments | T3 logged in | — | GET `/api/teacher/students` | 200 empty list | P3 | F | Integration | **PASS** (`test_tc_mark_01_and_authz_12_teacher_students_listing`) |

## 4. Marks entry and validation (TC-MARK)

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M5) |
|---|---|---|---|---|---|---|---|---|---|
| TC-MARK-01 | Teacher list shows only assigned students | T1 logged in | — | GET `/api/teacher/students` | Only S1 with `assigned_subjects=["ENG","MAT"]` | P1 | F,S | Integration | **PASS** (`test_tc_mark_01_and_authz_12_teacher_students_listing`) |
| TC-MARK-02 | Save multiple subjects atomically | T2 logged in | S1: HIN 60, SCI 72.5, SST 35 | PUT | 200 `saved=3`; recomputed summary returned | P1 | F | Integration | **PASS** (`test_tc_mark_02_and_08_save_multiple_subjects_atomically_and_audit`) |
| TC-MARK-03 | Malformed values rejected | T1 logged in | `"abc"`, `""`, `" "`, `"1e2"`, `"NaN"`, `"Infinity"`, `true`, `[]`, `{}`, `"12,5"`, `"0x10"` | PUT each (ENG) | 422, field error for ENG; DB unchanged | P1 | N | Unit (parser) + Integration | **PASS** (`test_tc_mark_03_and_04_invalid_mark_inputs_rejected`) |
| TC-MARK-04 | Invalid step | T1 | `78.25`, `78.3`, `0.1` | PUT | 422 "Marks must be in steps of 0.5" | P2 | N,B | Unit + Integration | **PASS** (`test_tc_mark_03_and_04_invalid_mark_inputs_rejected`) |
| TC-MARK-05 | Unknown exam | T1 | `exam_id: 999999`, `exam_id: "1"`, missing | PUT | 422 | P2 | N | Integration | **PASS** (`test_tc_mark_05_unknown_or_string_exam_id_rejected`) |
| TC-MARK-06 | Unknown subject / subject not in exam | T1; subject `ART` exists but not in E1 | `subject_id: 999999`; ART id | PUT | 422; nothing saved | P2 | N | Integration | **PASS** (`test_tc_mark_06_subject_not_in_exam_rejected`) |
| TC-MARK-07 | Clear a mark | S1 ENG=78 saved by T1 | ENG `null` | PUT | 200; `marks_obtained` NULL; audit `clear`; S1 result `INCOMPLETE` | P2 | F | Integration | **PASS** (`test_tc_mark_07_clear_mark_with_null`) |
| TC-MARK-08 | Audit trail recorded | T1 | ENG 50 → 60 | PUT twice | Audit rows: `create (NULL→50)`, `update (50→60)`, `changed_by=T1.user_id` | P2 | F | Integration | **PASS** (`test_tc_mark_02_and_08_save_multiple_subjects_atomically_and_audit`) |
| TC-MARK-09 | Duplicate subject in request | T1 | ENG twice | PUT | 422 | P3 | N | Integration | **PASS** (`test_tc_mark_09_duplicate_subject_in_request_rejected`) |
| TC-MARK-10 | Malformed body | T1 | non-JSON, JSON array, `marks: []`, 21 items | PUT | 400 / 422 | P3 | N | Integration | **PASS** (`test_tc_mark_10_malformed_body_rejected`) |

## 5. Result calculation (TC-CALC)

Rules from requirements §4.4.1. All maxima 100, pass 35 unless stated.

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M5) |
|---|---|---|---|---|---|---|---|---|---|
| TC-CALC-01 | Mark = 0 accepted | — | `0`, `"0"`, `"0.0"` max 100 | `parse_mark` | `Decimal("0")` | P1 | B | Unit | **PASS** (`test_zero_mark_accepted`) |
| TC-CALC-02 | Mark = max accepted | — | `100`, `"100.00"`; max 80 → `80` | parse | accepted | P1 | B | Unit | **PASS** (`test_maximum_mark_accepted`) |
| TC-CALC-03 | Negative rejected | — | `-0.5`, `-1`, `"-10"` | parse | `ValidationError` (negative values rejected; sign not accepted by the format rule) | P1 | N,B | Unit | **PASS** (`test_negative_marks_rejected`) |
| TC-CALC-04 | Above max rejected | — | `100.5`, `101`, `1000`; max 80 → `80.5` | parse | `ValidationError("must be ≤ max")` | P1 | N,B | Unit | **PASS** (`test_marks_exceeding_maximum_rejected`) |
| TC-CALC-05 | Decimal (0.5 step) supported | — | `0.5`, `78.5`, `99.50` | parse | accepted exactly | P2 | F | Unit | **PASS** (`test_decimal_marks_half_step_accepted`) |
| TC-CALC-06 | Missing marks → INCOMPLETE | — | ENG–SCI given, SST missing | `compute_result` | status `INCOMPLETE`; total/percentage/grade `None`; missing subject flagged | P1 | F | Unit + Integration | **PASS** (`test_missing_marks_yields_incomplete_status`, `test_tc_calc_06_missing_marks_returns_incomplete_status`) |
| TC-CALC-07 | All subjects at max | — | 100×5 | compute | 500/500, `100.00`, A1, PASS | P1 | B | Unit | **PASS** (`test_all_subjects_at_maximum`) |
| TC-CALC-08 | All subjects zero | — | 0×5 | compute | 0/500, `0.00`, E, FAIL | P1 | B | Unit | **PASS** (`test_all_subjects_at_zero`) |
| TC-CALC-09 | Total and percentage (uniform max) | — | 78, 65, 90, 55, 42 | compute | 330/500, `66.00`, B2, PASS | P1 | F | Unit | **PASS** (`test_student_passing_all_subjects`) |
| TC-CALC-10 | Percentage with non-uniform maxima | — | 80/100, 40/80, 25/50 (pass 35/28/17.5) | compute | 145/230 = `63.04`, B2, PASS | P1 | F | Unit (DEF-001 regression) | **PASS** (`test_def_001_regression_non_uniform_maximums_percentage`) |
| TC-CALC-11 | Rounding half-up | — | 1 of 160 → 0.625 | `percentage()` | `0.63` (not banker's `0.62`); 2/3 → `66.67` | P2 | B | Unit | **PASS** (`test_percentage_rounding_half_up`) |
| TC-CALC-12 | Grade at every boundary | — | pct: 0, 34.99, 35.00, 39.99, 40.00, 49.99, 50.00, 59.99, 60.00, 69.99, 70.00, 79.99, 80.00, 89.99, 90.00, 100.00 | `grade_for_percentage` | E, E, D, D, C2, C2, C1, C1, B2, B2, B1, B1, A2, A2, A1, A1 | P1 | B | Unit (DEF-002 regression) | **PASS** (`test_def_002_regression_grade_boundary_precision`) |
| TC-CALC-13 | Pass/fail boundaries | — | (a) one subject 34.5, others 100 (b) one subject 35, others 35 (c) all 35.5 (d) one subject 0, others 100 → 80 % | compute | (a) FAIL, grade E (b) PASS 35.00 D (c) PASS 35.50 D (d) FAIL, E despite 80 % | P1 | B | Unit | **PASS** (`test_student_fails_one_subject_despite_high_overall_percentage`, `test_student_passes_with_all_subjects_at_exact_pass_mark`) |
| TC-CALC-14 | Updated marks reflected in result | S1 all 5 marks saved (T1+T2) | change MAT 40 → 90 | PUT, then S1 GET result | total +50, percentage/grade updated | P1 | F,P | Integration | **PASS** (`test_tc_calc_14_updated_marks_reflected_in_result`) |
| TC-CALC-15 | Server never trusts client values | S1 complete marks; DB updated directly | — | GET result | Summary equals recomputation from DB rows; no client input path exists | P1 | S | Integration | **PASS** (`test_tc_calc_15_server_side_result_calculation_integrity`) |
| TC-CALC-16 | Grading input guards | — | pct −0.01, 100.01; max 0; obtained > max | grading funcs | `ValueError` | P2 | N | Unit | **PASS** (`test_percentage_out_of_range_raises_value_error`, `test_compute_result_out_of_range_raises_value_error`) |
| TC-CALC-17 | Subject grade per subject | — | ENG 89.5 → A2, MAT 90 → A1 | compute | per-subject grades correct | P2 | F | Unit | **PASS** (`test_subject_grade_calculation`) |

## 6. Database and integration (TC-DB)

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M5) |
|---|---|---|---|---|---|---|---|---|---|
| TC-DB-01 | Create & retrieve student | Migrated empty DB | factory student | insert, new session query | Fields round-trip; unique `student_code` enforced (duplicate → IntegrityError) | P2 | F | Integration | **PASS** (`test_duplicate_student_code_rejected`) |
| TC-DB-02 | Save marks & retrieve after refresh | T1 | S1 ENG 78 | PUT; new client/session GET marks | ENG `78.00` returned | P1 | P | Integration + E2E (TC-UI-06) | **PASS** (`test_tc_authz_04_teacher_reads_assigned_student_marks_success`, `test_tc_mark_02_and_08_save_multiple_subjects_atomically_and_audit`) |
| TC-DB-03 | Invalid FK reference | — | mark with student_id 999999 | direct ORM insert + commit | `IntegrityError`; session rolled back; no row | P2 | N | Integration | **PASS** (`test_invalid_foreign_key_rejected`) |
| TC-DB-04 | Persistence across app restart | T1 saves S1 ENG 78 | — | dispose engine, `create_app()` new instance, read | Value still 78.00 | P1 | P | Integration | **PASS** (`test_marks_save_and_audit_creation`) |
| TC-DB-05 | Result consistent with stored marks | S1 complete | — | SQL `SUM(marks_obtained)` vs API `total_obtained` | Equal | P1 | F | Integration | **PASS** (`test_tc_db_05_database_sum_matches_api_total`) |
| TC-DB-06 | Rollback on multi-step failure | T2; monkeypatch audit insert to raise on 2nd subject | S1 HIN 60, SCI 70, SST 80 | PUT | 500 generic JSON; **no** marks/audit rows changed | P1 | N,P | Integration (DEF-004 regression) | **PASS** (`test_failed_transaction_rolls_back_completely`) |
| TC-DB-07 | Test DB safety guard | — | `TEST_DATABASE_URL` = `DATABASE_URL`; name without `test` | start pytest session (subprocess) | Session aborts with clear message before touching DB | P1 | S | Integration | **PASS** (conftest safety fixture) |
| TC-DB-08 | DB unavailable handled safely | App configured with unreachable DB | — | GET `/health`, GET `/api/student/result` (logged-in mocked user) | 503 JSON, no stack trace / credentials in body | P2 | N | Integration | **PASS** (`test_health_endpoint_degraded_when_db_fails`) |
| TC-DB-09 | Unique (student, exam_subject) | — | two mark rows same pair | insert | IntegrityError | P3 | N | Integration | **PASS** (`test_duplicate_mark_same_student_exam_subject_rejected`) |
| TC-DB-10 | Migrations up/down | Empty test DB | — | `alembic upgrade head`, `downgrade base`, `upgrade head` | All succeed | P2 | F | Integration | **PASS** (`test_migration_downgrade_and_upgrade_cycle`) |
| TC-DB-06 | Rollback on multi-step failure | T2; monkeypatch audit insert to raise on 2nd subject | S1 HIN 60, SCI 70, SST 80 | PUT | 500 generic JSON; **no** marks/audit rows changed | P1 | N,P | Integration (DEF-004 regression) | **PASS** (`test_failed_transaction_rolls_back_completely`) |
| TC-DB-07 | Test DB safety guard | — | `TEST_DATABASE_URL` = `DATABASE_URL`; name without `test` | start pytest session (subprocess) | Session aborts with clear message before touching DB | P1 | S | Integration | **PASS** (conftest safety fixture) |
| TC-DB-08 | DB unavailable handled safely | App configured with unreachable DB | — | GET `/health`, GET `/api/student/result` (logged-in mocked user) | 503 JSON, no stack trace / credentials in body | P2 | N | Integration | **PASS** (`test_health_endpoint_degraded_when_db_fails`) |
| TC-DB-09 | Unique (student, exam_subject) | — | two mark rows same pair | insert | IntegrityError | P3 | N | Integration | **PASS** (`test_duplicate_mark_same_student_exam_subject_rejected`) |
| TC-DB-10 | Migrations up/down | Empty test DB | — | `alembic upgrade head`, `downgrade base`, `upgrade head` | All succeed | P2 | F | Integration | **PASS** (`test_migration_downgrade_and_upgrade_cycle`) |

## 7. Security (TC-SEC)

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M4) |
|---|---|---|---|---|---|---|---|---|---|
| TC-SEC-01 | SQL-injection-style input | PC-STD | ID `' OR '1'='1`, `STU_T001'--`, `'; DROP TABLE users;--`; same in password | POST login | 401 generic (or 400 length); no 500; `users` row count unchanged | P1 | S | Integration | **PASS** (`test_tc_sec_01_sql_injection_safely_handled`) |
| TC-SEC-02 | Stored XSS escaped | Student name `<script>alert(1)</script>` | — | Render dashboards (student + teacher), result modal | Literal text shown escaped; no script executes (E2E checks no alert) | P2 | S | Integration + E2E | Deferred to M6/M7 |
| TC-SEC-03 | CSRF enforced | CSRF enabled in this test | valid session, no/invalid token | PUT marks; POST logout; POST login | 400 `csrf_failed`; no state change | P1 | S | Integration | **PASS** (`test_tc_sec_03_csrf_protection_enforced`) |
| TC-SEC-04 | Security headers | — | — | GET `/`, `/student/login`, an API | CSP, nosniff, X-Frame-Options DENY, Referrer-Policy present; `Cache-Control: no-store` on authed responses | P2 | S | Integration | **PASS** (`test_tc_sec_04_security_headers_present`) |
| TC-SEC-05 | Password hashing | create user | pw `S1-Passw0rd!` | inspect DB | hash starts `scrypt:`; ≠ plaintext; two users same pw → different hashes | P1 | S | Unit/Integration | **PASS** (`test_user_creation_and_password_hashing`) |
| TC-SEC-06 | Session regenerated on login | Anonymous with pre-set session value | — | login | Old session keys cleared; new cookie value | P2 | S | Integration | **PASS** (`test_tc_sec_06_session_fixation_prevention`) |
| TC-SEC-07 | No secrets committed | Repo | — | CI `gitleaks` scan; check `.env` untracked | No findings | P1 | S | CI job | **PASS** (verified .gitignore & repo scan) |
| TC-SEC-08 | Production config interlocks | — | `APP_ENV=production` with: DEBUG on; missing/short `SECRET_KEY` (<32 chars); mock CAPTCHA; test keys | `create_app()` | `ConfigError` for each | P1 | S | Unit | **PASS** (`test_config.py` suite) |
| TC-SEC-09 | Open redirect prevented | Anonymous | `next=https://evil.example`, `next=//evil.example` | login with next | Redirect to own dashboard | P2 | S | Integration | **PASS** (`test_tc_sec_09_open_redirect_prevented`, `test_is_safe_url_cases`) |
| TC-SEC-10 | Production cookie flags | production config object | — | inspect config / response `Set-Cookie` | `Secure; HttpOnly; SameSite=Lax` | P1 | S | Unit | **PASS** (`test_tc_sec_10_cookie_security_attributes`, `test_production_config_interlocks`) |
| TC-SEC-11 | No stack traces leaked | Route forced to raise | — | GET | 500 generic page/JSON; no traceback text | P2 | S | Integration | **PASS** (`test_tc_sec_11_no_stack_traces_leaked_on_500`) |

## 8. User interface — Selenium (TC-UI)

Live server (thread) on test DB; headless Chrome; explicit waits; screenshot on failure.

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation |
|---|---|---|---|---|---|---|---|---|
| TC-UI-01 | Login form validation | — | empty fields; ID only | Click Sign in | Inline errors linked to inputs (`aria-describedby`); no navigation | P1 | U,N | E2E |
| TC-UI-02 | Student login → dashboard | FX; Turnstile test keys (or mock widget) | S1 | Fill, wait token, submit | `/student/dashboard`, heading shows "Test Student One" | P1 | F | E2E |
| TC-UI-03 | Teacher login → dashboard | FX | T1 | same | `/teacher/dashboard`, list contains `STU_T001` only | P1 | F | E2E |
| TC-UI-04 | Student result rendering | S1 marks 78,65,90,55,42 | — | Open dashboard, click "View detailed result" | Modal shows 5 rows, total 330 / 500, 66.00 %, B2, PASS, demo-data label | P1 | F | E2E |
| TC-UI-05 | Modal keyboard accessibility | logged-in S1 | — | Tab to button, Enter, Esc | Modal opens with focus inside, Esc closes and focus returns to button | P3 | U | E2E |
| TC-UI-06 | Teacher marks entry & update | T1 logged in | S1 ENG 81, MAT 92.5 | Select S1, enter, Save, reload page | "Marks saved" message; values persist after reload; summary updated | P1 | F,P | E2E |
| TC-UI-07 | Logout | S1 logged in | — | Click Logout; browser Back; open dashboard URL | Landing page with "logged out"; dashboard redirects to login | P1 | S | E2E |
| TC-UI-08 | Unauthorized navigation | S1 logged in; also anonymous | — | Open `/teacher/dashboard` | 403 page for S1; login page for anonymous | P1 | S | E2E |
| TC-UI-09 | Invalid mark input feedback | T1 | ENG `101`, MAT `-1`, `abc` | Save | Inline errors per field, nothing saved (reload shows old values) | P2 | N | E2E |
| TC-UI-10 | Loading states | T1; Chrome network throttling via `driver.set_network_conditions` (latency 1500 ms) | — | Click Save / Sign in | Button disabled with "Saving…"/"Signing in…" text while pending, re-enabled after | P3 | U | E2E |
| TC-UI-11 | Wrong password message | — | S1 wrong pw | Submit | "Invalid ID or password." in `role="alert"` region | P2 | N | E2E |
| TC-UI-12 | Responsive layout | — | viewport 375×812 | Load login + dashboards | No horizontal scroll (`scrollWidth ≤ clientWidth`); form usable | P3 | U | E2E |
| TC-UI-13 | Error state on network failure | T1; offline network condition | — | Save | "Network error — marks not saved" message | P3 | N | E2E |

## 9. Operations (TC-OPS)

| ID | Title | Preconditions | Test data | Steps | Expected result | Pri | Type | Automation | Status (M3) |
|---|---|---|---|---|---|---|---|---|---|
| TC-OPS-01 | Health OK | DB up | — | GET `/health` | 200 `status:ok, database:ok` | P1 | F | Integration + External | **PASS** (`test_health_endpoint_healthy`) |
| TC-OPS-02 | Health degraded | DB unreachable | — | GET `/health` | 503 `database:error` | P2 | N | Integration | **PASS** (`test_health_endpoint_degraded_when_db_fails`) |
| TC-OPS-03 | Seed blocked in production | `APP_ENV=production` | — | `flask seed-demo`; `--reset` with override | Non-zero exit, no rows; `--reset` always refused | P1 | S | Integration (CLI runner) | **PASS** (`test_seed_demo_blocked_in_production_without_override`, `test_seed_demo_reset_strictly_forbidden_in_production`) |
| TC-OPS-04 | Seed idempotent | testing | env demo passwords | run twice | Same row counts | P2 | F | Integration | **PASS** (`test_seed_demo_success_and_idempotency`) |
| TC-OPS-05 | `create-user` CLI | testing | duplicate login id | run | Hashed password stored; duplicate rejected with message | P2 | F | Integration | **PASS** (`test_create_user_duplicate_login_id_rejected`, `test_create_student_success`, `test_create_teacher_success`) |
| TC-OPS-06 | Deployed smoke test | Deployed, demo accounts seeded | `BASE_URL`, demo creds via env (manual CAPTCHA by human) | Checklist in deployment doc; automated read-only part: `/health`, login page loads with Turnstile script, HTTPS, headers | All pass | P1 | F | External (automated part) + Manual (login with real CAPTCHA) | Deferred to M8 (Deployment) |

## 10. Black-box design (TC-BB) — Equivalence partitioning & BVA

### 10.1 Marks field (subject max = 100, step 0.5)

| Partition | Class | Representative | Expected |
|---|---|---|---|
| EP-M1 | Valid 0 ≤ x ≤ 100, step 0.5 | 55, 72.5 | Accept |
| EP-M2 | Invalid x < 0 | −10 | Reject (≥ 0) |
| EP-M3 | Invalid x > 100 | 150 | Reject (≤ max) |
| EP-M4 | Invalid non-numeric | `abc`, `NaN`, `1e2` | Reject (malformed) |
| EP-M5 | Invalid step | 45.25 | Reject (step) |
| EP-M6 | Blank / null | `null` | Accept as "not entered" (clear) |

| ID | BVA value | Expected | Automation |
|---|---|---|---|
| TC-BB-01 | −0.5 | Reject | Unit |
| TC-BB-02 | 0 | Accept | Unit |
| TC-BB-03 | 0.5 | Accept | Unit |
| TC-BB-04 | 99.5 | Accept | Unit |
| TC-BB-05 | 100 | Accept | Unit |
| TC-BB-06 | 100.5 | Reject | Unit (DEF-003 regression) |
| TC-BB-07 | Subject pass mark 34.5 / 35 / 35.5 | fail / pass / pass | Unit |
| TC-BB-08 | Each EP-M representative above | as table | Unit (parametrized) |

### 10.2 Percentage → grade (EP = grade bands; BVA = TC-CALC-12)

| Band | Representative | Expected |
|---|---|---|
| Invalid < 0 | −5 | ValueError |
| E | 20 | E |
| D | 37 | D |
| C2 | 45 | C2 |
| C1 | 55 | C1 |
| B2 | 65 | B2 |
| B1 | 75 | B1 |
| A2 | 85 | A2 |
| A1 | 95 | A1 |
| Invalid > 100 | 101 | ValueError |
TC-BB-09 implements this table (Unit, parametrized).

### 10.3 Overall status — decision table (TC-BB-10, Unit)

| Rule | Any mark missing | All subjects ≥ pass | Aggregate ≥ 35 % | Status | Grade |
|---|---|---|---|---|---|
| R1 | Y | – | – | INCOMPLETE | — |
| R2 | N | Y | Y | PASS | from table |
| R3 | N | N | Y | FAIL | E |
| R4 | N | N | N | FAIL | E |
| R5 | N | Y | N | FAIL | E *(unreachable when every pass mark ≥ 35 % of max; reachable with configurable lower pass marks — tested with pass marks 20)* |

### 10.4 Login ID (TC-BB-11, Integration)

| Class | Example | Expected |
|---|---|---|
| Valid existing | `STU_T001` | proceed to password check |
| Valid format, unknown | `STU_X999` | 401 generic |
| Empty / whitespace | `""`, `"  "` | 400 |
| Length 32 / 33 | 32 chars / 33 chars | 401 / 400 |
| Injection | `' OR 1=1--` | 401 generic |

## 11. White-box design (TC-WB) — `app/services/grading.py` & `parse_mark`

Planned function structure (final line numbers will be referenced from the coverage report):

```text
grade_for_percentage(pct):
  B1  if pct < 0 or pct > 100: raise ValueError        (T/F)
  B2  for (grade, lower) in thresholds (desc):          (loop taken / exhausted)
  B3      if pct >= lower: return grade                 (T/F)
      return "E"

percentage(obtained, maximum):
  B4  if maximum <= 0: raise ValueError                 (T/F)
  B5  if obtained < 0 or obtained > maximum: raise      (T/F)
      return (obtained / maximum * 100).quantize(0.01, ROUND_HALF_UP)

compute_result(entries, cfg):
  B6  if any entry.obtained is None: return INCOMPLETE  (T/F)
  B7  all_passed = all(e.obtained >= e.pass_marks)      (T/F per element)
  B8  if all_passed and pct >= cfg.min_overall: PASS    (T/F, short-circuit both sides)
      else FAIL, grade E

parse_mark(raw, max_marks):
  B9  raw is None -> None                                (T/F)
  B10 isinstance(raw, bool) -> malformed                 (T/F)
  B11 type not in (int, float, str, Decimal) -> malformed
  B12 regex mismatch -> malformed
  B13 value > max -> error
  B14 (value * 2) not integral -> step error
```

| ID | Target branch(es) | Input | Expected |
|---|---|---|---|
| TC-WB-01 | B1 True (low) | −0.01 | ValueError |
| TC-WB-02 | B1 True (high) | 100.01 | ValueError |
| TC-WB-03 | B1 False, B3 True on first iteration | 95 | A1 |
| TC-WB-04 | B3 False then True (middle) | 65 | B2 |
| TC-WB-05 | B2 loop exhausted → fallback | 10 | E |
| TC-WB-06 | B4 True | max 0 | ValueError |
| TC-WB-07 | B5 True (both sides) | obtained −1; obtained 101 of 100 | ValueError |
| TC-WB-08 | B4/B5 False | 50 of 100 | 50.00 |
| TC-WB-09 | B6 True | one None | INCOMPLETE |
| TC-WB-10 | B6 False, B8 True | all 60 | PASS |
| TC-WB-11 | B7 False → B8 False (left operand) | one 20, rest 100 | FAIL |
| TC-WB-12 | B7 True, pct < min → B8 False (right operand) | pass marks 20, all 30 | FAIL (R5) |
| TC-WB-13 | B9–B14 each True and the all-False path | `None`, `True`, `[]`, `"x"`, `101`, `10.25`, `"10.5"` | None / malformed / malformed / malformed / range / step / Decimal('10.5') |

Measurement: `pytest tests/unit --cov=app.services.grading --cov=app.services.marks_service --cov-branch --cov-report=term-missing`. Reported numbers will be copied from actual output only. A deliberate demonstration also shows a test subset that reaches 100 % statement but < 100 % branch coverage (in `academic/coverage_demo`).

## 12. Academic syllabus exercises (TC-ACAD) — separate from the app

| ID | Exercise | Cases (summary) | Automation |
|---|---|---|---|
| TC-ACAD-01 | Division program — **faulty** version (`academic/division/faulty.py`) | `divide(10, 0)` expected `ValueError("Division by zero")`; faulty version crashes / returns wrong result → test **fails** (DEF-006) | Unit (`fault_demo`) |
| TC-ACAD-02 | Division — corrected | 10/2=5, −9/3=−3, 7/2=3.5, 0/5=0, 10/0 → ValueError, non-numeric → TypeError | Unit |
| TC-ACAD-03 | Age field 18–60 (EP+BVA) | 17 ✗, 18 ✓, 19 ✓, 35 ✓, 59 ✓, 60 ✓, 61 ✗, −1 ✗, `"abc"` ✗, empty ✗, 25.5 ✗ | Unit |
| TC-ACAD-04 | ATM withdrawal black-box | EP/BVA on amount, balance, daily limit, multiples rule — **rules to be taken from your syllabus** (default proposal: multiples of 100, 100 ≤ amount ≤ 10 000 per transaction, ≤ balance, daily limit 20 000, correct PIN, max 3 PIN attempts) | Unit |
| TC-ACAD-05 | Statement vs branch coverage | `classify(n)` example; test set A → 100 % statement / < 100 % branch; set B → 100 % both (measured) | Unit + pytest-cov |
| TC-ACAD-06 | Top-down integration | `ReportModule → GradeModule(stub) → MarksRepo(stub)`; step 1 stubs, step 2 real GradeModule, step 3 real repo (in-memory) | Unit/Integration |
| TC-ACAD-07 | Defect life cycle | State machine New→Assigned→Open→Fixed→Retest→Verified→Closed, plus Reopened/Rejected/Deferred/Duplicate; valid and invalid transitions | Unit |
| TC-ACAD-08 | Agile vs Waterfall estimates | Compute timelines from phase/sprint inputs — **inputs from syllabus** | Unit |
| TC-ACAD-09 | Defect density & productivity | density = defects / KLOC; productivity = LOC (or FP) / person-month — **sample data from syllabus required** | Unit |

## 13. Fault-injection demonstrations (FI) — see test-plan §8

| ID | Defect | Test | Before fix (expected) | After fix (expected) | Automation |
|---|---|---|---|---|---|
| FI-001 | DEF-001 wrong denominator | non-uniform maxima 145/230 | **Fails**: gets ≠ 63.04 | Pass 63.04 | Unit (`fault_demo`) |
| FI-002 | DEF-002 `>` vs `>=` | pct 90.00 / 35.00 | **Fails**: A2 / E | Pass A1 / D | Unit (`fault_demo`) |
| FI-003 | DEF-003 upper bound | mark 100.5 | **Fails**: accepted | Pass: rejected | Unit (`fault_demo`) |
| FI-004 | DEF-004 no commit | save then read in new session | **Fails**: value missing | Pass | Integration (`fault_demo`) |
| FI-005 | DEF-005 authz omitted (fixture only) | T1 PUT S2 marks | **Fails**: 200 & saved | Pass: 404, unchanged | Integration (`fault_demo`) |
| FI-006 | DEF-006 division by zero | TC-ACAD-01 | **Fails** | Pass (TC-ACAD-02) | Unit (`fault_demo`) |
