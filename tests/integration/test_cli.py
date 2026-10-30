"""PostgreSQL integration tests for operator CLI commands.

Tests:
- TC-OPS-03: Seed blocked in production / reset forbidden in production.
- TC-OPS-04: Seed idempotent in development/testing.
- TC-OPS-05: create-user CLI (roles, password hashing, duplicates).
- TC-OPS: db-status, create-subject, assign, unlock-user.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import (
    Exam,
    ExamSubject,
    Mark,
    MarkAudit,
    Section,
    Student,
    Subject,
    Teacher,
    TeacherAssignment,
    User,
)


@pytest.mark.integration
class TestDbStatusCli:
    """Tests for db-status CLI command."""

    def test_db_status_output(self, pg_runner):
        result = pg_runner.invoke(args=["db-status"])
        assert result.exit_code == 0
        assert "Database connection: OK" in result.output
        assert "Database Record Counts" in result.output
        assert "users" in result.output
        assert "students" in result.output


@pytest.mark.integration
class TestCreateUserCli:
    """TC-OPS-05: Tests for create-user CLI command."""

    def test_create_student_success(self, pg_runner, pg_app):
        result = pg_runner.invoke(
            args=[
                "create-user",
                "--role", "student",
                "--login-id", "STU2026001",
                "--name", "Test Student",
                "--password", "StudentPass123!",
                "--section", "A",
                "--roll", "1",
            ]
        )
        assert result.exit_code == 0
        assert "Success: Created student 'STU2026001'" in result.output

        with pg_app.app_context():
            user = db.session.scalar(select(User).where(User.login_id == "STU2026001"))
            assert user is not None
            assert user.role == "student"
            assert user.password_hash.startswith("scrypt:")
            assert user.check_password("StudentPass123!") is True

            student = db.session.scalar(select(Student).where(Student.student_code == "STU2026001"))
            assert student is not None
            assert student.full_name == "Test Student"
            assert student.roll_number == 1
            assert student.section.name == "A"

    def test_create_teacher_success(self, pg_runner, pg_app):
        result = pg_runner.invoke(
            args=[
                "create-user",
                "--role", "teacher",
                "--login-id", "TCH001",
                "--name", "Test Teacher",
                "--password", "TeacherPass123!",
            ]
        )
        assert result.exit_code == 0
        assert "Success: Created teacher 'TCH001'" in result.output

        with pg_app.app_context():
            user = db.session.scalar(select(User).where(User.login_id == "TCH001"))
            assert user is not None
            assert user.role == "teacher"
            assert user.check_password("TeacherPass123!") is True

            teacher = db.session.scalar(select(Teacher).where(Teacher.teacher_code == "TCH001"))
            assert teacher is not None
            assert teacher.full_name == "Test Teacher"

    def test_create_user_duplicate_login_id_rejected(self, pg_runner):
        # First creation succeeds
        r1 = pg_runner.invoke(
            args=[
                "create-user",
                "--role", "teacher",
                "--login-id", "TCH001",
                "--name", "Teacher 1",
                "--password", "Pass123456",
            ]
        )
        assert r1.exit_code == 0

        # Duplicate attempt fails
        r2 = pg_runner.invoke(
            args=[
                "create-user",
                "--role", "teacher",
                "--login-id", "TCH001",
                "--name", "Teacher 2",
                "--password", "Pass123456",
            ]
        )
        assert r2.exit_code == 1
        assert "already exists" in r2.output

    def test_create_student_missing_or_invalid_roll_rejected(self, pg_runner):
        result = pg_runner.invoke(
            args=[
                "create-user",
                "--role", "student",
                "--login-id", "STU001",
                "--name", "Student",
                "--password", "Pass123456",
            ]
        )
        assert result.exit_code == 1
        assert "Valid positive --roll number is required" in result.output

    def test_create_user_short_password_rejected(self, pg_runner):
        result = pg_runner.invoke(
            args=[
                "create-user",
                "--role", "student",
                "--login-id", "STU001",
                "--name", "Student",
                "--password", "123",
                "--roll", "1",
            ]
        )
        assert result.exit_code == 1
        assert "Password must be at least 6 characters" in result.output


@pytest.mark.integration
class TestCreateSubjectCli:
    """Tests for create-subject CLI command."""

    def test_create_subject_success(self, pg_runner, pg_app):
        result = pg_runner.invoke(args=["create-subject", "--code", "MAT", "--name", "Mathematics"])
        assert result.exit_code == 0
        assert "Subject 'MAT' (Mathematics) created" in result.output

        with pg_app.app_context():
            sub = db.session.scalar(select(Subject).where(Subject.code == "MAT"))
            assert sub is not None
            assert sub.name == "Mathematics"

    def test_create_subject_duplicate_rejected(self, pg_runner):
        pg_runner.invoke(args=["create-subject", "--code", "MAT", "--name", "Mathematics"])
        result = pg_runner.invoke(args=["create-subject", "--code", "MAT", "--name", "Mathematics"])
        assert result.exit_code == 1
        assert "already exists" in result.output


@pytest.mark.integration
class TestAssignCli:
    """Tests for assign CLI command."""

    def test_assign_teacher_success(self, pg_runner, pg_app):
        # Provision prerequisite records
        pg_runner.invoke(args=["create-user", "--role", "teacher", "--login-id", "TCH001", "--name", "Teacher Smith", "--password", "Pass123!"])
        pg_runner.invoke(args=["create-user", "--role", "student", "--login-id", "STU001", "--name", "Student Doe", "--password", "Pass123!", "--roll", "1"])
        pg_runner.invoke(args=["create-subject", "--code", "ENG", "--name", "English"])

        result = pg_runner.invoke(args=["assign", "--teacher", "TCH001", "--student", "STU001", "--subject", "ENG"])
        assert result.exit_code == 0
        assert "Assigned TCH001 to STU001 for ENG" in result.output

        with pg_app.app_context():
            assignment = db.session.scalar(select(TeacherAssignment))
            assert assignment is not None
            assert assignment.teacher.teacher_code == "TCH001"
            assert assignment.student.student_code == "STU001"
            assert assignment.subject.code == "ENG"

    def test_assign_duplicate_rejected(self, pg_runner):
        pg_runner.invoke(args=["create-user", "--role", "teacher", "--login-id", "TCH001", "--name", "Teacher Smith", "--password", "Pass123!"])
        pg_runner.invoke(args=["create-user", "--role", "student", "--login-id", "STU001", "--name", "Student Doe", "--password", "Pass123!", "--roll", "1"])
        pg_runner.invoke(args=["create-subject", "--code", "ENG", "--name", "English"])

        pg_runner.invoke(args=["assign", "--teacher", "TCH001", "--student", "STU001", "--subject", "ENG"])
        result = pg_runner.invoke(args=["assign", "--teacher", "TCH001", "--student", "STU001", "--subject", "ENG"])
        assert result.exit_code == 1
        assert "already assigned" in result.output

    def test_assign_unknown_entity_rejected(self, pg_runner):
        result = pg_runner.invoke(args=["assign", "--teacher", "NOBODY", "--student", "NOBODY", "--subject", "NOBODY"])
        assert result.exit_code == 1
        assert "not found" in result.output


@pytest.mark.integration
class TestUnlockUserCli:
    """Tests for unlock-user CLI command."""

    def test_unlock_user_clears_lockout(self, pg_runner, pg_app):
        pg_runner.invoke(args=["create-user", "--role", "student", "--login-id", "LOCKED01", "--name", "Locked User", "--password", "Pass123!", "--roll", "10"])

        # Manually set lockout in DB
        with pg_app.app_context():
            u = db.session.scalar(select(User).where(User.login_id == "LOCKED01"))
            u.failed_login_count = 5
            u.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.session.commit()

        result = pg_runner.invoke(args=["unlock-user", "LOCKED01"])
        assert result.exit_code == 0
        assert "has been unlocked" in result.output

        with pg_app.app_context():
            u = db.session.scalar(select(User).where(User.login_id == "LOCKED01"))
            assert u.failed_login_count == 0
            assert u.locked_until is None

    def test_unlock_nonexistent_user(self, pg_runner):
        result = pg_runner.invoke(args=["unlock-user", "DOESNOTEXIST"])
        assert result.exit_code == 1
        assert "not found" in result.output


@pytest.mark.integration
class TestSeedDemoCli:
    """TC-OPS-03 & TC-OPS-04: Tests for seed-demo CLI command."""

    def test_seed_demo_success_and_idempotency(self, pg_runner, pg_app):
        # First execution seeds all demo records
        result1 = pg_runner.invoke(args=["seed-demo"])
        assert result1.exit_code == 0
        assert "Fictional demo dataset seeded successfully" in result1.output

        with pg_app.app_context():
            u_count = db.session.scalar(select(db.func.count(User.id)))
            s_count = db.session.scalar(select(db.func.count(Student.id)))
            t_count = db.session.scalar(select(db.func.count(Teacher.id)))
            m_count = db.session.scalar(select(db.func.count(Mark.id)))
            assert u_count == 6
            assert s_count == 4
            assert t_count == 2
            assert m_count == 12

        # TC-OPS-04: Second execution is idempotent and does not produce duplicates
        result2 = pg_runner.invoke(args=["seed-demo"])
        assert result2.exit_code == 0

        with pg_app.app_context():
            assert db.session.scalar(select(db.func.count(User.id))) == 6
            assert db.session.scalar(select(db.func.count(Student.id))) == 4
            assert db.session.scalar(select(db.func.count(Teacher.id))) == 2
            assert db.session.scalar(select(db.func.count(Mark.id))) == 12

    def test_seed_demo_reset_flag(self, pg_runner, pg_app):
        # Seed initial
        pg_runner.invoke(args=["seed-demo"])
        # Reset and re-seed
        result = pg_runner.invoke(args=["seed-demo", "--reset"])
        assert result.exit_code == 0
        assert "Tables cleared." in result.output
        assert "Fictional demo dataset seeded successfully" in result.output

        with pg_app.app_context():
            assert db.session.scalar(select(db.func.count(User.id))) == 6

    def test_seed_demo_blocked_in_production_without_override(self, pg_app):
        # TC-OPS-03: Production requires explicit --i-understand-this-is-production
        orig_env = pg_app.config.get("APP_ENV")
        pg_app.config["APP_ENV"] = "production"
        try:
            runner = pg_app.test_cli_runner()
            result = runner.invoke(args=["seed-demo"])
            assert result.exit_code != 0
            assert "ABORTED: seed-demo in production requires" in result.output
        finally:
            pg_app.config["APP_ENV"] = orig_env

    def test_seed_demo_reset_strictly_forbidden_in_production(self, pg_app):
        # TC-OPS-03: --reset is strictly forbidden in production under all circumstances
        orig_env = pg_app.config.get("APP_ENV")
        pg_app.config["APP_ENV"] = "production"
        try:
            runner = pg_app.test_cli_runner()
            result = runner.invoke(args=["seed-demo", "--reset", "--i-understand-this-is-production"])
            assert result.exit_code != 0
            assert "strictly forbidden in production" in result.output
        finally:
            pg_app.config["APP_ENV"] = orig_env


@pytest.mark.integration
class TestSetupProductionAccountsCli:
    """Tests for setup-production-accounts CLI command and provisioning script."""

    def test_setup_production_accounts_creates_and_is_idempotent(self, pg_runner, pg_app):
        # 1. First run creates missing accounts
        res1 = pg_runner.invoke(
            args=[
                "setup-production-accounts",
                "--student-id", "4INI23IS036",
                "--teacher-id", "TCH001",
                "--teacher-name", "Mathematics Teacher",
                "--class-name", "10th Standard",
                "--section", "A",
                "--roll", "36",
            ]
        )
        assert res1.exit_code == 0
        assert "Production Accounts Setup" in res1.output
        assert "Linked to Mathematics" in res1.output

        with pg_app.app_context():
            stu = db.session.scalar(select(User).where(User.login_id == "4INI23IS036"))
            tch = db.session.scalar(select(User).where(User.login_id == "TCH001"))
            assert stu is not None
            assert stu.role == "student"
            assert tch is not None
            assert tch.role == "teacher"

        # 2. Second run is idempotent
        res2 = pg_runner.invoke(
            args=[
                "setup-production-accounts",
                "--student-id", "4INI23IS036",
                "--teacher-id", "TCH001",
            ]
        )
        assert res2.exit_code == 0
        assert "EXISTS" in res2.output

    def test_setup_production_accounts_prompt_passwords(self, pg_runner, pg_app):
        # Interactive prompt test with confirmation
        res = pg_runner.invoke(
            args=[
                "setup-production-accounts",
                "--prompt-passwords",
                "--student-id", "4INI23IS099",
                "--teacher-id", "TCH099",
                "--teacher-name", "Science Teacher",
                "--roll", "99",
            ],
            input="TeacherSecure123!\nTeacherSecure123!\nStudentSecure123!\nStudentSecure123!\n",
        )
        assert res.exit_code == 0
        assert "NOT ECHOED TO LOGS" in res.output

        with pg_app.app_context():
            stu = db.session.scalar(select(User).where(User.login_id == "4INI23IS099"))
            tch = db.session.scalar(select(User).where(User.login_id == "TCH099"))
            assert stu is not None
            assert stu.check_password("StudentSecure123!") is True
            assert tch is not None
            assert tch.check_password("TeacherSecure123!") is True


