# Test Plan — SRMS (STQA Lab)

> Phase 1 draft (IEEE 829-style, condensed). Test cases: [test-cases.md](test-cases.md).

## 1. Objectives
1. Verify functional requirements in [requirements.md](requirements.md) — especially result calculation, authentication with CAPTCHA, and authorization.
2. Demonstrate black-box (EP, BVA) and white-box (statement/branch coverage) techniques with **measured** coverage.
3. Demonstrate defect life cycle via controlled fault injection with before/after evidence.
4. Provide a reproducible, automated suite runnable locally and in GitHub Actions.

## 2. Scope

| In scope | Out of scope |
|---|---|
| Grading/validation logic, auth, CAPTCHA verification handling, authorization, marks persistence, UI flows, security headers/CSRF, migrations, deployed smoke test, academic exercises | Load/stress testing at scale, penetration testing beyond listed cases, cross-browser matrix beyond Chrome (Edge optional locally), Cloudflare's own CAPTCHA strength |

## 3. Test levels and types

| Level | Location | Tooling | Dependencies | Runs in CI |
|---|---|---|---|---|
| Unit | `tests/unit/` | pytest, `unittest.mock` | none (no DB, no network) | ✅ |
| Integration | `tests/integration/` | pytest + Flask test client | PostgreSQL test DB, `CAPTCHA_MODE=mock` | ✅ (Postgres service container) |
| End-to-end (UI) | `tests/e2e/` | Selenium 4 + headless Chrome, live server thread | PostgreSQL test DB; Turnstile **test** keys (internet) **or** mock widget (offline) | ✅ |
| External smoke | `tests/e2e/test_smoke_deployed.py` (`-m external`) | Selenium/requests against `BASE_URL` | Deployed app + demo credentials via env | ❌ manual / `workflow_dispatch` only |
| Academic exercises | `academic/tests/` | pytest, pytest-cov | none | ✅ |
| Fault-injection demos | `fault_injection/tests/` (`-m fault_demo`) | pytest | unit: none; integration faults: test DB | ❌ by default (expected failures are demonstrated on purpose); a separate CI job runs them in "fixed" mode |

Test types: functional, negative, boundary, security (authz/IDOR, CSRF, SQLi, XSS, session), regression, smoke, persistence.

## 4. Techniques

* **Equivalence partitioning:** marks (invalid-low < 0, valid 0..max, invalid-high > max, malformed, invalid step), percentage → grade bands, login inputs (valid / invalid / empty / oversized / injection strings).
* **Boundary value analysis:** marks −0.5, 0, 0.5, max−0.5, max, max+0.5; subject pass mark 34.5 / 35 / 35.5; every grade boundary (x−0.01, x, x+0.01 for 35, 40, 50, 60, 70, 80, 90, 100); lockout 4/5/6 attempts; session lifetime just before/after expiry.
* **Decision table:** overall status = f(all subjects passed?, aggregate ≥ 35?, any missing?).
* **State transition:** account Active → Locked → Active (time) ; session Anonymous → Authenticated → Logged-out/Expired.
* **White-box:** statement + branch coverage of `app/services/grading.py` and `app/services/marks_service.py::parse_mark/validate_marks` measured with `pytest --cov --cov-branch`. Branch-to-test mapping documented in test-cases.md §WB.
* **Fault injection / mutation-style:** controlled faults (§8).

## 5. Environments

| Env | DB | CAPTCHA | Purpose |
|---|---|---|---|
| Local dev | Docker Postgres `srms_dev` | Turnstile test keys (always pass) | Development |
| Local test | Docker Postgres `srms_test` | Mock (unit/integration), Turnstile test keys or mock widget (E2E) | Running the suite |
| CI | Postgres 16 service container `srms_test` | Same as local test | Automated gate |
| Production | Neon Postgres | Turnstile **real** keys | Public demo + smoke tests |

Test data: created by factory fixtures in `tests/fixtures/`, cleaned up by table truncation after each test. Tests never read `DATABASE_URL`; they only use `TEST_DATABASE_URL`, guarded (name must contain `test`, must differ from `DATABASE_URL`).

## 6. Entry / exit criteria

**Entry:** code compiles, migrations apply on empty DB, test DB reachable.
**Exit (per milestone and final):**
* 100 % of P1 (critical) automated tests pass; no open Critical/High defects.
* All CI jobs green on `main`.
* Coverage target: ≥ 90 % line & branch on grading + marks validation; ≥ 80 % overall `app/` (targets; actual numbers reported from real runs).
* Deployed smoke checklist passes.

## 7. Deliverables
* Automated tests, `pytest.ini` markers, CI workflow.
* `reports/` (generated, git-ignored): `unit.html`, `integration.html`, `e2e.html`, `junit-*.xml`, `coverage/` HTML, `coverage.xml`.
* `docs/evidence/` (committed): **actual** console outputs/summaries of final runs, coverage summary, fault-injection before/after logs, E2E screenshots, smoke-test record.
* `docs/defects.md`: defect log (template §8.2).

## 8. Fault injection & defect tracking

### 8.1 Approach
Faults live in `fault_injection/` — **never imported by `app/`** and never deployed. Each fault is a minimal faulty variant of a real function, activated by a pytest fixture that monkeypatches the real implementation (for integration-level faults) or by importing the faulty module directly (for unit-level faults). Each defect demo produces:

1. `pytest -m fault_demo --fault=DEF-00X` → **fails** (real output captured to `docs/evidence/faults/DEF-00X-before.txt`).
2. Root cause documented.
3. Corrected implementation = the real `app/` function.
4. Same test run against the corrected implementation → **passes** (`…-after.txt`).
5. Regression test IDs in the normal suite that guard against reintroduction.

