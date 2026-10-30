"""Authentication and role-based authorization decorators and helpers.

Enforces:
- Authenticated user check.
- Role isolation (student-only vs teacher-only).
- JSON vs HTML error responses based on request path/content-type.
- Safe redirect validation preventing open redirect attacks (TC-SEC-09).
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable
from urllib.parse import urlparse

from flask import abort, current_app, jsonify, redirect, request, session, url_for
from flask_login import current_user, logout_user


def is_safe_url(target: str | None) -> bool:
    """Validate that target URL is a safe, relative path on the same origin (TC-SEC-09)."""
    if not target or not isinstance(target, str):
        return False
    target = target.strip()
    # Reject protocol-relative URLs (e.g. //evil.example)
    if target.startswith("//") or target.startswith("\\\\"):
        return False
    # Must start with single /
    if not target.startswith("/"):
        return False
    parsed = urlparse(target)
    # Must not contain scheme or netloc (domain)
    return not parsed.scheme and not parsed.netloc


def _wants_json() -> bool:
    """Determine whether the client expects a JSON response."""
    return (
        request.path.startswith("/api/")
        or request.is_json
        or request.accept_mimetypes.best == "application/json"
    )


def student_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """Ensure current user is authenticated with role='student'."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_authenticated:
            if _wants_json():
                return (
                    jsonify(
                        {
                            "error": {
                                "code": "unauthenticated",
                                "message": "Authentication required.",
                            }
                        }
                    ),
                    401,
                )
            next_url = request.full_path if request.method == "GET" and is_safe_url(request.full_path) else None
            return redirect(url_for("auth.student_login", next=next_url))

        if getattr(current_user, "role", None) != "student":
            if _wants_json():
                return (
                    jsonify(
                        {
                            "error": {
                                "code": "forbidden",
                                "message": "Access denied. Student role required.",
                            }
                        }
                    ),
                    403,
                )
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def teacher_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """Ensure current user is authenticated with role='teacher'."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_authenticated:
            if _wants_json():
                return (
                    jsonify(
                        {
                            "error": {
                                "code": "unauthenticated",
                                "message": "Authentication required.",
                            }
                        }
                    ),
                    401,
                )
            next_url = request.full_path if request.method == "GET" and is_safe_url(request.full_path) else None
            return redirect(url_for("auth.teacher_login", next=next_url))

        if getattr(current_user, "role", None) != "teacher":
            if _wants_json():
                return (
                    jsonify(
                        {
                            "error": {
                                "code": "forbidden",
                                "message": "Access denied. Teacher role required.",
                            }
                        }
                    ),
                    403,
                )
            abort(403)

        return f(*args, **kwargs)

    return decorated_function
