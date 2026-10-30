"""Unit tests for configuration parsing, validation, and safety interlocks."""
from __future__ import annotations

import pytest

from app.config import (
    ConfigError,
    build_config,
    is_turnstile_test_key,
    normalize_database_url,
    validate_config,
)


@pytest.mark.unit
class TestDatabaseUrlNormalization:
    """Tests for database URL driver normalization."""

    def test_postgres_url_converted_to_psycopg(self):
        url = "postgres://user:pass@host:5432/db"
        assert normalize_database_url(url) == "postgresql+psycopg://user:pass@host:5432/db"

    def test_postgresql_url_converted_to_psycopg(self):
        url = "postgresql://user:pass@host:5432/db"
        assert normalize_database_url(url) == "postgresql+psycopg://user:pass@host:5432/db"

    def test_postgresql_psycopg2_url_converted_to_psycopg(self):
        url = "postgresql+psycopg2://user:pass@host:5432/db"
        assert normalize_database_url(url) == "postgresql+psycopg://user:pass@host:5432/db"

    def test_sqlite_url_preserved(self):
        url = "sqlite:///:memory:"
        assert normalize_database_url(url) == "sqlite:///:memory:"

    def test_empty_or_none_url_handled(self):
        assert normalize_database_url(None) is None
        assert normalize_database_url("") == ""


@pytest.mark.unit
class TestTurnstileTestKeyDetection:
    """Tests for detecting official Cloudflare Turnstile test keys."""

    def test_official_test_site_keys_detected(self):
        assert is_turnstile_test_key("1x00000000000000000000AA") is True
        assert is_turnstile_test_key("2x00000000000000000000AB") is True
        assert is_turnstile_test_key("3x00000000000000000000FF") is True

    def test_official_test_secret_keys_detected(self):
        assert is_turnstile_test_key("1x0000000000000000000000000000000AA") is True
        assert is_turnstile_test_key("2x0000000000000000000000000000000AA") is True
        assert is_turnstile_test_key("3x0000000000000000000000000000000AA") is True

    def test_production_format_keys_not_flagged_as_test_keys(self):
        assert is_turnstile_test_key("0x4AAAAAAAxRealSiteKey999") is False
        assert is_turnstile_test_key("0x4AAAAAAAxRealSecretKey123456789") is False
        assert is_turnstile_test_key("") is False


@pytest.mark.unit
class TestConfigValidation:
    """Tests for environment validation and security interlocks."""

    def test_invalid_app_env_rejected(self):
        cfg = build_config({"APP_ENV": "staging"})
        with pytest.raises(ConfigError, match="APP_ENV must be one of"):
            validate_config(cfg)

    def test_invalid_captcha_mode_rejected(self):
        cfg = build_config({"CAPTCHA_MODE": "recaptcha"})
        with pytest.raises(ConfigError, match="CAPTCHA_MODE must be one of"):
            validate_config(cfg)

    def test_mock_captcha_rejected_in_development(self):
        cfg = build_config({
            "APP_ENV": "development",
            "CAPTCHA_MODE": "mock",
            "SECRET_KEY": "dev-secret-key",
            "DATABASE_URL": "sqlite:///:memory:",
        })
        with pytest.raises(ConfigError, match="CAPTCHA_MODE=mock is only allowed when APP_ENV=testing"):
            validate_config(cfg)

    def test_mock_captcha_rejected_in_production(self):
        cfg = build_config({
            "APP_ENV": "production",
            "CAPTCHA_MODE": "mock",
            "SECRET_KEY": "a" * 32,
            "DATABASE_URL": "postgresql://u:p@h/db",
            "TURNSTILE_ALLOWED_HOSTNAMES": "app.onrender.com",
        })
        with pytest.raises(ConfigError, match="CAPTCHA_MODE=mock is only allowed when APP_ENV=testing"):
            validate_config(cfg)

    def test_missing_database_url_rejected(self):
        cfg = build_config({
            "APP_ENV": "development",
            "SECRET_KEY": "dev-secret",
            "DATABASE_URL": "",
            "TURNSTILE_SITE_KEY": "1x00000000000000000000AA",
            "TURNSTILE_SECRET_KEY": "1x0000000000000000000000000000000AA",
        })
        with pytest.raises(ConfigError, match="DATABASE_URL is required"):
            validate_config(cfg)

    def test_missing_secret_key_rejected(self):
        cfg = build_config({
            "APP_ENV": "development",
            "DATABASE_URL": "sqlite:///:memory:",
            "SECRET_KEY": "",
            "TURNSTILE_SITE_KEY": "1x00000000000000000000AA",
            "TURNSTILE_SECRET_KEY": "1x0000000000000000000000000000000AA",
        })
        with pytest.raises(ConfigError, match="SECRET_KEY is required"):
            validate_config(cfg)

    def test_turnstile_mode_requires_site_and_secret_keys(self):
        cfg = build_config({
            "APP_ENV": "development",
            "DATABASE_URL": "sqlite:///:memory:",
            "SECRET_KEY": "dev-secret",
            "CAPTCHA_MODE": "turnstile",
            "TURNSTILE_SITE_KEY": "",
            "TURNSTILE_SECRET_KEY": "",
        })
        with pytest.raises(ConfigError, match="TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY are required"):
            validate_config(cfg)


