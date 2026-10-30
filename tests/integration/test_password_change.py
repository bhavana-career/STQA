"""Integration tests for password change mechanism across Student and Teacher roles."""
from __future__ import annotations

import pytest

from app.extensions import db
from app.models import Section, Student, Teacher, User


@pytest.fixture
def seeded_users(pg_app):
    """Seed a test student and teacher user."""
    with pg_app.app_context():
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        u_stu = User(login_id="STU2026001", role="student")
        u_stu.set_password("StudentPass123!")
        db.session.add(u_stu)
        db.session.flush()

        student = Student(
            user_id=u_stu.id,
            student_code="STU2026001",
            full_name="Test Student One",
            section_id=sec.id,
            roll_number=1,
        )
        db.session.add(student)

        u_tch = User(login_id="TCH001", role="teacher")
        u_tch.set_password("TeacherPass123!")
        db.session.add(u_tch)
        db.session.flush()

        teacher = Teacher(
            user_id=u_tch.id,
            teacher_code="TCH001",
            full_name="Test Teacher",
        )
        db.session.add(teacher)
        db.session.commit()
        return u_stu.id, u_tch.id


@pytest.mark.integration
class TestPasswordChange:
    """Tests for POST /change-password."""

    def test_unauthenticated_cannot_change_password(self, pg_client):
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewPassword456!",
                "confirm_password": "NewPassword456!",
            },
        )
        assert res.status_code == 401

    def test_missing_fields(self, pg_client, seeded_users):
        # Log in student
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock"},
        )
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "StudentPass123!",
                "new_password": "",
                "confirm_password": "",
            },
        )
        assert res.status_code == 400
        assert res.json["error"]["code"] == "missing_fields"

    def test_incorrect_current_password(self, pg_client, seeded_users):
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock"},
        )
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewStrongP@ss123",
                "confirm_password": "NewStrongP@ss123",
            },
        )
        assert res.status_code == 400
        assert res.json["error"]["code"] == "invalid_current_password"

    def test_password_mismatch(self, pg_client, seeded_users):
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock"},
        )
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "StudentPass123!",
                "new_password": "NewStrongP@ss123",
                "confirm_password": "DifferentP@ss123",
            },
        )
        assert res.status_code == 400
        assert res.json["error"]["code"] == "password_mismatch"

    def test_same_password_rejected(self, pg_client, seeded_users):
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock"},
        )
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "StudentPass123!",
                "new_password": "StudentPass123!",
                "confirm_password": "StudentPass123!",
            },
        )
        assert res.status_code == 400
        assert res.json["error"]["code"] == "same_password"

    def test_weak_password_rejected(self, pg_client, seeded_users):
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock"},
        )
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "StudentPass123!",
                "new_password": "short1!",
                "confirm_password": "short1!",
            },
        )
        assert res.status_code == 400
        assert res.json["error"]["code"] == "weak_password"

    def test_successful_password_change_student(self, pg_client, pg_app, seeded_users):
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock"},
        )
        new_pw = "BrandNewStr0ngP@ssword!"
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "StudentPass123!",
                "new_password": new_pw,
                "confirm_password": new_pw,
            },
        )
        assert res.status_code == 200
        assert res.json["status"] == "ok"

        with pg_app.app_context():
            user = db.session.query(User).filter_by(login_id="STU2026001").first()
            assert user.check_password(new_pw) is True
            assert user.check_password("StudentPass123!") is False

    def test_successful_password_change_teacher(self, pg_client, pg_app, seeded_users):
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock"},
        )
        new_pw = "TeacherNewStr0ngP@ss!"
        res = pg_client.post(
            "/change-password",
            json={
                "current_password": "TeacherPass123!",
                "new_password": new_pw,
                "confirm_password": new_pw,
            },
        )
        assert res.status_code == 200
        assert res.json["status"] == "ok"

        with pg_app.app_context():
            user = db.session.query(User).filter_by(login_id="TCH001").first()
            assert user.check_password(new_pw) is True

    def test_form_submission_success_student(self, pg_client, pg_app, seeded_users):
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock"},
        )
        new_pw = "FormStr0ngP@ss123"
        res = pg_client.post(
            "/change-password",
            data={
                "current_password": "StudentPass123!",
                "new_password": new_pw,
                "confirm_password": new_pw,
            },
            follow_redirects=True,
        )
        assert res.status_code == 200
        assert b"Student Profile" in res.data
        with pg_app.app_context():
            user = db.session.query(User).filter_by(login_id="STU2026001").first()
            assert user.check_password(new_pw) is True

    def test_form_submission_validation_errors(self, pg_client, seeded_users):
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock"},
        )
        # Missing fields
        res = pg_client.post("/change-password", data={}, follow_redirects=True)
        assert res.status_code == 200

        # Wrong current password
        res = pg_client.post(
            "/change-password",
            data={"current_password": "Bad", "new_password": "NewStrongP@ss123", "confirm_password": "NewStrongP@ss123"},
            follow_redirects=True,
        )
        assert res.status_code == 200

        # Mismatch
        res = pg_client.post(
            "/change-password",
            data={"current_password": "TeacherPass123!", "new_password": "NewStrongP@ss123", "confirm_password": "DifferentP@ss123"},
            follow_redirects=True,
        )
        assert res.status_code == 200

        # Same password
        res = pg_client.post(
            "/change-password",
            data={"current_password": "TeacherPass123!", "new_password": "TeacherPass123!", "confirm_password": "TeacherPass123!"},
            follow_redirects=True,
        )
        assert res.status_code == 200

        # Weak password
        res = pg_client.post(
            "/change-password",
            data={"current_password": "TeacherPass123!", "new_password": "short", "confirm_password": "short"},
            follow_redirects=True,
        )
        assert res.status_code == 200

