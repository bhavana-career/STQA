"""Flask application factory for the Student Result Management System (SRMS)."""

from typing import Optional, Dict, Any
from flask import Flask, render_template
from app.config import Config
from app.routes.login import login_bp
from app.routes.teacher import teacher_bp
from app.routes.student import student_bp


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure the SRMS Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Register blueprints
    app.register_blueprint(login_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return (
            render_template(
                "error.html",
                error_code=403,
                error_title="Access Denied (403 Forbidden)",
                error_message="You do not have permission to access this resource or view another user's records.",
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found_error(error):
        return (
            render_template(
                "error.html",
                error_code=404,
                error_title="Resource Not Found (404)",
                error_message="The requested student record or page could not be found.",
            ),
            404,
        )

    return app
