"""Blueprint registration."""
from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .student import bp as student_bp
    from .teacher import bp as teacher_bp
    from .provision import bp as provision_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(provision_bp)

