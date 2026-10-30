"""One-time authenticated production provisioning workflow.

Enforces:
- Secret token authentication through masked POST field (never in URL or logs).
- Constant-time secret comparison preventing timing attacks.
- Enforces strong password policy (>= 12 characters, upper, lower, numbers, symbols).
- Atomic transaction with concurrency safety.
- Never overwrites existing account passwords silently.
- One-time database lockout flag ('bootstrap_completed').
- Returns HTTP 404 when disabled or completed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hmac
import os
import threading
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    make_response,
    render_template,
    request,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Exam,
    ExamSubject,
    Section,
    Student,
    Subject,
    SystemSetting,
    Teacher,
    TeacherAssignment,
    User,
    utc_now,
)
from ..services.password_policy import validate_password_strength
from ..services.seed_data import AccountAlreadyExistsError, provision_stqa_scenario

bp = Blueprint("provision", __name__, url_prefix="/system")

# Unique 64-bit integer constant for PostgreSQL advisory transaction lock ("SRMSPROV")
PROVISIONING_ADVISORY_LOCK_ID = 6004000305882656630

# In-memory IP rate limiter for provisioning failures
_FAILED_ATTEMPTS: dict[str, list[datetime]] = {}
_LOCK = threading.Lock()
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def _is_rate_limited(ip: str) -> bool:
    """Check if IP has exceeded maximum failed attempts in the lockout window."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    with _LOCK:
        attempts = [t for t in _FAILED_ATTEMPTS.get(ip, []) if t > cutoff]
        _FAILED_ATTEMPTS[ip] = attempts
        return len(attempts) >= MAX_FAILED_ATTEMPTS


def _record_failure(ip: str) -> None:
    """Record a failed attempt for the given IP address."""
    now = datetime.now(timezone.utc)
    with _LOCK:
        if ip not in _FAILED_ATTEMPTS:
            _FAILED_ATTEMPTS[ip] = []
        _FAILED_ATTEMPTS[ip].append(now)


def _get_provisioning_secret() -> str | None:
    """Retrieve and validate the configured provisioning secret from environment."""
    secret = os.environ.get("PROVISIONING_SECRET") or current_app.config.get("PROVISIONING_SECRET")
    if not secret or len(secret.strip()) < 32:
        return None
    return secret.strip()


def _is_bootstrap_already_completed() -> bool:
    """Check whether one-time provisioning has already been executed in the database."""
    try:
        setting = db.session.scalar(
            select(SystemSetting).where(SystemSetting.key == "bootstrap_completed")
        )
        return setting is not None and setting.value.lower() == "true"
    except Exception:
        return False


def _set_security_headers(response: Response) -> Response:
    """Apply strict anti-indexing and no-cache headers."""
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@bp.get("/provision")
def provision_form() -> Response:
    """Render masked provisioning form or return 404 if disabled/completed."""
    if _get_provisioning_secret() is None or _is_bootstrap_already_completed():
        abort(404)

    client_ip = request.remote_addr or "unknown"
    if _is_rate_limited(client_ip):
        abort(429)

    resp = make_response(render_template("provision/setup.html"))
    return _set_security_headers(resp)


@bp.post("/provision")
def process_provision() -> Response:
    """Process one-time account provisioning atomically."""
    env_secret = _get_provisioning_secret()
    if env_secret is None or _is_bootstrap_already_completed():
        abort(404)

    client_ip = request.remote_addr or "unknown"
    if _is_rate_limited(client_ip):
        abort(429)

    submitted_secret = request.form.get("provisioning_secret") or ""
    teacher_password = request.form.get("teacher_password") or ""
    confirm_teacher_password = request.form.get("confirm_teacher_password") or ""
    student_password = request.form.get("student_password") or ""
    confirm_student_password = request.form.get("confirm_student_password") or ""

    # Verify secret with constant-time comparison
    if not hmac.compare_digest(env_secret, submitted_secret):
        _record_failure(client_ip)
        resp = make_response(
            render_template(
                "provision/setup.html",
                error="Invalid provisioning secret. Please check your Render environment configuration.",
            ),
            400,
        )
        return _set_security_headers(resp)

    # Check required fields
    if not teacher_password or not student_password:
        resp = make_response(
            render_template("provision/setup.html", error="All password fields are required."),
            400,
        )
        return _set_security_headers(resp)

    # Confirm matching passwords
    if teacher_password != confirm_teacher_password:
        resp = make_response(
            render_template(
                "provision/setup.html",
                error="Teacher password and confirmation do not match.",
            ),
            400,
        )
        return _set_security_headers(resp)

    if student_password != confirm_student_password:
        resp = make_response(
            render_template(
                "provision/setup.html",
                error="Student password and confirmation do not match.",
            ),
            400,
        )
        return _set_security_headers(resp)

    # Validate strong password policy
    valid_t, _ = validate_password_strength(teacher_password, min_length=12)
    if not valid_t:
        resp = make_response(
            render_template(
                "provision/setup.html",
                error="Teacher password does not meet complexity requirements (minimum 12 characters with uppercase, lowercase, numbers, and special characters).",
            ),
            400,
        )
        return _set_security_headers(resp)

    valid_s, _ = validate_password_strength(student_password, min_length=12)
    if not valid_s:
        resp = make_response(
            render_template(
                "provision/setup.html",
                error="Student password does not meet complexity requirements (minimum 12 characters with uppercase, lowercase, numbers, and special characters).",
            ),
            400,
        )
        return _set_security_headers(resp)

    # Atomic execution with safety check against silent overwrite
    try:
        # 1. PostgreSQL advisory transaction lock across workers for initial request
        is_postgres = False
        try:
            is_postgres = db.session.bind.dialect.name == "postgresql"
        except Exception:
            pass

        if is_postgres:
            acquired = db.session.scalar(
                select(func.pg_try_advisory_xact_lock(PROVISIONING_ADVISORY_LOCK_ID))
            )
            if not acquired:
                db.session.rollback()
                resp = make_response(
                    render_template(
                        "provision/setup.html",
                        error="Provisioning is currently in progress. Please try again shortly.",
                    ),
                    409,
                )
                return _set_security_headers(resp)

        # 2. Check if bootstrap has already completed
        if _is_bootstrap_already_completed():
            db.session.rollback()
            abort(404)

        # 3. Provision STQA Testing Scenario (General Teacher TCH001, 5 Students, 5 Subjects, 25 Assignments, Realistic Marks)
        summary = provision_stqa_scenario(
            teacher_password=teacher_password,
            student_password=student_password,
            overwrite_passwords=False,
            lockout_system=True,
        )

    except AccountAlreadyExistsError:
        db.session.rollback()
        current_app.logger.warning("Provisioning rejected: one or more accounts already exist.")
        resp = make_response(
            render_template(
                "provision/setup.html",
                error="One or more accounts already exist. Provisioning aborted to prevent overwriting existing data.",
            ),
            409,
        )
        return _set_security_headers(resp)
    except IntegrityError as exc:
        db.session.rollback()
        current_app.logger.error("Provisioning integrity error: %s", exc)
        abort(404)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Provisioning transaction error: %s", exc, exc_info=True)
        resp = make_response(
            render_template(
                "provision/setup.html",
                error="An error occurred while processing the provisioning request. Please check the system logs.",
            ),
            500,
        )
        return _set_security_headers(resp)

    resp = make_response(render_template("provision/success.html", summary=summary))
    return _set_security_headers(resp)
