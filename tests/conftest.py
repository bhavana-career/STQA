"""Pytest fixtures for SRMS test suite."""
from __future__ import annotations

import os
from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy import text

from app import create_app
from app.extensions import db as _db

DEFAULT_PG_TEST_URL = "postgresql+psycopg://srms:srms_local_pw@localhost:5433/srms_test"

# Default test environment dictionary for in-memory SQLite unit testing
DEFAULT_TEST_ENV = {
    "APP_ENV": "testing",
    "SECRET_KEY": "test-secret-key-for-unit-and-integration-tests",
    "DATABASE_URL": "sqlite:///:memory:",
    "TEST_DATABASE_URL": "sqlite:///:memory:",
    "CAPTCHA_MODE": "mock",
    "TURNSTILE_SITE_KEY": "1x00000000000000000000AA",
    "TURNSTILE_SECRET_KEY": "1x0000000000000000000000000000000AA",
    "TURNSTILE_ALLOWED_HOSTNAMES": "localhost,127.0.0.1",
    "WTF_CSRF_ENABLED": "0",
}


@pytest.fixture
def app() -> Flask:
    """Create a Flask application configured for in-memory test execution."""
    test_env = dict(DEFAULT_TEST_ENV)
    test_app = create_app(
        overrides={
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        },
        env=test_env,
    )

    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for HTTP requests on the in-memory app."""
    return app.test_client()


@pytest.fixture(scope="session")
def pg_test_db_url() -> str:
    """Resolve and validate PostgreSQL test database URL."""
    url = os.environ.get("TEST_DATABASE_URL", DEFAULT_PG_TEST_URL).strip()
    prod_url = os.environ.get("DATABASE_URL", "").strip()

    # Safety Guard (TC-DB-07): Ensure test DB is distinct from production and contains 'test'
    if prod_url and url == prod_url:
        pytest.fail(f"SAFETY ABORT: TEST_DATABASE_URL matches DATABASE_URL: {url}")
    if "test" not in url.lower():
        pytest.fail(f"SAFETY ABORT: Test database name must contain 'test': {url}")

    return url


@pytest.fixture
def pg_app(pg_test_db_url: str) -> Generator[Flask, None, None]:
    """Create a Flask application connected to PostgreSQL test database."""
    test_env = dict(DEFAULT_TEST_ENV)
    test_env["DATABASE_URL"] = pg_test_db_url
    test_env["TEST_DATABASE_URL"] = pg_test_db_url

    test_app = create_app(
        overrides={
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        },
        env=test_env,
    )

    with test_app.app_context():
        yield test_app
        _db.session.remove()
        # Truncate tables to ensure completely clean state between tests
        try:
            _db.session.execute(
                text(
                    "TRUNCATE TABLE mark_audit, marks, teacher_assignments, "
                    "exam_subjects, exams, students, teachers, subjects, sections, users CASCADE"
                )
            )
            _db.session.commit()
        except Exception:
            _db.session.rollback()


@pytest.fixture
def pg_client(pg_app: Flask) -> FlaskClient:
    """Test client for PostgreSQL-backed tests."""
    return pg_app.test_client()


@pytest.fixture
def pg_runner(pg_app: Flask) -> FlaskCliRunner:
    """CLI runner for testing Flask commands against PostgreSQL."""
    return pg_app.test_cli_runner()
