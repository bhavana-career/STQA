"""Public routes: landing page and health check."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template
from sqlalchemy import text

from ..extensions import csrf, db

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/health")
@csrf.exempt
def health():
    """Liveness + database readiness. Never exposes exception details."""
    version = current_app.config.get("APP_VERSION", "dev")
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok", database="ok", version=version), 200
    except Exception:  # noqa: BLE001 - any DB failure means "degraded"
        db.session.rollback()
        current_app.logger.exception("Health check: database unreachable")
        return jsonify(status="degraded", database="error", version=version), 503


@bp.get("/api/student/result")
def api_student_result():
    """Proxy route to student result API matching docs/api-design.md."""
    from ..auth import student_required
    from .student import _build_student_result_response

    @student_required
    def _handler():
        return _build_student_result_response()

    return _handler()
