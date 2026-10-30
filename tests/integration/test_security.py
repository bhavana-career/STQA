"""Integration tests for Security Controls, CSRF, Headers, and Cookies (TC-SEC).

Tests execute against PostgreSQL test database and Flask test client.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import Section, Student, User


@pytest.fixture
def test_student(pg_app):
    """Seed student user."""
    with pg_app.app_context():
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        user = User(login_id="STU2026001", role="student")
        user.set_password("StudentPass123!")
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            student_code="STU2026001",
            full_name="Test Student One",
            section_id=sec.id,
            roll_number=1,
        )
        db.session.add(student)
        db.session.commit()
        return user.id


@pytest.mark.integration
class TestSecurityControls:
    """TC-SEC: Security controls test suite."""

    @pytest.mark.parametrize(
        "sql_injection_id",
        [
            "' OR '1'='1",
            "STU2026001'--",
            "'; DROP TABLE users;--",
            "admin' /*",
        ],
    )
    def test_tc_sec_01_sql_injection_safely_handled(self, pg_client, pg_app, test_student, sql_injection_id):
        # Count users before attack
        with pg_app.app_context():
            count_before = db.session.scalar(select(db.func.count(User.id)))

        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": sql_injection_id,
                "password": "Password123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        # Must return 401 generic or 400 validation, never 500
        assert resp.status_code in (400, 401)
        assert b"Invalid ID or password." in resp.data or b"validation" in resp.data

        # Database rows must remain intact
        with pg_app.app_context():
            count_after = db.session.scalar(select(db.func.count(User.id)))
            assert count_after == count_before

    def test_tc_sec_03_csrf_protection_enforced(self, pg_test_db_url, test_student):
        # Create app instance with WTF_CSRF_ENABLED=True
        env = {
            "APP_ENV": "testing",
            "SECRET_KEY": "test-secret-key-for-unit-and-integration-tests",
            "DATABASE_URL": pg_test_db_url,
            "CAPTCHA_MODE": "mock",
            "WTF_CSRF_ENABLED": "1",
        }
        csrf_app = create_app(
            overrides={
                "TESTING": True,
                "WTF_CSRF_ENABLED": True,
            },
            env=env,
        )
        client = csrf_app.test_client()

        # POST without CSRF token must fail with 400 csrf_failed
        resp = client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert resp.status_code == 400
        assert b"csrf_failed" in resp.data or b"session form token is missing or invalid" in resp.data

    def test_tc_sec_04_security_headers_present(self, pg_client, test_student):
        # Public route
        resp = pg_client.get("/")
        assert resp.status_code == 200
        assert "Content-Security-Policy" in resp.headers
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "same-origin"

        # Authenticated route must include Cache-Control: no-store
        pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        authed_resp = pg_client.get("/student/dashboard")
        assert authed_resp.status_code == 200
        assert "no-store" in authed_resp.headers.get("Cache-Control", "")

    def test_tc_sec_06_session_fixation_prevention(self, pg_client, test_student):
        # 1. Anonymous visitor gets a pre-existing session value
        with pg_client.session_transaction() as sess:
            sess["pre_login_tracker"] = "pre_auth_cookie_value"

        # 2. Authenticate
        pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )

        # 3. Pre-login session key must be cleared (session.clear())
        with pg_client.session_transaction() as sess:
            assert "pre_login_tracker" not in sess
            assert sess.get("session_version") == 1

    def test_tc_sec_09_open_redirect_prevented(self, pg_client, test_student):
        # Attempt open redirect via external URL
        resp1 = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
                "next": "https://evil.example.com",
            },
            follow_redirects=False,
        )
        assert resp1.status_code == 302
        assert resp1.headers["Location"].endswith("/student/dashboard")
        assert "evil.example.com" not in resp1.headers["Location"]

        # Attempt protocol-relative open redirect
        resp2 = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
                "next": "//evil.example.com/steal-creds",
            },
            follow_redirects=False,
        )
        assert resp2.status_code == 302
        assert resp2.headers["Location"].endswith("/student/dashboard")
        assert "evil.example.com" not in resp2.headers["Location"]

    def test_tc_sec_10_cookie_security_attributes(self, pg_client, test_student):
        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        # Check Set-Cookie attributes on session cookie
        cookies = resp.headers.getlist("Set-Cookie")
        session_cookie = [c for c in cookies if "srms_session=" in c]
        assert len(session_cookie) > 0
        cookie_header = session_cookie[0]
        assert "HttpOnly" in cookie_header
        assert "SameSite=Lax" in cookie_header

    def test_tc_sec_11_no_stack_traces_leaked_on_500(self, pg_app):
        # Register a temporary route that deliberately raises an unhandled exception
        @pg_app.route("/force-unhandled-error")
        def force_error():
            raise RuntimeError("Database connection crashed with secret db_pass_123")

        client = pg_app.test_client()
        resp = client.get("/force-unhandled-error")
        assert resp.status_code == 500
        # Check that secret details or traceback are not leaked in HTML body
        assert b"secret db_pass_123" not in resp.data
        assert b"Traceback (most recent call last)" not in resp.data
        assert b"An unexpected error occurred." in resp.data
