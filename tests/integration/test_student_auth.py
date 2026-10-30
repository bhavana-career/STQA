"""Integration tests for Student Authentication (TC-AUTH).

Tests execute against PostgreSQL test database with real models, sessions, and cookies.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Section, Student, User


@pytest.fixture
def student_user(pg_app):
    """Seed a test student user."""
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
class TestStudentAuthentication:
    """TC-AUTH: Student authentication test suite."""

    def test_tc_auth_01_valid_student_login(self, pg_client, pg_app, student_user):
        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/student/dashboard")

        # Verify DB updates
        with pg_app.app_context():
            u = db.session.get(User, student_user)
            assert u.failed_login_count == 0
            assert u.locked_until is None
            assert u.last_login_at is not None

        # Verify authenticated session can access dashboard
        dash_resp = pg_client.get("/student/dashboard")
        assert dash_resp.status_code == 200
        assert b"STU2026001" in dash_resp.data

    def test_tc_auth_03_invalid_id_or_password_non_revealing(self, pg_client, student_user):
        # Case A: Non-existent ID
        r1 = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU999999",
                "password": "AnyPassword123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert r1.status_code == 401
        assert b"Invalid ID or password." in r1.data

        # Case B: Correct ID, wrong password
        r2 = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "WrongPassword!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert r2.status_code == 401
        assert b"Invalid ID or password." in r2.data

    def test_tc_auth_04_empty_login_fields(self, pg_client):
        # Both empty
        r1 = pg_client.post(
            "/student/login",
            data={"login_id": "", "password": "", "cf-turnstile-response": "mock-pass"},
        )
        assert r1.status_code == 400
        assert b"Please enter both Login ID and password." in r1.data

        # Password only
        r2 = pg_client.post(
            "/student/login",
            data={"login_id": "", "password": "SecretPassword!", "cf-turnstile-response": "mock-pass"},
        )
        assert r2.status_code == 400
        assert b"Please enter both Login ID and password." in r2.data

        # ID only
        r3 = pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "", "cf-turnstile-response": "mock-pass"},
        )
        assert r3.status_code == 400
        assert b"Please enter both Login ID and password." in r3.data

        # Whitespace-only ID
        r4 = pg_client.post(
            "/student/login",
            data={"login_id": "   ", "password": "SecretPassword!", "cf-turnstile-response": "mock-pass"},
        )
        assert r4.status_code == 400
        assert b"Please enter both Login ID and password." in r4.data

    def test_tc_auth_05_missing_captcha_token(self, pg_client, student_user):
        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "",
            },
        )
        assert resp.status_code == 400
        assert b"Please complete the CAPTCHA." in resp.data

    def test_tc_auth_06_invalid_captcha_token(self, pg_client, student_user):
        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-fail",
            },
        )
        assert resp.status_code == 400
        assert b"CAPTCHA verification failed. Please try again." in resp.data

    def test_tc_auth_07_expired_captcha_token(self, pg_client, student_user):
        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-expired",
            },
        )
        assert resp.status_code == 400
        assert b"CAPTCHA verification failed. Please try again." in resp.data

    def test_tc_auth_08_captcha_service_unavailable(self, pg_client, student_user):
        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-unavailable",
            },
        )
        assert resp.status_code == 503
        assert b"Verification service unavailable. Please try again shortly." in resp.data

    def test_tc_auth_09_logout_invalidates_session(self, pg_client, pg_app, student_user):
        # 1. Log in
        pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        dash1 = pg_client.get("/student/dashboard")
        assert dash1.status_code == 200

        # 2. Log out
        logout_resp = pg_client.post("/logout", follow_redirects=False)
        assert logout_resp.status_code == 302
        assert logout_resp.headers["Location"].endswith("/")

        # 3. Subsequent access to dashboard redirects to login
        dash2 = pg_client.get("/student/dashboard", follow_redirects=False)
        assert dash2.status_code == 302
        assert "/student/login" in dash2.headers["Location"]

        # 4. Check DB: session_version incremented
        with pg_app.app_context():
            u = db.session.get(User, student_user)
            assert u.session_version == 2

    def test_tc_auth_11_unauthenticated_page_access_redirects(self, pg_client):
        resp = pg_client.get("/student/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/student/login" in resp.headers["Location"]
        assert "next=" in resp.headers["Location"]

    def test_tc_auth_12_account_lockout_policy(self, pg_client, pg_app, student_user):
        # 4 failed attempts: each 401
        for i in range(1, 5):
            r = pg_client.post(
                "/student/login",
                data={
                    "login_id": "STU2026001",
                    "password": f"WrongAttempt{i}!",
                    "cf-turnstile-response": "mock-pass",
                },
            )
            assert r.status_code == 401
            assert b"Invalid ID or password." in r.data

        # 5th attempt locks the account
        r5 = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "WrongAttempt5!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert r5.status_code == 401

        with pg_app.app_context():
            u = db.session.get(User, student_user)
            assert u.failed_login_count == 5
            assert u.is_locked() is True

        # 6th attempt (even with correct password) returns 429 Locked
        r6 = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert r6.status_code == 429
        assert b"Account is temporarily locked" in r6.data

        # Simulate lockout expiration by shifting locked_until into the past
        with pg_app.app_context():
            u = db.session.get(User, student_user)
            u.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.session.commit()

        # Now correct password succeeds and resets lockout
        r_after = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
            follow_redirects=False,
        )
        assert r_after.status_code == 302
        assert r_after.headers["Location"].endswith("/student/dashboard")

        with pg_app.app_context():
            u = db.session.get(User, student_user)
            assert u.failed_login_count == 0
            assert u.locked_until is None

    def test_tc_auth_14_inactive_account_rejected(self, pg_client, pg_app, student_user):
        with pg_app.app_context():
            u = db.session.get(User, student_user)
            u.is_active = False
            db.session.commit()

        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert resp.status_code == 401
        assert b"Invalid ID or password." in resp.data

    def test_tc_auth_15_case_insensitive_and_trimmed_login_id(self, pg_client, student_user):
        resp = pg_client.post(
            "/student/login",
            data={
                "login_id": "   stu2026001   ",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/student/dashboard")

    def test_tc_auth_16_oversized_inputs_rejected(self, pg_client):
        long_id = "A" * 33
        long_pw = "B" * 129

        resp1 = pg_client.post(
            "/student/login",
            data={
                "login_id": long_id,
                "password": "ValidPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert resp1.status_code == 400
        assert b"Input exceeds maximum allowed length." in resp1.data

        resp2 = pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": long_pw,
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert resp2.status_code == 400
        assert b"Input exceeds maximum allowed length." in resp2.data

    def test_tc_auth_10_session_idle_expiry(self, pg_test_db_url, student_user):
        import time
        from app import create_app

        env = {
            "APP_ENV": "testing",
            "SECRET_KEY": "test-secret-key-for-unit-and-integration-tests",
            "DATABASE_URL": pg_test_db_url,
            "CAPTCHA_MODE": "mock",
            "SESSION_LIFETIME_MINUTES": "1",
        }
        short_session_app = create_app(
            overrides={
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "PERMANENT_SESSION_LIFETIME": timedelta(seconds=1),
            },
            env=env,
        )
        client = short_session_app.test_client()

        # Log in
        r_login = client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert r_login.status_code == 302

        # Immediate request succeeds
        r_now = client.get("/student/dashboard")
        assert r_now.status_code == 200

        # Wait for session expiry (itsdangerous timestamp precision is in whole seconds)
        time.sleep(2.5)

        # Expired request redirects to login
        r_expired = client.get("/student/dashboard", follow_redirects=False)
        assert r_expired.status_code == 302
        assert "/student/login" in r_expired.headers["Location"]
