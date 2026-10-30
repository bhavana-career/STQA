"""Application configuration.

Configuration is built from environment variables by :func:`build_config` and then
checked by :func:`validate_config`. Validation contains the *safety interlocks*
described in docs/architecture.md §4.3 — e.g. production refuses to start with
CAPTCHA test keys, the mock CAPTCHA verifier, debug mode or a weak SECRET_KEY.
"""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Mapping

VALID_ENVS = ("development", "testing", "production")
VALID_CAPTCHA_MODES = ("turnstile", "mock")

# Cloudflare Turnstile documented test keys look like "1x00000000000000000000AA",
# "2x00000000000000000000AB", "3x0000000000000000000000000000000AA", ...
TURNSTILE_TEST_KEY_RE = re.compile(r"^[123]x0{10,}[A-Za-z0-9]{2}$")
# The dummy token produced by Turnstile test site keys.
TURNSTILE_DUMMY_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"

MIN_PRODUCTION_SECRET_LENGTH = 32


class ConfigError(RuntimeError):
    """Raised when the configuration is unsafe or incomplete."""


def normalize_database_url(url: str | None) -> str | None:
    """Force the psycopg (v3) SQLAlchemy driver for plain postgres URLs.

    Hosting providers (Neon, Render) hand out ``postgres://`` or ``postgresql://`` URLs.
    """
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer") from exc


def _csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip().lower() for part in value.split(",") if part.strip())


def build_config(env: Mapping[str, str]) -> dict[str, Any]:
    """Translate environment variables into a Flask config dict (no validation)."""
    app_env = (env.get("APP_ENV") or "development").strip().lower()
    is_prod = app_env == "production"
    session_minutes = _int(env, "SESSION_LIFETIME_MINUTES", 30)

    return {
        "APP_ENV": app_env,
        "DEBUG": app_env == "development" and env.get("FLASK_DEBUG", "0") == "1",
        "TESTING": app_env == "testing",
        "SECRET_KEY": env.get("SECRET_KEY") or "",
        "SQLALCHEMY_DATABASE_URI": normalize_database_url(env.get("DATABASE_URL")),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "pool_recycle": 280},
        # Sessions / cookies
        "SESSION_COOKIE_NAME": "srms_session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": is_prod,
        "REMEMBER_COOKIE_SECURE": is_prod,
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=session_minutes),
        "SESSION_REFRESH_EACH_REQUEST": True,
        "PREFERRED_URL_SCHEME": "https" if is_prod else "http",
        # CSRF
        "WTF_CSRF_ENABLED": True,
        "WTF_CSRF_TIME_LIMIT": None,  # token valid for the session lifetime
        # Login policy
        "LOGIN_MAX_ATTEMPTS": _int(env, "LOGIN_MAX_ATTEMPTS", 5),
        "LOGIN_LOCKOUT_MINUTES": _int(env, "LOGIN_LOCKOUT_MINUTES", 15),
        # CAPTCHA
        "CAPTCHA_MODE": (env.get("CAPTCHA_MODE") or "turnstile").strip().lower(),
        "TURNSTILE_SITE_KEY": (env.get("TURNSTILE_SITE_KEY") or "").strip(),
        "TURNSTILE_SECRET_KEY": (env.get("TURNSTILE_SECRET_KEY") or "").strip(),
        "TURNSTILE_ALLOWED_HOSTNAMES": _csv(env.get("TURNSTILE_ALLOWED_HOSTNAMES")),
        "TURNSTILE_VERIFY_URL": "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        "TURNSTILE_TIMEOUT_SECONDS": 5,
        "TURNSTILE_EXPECTED_ACTION": "login",
        # Misc
        "LOG_LEVEL": (env.get("LOG_LEVEL") or "INFO").upper(),
        "APP_VERSION": env.get("RENDER_GIT_COMMIT", "")[:7] or env.get("APP_VERSION", "dev"),
        "JSON_SORT_KEYS": False,
    }


def is_turnstile_test_key(value: str) -> bool:
    return bool(TURNSTILE_TEST_KEY_RE.match(value or ""))


def validate_config(cfg: Mapping[str, Any]) -> None:
    """Raise :class:`ConfigError` if the configuration is unsafe."""
    app_env = cfg.get("APP_ENV")
    if app_env not in VALID_ENVS:
        raise ConfigError(f"APP_ENV must be one of {VALID_ENVS}, got {app_env!r}")

    mode = cfg.get("CAPTCHA_MODE")
    if mode not in VALID_CAPTCHA_MODES:
        raise ConfigError(f"CAPTCHA_MODE must be one of {VALID_CAPTCHA_MODES}, got {mode!r}")
    if mode == "mock" and app_env != "testing":
        raise ConfigError("CAPTCHA_MODE=mock is only allowed when APP_ENV=testing")

    if not cfg.get("SQLALCHEMY_DATABASE_URI"):
        raise ConfigError("DATABASE_URL is required")

    secret = cfg.get("SECRET_KEY") or ""
    if not secret:
        raise ConfigError("SECRET_KEY is required")

    if mode == "turnstile":
        if not cfg.get("TURNSTILE_SITE_KEY") or not cfg.get("TURNSTILE_SECRET_KEY"):
            raise ConfigError("TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY are required")

    if app_env == "production":
        if cfg.get("DEBUG"):
            raise ConfigError("DEBUG must be disabled in production")
        if len(secret) < MIN_PRODUCTION_SECRET_LENGTH or secret.startswith("change-me"):
            raise ConfigError(
                f"SECRET_KEY must be a random value of at least {MIN_PRODUCTION_SECRET_LENGTH} characters"
            )
        if is_turnstile_test_key(cfg.get("TURNSTILE_SITE_KEY", "")) or is_turnstile_test_key(
            cfg.get("TURNSTILE_SECRET_KEY", "")
        ):
            raise ConfigError("Cloudflare Turnstile TEST keys are not allowed in production")
        if not cfg.get("TURNSTILE_ALLOWED_HOSTNAMES"):
            raise ConfigError("TURNSTILE_ALLOWED_HOSTNAMES is required in production")
        if not cfg.get("SESSION_COOKIE_SECURE"):
            raise ConfigError("SESSION_COOKIE_SECURE must be enabled in production")
