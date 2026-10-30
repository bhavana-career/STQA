"""Blueprint registration."""
from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
