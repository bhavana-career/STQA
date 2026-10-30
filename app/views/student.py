"""Student views: Dashboard and examination result APIs.

Enforces:
- Student-only role authorization (@student_required).
- Strict isolation: Students can ONLY access their own result.
- Client student_id/student_code parameters are ignored.
- Server-side calculation using app.services.grading.compute_result.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import select

from ..auth import student_required
from ..extensions import db
from ..models import Exam, ExamSubject, Mark, Student, Subject
from ..services.grading import SubjectResult, compute_result

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.get("/dashboard")
@student_required
def dashboard():
    """Student dashboard page showing student profile, available exams, and result modal."""
    student = current_user.student
    if not student:
        return render_template("error.html", status=404, message="Student profile not found."), 404

    exams = db.session.scalars(select(Exam).order_by(Exam.id.desc())).all()
    latest_exam = exams[0] if exams else None

    return render_template(
        "student/dashboard.html",
        student=student,
        exams=exams,
        latest_exam=latest_exam,
    )


@bp.get("/result")
@bp.get("/api/result")
@student_required
def get_result():
    """Student result API endpoint.

    Accessible via:
    - /student/result (HTML page or JSON)
    - /student/api/result (JSON)
    - /api/student/result (registered via main or URL prefix)
    """
    return _build_student_result_response()


def _build_student_result_response():
    """Compute and return result strictly for the authenticated student."""
    student = current_user.student
    if not student:
        return (
            jsonify({"error": {"code": "not_found", "message": "Student profile not found."}}),
            404,
        )

    # TC-AUTHZ-03: Ignore any student_id / student_code parameter submitted by the client!
    exam_id_raw = request.args.get("exam_id")
    if exam_id_raw:
        try:
            exam_id = int(exam_id_raw)
        except (ValueError, TypeError):
            return (
                jsonify({"error": {"code": "bad_request", "message": "Invalid exam_id parameter."}}),
                400,
            )
        exam = db.session.get(Exam, exam_id)
        if not exam:
            return (
                jsonify({"error": {"code": "not_found", "message": "Exam not found."}}),
                404,
            )
    else:
        exam = db.session.scalar(select(Exam).order_by(Exam.id.desc()))
        if not exam:
            return (
                jsonify({"error": {"code": "not_found", "message": "No examinations found."}}),
                404,
            )

    # Fetch all subjects configured for this examination
    exam_subjects = db.session.scalars(
        select(ExamSubject)
        .where(ExamSubject.exam_id == exam.id)
        .join(ExamSubject.subject)
        .order_by(Subject.id)
    ).all()

    if not exam_subjects:
        return (
            jsonify(
                {
                    "error": {
                        "code": "not_found",
                        "message": f"No subjects configured for exam '{exam.name}'.",
                    }
                }
            ),
            404,
        )

    # Fetch marks obtained by this student for this exam
    es_ids = [es.id for es in exam_subjects]
    marks = db.session.scalars(
        select(Mark).where(
            Mark.student_id == student.id,
            Mark.exam_subject_id.in_(es_ids),
        )
    ).all()
    marks_by_es_id: dict[int, Decimal | None] = {m.exam_subject_id: m.marks_obtained for m in marks}

    # Prepare input for compute_result()
    entries: list[SubjectResult] = []
    for es in exam_subjects:
        val = marks_by_es_id.get(es.id)
        entries.append(
            SubjectResult(
                code=es.subject.code,
                name=es.subject.name,
                max_marks=es.max_marks,
                pass_marks=es.pass_marks,
                marks_obtained=val,
            )
        )

    # Server-side pure result calculation
    summary = compute_result(entries)

    # Build subjects response list
    subjects_data: list[dict[str, Any]] = []
    for sub in summary.subjects:
        subjects_data.append(
            {
                "code": sub.code,
                "name": sub.name,
                "marks_obtained": str(sub.marks_obtained) if sub.marks_obtained is not None else None,
                "max_marks": str(sub.max_marks),
                "pass_marks": str(sub.pass_marks),
                "percentage": str(sub.percentage) if sub.percentage is not None else None,
                "grade": sub.grade,
                "passed": sub.passed,
            }
        )

    # Format JSON payload matching docs/api-design.md
    payload = {
        "demo_data": True,
        "student": {
            "student_code": student.student_code,
            "full_name": student.full_name,
            "class_name": student.section.class_name,
            "section": student.section.name,
            "roll_number": student.roll_number,
        },
        "exam": {
            "id": exam.id,
            "name": exam.name,
            "academic_year": exam.academic_year,
        },
        "subjects": subjects_data,
        "summary": {
            "status": summary.status,
            "total_obtained": str(summary.total_obtained) if summary.total_obtained is not None else None,
            "total_max": str(summary.total_max),
            "percentage": str(summary.percentage) if summary.percentage is not None else None,
            "grade": summary.grade,
        },
    }

    return jsonify(payload), 200
