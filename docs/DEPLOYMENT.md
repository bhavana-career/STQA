# Production Deployment Guide: Render, Neon PostgreSQL & Cloudflare Turnstile

This guide provides end-to-end instructions for deploying the **Student Result Management System (SRMS)** to production using **Render** (Flask web service) and **Neon** (Serverless PostgreSQL), secured with **Cloudflare Turnstile CAPTCHA**.

---

## 1. Production Architecture Overview

```
[ User Browser ]
       | HTTPS
       v
[ Cloudflare Edge / Turnstile CAPTCHA ]
       | (Token verification)
       v
[ Render Web Service (Gunicorn + Flask WSGI) ]
   - ProxyFix handles forwarded HTTPS headers
   - Security headers (CSP, HSTS, X-Frame-Options, CSRF)
   - Connection pool: pool_pre_ping=True, pool_recycle=280s
       |
       | SSL Encrypted (sslmode=require)
       v
[ Neon PostgreSQL Serverless ]
   - Database: srms
   - Schema managed via Alembic migrations
```

---

## 2. Step 1: Provision Neon PostgreSQL Database

1. Sign up or log in to [Neon Console](https://console.neon.tech).
2. Click **Create Project**:
   - **Project Name:** `srms-production`
   - **Database Name:** `srms`
   - **Region:** Select a region close to your Render deployment (e.g., `US East (Ohio)` or `US West (Oregon)`).
   - **Compute Size:** Free tier default.
3. In the project dashboard under **Connection Details**:
   - Select **Pooled connection** (recommended for web services).
   - Ensure `sslmode=require` is present in the connection string.
   - The connection string format:
     ```text
     postgresql://<user>:<password>@<endpoint>-pooler.<region>.aws.neon.tech/srms?sslmode=require
     ```
4. Save this URL securely; this will be set as `DATABASE_URL` on Render.

> [!NOTE]
> The application automatically normalizes `postgres://` or `postgresql://` connection strings to use the modern `postgresql+psycopg://` driver, with automated reconnection (`pool_pre_ping=True`) when Neon wakes up from auto-suspend.

---

## 3. Step 2: Configure Cloudflare Turnstile CAPTCHA

1. Sign up or log in to [Cloudflare Dashboard](https://dash.cloudflare.com).
2. Navigate to **Turnstile** in the left sidebar and click **Add Site**:
   - **Site Name:** `SRMS Production Portal`
   - **Domain:** Enter your Render application domain (e.g., `srms-portal.onrender.com`).
   - **Widget Mode:** **Managed** (recommended for optimal bot detection).
3. Click **Create**:
   - Copy the **Site Key** (public, rendered in HTML).
   - Copy the **Secret Key** (confidential, server-side validation).

> [!WARNING]
> **Production Safety Interlock:**  
> The application strictly rejects test keys (`1x0000...`, `2x0000...`, `3x0000...`) when `APP_ENV=production`. You must provide real Turnstile keys generated in the Cloudflare dashboard.

---

## 4. Step 3: Deploy to Render

### Method A: Deploy via `render.yaml` Blueprint (Recommended)

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **Blueprints** -> **New Blueprint Instance**.
3. Connect your GitHub repository: `https://github.com/bhavana-career/STQA`.
4. Render automatically parses [`render.yaml`](file:///c:/Users/bhava/Downloads/ST&QA/render.yaml).
5. When prompted for environment variables marked `sync: false`, input:
   - `DATABASE_URL`: Your pooled Neon connection string.
   - `TURNSTILE_SITE_KEY`: Your real Cloudflare site key.
   - `TURNSTILE_SECRET_KEY`: Your real Cloudflare secret key.
   - `TURNSTILE_ALLOWED_HOSTNAMES`: Your Render domain (e.g., `srms-portal.onrender.com`).
6. Click **Apply**.

---

### Method B: Manual Web Service Setup

If setting up manually in the Render dashboard:
1. Click **New +** -> **Web Service**.
2. Connect `https://github.com/bhavana-career/STQA`.
3. Configure settings:
   - **Name:** `srms-portal`
   - **Region:** Same region as Neon (e.g., Oregon or Ohio).
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `flask db upgrade && gunicorn wsgi:app --workers 2 --threads 4 --timeout 60 --access-logfile - --error-logfile -`
   - **Plan:** `Free`
4. Under **Advanced** -> **Health Check Path**, enter: `/health`.
5. Add the following **Environment Variables**:

| Variable Name | Value / Description | Sensitive? |
|---|---|:---:|
| `APP_ENV` | `production` | No |
| `PYTHON_VERSION` | `3.11.9` | No |
| `FLASK_APP` | `wsgi:app` | No |
| `SECRET_KEY` | Long random token ($\ge 32$ characters) | **Yes** |
| `DATABASE_URL` | Pooled Neon PostgreSQL connection URL | **Yes** |
| `CAPTCHA_MODE` | `turnstile` | No |
| `TURNSTILE_SITE_KEY` | Real Cloudflare Turnstile Site Key | No |
| `TURNSTILE_SECRET_KEY` | Real Cloudflare Turnstile Secret Key | **Yes** |
| `TURNSTILE_ALLOWED_HOSTNAMES` | `srms-portal.onrender.com` | No |
| `LOG_LEVEL` | `INFO` | No |

---

## 5. Step 4: Database Migrations & Initial Account Provisioning

### Database Migrations
Database migrations execute automatically on service startup before Gunicorn workers initialize:
```bash
flask db upgrade
```
If migrations fail, the deployment is safely halted, preventing inconsistent database state.

### Initial Account Provisioning

Render Free tier instances do not support Shell/SSH access. The application provides two secure provisioning methods:

#### Method A: One-Time Authenticated Web Bootstrap (Recommended for Render Free Tier)
1. Generate a cryptographically secure token ($\ge 32$ characters):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. In the Render Dashboard under **Environment**, add:
   - Key: `PROVISIONING_SECRET`
   - Value: *(your generated token)*
   Render will automatically redeploy with the secret loaded in memory.
3. In your browser, navigate to:
   ```
   https://<your-render-app>.onrender.com/system/provision
   ```
4. Enter the `PROVISIONING_SECRET` and specify custom passwords (min 12 chars, upper, lower, digit, symbol) for Student `4INI23IS036` and Teacher `TCH001`.
5. Click **Provision Production Accounts**. Upon success:
   - Accounts and the Mathematics subject assignment are created atomically.
   - The system permanently writes `bootstrap_completed = true` in the database.
   - The `/system/provision` endpoint immediately reverts to HTTP 404 stealth mode.
6. Delete `PROVISIONING_SECRET` from the Render Dashboard environment settings.

#### Method B: Provisioning Accounts via Render Shell (Render Paid Tiers)
If you are on a paid Render plan with Shell access, open the **Shell** tab:

```bash
# Securely provisions Student (4INI23IS036) and Teacher (TCH001) linked for Mathematics
# Interactively prompts for passwords using hidden input (getpass) with confirmation:
flask setup-production-accounts --prompt-passwords
```

#### Method C: Provision Custom Teacher & Student Accounts (Shell)
```bash
# Provision a teacher account (prompts for password securely via getpass)
flask create-user --role teacher --login-id TCH001 --name "Lead Teacher"

# Provision a student account
flask create-user --role student --login-id STU2026001 --name "Jane Doe" --section A --roll 1
```

#### Option 3: Seed Demonstration Dataset Safely
In production, demo seeding requires explicit confirmation flags and temporary environment passwords:
```bash
DEMO_STUDENT_PASSWORD="YourSecureStudentPassword123!" \
DEMO_TEACHER_PASSWORD="YourSecureTeacherPassword123!" \
flask seed-demo --i-understand-this-is-production
```
*(Notice: The `--reset` destructive flag is strictly disabled in production).*

---

## 6. Step 5: Post-Deployment Smoke Verification Checklist

After deployment, perform the following verification:

1. **Health Check Endpoint:**
   - Navigate to: `https://<your-service>.onrender.com/health`
   - Expected Response: `{"status": "ok", "database": "ok", "version": "..."}` with HTTP 200.
2. **Security Headers Verification:**
   - Inspect response headers using `curl -I https://<your-service>.onrender.com/`:
     - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
     - `X-Frame-Options: DENY`
     - `X-Content-Type-Options: nosniff`
     - `Content-Security-Policy: default-src 'self' ...`
3. **Turnstile Widget Rendering:**
   - Open `/student/login` and `/teacher/login`.
   - Verify the Cloudflare Turnstile interactive checkbox/widget renders correctly.
4. **Authentication & Authorization:**
   - Log in as student `STU2026001`. Verify dashboard shows only this student's result.
   - Verify result modal displays statement of marks, percentage, and grade.
   - Log out. Verify session is revoked (`session_version` invalidated).
   - Log in as teacher `TCH001`. Edit marks for an assigned student and verify audit trail persistence.

---

## 7. Step 6: Troubleshooting & Common Pitfalls

| Symptom / Error | Root Cause | Resolution |
|---|---|---|
| **Render Free Tier Cold Start** | Free-tier Web Services spin down after 15 minutes of inactivity. First request takes 30–50s. | Normal on Render free tier. Open the URL 1 minute prior to evaluation presentations. |
| **`ConfigError: SQLite is not allowed in production`** | `DATABASE_URL` is set to an SQLite database path. | Provide a valid Neon PostgreSQL connection URL. |
| **`ConfigError: Cloudflare Turnstile TEST keys are not allowed in production`** | Test keys (`1x...`, `2x...`) were provided in production. | Generate real site & secret keys in Cloudflare Turnstile dashboard. |
| **`ConfigError: TURNSTILE_ALLOWED_HOSTNAMES is required`** | Allowed hostnames list is empty or unset. | Set `TURNSTILE_ALLOWED_HOSTNAMES` to your Render service domain. |
| **`ConfigError: SECRET_KEY must be a random value of at least 32 characters`** | `SECRET_KEY` is too short or contains `change-me`. | Generate a 32+ char random key via `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| **Database Connection Failures during Idle Periods** | Neon serverless computes auto-suspend when idle. | The application includes `pool_pre_ping=True` and `pool_recycle=280` in SQLAlchemy engine options to automatically reconnect. |
