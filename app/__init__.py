"""Student Result Management System — application factory.

Fictional 10th Standard result portal for an STQA laboratory. Demonstration data only.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Mapping

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import ConfigError, build_config, validate_config
from .extensions import csrf, db, login_manager, migrate

__all__ = ["create_app", "ConfigError"]

CSP = (
    "default-src 'self'; "
    "script-src 'self' https://challenges.cloudflare.com; "
    "frame-src https://challenges.cloudflare.com; "
    "connect-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


def _load_dotenv_if_appropriate() -> None:
    """Load a local .env file for development convenience (never in production)."""
    if os.environ.get("APP_ENV", "development").lower() == "production":
        return
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency
        return
    load_dotenv(override=False)


def create_app(
    overrides: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
) -> Flask:
    """Create and configure the Flask app.

    :param overrides: config values applied after env parsing (used by tests).
    :param env: environment mapping; defaults to ``os.environ`` (+ optional .env).
    """
    if env is None:
        _load_dotenv_if_appropriate()
        env = os.environ

    cfg = build_config(env)
    if overrides:
        cfg.update(overrides)
    validate_config(cfg)

    app = Flask(__name__)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(cfg)

    _configure_logging(app)

    if app.config["APP_ENV"] == "production":
        # Render terminates TLS at its proxy and forwards X-Forwarded-For / -Proto.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

    db.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations"))
    csrf.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            from .models import User
            if hasattr(User, "query"):
                return db.session.get(User, int(user_id))
        except Exception:
            pass
        return None

    from . import models  # noqa: F401  (register models with SQLAlchemy metadata)
    from .views import register_blueprints

    register_blueprints(app)
    _register_security_headers(app)

    from .errors import register_error_handlers

    register_error_handlers(app)

    from .cli import register_cli

    register_cli(app)
    return app


def _configure_logging(app: Flask) -> None:
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)
    app.logger.setLevel(level)
    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        app.logger.addHandler(handler)


def _register_security_headers(app: Flask) -> None:
    is_prod = app.config["APP_ENV"] == "production"

    @app.after_request
    def set_headers(response):  # type: ignore[no-untyped-def]
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if is_prod:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        from flask_login import current_user

        if getattr(current_user, "is_authenticated", False):
            response.headers["Cache-Control"] = "no-store"
        return response
