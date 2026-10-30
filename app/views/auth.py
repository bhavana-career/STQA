"""Authentication views: Student login, Teacher login, and Logout.

Enforces:
- Cloudflare Turnstile verification.
- Account lockout policy (TC-AUTH-12).
- Non-revealing error messages (TC-AUTH-03).
- Role segregation (TC-AUTH-13).
- Session fixation protection (TC-SEC-06).
- Safe redirection (TC-SEC-09).
"""
from __future__ import annotations

from typing import Any
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from ..auth import _wants_json, is_safe_url
from ..extensions import db
from ..models import User
from ..services.captcha import verify_captcha
from ..services.password_policy import validate_password_strength

bp = Blueprint("auth", __name__)


def _render_auth_page_or_json(
    role: str,
    error_message: str | None = None,
    status: int = 200,
    login_id: str = "",
) -> Response | tuple[Any, int]:
    """Helper to render login template or return JSON error if client expects JSON."""
    if _wants_json() and error_message:
        code_map = {
            400: "bad_request",
            401: "unauthenticated",
            403: "forbidden",
            429: "locked",
            503: "captcha_unavailable",
        }
        return (
            jsonify(
                {
                    "error": {
                        "code": code_map.get(status, "error"),
                        "message": error_message,
                    }
                }
            ),
            status,
        )

    title = "Student Portal Sign In" if role == "student" else "Teacher Portal Sign In"
    site_key = current_app.config.get("TURNSTILE_SITE_KEY", "")
    next_url = request.args.get("next") or request.form.get("next") or ""

    return (
        render_template(
            "auth/login.html",
            role=role,
            title=title,
            site_key=site_key,
            action="login",
            error_message=error_message,
            login_id=login_id,
            next=next_url if is_safe_url(next_url) else "",
        ),
        status,
    )


def _handle_login(role: str) -> Response | tuple[Any, int]:
    """Shared login handler for both student and teacher roles."""
    login_id = (request.form.get("login_id") or "").strip()
    password = request.form.get("password") or ""
    turnstile_token = request.form.get("cf-turnstile-response")
    next_url = request.form.get("next") or request.args.get("next")

    # TC-AUTH-04: Empty fields check before CAPTCHA
    if not login_id or not password:
        return _render_auth_page_or_json(
            role,
            error_message="Please enter both Login ID and password.",
            status=400,
            login_id=login_id,
        )

    # TC-AUTH-16: Length limits
    if len(login_id) > 32 or len(password) > 128:
        return _render_auth_page_or_json(
            role,
            error_message="Input exceeds maximum allowed length.",
            status=400,
            login_id=login_id,
        )

    # TC-AUTH-05: Missing CAPTCHA check
    if not turnstile_token or not turnstile_token.strip():
        return _render_auth_page_or_json(
            role,
            error_message="Please complete the CAPTCHA.",
            status=400,
            login_id=login_id,
        )

    # Verify CAPTCHA
    captcha_res = verify_captcha(turnstile_token, remote_ip=request.remote_addr)
    if captcha_res.unavailable:
        # TC-AUTH-08
        return _render_auth_page_or_json(
            role,
            error_message="Verification service unavailable. Please try again shortly.",
            status=503,
            login_id=login_id,
        )
    if not captcha_res.ok:
        # TC-AUTH-06, TC-AUTH-07
        return _render_auth_page_or_json(
            role,
            error_message="CAPTCHA verification failed. Please try again.",
            status=400,
            login_id=login_id,
        )

    # TC-AUTH-15: Case-insensitive login ID lookup
    norm_id = login_id.upper()
    user = db.session.scalar(select(User).where(User.login_id == norm_id))

    max_attempts = current_app.config.get("LOGIN_MAX_ATTEMPTS", 5)
    lockout_minutes = current_app.config.get("LOGIN_LOCKOUT_MINUTES", 15)

    # TC-AUTH-12: Account lockout check
    if user and user.is_locked():
        return _render_auth_page_or_json(
            role,
            error_message="Account is temporarily locked due to too many failed attempts. Try again later.",
            status=429,
            login_id=login_id,
        )

    # TC-AUTH-03, TC-AUTH-13, TC-AUTH-14: Credential and role verification
    generic_error = "Invalid ID or password."

    if not user:
        return _render_auth_page_or_json(role, error_message=generic_error, status=401, login_id=login_id)

    if not user.is_active or user.role != role or not user.check_password(password):
        # Record failed attempt against existing account
        user.record_failed_login(max_attempts=max_attempts, lockout_minutes=lockout_minutes)
        db.session.commit()
        return _render_auth_page_or_json(role, error_message=generic_error, status=401, login_id=login_id)

    # Success: Record login and clear lockout
    user.record_successful_login()

    # TC-SEC-06: Session fixation protection - clear existing session
    session.clear()
    session.permanent = True  # TC-AUTH-10: Enforces idle session expiry

    # Create new session
    login_user(user, remember=False)
    session["session_version"] = user.session_version
    db.session.commit()

    # Determine destination URL
    default_url = (
        url_for("student.dashboard")
        if role == "student"
        else url_for("teacher.dashboard")
    )
    destination = next_url if is_safe_url(next_url) else default_url

    if _wants_json():
        return jsonify({"status": "ok", "redirect": destination, "role": role}), 200

    return redirect(destination)


