"""Teacher views: Dashboard and marks management endpoints."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template
from ..auth import teacher_required

bp = Blueprint("teacher", __name__)


@bp.get("/teacher/dashboard")
@teacher_required
def dashboard():
    """Teacher dashboard page (TC-AUTHZ-01)."""
    return render_template("teacher/dashboard.html")


@bp.get("/api/teacher/students")
@teacher_required
def get_students():
    """Teacher students list API (TC-AUTHZ-01, TC-AUTHZ-10)."""
    return jsonify({"students": []}), 200


@bp.get("/api/teacher/students/<int:student_id>/marks")
@teacher_required
def get_student_marks(student_id: int):
    """Teacher view student marks API (TC-AUTHZ-04)."""
    return jsonify({"student_id": student_id, "marks": []}), 200


@bp.put("/api/teacher/students/<int:student_id>/marks")
@teacher_required
def update_student_marks(student_id: int):
    """Teacher update student marks API (TC-AUTHZ-02)."""
    return jsonify({"message": "Marks saved.", "student_id": student_id}), 200
