"""Student views: Dashboard and result endpoints."""
from __future__ import annotations

from flask import Blueprint, render_template
from ..auth import student_required

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.get("/dashboard")
@student_required
def dashboard():
    """Student dashboard page (TC-AUTHZ-01)."""
    return render_template("student/dashboard.html")
