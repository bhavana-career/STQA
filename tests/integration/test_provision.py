"""Integration tests for one-time authenticated production provisioning workflow."""
from __future__ import annotations

import os
import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Section, Student, Subject, SystemSetting, Teacher, TeacherAssignment, User
from app.views.provision import _FAILED_ATTEMPTS, MAX_FAILED_ATTEMPTS

TEST_SECRET = "a_very_secure_test_provisioning_secret_key_32_chars_long"


@pytest.fixture(autouse=True)
def clear_failed_attempts():
    """Reset failed attempts tracker before each test."""
    _FAILED_ATTEMPTS.clear()
    yield
    _FAILED_ATTEMPTS.clear()


@pytest.mark.integration
class TestOneTimeProvisioningWorkflow:
    """Test suite verifying security, lockout, and atomic behavior of /system/provision."""

    def test_disabled_when_secret_not_set(self, pg_client):
        """Returns 404 when PROVISIONING_SECRET is not configured."""
        res_get = pg_client.get("/system/provision")
        assert res_get.status_code == 404

        res_post = pg_client.post("/system/provision", data={})
        assert res_post.status_code == 404

    def test_disabled_when_secret_too_short(self, pg_client, monkeypatch):
        """Returns 404 if PROVISIONING_SECRET is shorter than 32 characters."""
        monkeypatch.setenv("PROVISIONING_SECRET", "too_short_secret")
        res = pg_client.get("/system/provision")
        assert res.status_code == 404

    def test_form_renders_when_secret_configured(self, pg_client, monkeypatch):
        """GET /system/provision returns 200 with security headers and masked fields."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)
        res = pg_client.get("/system/provision")
        assert res.status_code == 200
        assert res.headers.get("X-Robots-Tag") == "noindex, nofollow, noarchive"
        assert "no-store" in res.headers.get("Cache-Control", "")
        assert b"provisioning_secret" in res.data
        assert b"teacher_password" in res.data
        assert b"student_password" in res.data

    def test_invalid_provisioning_secret_rejected(self, pg_client, monkeypatch):
        """POST with wrong secret returns 400 error."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)
        res = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": "wrong_secret_value_that_fails_comparison!",
                "teacher_password": "ValidStr0ngP@ss1",
                "confirm_teacher_password": "ValidStr0ngP@ss1",
                "student_password": "ValidStr0ngP@ss2",
                "confirm_student_password": "ValidStr0ngP@ss2",
            },
        )
        assert res.status_code == 400
        assert b"Invalid provisioning secret" in res.data

    def test_missing_and_mismatched_passwords_rejected(self, pg_client, monkeypatch):
        """Rejects missing passwords and confirmation mismatches."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        # Missing fields
        res_missing = pg_client.post(
            "/system/provision",
            data={"provisioning_secret": TEST_SECRET},
        )
        assert res_missing.status_code == 400
        assert b"required" in res_missing.data

        # Teacher mismatch
        res_tmismatch = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "ValidStr0ngP@ss1",
                "confirm_teacher_password": "DifferentP@ss123",
                "student_password": "ValidStr0ngP@ss2",
                "confirm_student_password": "ValidStr0ngP@ss2",
            },
        )
        assert res_tmismatch.status_code == 400
        assert b"Teacher password and confirmation do not match" in res_tmismatch.data

        # Student mismatch
        res_smismatch = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "ValidStr0ngP@ss1",
                "confirm_teacher_password": "ValidStr0ngP@ss1",
                "student_password": "ValidStr0ngP@ss2",
                "confirm_student_password": "DifferentP@ss123",
            },
        )
        assert res_smismatch.status_code == 400
        assert b"Student password and confirmation do not match" in res_smismatch.data

    def test_weak_password_rejected(self, pg_client, monkeypatch):
        """Enforces minimum 12-char complexity policy on teacher and student passwords."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        # Weak teacher password (< 12 chars)
        res = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "Short1!",
                "confirm_teacher_password": "Short1!",
                "student_password": "ValidStr0ngP@ss2",
                "confirm_student_password": "ValidStr0ngP@ss2",
            },
        )
        assert res.status_code == 400
        assert b"Teacher password does not meet complexity requirements" in res.data

        # Weak student password (no special character)
        res2 = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "ValidStr0ngP@ss1",
                "confirm_teacher_password": "ValidStr0ngP@ss1",
                "student_password": "NoSpecialCharacter1234",
                "confirm_student_password": "NoSpecialCharacter1234",
            },
        )
        assert res2.status_code == 400
        assert b"Student password does not meet complexity requirements" in res2.data

    def test_successful_atomic_provisioning_and_subsequent_lockout(self, pg_client, pg_app, monkeypatch):
        """Successful submission provisions accounts, assigns Mathematics, and permanently self-locks."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        t_pass = "TeachStrongP@ssw0rd1!"
        s_pass = "StudStrongP@ssw0rd2!"

        res = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": t_pass,
                "confirm_teacher_password": t_pass,
                "student_password": s_pass,
                "confirm_student_password": s_pass,
            },
        )
        assert res.status_code == 200
        assert b"Accounts Provisioned Successfully" in res.data
        assert b"bootstrap_completed" in res.data

        # Verify database entities
        with pg_app.app_context():
            # Users
            t_user = db.session.scalar(select(User).where(User.login_id == "TCH001"))
            s_user = db.session.scalar(select(User).where(User.login_id == "4INI23IS036"))
            assert t_user is not None
            assert t_user.role == "teacher"
            assert t_user.check_password(t_pass) is True

            assert s_user is not None
            assert s_user.role == "student"
            assert s_user.check_password(s_pass) is True

            # Profiles
            assert t_user.teacher is not None
            assert t_user.teacher.full_name == "General Teacher"

            assert s_user.student is not None
            assert s_user.student.roll_number == 36
            assert s_user.student.section.class_name == "10th Standard"
            assert s_user.student.section.name == "A"

            # All 5 STQA students must exist
            all_usns = ["4INI23IS036", "4INI23IS001", "4INI23IS002", "4INI23IS003", "4INI23IS004"]
            for usn in all_usns:
                stu_u = db.session.scalar(select(User).where(User.login_id == usn))
                assert stu_u is not None
                assert stu_u.role == "student"
                assert stu_u.check_password(s_pass) is True

            # Subject Assignments: General Teacher assigned across all 5 subjects
            assignments = db.session.scalars(
                select(TeacherAssignment).where(TeacherAssignment.teacher_id == t_user.teacher.id)
            ).all()
            assert len(assignments) == 25

            # Lockout flag recorded
            setting = db.session.scalar(select(SystemSetting).where(SystemSetting.key == "bootstrap_completed"))
            assert setting is not None
            assert setting.value == "true"

        # Subsequent attempts must return 404
        assert pg_client.get("/system/provision").status_code == 404
        assert pg_client.post("/system/provision", data={"provisioning_secret": TEST_SECRET}).status_code == 404

    def test_never_overwrites_existing_account_passwords_silently(self, pg_client, pg_app, monkeypatch):
        """Aborts with 409 if an account already exists with a password and bootstrap is attempted."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        # Pre-seed an existing teacher with password
        with pg_app.app_context():
            u = User(login_id="TCH001", role="teacher")
            u.set_password("ExistingTeacherPass123!")
            db.session.add(u)
            db.session.commit()

        res = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "NewTeacherP@ssw0rd1!",
                "confirm_teacher_password": "NewTeacherP@ssw0rd1!",
                "student_password": "NewStudentP@ssw0rd2!",
                "confirm_student_password": "NewStudentP@ssw0rd2!",
            },
        )
        assert res.status_code == 409
        assert b"One or more accounts already exist" in res.data

        # Ensure existing password was NOT modified
        with pg_app.app_context():
            teacher = db.session.scalar(select(User).where(User.login_id == "TCH001"))
            assert teacher.check_password("ExistingTeacherPass123!") is True
            assert teacher.check_password("NewTeacherP@ssw0rd1!") is False

    def test_simultaneous_first_time_requests(self, pg_app, monkeypatch):
        """Simultaneous first-time requests across workers are safely serialized; only one executes."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        t_pass = "TeachStrongP@ssw0rd1!"
        s_pass = "StudStrongP@ssw0rd2!"
        payload = {
            "provisioning_secret": TEST_SECRET,
            "teacher_password": t_pass,
            "confirm_teacher_password": t_pass,
            "student_password": s_pass,
            "confirm_student_password": s_pass,
        }

        results = []

        def make_request():
            with pg_app.test_client() as client:
                res = client.post("/system/provision", data=payload)
                results.append(res.status_code)

        import threading
        t1 = threading.Thread(target=make_request)
        t2 = threading.Thread(target=make_request)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # One request must succeed (200), the other must be rejected (409 lock contention or 404 lockout)
        assert 200 in results
        assert all(code in (200, 404, 409) for code in results)
        assert results.count(200) == 1

        # Database state: exactly 1 teacher and 5 students
        with pg_app.app_context():
            teacher_count = db.session.scalar(select(db.func.count(Teacher.id)))
            student_count = db.session.scalar(select(db.func.count(Student.id)))
            assert teacher_count == 1
            assert student_count == 5
            setting = db.session.scalar(select(SystemSetting).where(SystemSetting.key == "bootstrap_completed"))
            assert setting is not None
            assert setting.value == "true"

    def test_missing_passwords_rejected_and_nothing_seeded(self, pg_client, pg_app, monkeypatch):
        """Rejects empty teacher or student passwords and ensures no records are seeded."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        # Empty teacher password
        res = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "",
                "confirm_teacher_password": "",
                "student_password": "ValidStr0ngP@ss2",
                "confirm_student_password": "ValidStr0ngP@ss2",
            },
        )
        assert res.status_code == 400
        assert b"All password fields are required" in res.data

        # Empty student password
        res2 = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "ValidStr0ngP@ss1",
                "confirm_teacher_password": "ValidStr0ngP@ss1",
                "student_password": "",
                "confirm_student_password": "",
            },
        )
        assert res2.status_code == 400
        assert b"All password fields are required" in res2.data

        with pg_app.app_context():
            assert db.session.scalar(select(db.func.count(User.id))) == 0

    def test_rollback_behavior_on_failure(self, pg_client, pg_app, monkeypatch):
        """If an unexpected exception occurs during provisioning, all changes are rolled back."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        from app.views import provision as prov_module

        def failing_provision(*args, **kwargs):
            u = User(login_id="TCH001", role="teacher")
            u.set_password("ValidP@ssw0rd123!")
            db.session.add(u)
            db.session.flush()
            raise RuntimeError("Database connection lost during provisioning")

        monkeypatch.setattr(prov_module, "provision_stqa_scenario", failing_provision)

        res = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "ValidStr0ngP@ss1",
                "confirm_teacher_password": "ValidStr0ngP@ss1",
                "student_password": "ValidStr0ngP@ss2",
                "confirm_student_password": "ValidStr0ngP@ss2",
            },
        )
        assert res.status_code == 500
        assert b"An error occurred while processing the provisioning request" in res.data
        # Ensure raw internal exception is never exposed to user
        assert b"Database connection lost" not in res.data
        assert b"RuntimeError" not in res.data

        # Verify nothing was committed
        with pg_app.app_context():
            assert db.session.scalar(select(db.func.count(User.id))) == 0
            assert db.session.scalar(select(SystemSetting).where(SystemSetting.key == "bootstrap_completed")) is None

    def test_rate_limiting_on_repeated_failed_attempts(self, pg_client, monkeypatch):
        """Blocks IP after 5 failed attempts with HTTP 429."""
        monkeypatch.setenv("PROVISIONING_SECRET", TEST_SECRET)

        for _ in range(MAX_FAILED_ATTEMPTS):
            res = pg_client.post(
                "/system/provision",
                data={
                    "provisioning_secret": "bad_secret_attempt",
                    "teacher_password": "ValidStr0ngP@ss1",
                    "confirm_teacher_password": "ValidStr0ngP@ss1",
                    "student_password": "ValidStr0ngP@ss2",
                    "confirm_student_password": "ValidStr0ngP@ss2",
                },
            )
            assert res.status_code == 400

        # Next attempt should be rate limited (429)
        res_blocked = pg_client.post(
            "/system/provision",
            data={
                "provisioning_secret": TEST_SECRET,
                "teacher_password": "ValidStr0ngP@ss1",
                "confirm_teacher_password": "ValidStr0ngP@ss1",
                "student_password": "ValidStr0ngP@ss2",
                "confirm_student_password": "ValidStr0ngP@ss2",
            },
        )
        assert res_blocked.status_code == 429
