"""Teacher views: Dashboard, student listing, and marks management endpoints.

Enforces:
- Role-based authorization (@teacher_required).
- Strict assignment verification: Teachers can only view/edit students and subjects assigned to them.
- Access to unassigned students returns 404 (non-disclosure).
- Submitting marks for unassigned subjects returns 403 (atomic, nothing saved).
- Full audit logging into MarkAudit for every create, update, or clear action.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import select

from ..auth import teacher_required
from ..extensions import db
from ..models import Exam, ExamSubject, Mark, MarkAudit, Student, Subject, TeacherAssignment
from ..services.grading import SubjectResult, compute_result
from ..services.marks_service import ValidationError, parse_mark

bp = Blueprint("teacher", __name__)


@bp.get("/teacher/dashboard")
@teacher_required
def dashboard():
    """Teacher dashboard page (TC-AUTHZ-01)."""
    teacher = current_user.teacher
    exams = db.session.scalars(select(Exam).order_by(Exam.id.desc())).all()
    latest_exam = exams[0] if exams else None

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher,
        exams=exams,
        latest_exam=latest_exam,
    )


@bp.get("/api/teacher/students")
@teacher_required
def get_students():
    """Teacher students list API (TC-AUTHZ-01, TC-AUTHZ-10, TC-AUTHZ-12, TC-MARK-01).

    Returns assigned students with assigned subjects and computed result status.
    """
    teacher = current_user.teacher
    if not teacher:
        return jsonify({"error": {"code": "not_found", "message": "Teacher profile not found."}}), 404

    # Resolve examination
    exam_id_raw = request.args.get("exam_id")
    if exam_id_raw is not None:
        try:
            exam_id = int(exam_id_raw)
        except (ValueError, TypeError):
            return jsonify({"error": {"code": "bad_request", "message": "Invalid exam_id parameter."}}), 400
        exam = db.session.get(Exam, exam_id)
        if not exam:
            return jsonify({"error": {"code": "not_found", "message": "Exam not found."}}), 404
    else:
        exam = db.session.scalar(select(Exam).order_by(Exam.id.desc()))
        if not exam:
            return jsonify({"error": {"code": "not_found", "message": "No examinations found."}}), 404

    # Query all assignments for this teacher
    assignments = db.session.scalars(
        select(TeacherAssignment)
        .where(TeacherAssignment.teacher_id == teacher.id)
        .join(TeacherAssignment.subject)
        .order_by(Subject.code)
    ).all()

    if not assignments:
        return jsonify({
            "exam": {
                "id": exam.id,
                "name": exam.name,
                "academic_year": exam.academic_year,
            },
            "students": [],
        }), 200

    # Group assigned subject codes by student_id
    student_assigned_codes: dict[int, list[str]] = defaultdict(list)
    for a in assignments:
        student_assigned_codes[a.student_id].append(a.subject.code)

    student_ids = list(student_assigned_codes.keys())

    # Fetch students
    students = db.session.scalars(
        select(Student)
        .where(Student.id.in_(student_ids))
        .join(Student.section)
        .order_by(Student.section_id, Student.roll_number, Student.student_code)
    ).all()

    # Fetch exam subjects and existing marks to compute result status per student
    exam_subjects = db.session.scalars(
        select(ExamSubject)
        .where(ExamSubject.exam_id == exam.id)
        .join(ExamSubject.subject)
        .order_by(Subject.id)
    ).all()

    marks = db.session.scalars(
        select(Mark).where(
            Mark.student_id.in_(student_ids),
            Mark.exam_subject_id.in_([es.id for es in exam_subjects]),
        )
    ).all()

    marks_by_student_es: dict[tuple[int, int], Decimal | None] = {
        (m.student_id, m.exam_subject_id): m.marks_obtained for m in marks
    }

    students_data: list[dict[str, Any]] = []
    for s in students:
        entries = [
            SubjectResult(
                code=es.subject.code,
                name=es.subject.name,
                max_marks=es.max_marks,
                pass_marks=es.pass_marks,
                marks_obtained=marks_by_student_es.get((s.id, es.id)),
            )
            for es in exam_subjects
        ]
        summary = compute_result(entries)

        students_data.append({
            "id": s.id,
            "student_code": s.student_code,
            "full_name": s.full_name,
            "section": s.section.name,
            "roll_number": s.roll_number,
            "assigned_subjects": student_assigned_codes.get(s.id, []),
            "result_status": summary.status,
        })

    return jsonify({
        "exam": {
            "id": exam.id,
            "name": exam.name,
            "academic_year": exam.academic_year,
        },
        "students": students_data,
    }), 200


@bp.get("/api/teacher/students/<int:student_id>/marks")
@teacher_required
def get_student_marks(student_id: int):
    """Teacher view student marks API (TC-AUTHZ-04, TC-AUTHZ-05).

    Returns 404 non-disclosure if student does not exist or has no assignment to teacher.
    """
    teacher = current_user.teacher
    if not teacher:
        return jsonify({"error": {"code": "not_found", "message": "Teacher profile not found."}}), 404

    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": {"code": "not_found", "message": "Student not found or not assigned to you."}}), 404

    # Verify assignment (TC-AUTHZ-05: Non-disclosure)
    assignments = db.session.scalars(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.student_id == student.id,
        )
    ).all()
    if not assignments:
        return jsonify({"error": {"code": "not_found", "message": "Student not found or not assigned to you."}}), 404

    assigned_sub_ids = {a.subject_id for a in assignments}

    # Resolve examination
    exam_id_raw = request.args.get("exam_id")
    if exam_id_raw is not None:
        try:
            exam_id = int(exam_id_raw)
        except (ValueError, TypeError):
            return jsonify({"error": {"code": "bad_request", "message": "Invalid exam_id parameter."}}), 400
        exam = db.session.get(Exam, exam_id)
        if not exam:
            return jsonify({"error": {"code": "not_found", "message": "Exam not found."}}), 404
    else:
        exam = db.session.scalar(select(Exam).order_by(Exam.id.desc()))
        if not exam:
            return jsonify({"error": {"code": "not_found", "message": "No examinations found."}}), 404

    exam_subjects = db.session.scalars(
        select(ExamSubject)
        .where(ExamSubject.exam_id == exam.id)
        .join(ExamSubject.subject)
        .order_by(Subject.id)
    ).all()

    marks = db.session.scalars(
        select(Mark).where(
            Mark.student_id == student.id,
            Mark.exam_subject_id.in_([es.id for es in exam_subjects]),
        )
    ).all()
    marks_map = {m.exam_subject_id: m.marks_obtained for m in marks}

    entries = [
        SubjectResult(
            code=es.subject.code,
            name=es.subject.name,
            max_marks=es.max_marks,
            pass_marks=es.pass_marks,
            marks_obtained=marks_map.get(es.id),
        )
        for es in exam_subjects
    ]
    summary = compute_result(entries)

    subjects_data: list[dict[str, Any]] = []
    for es in exam_subjects:
        val = marks_map.get(es.id)
        subjects_data.append({
            "subject_id": es.subject.id,
            "code": es.subject.code,
            "name": es.subject.name,
            "max_marks": str(es.max_marks),
            "pass_marks": str(es.pass_marks),
            "marks_obtained": str(val) if val is not None else None,
            "editable": es.subject.id in assigned_sub_ids,
        })

    return jsonify({
        "student": {
            "id": student.id,
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
    }), 200


@bp.put("/api/teacher/students/<int:student_id>/marks")
@teacher_required
def update_student_marks(student_id: int):
    """Teacher update student marks API (TC-AUTHZ-06, TC-AUTHZ-07, TC-AUTHZ-08, TC-AUTHZ-09, TC-MARK-*).

    Validates schema, strict assignments, subject marks, and writes atomic DB updates & MarkAudit logs.
    """
    teacher = current_user.teacher
    if not teacher:
        return jsonify({"error": {"code": "not_found", "message": "Teacher profile not found."}}), 404

    if not request.is_json:
        return jsonify({"error": {"code": "bad_request", "message": "Expected JSON payload."}}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": {"code": "validation_error", "message": "Request body must be a JSON object."}}), 422

    # TC-AUTHZ-09: Body must contain strictly {"exam_id", "marks"}
    allowed_keys = {"exam_id", "marks"}
    extra_keys = set(data.keys()) - allowed_keys
    if extra_keys:
        return jsonify({
            "error": {
                "code": "validation_error",
                "message": f"Unexpected keys in request body: {', '.join(sorted(extra_keys))}.",
                "details": {"unknown_keys": sorted(list(extra_keys))},
            }
        }), 422

    if "exam_id" not in data or "marks" not in data:
        return jsonify({
            "error": {
                "code": "validation_error",
                "message": "Both 'exam_id' and 'marks' are required.",
            }
        }), 422

    raw_exam_id = data["exam_id"]
    # TC-MARK-05: exam_id must be integer, not string or bool
    if not isinstance(raw_exam_id, int) or isinstance(raw_exam_id, bool):
        return jsonify({"error": {"code": "validation_error", "message": "'exam_id' must be an integer."}}), 422

    exam = db.session.get(Exam, raw_exam_id)
    if not exam:
        # TC-MARK-05: Unknown exam returns 422
        return jsonify({"error": {"code": "validation_error", "message": f"Unknown examination ID {raw_exam_id}."}}), 422

    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": {"code": "not_found", "message": "Student not found or not assigned to you."}}), 404

    # Verify teacher is assigned to student for at least one subject
    teacher_assignments = db.session.scalars(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.student_id == student.id,
        )
    ).all()
    if not teacher_assignments:
        # TC-AUTHZ-07: Teacher edits unassigned student -> 404
        return jsonify({"error": {"code": "not_found", "message": "Student not found or not assigned to you."}}), 404

    assigned_sub_ids = {a.subject_id for a in teacher_assignments}

    marks_list = data["marks"]
    # TC-MARK-10: marks must be a non-empty list of at most 20 items
    if not isinstance(marks_list, list) or len(marks_list) == 0 or len(marks_list) > 20:
        return jsonify({
            "error": {
                "code": "validation_error",
                "message": "'marks' must be a non-empty array with at most 20 items.",
            }
        }), 422

    seen_sub_ids: set[int] = set()
    for idx, item in enumerate(marks_list):
        if not isinstance(item, dict):
            return jsonify({
                "error": {"code": "validation_error", "message": f"Item at index {idx} must be a JSON object."}
            }), 422
        if set(item.keys()) - {"subject_id", "marks_obtained"}:
            return jsonify({
                "error": {"code": "validation_error", "message": f"Unexpected keys in marks item at index {idx}."}
            }), 422
        if "subject_id" not in item:
            return jsonify({
                "error": {"code": "validation_error", "message": f"Missing 'subject_id' at index {idx}."}
            }), 422
        sub_id = item["subject_id"]
        if not isinstance(sub_id, int) or isinstance(sub_id, bool):
            return jsonify({
                "error": {"code": "validation_error", "message": f"Invalid 'subject_id' at index {idx}."}
            }), 422
        if sub_id in seen_sub_ids:
            # TC-MARK-09: Duplicate subject in request
            return jsonify({
                "error": {"code": "validation_error", "message": f"Duplicate subject_id {sub_id} in request."}
            }), 422
        seen_sub_ids.add(sub_id)

    # Fetch all subjects for this exam
    exam_subjects = db.session.scalars(
        select(ExamSubject)
        .where(ExamSubject.exam_id == exam.id)
        .join(ExamSubject.subject)
        .order_by(Subject.id)
    ).all()
    es_by_sub_id = {es.subject_id: es for es in exam_subjects}

    # TC-MARK-06: Unknown subject or subject not in exam -> 422
    for item in marks_list:
        sub_id = item["subject_id"]
        if sub_id not in es_by_sub_id:
            return jsonify({
                "error": {
                    "code": "validation_error",
                    "message": f"Subject ID {sub_id} is not part of examination {exam.id}.",
                }
            }), 422

    # TC-AUTHZ-08: Every subject must be assigned to this teacher for this student -> else 403 (nothing saved)
    for item in marks_list:
        sub_id = item["subject_id"]
        if sub_id not in assigned_sub_ids:
            return jsonify({
                "error": {
                    "code": "forbidden",
                    "message": f"You are not assigned to edit marks for subject ID {sub_id} for this student.",
                }
            }), 403

    # Parse and validate each mark value
    parsed_values: dict[int, Decimal | None] = {}
    field_errors: dict[str, str] = {}
    for item in marks_list:
        sub_id = item["subject_id"]
        es = es_by_sub_id[sub_id]
        raw_val = item.get("marks_obtained")
        try:
            parsed_val = parse_mark(raw_val, max_marks=es.max_marks)
            parsed_values[sub_id] = parsed_val
        except (ValidationError, ValueError) as exc:
            field_errors[es.subject.code] = getattr(exc, "message", str(exc))

    if field_errors:
        return jsonify({
            "error": {
                "code": "validation_error",
                "message": "Marks validation failed.",
                "details": {"fields": field_errors},
            }
        }), 422

    # TC-DB-06 & TC-MARK-08: Atomic database transaction with audit logging
    try:
        for sub_id, new_val in parsed_values.items():
            es = es_by_sub_id[sub_id]
            mark = db.session.scalar(
                select(Mark).where(
                    Mark.student_id == student.id,
                    Mark.exam_subject_id == es.id,
                )
            )

            if mark is None:
                mark = Mark(
                    student_id=student.id,
                    exam_subject_id=es.id,
                    marks_obtained=new_val,
                    updated_by=current_user.id,
                )
                db.session.add(mark)
                db.session.flush()

                action = "clear" if new_val is None else "create"
                audit = MarkAudit(
                    mark_id=mark.id,
                    action=action,
                    old_value=None,
                    new_value=new_val,
                    changed_by=current_user.id,
                )
                db.session.add(audit)
            else:
                old_val = mark.marks_obtained
                if old_val != new_val:
                    if new_val is None:
                        action = "clear"
                    elif old_val is None:
                        action = "create"
                    else:
                        action = "update"

                    mark.marks_obtained = new_val
                    mark.updated_by = current_user.id
                    audit = MarkAudit(
                        mark_id=mark.id,
                        action=action,
                        old_value=old_val,
                        new_value=new_val,
                        changed_by=current_user.id,
                    )
                    db.session.add(audit)

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # Recompute result summary
    all_marks = db.session.scalars(
        select(Mark).where(
            Mark.student_id == student.id,
            Mark.exam_subject_id.in_([es.id for es in exam_subjects]),
        )
    ).all()
    all_marks_map = {m.exam_subject_id: m.marks_obtained for m in all_marks}

    entries = [
        SubjectResult(
            code=es.subject.code,
            name=es.subject.name,
            max_marks=es.max_marks,
            pass_marks=es.pass_marks,
            marks_obtained=all_marks_map.get(es.id),
        )
        for es in exam_subjects
    ]
    summary = compute_result(entries)

    subjects_data: list[dict[str, Any]] = []
    for es in exam_subjects:
        val = all_marks_map.get(es.id)
        subjects_data.append({
            "subject_id": es.subject.id,
            "code": es.subject.code,
            "name": es.subject.name,
            "max_marks": str(es.max_marks),
            "pass_marks": str(es.pass_marks),
            "marks_obtained": str(val) if val is not None else None,
            "editable": es.subject.id in assigned_sub_ids,
        })

    return jsonify({
        "message": "Marks saved.",
        "saved": len(parsed_values),
        "subjects": subjects_data,
        "summary": {
            "status": summary.status,
            "total_obtained": str(summary.total_obtained) if summary.total_obtained is not None else None,
            "total_max": str(summary.total_max),
            "percentage": str(summary.percentage) if summary.percentage is not None else None,
            "grade": summary.grade,
        },
    }), 200
