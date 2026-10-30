# Implementation Plan, Risks & Deployment Strategy — SRMS

> Phase 1 draft — awaiting approval. No application code has been written yet.

## 1. Current repository state (inspected 2026-10-28)

| Item | Finding |
|---|---|
| Workspace `ST&QA` | Empty — no existing code, not a Git repository. Nothing to preserve. |
| Python | 3.11.9 ✅ |
| Git | 2.52 ✅, identity configured (`Bhavana S`) |
| GitHub CLI (`gh`) | Not installed — pushing will use plain `git` with your GitHub credentials/PAT, or you create the empty repo in the browser |
| Docker | Client 29.9 installed; daemon status unconfirmed (Docker Desktop may need to be started) — used for local PostgreSQL |
| PostgreSQL (`psql`) | Not installed natively → Docker container proposed |
| Chrome | 156 ✅ (Selenium Manager will fetch the matching driver); Edge also present |

> [!NOTE]
> The workspace path contains `&` (`ST&QA`). This works with PowerShell and Python but can break some shell scripts/`cmd.exe` calls; commands in the README will quote paths.

## 2. Milestones (each ends with a verifiable check)

| # | Milestone | Deliverables | Verification | Status |
|---|---|---|---|---|
| M0 | Phase 1 approval | These docs | Your approval | **APPROVED** |
| M1 | Skeleton & tooling | `git init`, `.gitignore`, `.env.example`, `requirements*.txt` (pinned), `docker-compose.yml`, app factory, config classes with production interlocks, `/health`, `pytest.ini` | `pytest -m unit` (config tests) passes; `/health` 200 locally | **COMPLETED & APPROVED** |
| M2 | Grading core (TDD) | `grading.py`, `parse_mark` + unit tests (CALC, BB, WB) | Unit tests pass; coverage measured and recorded (100% grading, 98% marks) | **COMPLETED & APPROVED** |
| M3 | Data layer | Models, initial Alembic migration, CLI `seed-demo` / `create-user` / `assign` / `unlock-user` | `flask db upgrade` on Docker Postgres; TC-DB-01/03/06/07/08/09/10, TC-OPS-01…05 pass (131 tests pass) | **COMPLETED & APPROVED** |
| M4 | Auth + CAPTCHA | Turnstile verifier, mock verifier, login/logout, lockout, session_version, CSRF, headers | TC-CAP-01…11, TC-AUTH-*, TC-AUTHZ-*, TC-SEC-* pass (190 tests pass, 91% coverage) | **COMPLETED & APPROVED** |
| M5 | Student & teacher features | Result API + dashboard + modal; teacher list/editor + PUT API with atomic save & audit | TC-AUTHZ-*, TC-MARK-*, TC-CALC-14/15, TC-DB-* pass (211 tests pass, 88% coverage) | **COMPLETED & APPROVED** |
| M6 | UI polish & accessibility | Responsive CSS, loading/error states, keyboard modal, headless Selenium setup & smoke suite | 10 Selenium E2E smoke tests pass; 224 total tests pass with 90% branch/stmt coverage | **COMPLETED & APPROVED** |
| M7 | Selenium E2E | Page Object Model architecture (`tests/e2e/pages/`), student/teacher complete journeys, boundary/negative suites, audit verification | 22 Selenium E2E tests pass in headless Chrome; 236 total suite tests pass with 90% branch/stmt coverage | **COMPLETED** (Ready for Review) |
| M8 | Academic exercises + fault injection | `academic/`, `fault_injection/`, `docs/defects.md` with real before/after outputs | `pytest -m fault_demo` shows the expected failures; fixed runs pass |
| M9 | CI | `.github/workflows/ci.yml`: unit → integration (Postgres service) → e2e (headless Chrome) → coverage/report artifacts; gitleaks | Green run on GitHub (link recorded) |
| M10 | Deployment | Render + Neon + real Turnstile keys; migrations; manual demo seeding | Public URL smoke checklist executed and recorded |
| M11 | Handover | README, deployment guide, evidence folder, final test/coverage results | Fresh-clone reproduction of the documented commands |

## 3. Deployment strategy (proposed)

