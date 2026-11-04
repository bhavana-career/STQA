"""Student routes for viewing personal dashboard, examination result, and grading matrix."""

from flask import Blueprint, render_template, session, current_app, abort
from app.config import EXAMINATION_NAME, GRADING_MATRIX
from app.routes import student_required
from app.services.student_service import get_student_by_id
from app.services.result_service import evaluate_student_result, should_show_success_popup

student_bp = Blueprint("student", __name__, url_prefix="/student")


def _get_logged_in_student():
    """Retrieve the current logged-in student's record from JSON storage."""
    user = session.get("user", {})
    student_id = user.get("student_id")
    students_file = current_app.config["STUDENTS_FILE"]
    student = get_student_by_id(students_file, student_id, include_results=True)
    if not student:
        abort(404)
    return student


@student_bp.route("/dashboard", methods=["GET"])
@student_required
def dashboard():
    """
    Render Student Dashboard showing personal details, 6 subject marks & grades,
    total out of 600, percentage, overall classification, pass/fail status,
    grading matrix, and one-time celebratory popup for passing students.
    """
    student = _get_logged_in_student()
    result_obj = evaluate_student_result(student["marks"])

    popup_already_shown = bool(session.get("popup_shown", False))
    show_popup = should_show_success_popup(result_obj, popup_already_shown=popup_already_shown)
    if show_popup:
        session["popup_shown"] = True

    return render_template(
        "student_dashboard.html",
        student=student,
        result=student["result"],
        examination_name=EXAMINATION_NAME,
        grading_matrix=GRADING_MATRIX,
        show_popup=show_popup,
        is_teacher_view=False,
        active_page="student_dashboard",
    )


@student_bp.route("/results", methods=["GET"])
@student_required
def my_results():
    """Render My Results section on the student dashboard without repeating the popup."""
    student = _get_logged_in_student()
    return render_template(
        "student_dashboard.html",
        student=student,
        result=student["result"],
        examination_name=EXAMINATION_NAME,
        grading_matrix=GRADING_MATRIX,
        show_popup=False,
        is_teacher_view=False,
        active_page="my_results",
    )


@student_bp.route("/grading-matrix", methods=["GET"])
@student_required
def grading_matrix_view():
    """Render Grading Matrix view on the student dashboard without repeating the popup."""
    student = _get_logged_in_student()
    return render_template(
        "student_dashboard.html",
        student=student,
        result=student["result"],
        examination_name=EXAMINATION_NAME,
        grading_matrix=GRADING_MATRIX,
        show_popup=False,
        is_teacher_view=False,
        active_page="grading_matrix",
    )


@student_bp.route("/view/<target_student_id>", methods=["GET"])
@student_required
def view_specific_student(target_student_id: str):
    """
    Enforce student isolation: a student can ONLY access their own student_id.
    Attempting to view any other student's ID returns 403 Forbidden.
    """
    user = session.get("user", {})
    own_id = str(user.get("student_id", "")).strip().lower()
    if target_student_id.strip().lower() != own_id:
        abort(403)
    return dashboard()
