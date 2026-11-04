"""Route blueprints for SRMS."""

from functools import wraps
from flask import session, redirect, url_for, flash, abort


def login_required(view):
    """Ensure the user is logged in before accessing a route."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login.login_page"))
        return view(*args, **kwargs)
    return wrapped_view


def teacher_required(view):
    """Ensure the logged-in user has the 'teacher' role."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = session.get("user")
        if not user:
            flash("Please log in as a teacher to access this page.", "warning")
            return redirect(url_for("login.login_page"))
        if user.get("role") != "teacher":
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view


def student_required(view):
    """Ensure the logged-in user has the 'student' role."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = session.get("user")
        if not user:
            flash("Please log in to view your student dashboard.", "warning")
            return redirect(url_for("login.login_page"))
        if user.get("role") != "student":
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view
