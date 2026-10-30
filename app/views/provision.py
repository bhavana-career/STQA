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
from sqlalchemy import select
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

bp = Blueprint("provision", __name__, url_prefix="/system")

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
    valid_t, err_t = validate_password_strength(teacher_password, min_length=12)
    if not valid_t:
        resp = make_response(
            render_template(
                "provision/setup.html",
                error=f"Teacher password policy error: {err_t}",
            ),
            400,
        )
        return _set_security_headers(resp)

    valid_s, err_s = validate_password_strength(student_password, min_length=12)
    if not valid_s:
        resp = make_response(
            render_template(
                "provision/setup.html",
                error=f"Student password policy error: {err_s}",
            ),
            400,
        )
        return _set_security_headers(resp)

    # Atomic execution with safety check against silent overwrite
    try:
        # 1. Concurrency guard: Lock or check bootstrap_completed row
        setting = db.session.scalar(
            select(SystemSetting).where(SystemSetting.key == "bootstrap_completed").with_for_update()
        )
        if setting and setting.value.lower() == "true":
            db.session.rollback()
            abort(404)

        # 2. Never overwrite existing passwords silently
        existing_teacher = db.session.scalar(select(User).where(User.login_id == "TCH001"))
        if existing_teacher and existing_teacher.password_hash:
            db.session.rollback()
            resp = make_response(
                render_template(
                    "provision/setup.html",
                    error="Teacher account TCH001 already exists with an active password. Aborting to avoid silent overwrite.",
                ),
                409,
            )
            return _set_security_headers(resp)

        existing_student = db.session.scalar(select(User).where(User.login_id == "4INI23IS036"))
        if existing_student and existing_student.password_hash:
            db.session.rollback()
            resp = make_response(
                render_template(
                    "provision/setup.html",
                    error="Student account 4INI23IS036 already exists with an active password. Aborting to avoid silent overwrite.",
                ),
                409,
            )
            return _set_security_headers(resp)

        # 3. Section: 10th Standard Section A (2025-26)
        sec = db.session.scalar(
            select(Section).where(
                Section.class_name == "10th Standard",
                Section.name == "A",
                Section.academic_year == "2025-26",
            )
        )
        if not sec:
            sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
            db.session.add(sec)
            db.session.flush()

        # 4. Subject: Mathematics (MAT)
        sub_mat = db.session.scalar(select(Subject).where(Subject.code == "MAT"))
        if not sub_mat:
            sub_mat = Subject(code="MAT", name="Mathematics")
            db.session.add(sub_mat)
            db.session.flush()

        # 5. Exam: Annual Examination 2025-26
        exam = db.session.scalar(select(Exam).where(Exam.academic_year == "2025-26"))
        if not exam:
            exam = Exam(name="Annual Examination 2025-26", academic_year="2025-26")
            db.session.add(exam)
            db.session.flush()

        es = db.session.scalar(
            select(ExamSubject).where(ExamSubject.exam_id == exam.id, ExamSubject.subject_id == sub_mat.id)
        )
        if not es:
            es = ExamSubject(
                exam_id=exam.id,
                subject_id=sub_mat.id,
                max_marks=Decimal("100.00"),
                pass_marks=Decimal("35.00"),
            )
            db.session.add(es)
            db.session.flush()

        # 6. Teacher Account (TCH001)
        if not existing_teacher:
            teacher_user = User(login_id="TCH001", role="teacher")
            teacher_user.set_password(teacher_password)
            db.session.add(teacher_user)
            db.session.flush()

            teacher_record = Teacher(
                user_id=teacher_user.id,
                teacher_code="TCH001",
                full_name="Mathematics Teacher",
            )
            db.session.add(teacher_record)
            db.session.flush()
        else:
            teacher_record = existing_teacher.teacher
            existing_teacher.set_password(teacher_password)

        # 7. Student Account (4INI23IS036)
        if not existing_student:
            student_user = User(login_id="4INI23IS036", role="student")
            student_user.set_password(student_password)
            db.session.add(student_user)
            db.session.flush()

            student_record = Student(
                user_id=student_user.id,
                student_code="4INI23IS036",
                full_name="Student 4INI23IS036",
                section_id=sec.id,
                roll_number=36,
            )
            db.session.add(student_record)
            db.session.flush()
        else:
            student_record = existing_student.student
            existing_student.set_password(student_password)

        # 8. Teacher Assignment
        assignment = db.session.scalar(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == teacher_record.id,
                TeacherAssignment.student_id == student_record.id,
                TeacherAssignment.subject_id == sub_mat.id,
            )
        )
        if not assignment:
            assignment = TeacherAssignment(
                teacher_id=teacher_record.id,
                student_id=student_record.id,
                subject_id=sub_mat.id,
            )
            db.session.add(assignment)

        # 9. Commit Lockout Flag atomically
        if setting:
            setting.value = "true"
            setting.updated_at = utc_now()
        else:
            setting = SystemSetting(key="bootstrap_completed", value="true")
            db.session.add(setting)

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        abort(404)
    except Exception as exc:
        db.session.rollback()
        resp = make_response(
            render_template(
                "provision/setup.html",
                error=f"Provisioning transaction failed: {exc}",
            ),
            500,
        )
        return _set_security_headers(resp)

    resp = make_response(render_template("provision/success.html"))
    return _set_security_headers(resp)