1. **Neon:** create project → database `srms` → copy pooled connection string (`postgresql://…?sslmode=require`) → `DATABASE_URL` (driver prefix normalised to `postgresql+psycopg://` in config).
2. **Cloudflare Turnstile:** add widget, hostnames `<service>.onrender.com` (+ `localhost` only on a *separate* dev widget, or use test keys locally), mode *Managed* → site key + secret key.
3. **Render:** New Web Service from GitHub repo (or Blueprint via `render.yaml`), Python 3.11, build `pip install -r requirements.txt`, start `flask --app wsgi db upgrade && gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT`, health check path `/health`.
4. Env vars on Render: `APP_ENV=production`, `SECRET_KEY` (≥ 32 random bytes), `DATABASE_URL`, `CAPTCHA_MODE=turnstile`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `TURNSTILE_ALLOWED_HOSTNAMES`, `LOG_LEVEL=INFO`.
5. Demo accounts: run once from Render Shell (or locally with `DATABASE_URL` set to Neon) — `flask seed-demo --i-understand-this-is-production` with `DEMO_STUDENT_PASSWORD` / `DEMO_TEACHER_PASSWORD` set only for that command. Credentials shared privately with the team, not committed.
6. Smoke checklist (recorded in `docs/evidence/smoke-test.md`): HTTPS + headers, `/health`, both login pages render real Turnstile, student login (human solves CAPTCHA) → own result only, teacher edits mark → student sees update, logout, restart/redeploy service → data still present.

Hosting credentials are required from you; I cannot create accounts. If you prefer, I prepare everything and you click through the dashboards while I guide you.

## 4. Key risks

| Area | Risk | Impact | Mitigation |
|---|---|---|---|
| Authentication | Cookie sessions can't be revoked server-side | Stolen cookie valid until expiry | `session_version` check on every request; 30-min idle expiry |
| Authentication | Lockout abused to lock demo accounts | Demo unavailable | CAPTCHA before password check; 15-min lock; `flask unlock-user` |
| CAPTCHA | Test/mock mode accidentally in production | CAPTCHA bypass | Startup interlocks + unit tests (TC-CAP-10/11, TC-SEC-08); Cloudflare prod secrets reject dummy token |
| CAPTCHA | Cloudflare outage | Nobody can log in | Fail-closed by design (documented trade-off), clear 503 message |
| CAPTCHA | CSP blocks widget | Login broken | CSP allows `challenges.cloudflare.com` for script/frame; E2E covers widget load |
| DB persistence | Free Postgres tiers expiring / sleeping | Data loss / slow first query | Neon (non-expiring free tier, auto-suspend → short wake-up); `pool_pre_ping=True` |
| DB | Migration failure on deploy | Service fails to start | Start command aborts before gunicorn; migrations tested in CI on fresh Postgres |
| Deployment | Render free cold starts (~30–60 s) | Slow demo first load | Documented; open URL before presenting |
| Deployment | Proxy/HTTPS detection | Secure cookies not set, wrong scheme | `ProxyFix`; smoke test checks `Set-Cookie` flags |
| Browser tests | Network dependency on Cloudflare for Turnstile test keys | Flaky CI | Offline mock-widget suite always runs; `captcha_live` suite runs in CI with one infra-retry |
| Browser tests | Chrome/driver version drift | CI breakage | Selenium Manager; `browser-actions/setup-chrome` |
| Browser tests | Timing flakiness | False failures | Explicit waits, `data-testid`, no sleeps |
| Local env | Docker daemon not running / `&` in path | Setup friction | README alternatives (native PostgreSQL installer), quoted paths |
| Process | Fabricated evidence | Academic integrity | Evidence files generated by commands (`tee`), CI artifacts linked |

## 5. Outstanding decisions (need your input)

1. **Hosting:** Render (web) + Neon (Postgres) — OK? Do you already have accounts on either, or a preferred provider?
2. **CAPTCHA:** Cloudflare Turnstile (recommended over reCAPTCHA for deterministic pass/fail test keys) — OK? You'll need a free Cloudflare account.
3. **Grading rules:** 8-band scale A1…E, subject pass 35/100, overall pass = all subjects passed and ≥ 35 %, FAIL ⇒ grade E, 0.5-step decimal marks. Confirm or give your syllabus/institution rules.
4. **Teacher assignment granularity:** per (student, subject) — confirm vs. simpler per-student (teacher edits all subjects).
5. **Syllabus data:** please share the syllabus's exact sample data/rules for (a) defect density & productivity, (b) Agile vs Waterfall estimates, (c) ATM withdrawal rules, (d) the division program if a specific one is given. Without it I'll use clearly-labelled placeholder data.
6. **Fault injection:** isolated `fault_injection/` module with monkeypatched faults (recommended) — and additionally a `fault-injection` Git branch for red→green CI evidence? (yes/no)
7. **GitHub:** repository name and visibility (public recommended so evaluators can view Actions). Will you create the empty repo and provide push access (HTTPS + PAT or Git Credential Manager)?