@bp.get("/student/login")
def student_login():
    """Render Student Login page or redirect if already authenticated."""
    if current_user.is_authenticated:
        if getattr(current_user, "role", None) == "student":
            return redirect(url_for("student.dashboard"))
        return redirect(url_for("teacher.dashboard"))
    return _render_auth_page_or_json("student")


@bp.post("/student/login")
def student_login_post():
    """Process Student Login."""
    return _handle_login("student")


@bp.get("/teacher/login")
def teacher_login():
    """Render Teacher Login page or redirect if already authenticated."""
    if current_user.is_authenticated:
        if getattr(current_user, "role", None) == "teacher":
            return redirect(url_for("teacher.dashboard"))
        return redirect(url_for("student.dashboard"))
    return _render_auth_page_or_json("teacher")


@bp.post("/teacher/login")
def teacher_login_post():
    """Process Teacher Login."""
    return _handle_login("teacher")


@bp.post("/logout")
def logout():
    """Invalidate session and log out the user (TC-AUTH-09)."""
    if current_user.is_authenticated:
        # Increment session version on server to invalidate all existing sessions
        current_user.increment_session_version()
        db.session.commit()
        logout_user()

    session.clear()
    flash("You have been logged out.", "info")

    if _wants_json():
        return jsonify({"status": "ok", "message": "Logged out successfully"}), 200

    return redirect(url_for("main.index"))


@bp.post("/change-password")
@login_required
def change_password():
    """Secure password change for authenticated students and teachers."""
    payload = request.get_json(silent=True) or {} if request.is_json else {}
    current_pw = request.form.get("current_password") or payload.get("current_password") or ""
    new_pw = request.form.get("new_password") or payload.get("new_password") or ""
    confirm_pw = request.form.get("confirm_password") or payload.get("confirm_password") or ""

    if not current_pw or not new_pw or not confirm_pw:
        msg = "All password fields are required."
        if _wants_json():
            return jsonify({"error": {"code": "missing_fields", "message": msg}}), 400
        flash(msg, "error")
        return redirect(_get_dashboard_url(current_user.role))

    if not current_user.check_password(current_pw):
        msg = "Current password is incorrect."
        if _wants_json():
            return jsonify({"error": {"code": "invalid_current_password", "message": msg}}), 400
        flash(msg, "error")
        return redirect(_get_dashboard_url(current_user.role))

    if new_pw != confirm_pw:
        msg = "New password and confirmation do not match."
        if _wants_json():
            return jsonify({"error": {"code": "password_mismatch", "message": msg}}), 400
        flash(msg, "error")
        return redirect(_get_dashboard_url(current_user.role))

    if current_pw == new_pw:
        msg = "New password cannot be identical to current password."
        if _wants_json():
            return jsonify({"error": {"code": "same_password", "message": msg}}), 400
        flash(msg, "error")
        return redirect(_get_dashboard_url(current_user.role))

    valid, err_msg = validate_password_strength(new_pw, min_length=12)
    if not valid:
        if _wants_json():
            return jsonify({"error": {"code": "weak_password", "message": err_msg}}), 400
        flash(err_msg or "Password does not meet complexity requirements.", "error")
        return redirect(_get_dashboard_url(current_user.role))

    # Update password and invalidate other sessions
    current_user.set_password(new_pw)
    current_user.increment_session_version()
    # Keep current session valid
    session["session_version"] = current_user.session_version
    db.session.commit()

    success_msg = "Password changed successfully."
    if _wants_json():
        return jsonify({"status": "ok", "message": success_msg}), 200

    flash(success_msg, "success")
    return redirect(_get_dashboard_url(current_user.role))


def _get_dashboard_url(role: str) -> str:
    return url_for("student.dashboard") if role == "student" else url_for("teacher.dashboard")

