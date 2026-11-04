"""Teacher routes for dashboard, student CRUD, marks management, and class analytics."""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    abort,
)
from app.config import SUBJECTS, VALID_SECTIONS, DEFAULT_CLASS, EXAMINATION_NAME, GRADING_MATRIX
from app.routes import teacher_required
from app.services.student_service import (
    get_all_students,
    get_student_by_id,
    search_and_filter_students,
    create_student,
    update_student,
    update_student_marks,
    delete_student,
    StudentValidationError,
)
from app.services.analytics_service import (
    calculate_dashboard_overview,
    calculate_section_analytics,
    calculate_all_sections_comparison,
)

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")


@teacher_bp.route("/dashboard", methods=["GET"])
@teacher_required
def dashboard():
    """Render Teacher Dashboard Overview with key statistics and recent student summary."""
    students_file = current_app.config["STUDENTS_FILE"]
    overview = calculate_dashboard_overview(students_file)
    students = get_all_students(students_file, include_results=True)
    sections_comparison = calculate_all_sections_comparison(students_file)

    return render_template(
        "teacher_dashboard.html",
        overview=overview,
        students=students,
        sections_comparison=sections_comparison,
        examination_name=EXAMINATION_NAME,
        active_page="dashboard",
    )


@teacher_bp.route("/students", methods=["GET"])
@teacher_required
def students_list():
    """Render Student Management page with search, section filter, and CRUD controls."""
    students_file = current_app.config["STUDENTS_FILE"]
    search_query = request.args.get("q", "").strip()
    section_filter = request.args.get("section", "").strip().upper()
    edit_id = request.args.get("edit", "").strip()

    students = search_and_filter_students(
        students_file,
        search_query=search_query if search_query else None,
        section_filter=section_filter if section_filter in VALID_SECTIONS else None,
    )

    edit_student = None
    if edit_id:
        edit_student = get_student_by_id(students_file, edit_id, include_results=True)

    return render_template(
        "students.html",
        students=students,
        subjects=SUBJECTS,
        sections=VALID_SECTIONS,
        search_query=search_query,
        section_filter=section_filter,
        edit_student=edit_student,
        active_page="students",
    )


@teacher_bp.route("/students/add", methods=["POST"])
@teacher_required
def add_student_route():
    """Handle creation of a new student record."""
    students_file = current_app.config["STUDENTS_FILE"]
    teachers_file = current_app.config["TEACHERS_FILE"]

    marks_input = {}
    for subj in SUBJECTS:
        field_key = f"mark_{subj}"
        marks_input[subj] = request.form.get(field_key, "")

    payload = {
        "student_id": request.form.get("student_id", "").strip(),
        "name": request.form.get("name", "").strip(),
        "username": request.form.get("username", "").strip(),
        "password": request.form.get("password", "").strip(),
        "class": request.form.get("class", DEFAULT_CLASS).strip() or DEFAULT_CLASS,
        "section": request.form.get("section", "").strip().upper(),
        "roll_number": request.form.get("roll_number", "").strip(),
        "marks": marks_input,
    }

    try:
        created = create_student(students_file, payload, teachers_file=teachers_file)
        flash(
            f"Student '{created['name']}' ({created['student_id']}) created successfully.",
            "success",
        )
    except StudentValidationError as exc:
        flash(f"Failed to create student: {exc}", "danger")

    return redirect(url_for("teacher.students_list"))


@teacher_bp.route("/students/<student_id>/edit", methods=["POST"])
@teacher_required
def edit_student_route(student_id: str):
    """Handle updating student personal information, section, credentials, and optionally marks."""
    students_file = current_app.config["STUDENTS_FILE"]
    teachers_file = current_app.config["TEACHERS_FILE"]

    existing = get_student_by_id(students_file, student_id, include_results=False)
    if not existing:
        flash(f"Student '{student_id}' not found.", "danger")
        return redirect(url_for("teacher.students_list"))

    marks_input = {}
    has_marks_in_form = any(f"mark_{subj}" in request.form for subj in SUBJECTS)
    if has_marks_in_form:
        for subj in SUBJECTS:
            marks_input[subj] = request.form.get(f"mark_{subj}", "")
    else:
        marks_input = existing["marks"]

    payload = {
        "student_id": existing["student_id"],
        "name": request.form.get("name", "").strip(),
        "username": request.form.get("username", "").strip(),
        "password": request.form.get("password", "").strip(),
        "class": request.form.get("class", DEFAULT_CLASS).strip() or DEFAULT_CLASS,
        "section": request.form.get("section", "").strip().upper(),
        "roll_number": request.form.get("roll_number", "").strip(),
        "marks": marks_input,
    }

    try:
        updated = update_student(students_file, student_id, payload, teachers_file=teachers_file)
        flash(
            f"Student '{updated['name']}' ({updated['student_id']}) updated successfully.",
            "success",
        )
    except StudentValidationError as exc:
        flash(f"Failed to update student: {exc}", "danger")
        return redirect(url_for("teacher.students_list", edit=student_id))

    return redirect(url_for("teacher.students_list"))


