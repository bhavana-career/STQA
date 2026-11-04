"""Login and session management routes for SRMS."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.services.student_service import authenticate_user

login_bp = Blueprint("login", __name__)


@login_bp.route("/", methods=["GET"])
def index():
    """Redirect root URL to appropriate dashboard if logged in, otherwise login page."""
    user = session.get("user")
    if user:
        if user.get("role") == "teacher":
            return redirect(url_for("teacher.dashboard"))
        if user.get("role") == "student":
            return redirect(url_for("student.dashboard"))
    return redirect(url_for("login.login_page"))


@login_bp.route("/login", methods=["GET", "POST"])
def login_page():
    """Render login form and authenticate predefined Teacher or Student credentials."""
    user = session.get("user")
    if request.method == "GET" and user:
        if user.get("role") == "teacher":
            return redirect(url_for("teacher.dashboard"))
        if user.get("role") == "student":
            return redirect(url_for("student.dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Both username and password are required."
        else:
            auth_user = authenticate_user(
                username=username,
                password=password,
                students_file=current_app.config["STUDENTS_FILE"],
                teachers_file=current_app.config["TEACHERS_FILE"],
            )
            if auth_user is None:
                error = "Invalid username or password. Please verify your assigned credentials."
            else:
                session.clear()
                session["user"] = auth_user
                session["popup_shown"] = False
                if auth_user["role"] == "teacher":
                    flash(f"Welcome back, {auth_user['name']}!", "success")
                    return redirect(url_for("teacher.dashboard"))
                flash(f"Welcome, {auth_user['name']}!", "success")
                return redirect(url_for("student.dashboard"))

    return render_template("login.html", error=error), (401 if error else 200)


@login_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Clear current user session and return to login page."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login.login_page"))
