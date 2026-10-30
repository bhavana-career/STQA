"""Integration tests for Teacher Authentication & Role Segregation (TC-AUTH).

Tests executed against PostgreSQL test database.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Section, Student, Teacher, User


@pytest.fixture
def auth_fixture(pg_app):
    """Seed both a student and a teacher for cross-role authentication tests."""
    with pg_app.app_context():
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        s_user = User(login_id="STU2026001", role="student")
        s_user.set_password("StudentPass123!")
        db.session.add(s_user)
        db.session.flush()

        student = Student(
            user_id=s_user.id,
            student_code="STU2026001",
            full_name="Test Student One",
            section_id=sec.id,
            roll_number=1,
        )
        db.session.add(student)

        t_user = User(login_id="TCH001", role="teacher")
        t_user.set_password("TeacherPass123!")
        db.session.add(t_user)
        db.session.flush()

        teacher = Teacher(
            user_id=t_user.id,
            teacher_code="TCH001",
            full_name="Test Teacher Smith",
        )
        db.session.add(teacher)
        db.session.commit()
        return {"student_user_id": s_user.id, "teacher_user_id": t_user.id}


@pytest.mark.integration
class TestTeacherAuthentication:
    """TC-AUTH: Teacher authentication and role segregation."""

    def test_tc_auth_02_valid_teacher_login(self, pg_client, pg_app, auth_fixture):
        resp = pg_client.post(
            "/teacher/login",
            data={
                "login_id": "TCH001",
                "password": "TeacherPass123!",
                "cf-turnstile-response": "mock-pass",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/teacher/dashboard")

        # Access teacher dashboard
        dash = pg_client.get("/teacher/dashboard")
        assert dash.status_code == 200
        assert b"TCH001" in dash.data

    def test_tc_auth_13_role_mismatch_on_login_pages(self, pg_client, pg_app, auth_fixture):
        # 1. Student attempts to log in on Teacher portal
        r_teacher_portal = pg_client.post(
            "/teacher/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert r_teacher_portal.status_code == 401
        assert b"Invalid ID or password." in r_teacher_portal.data

        # Failed attempt recorded on student
        with pg_app.app_context():
            s = db.session.get(User, auth_fixture["student_user_id"])
            assert s.failed_login_count == 1

        # 2. Teacher attempts to log in on Student portal
        r_student_portal = pg_client.post(
            "/student/login",
            data={
                "login_id": "TCH001",
                "password": "TeacherPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert r_student_portal.status_code == 401
        assert b"Invalid ID or password." in r_student_portal.data

        # Failed attempt recorded on teacher
        with pg_app.app_context():
            t = db.session.get(User, auth_fixture["teacher_user_id"])
            assert t.failed_login_count == 1

    def test_teacher_account_lockout(self, pg_client, pg_app, auth_fixture):
        # 5 failed attempts locks teacher
        for i in range(5):
            pg_client.post(
                "/teacher/login",
                data={
                    "login_id": "TCH001",
                    "password": "WrongPassword!",
                    "cf-turnstile-response": "mock-pass",
                },
            )

        resp = pg_client.post(
            "/teacher/login",
            data={
                "login_id": "TCH001",
                "password": "TeacherPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )
        assert resp.status_code == 429
        assert b"Account is temporarily locked" in resp.data

    def test_unauthenticated_teacher_dashboard_access_redirects(self, pg_client):
        resp = pg_client.get("/teacher/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/teacher/login" in resp.headers["Location"]