@teacher_bp.route("/students/<student_id>/delete", methods=["POST"])
@teacher_required
def delete_student_route(student_id: str):
    """Handle deleting a student record."""
    students_file = current_app.config["STUDENTS_FILE"]
    try:
        delete_student(students_file, student_id)
        flash(f"Student record '{student_id}' deleted permanently.", "success")
    except StudentValidationError as exc:
        flash(f"Failed to delete student: {exc}", "danger")

    return redirect(url_for("teacher.students_list"))


@teacher_bp.route("/students/<student_id>/result", methods=["GET"])
@teacher_required
def view_student_result(student_id: str):
    """Allow teacher to view a specific student's detailed result card."""
    students_file = current_app.config["STUDENTS_FILE"]
    student = get_student_by_id(students_file, student_id, include_results=True)
    if not student:
        abort(404)

    return render_template(
        "student_dashboard.html",
        student=student,
        result=student["result"],
        examination_name=EXAMINATION_NAME,
        grading_matrix=GRADING_MATRIX,
        show_popup=False,
        is_teacher_view=True,
        active_page="students",
    )


@teacher_bp.route("/marks", methods=["GET", "POST"])
@teacher_required
def marks_management():
    """Render Marks Management interface and handle marks entry/updates."""
    students_file = current_app.config["STUDENTS_FILE"]
    selected_id = request.args.get("student_id", "").strip()
    section_filter = request.args.get("section", "").strip().upper()

    if request.method == "POST":
        target_id = request.form.get("student_id", "").strip()
        marks_input = {subj: request.form.get(f"mark_{subj}", "") for subj in SUBJECTS}
        try:
            updated = update_student_marks(students_file, target_id, marks_input)
            flash(
                f"Marks updated for {updated['name']} ({updated['student_id']}) — "
                f"Total: {updated['result']['total_marks']}/600 "
                f"({updated['result']['formatted_percentage']}, {updated['result']['classification']}).",
                "success",
            )
            return redirect(url_for("teacher.marks_management", student_id=target_id))
        except StudentValidationError as exc:
            flash(f"Marks validation error: {exc}", "danger")
            selected_id = target_id

    students = search_and_filter_students(
        students_file,
        section_filter=section_filter if section_filter in VALID_SECTIONS else None,
    )

    selected_student = None
    if selected_id:
        selected_student = get_student_by_id(students_file, selected_id, include_results=True)
    elif students:
        selected_student = students[0]

    return render_template(
        "marks.html",
        students=students,
        selected_student=selected_student,
        subjects=SUBJECTS,
        sections=VALID_SECTIONS,
        section_filter=section_filter,
        grading_matrix=GRADING_MATRIX,
        active_page="marks",
    )


@teacher_bp.route("/analytics", methods=["GET"])
@teacher_required
def analytics():
    """Render Class Analytics for a selected section (A, B, C) and comparison across sections."""
    students_file = current_app.config["STUDENTS_FILE"]
    selected_section = request.args.get("section", "A").strip().upper()
    if selected_section not in VALID_SECTIONS:
        selected_section = "A"

    section_stats = calculate_section_analytics(students_file, selected_section)
    all_sections = calculate_all_sections_comparison(students_file)
    section_students = search_and_filter_students(students_file, section_filter=selected_section)

    return render_template(
        "analytics.html",
        selected_section=selected_section,
        sections=VALID_SECTIONS,
        section_stats=section_stats,
        all_sections=all_sections,
        section_students=section_students,
        subjects=SUBJECTS,
        active_page="analytics",
    )