Additionally (optional, your choice — see open decisions) a `fault-injection` Git branch can contain a commit introducing each fault and the fix commit on `main`, giving GitHub Actions red→green evidence.

### 8.2 Planned defects

| ID | Summary | Severity | Priority | Fault introduced | Detecting test(s) | Regression tests |
|---|---|---|---|---|---|---|
| DEF-001 | Percentage uses fixed denominator 100×(number of subjects present) instead of Σ max_marks | High | P1 | `percentage = total / (len(subjects)*100) * 100` | FI-001 (exam with max marks 100, 80, 50) | TC-CALC-10, TC-CALC-11 |
| DEF-002 | Grade boundary off-by-one: `>` instead of `>=` at band lower bounds | High | P1 | `if pct > 90: "A1"` | FI-002 (pct = 90.00, 35.00) | TC-CALC-12 (all boundaries), TC-WB-* |
| DEF-003 | Marks upper bound accepts max+0.5 (`<=` on max+0.5 / missing check) | Medium | P2 | `if value > max + Decimal("0.5")` | FI-003 | TC-CALC-04, TC-BB-03 |
| DEF-004 | Marks not persisted: session flushed but transaction not committed | High | P1 | `db.session.flush()` without `commit()` | FI-004 (save then re-read in new session) | TC-DB-02, TC-DB-06 |
| DEF-005 | Authorization check omitted in teacher marks save (controlled fixture only) | Critical | P1 | assignment check monkeypatched to always `True` | FI-005 (unassigned teacher PUT) | TC-AUTHZ-07, TC-AUTHZ-08 |
| DEF-006 | Academic: division program does not guard divisor 0 | Medium | P2 | `academic/division_faulty.py` | TC-ACAD-01 | TC-ACAD-02 |

Defect record template (filled in `docs/defects.md` with actual outputs):

| Field | Content |
|---|---|
| ID / Summary / Severity / Priority | |
| Steps to reproduce | exact pytest command |
| Expected result | |
| Actual result (before fix) | copied from real run |
| Status history | New → Assigned → Open → Fixed → Retest → Verified → Closed |
| Root cause | |
| Fix | file/function, commit |
| Retest result | copied from real run |
| Regression-test reference | test IDs |

## 9. Requirements traceability

| Requirement | Test cases |
|---|---|
| FR-AUTH-01 | TC-AUTH-01, TC-AUTH-02, TC-AUTH-13 |
| FR-AUTH-02 | TC-AUTH-04, TC-UI-01 |
| FR-AUTH-02 (inputs) | TC-AUTH-15, TC-AUTH-16, TC-BB-11 |
| FR-AUTH-03 | TC-CAP-01…06, TC-CAP-12…16, TC-AUTH-05/06/07 |
| FR-AUTH-04 | TC-CAP-07, TC-CAP-08, TC-AUTH-08 |
| FR-AUTH-05 | TC-SEC-05 |
| FR-AUTH-06 | TC-AUTH-03 |
| FR-AUTH-07 | TC-AUTH-12 |
| FR-AUTH-08 | TC-SEC-06 |
| FR-AUTH-09 | TC-AUTH-09, TC-UI-07 |
| FR-AUTH-10 | TC-AUTH-10 |
| FR-AUTH-11 | TC-AUTHZ-11 |
| FR-AUTH-07 (inactive) | TC-AUTH-14 |
| FR-AUTHZ-01…07 | TC-AUTHZ-01…12, TC-SEC-03 |
| FR-MARK-01…07 | TC-MARK-01…10, TC-CALC-01…06, TC-BB-01…08, TC-DB-02/05 |
| FR-RES-01…03 | TC-CALC-06…17, TC-BB-09/10, TC-WB-01…13, TC-UI-04 |
| FR-UI-01…06 | TC-UI-01…13 |
| FR-OPS-01…04 | TC-OPS-01…06 |
| NFR-SEC-01…06 | TC-SEC-01…11 |
| NFR-REL-01/02 | TC-DB-01…10 |
| CAP-01…05 | TC-CAP-01…16 |
| Academic exercises | TC-ACAD-01…09 |
| Fault injection | FI-001…006 |

## 10. Commands (planned — exact, verified commands will be finalised in README after implementation)

```powershell
# 1. Install
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
# 2. Configure test env
copy .env.example .env      # edit TEST_DATABASE_URL etc.
# 3. Start/init test DB
docker compose up -d db
flask --app wsgi db upgrade  # (tests also run migrations automatically on TEST_DATABASE_URL)
# 4-8. Run
pytest -m unit
pytest -m integration
pytest -m e2e
pytest                       # all except external/fault_demo
pytest --cov=app --cov-branch --cov-report=html:reports/coverage --cov-report=term-missing --html=reports/all.html --self-contained-html
```

## 11. Risks to testing

| Risk | Mitigation |
|---|---|
| Turnstile/network unavailable during E2E | Offline mock-widget E2E variant; network E2E marked and retried once on infra error only |
| Chrome/driver mismatch | Selenium Manager resolves driver; CI uses `browser-actions/setup-chrome` |
| Docker not running locally | README documents native PostgreSQL alternative |
| Flaky timing | Explicit waits; `data-testid` selectors; deterministic data |
| Test pollution | Per-test truncation; unique IDs from factories |

## 12. Schedule / milestones
See [implementation-plan.md](implementation-plan.md).