@pytest.mark.unit
class TestProductionConfigSafetyInterlocks:
    """Tests for mandatory production-only security safeguards."""

    @pytest.fixture
    def valid_prod_env(self) -> dict[str, str]:
        return {
            "APP_ENV": "production",
            "SECRET_KEY": "super-strong-production-secret-token-random-length",
            "DATABASE_URL": "postgresql://prod_user:prod_pw@neon.tech/srms",
            "CAPTCHA_MODE": "turnstile",
            "TURNSTILE_SITE_KEY": "0x4AAAAAAAxRealSiteKeyProd",
            "TURNSTILE_SECRET_KEY": "0x4AAAAAAAxRealSecretKeyProd12345",
            "TURNSTILE_ALLOWED_HOSTNAMES": "srms-stqa.onrender.com",
            "FLASK_DEBUG": "0",
        }

    def test_valid_production_config_passes(self, valid_prod_env):
        cfg = build_config(valid_prod_env)
        validate_config(cfg)
        assert cfg["APP_ENV"] == "production"
        assert cfg["DEBUG"] is False
        assert cfg["SESSION_COOKIE_SECURE"] is True

    def test_production_rejects_debug_mode(self, valid_prod_env):
        cfg = build_config(valid_prod_env)
        cfg["DEBUG"] = True
        with pytest.raises(ConfigError, match="DEBUG must be disabled in production"):
            validate_config(cfg)

    def test_production_rejects_short_secret(self, valid_prod_env):
        valid_prod_env["SECRET_KEY"] = "too-short-key"
        cfg = build_config(valid_prod_env)
        with pytest.raises(ConfigError, match="SECRET_KEY must be a random value of at least 32 characters"):
            validate_config(cfg)

    def test_production_rejects_placeholder_secret(self, valid_prod_env):
        valid_prod_env["SECRET_KEY"] = "change-me-to-a-long-random-string-placeholder"
        cfg = build_config(valid_prod_env)
        with pytest.raises(ConfigError, match="SECRET_KEY must be a random value of at least 32 characters"):
            validate_config(cfg)

    def test_production_rejects_turnstile_test_site_key(self, valid_prod_env):
        valid_prod_env["TURNSTILE_SITE_KEY"] = "1x00000000000000000000AA"
        cfg = build_config(valid_prod_env)
        with pytest.raises(ConfigError, match="Turnstile TEST keys are not allowed in production"):
            validate_config(cfg)

    def test_production_rejects_turnstile_test_secret_key(self, valid_prod_env):
        valid_prod_env["TURNSTILE_SECRET_KEY"] = "1x0000000000000000000000000000000AA"
        cfg = build_config(valid_prod_env)
        with pytest.raises(ConfigError, match="Turnstile TEST keys are not allowed in production"):
            validate_config(cfg)

    def test_production_requires_allowed_hostnames(self, valid_prod_env):
        valid_prod_env["TURNSTILE_ALLOWED_HOSTNAMES"] = ""
        cfg = build_config(valid_prod_env)
        with pytest.raises(ConfigError, match="TURNSTILE_ALLOWED_HOSTNAMES is required in production"):
            validate_config(cfg)

    def test_production_requires_session_cookie_secure(self, valid_prod_env):
        cfg = build_config(valid_prod_env)
        cfg["SESSION_COOKIE_SECURE"] = False
        with pytest.raises(ConfigError, match="SESSION_COOKIE_SECURE must be enabled in production"):
            validate_config(cfg)

    def test_production_rejects_sqlite_database(self, valid_prod_env):
        valid_prod_env["DATABASE_URL"] = "sqlite:///instance/prod.db"
        cfg = build_config(valid_prod_env)
        with pytest.raises(ConfigError, match="SQLite is not allowed in production"):
            validate_config(cfg)

    def test_postgresql_connection_pool_options_configured(self, valid_prod_env):
        cfg = build_config(valid_prod_env)
        opts = cfg["SQLALCHEMY_ENGINE_OPTIONS"]
        assert opts["pool_pre_ping"] is True
        assert opts["pool_recycle"] == 280
        assert opts["connect_args"]["connect_timeout"] == 10
        assert opts["pool_size"] == 5
        assert opts["max_overflow"] == 5
