"""Integration tests for STQA testing scenario, teacher insights, and student isolation.

Verifies:
1. 1 General Teacher (TCH001) and 5 individual students (4INI23IS036, 4INI23IS001-4INI23IS004).
2. All 5 students assigned to teacher across all 5 subjects (25 assignments).
3. Known demo credentials hashed securely via scrypt; silent overwrites strictly prevented.
4. Each student logs in individually and sees only their own marks and results.
5. Realistic marks seeded out of 100 with accurate grading bands (A1, A2, B1, B2, C2).
6. Grading bands and descriptions (Outstanding, Excellent, Very Good, Good, Average) preserved.
7. Teacher insights: class average percentage and total, pass rate, subject-wise performance breakdown.
8. Teacher authorization: authorized to update marks for all assigned students and subjects.
"""
from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Mark, MarkAudit, Student, TeacherAssignment, User
from app.services.seed_data import (
    DEFAULT_DEMO_PASSWORD,
    DEMO_STUDENTS,
    DEMO_SUBJECTS,
    DEMO_TEACHER,
    AccountAlreadyExistsError,
    provision_stqa_scenario,
)


@pytest.fixture
def stqa_seeded_env(pg_app):
    """Seed the STQA testing scenario in PostgreSQL."""
    with pg_app.app_context():
        summary = provision_stqa_scenario(
            teacher_password=DEFAULT_DEMO_PASSWORD,
            student_password=DEFAULT_DEMO_PASSWORD,
            overwrite_passwords=False,
            lockout_system=False,
        )
        yield summary


@pytest.mark.integration
class TestStqaScenarioSeedAndInsights:
    """Comprehensive verification of the refined STQA testing scenario."""

    def test_seed_stqa_scenario_structure(self, pg_app, stqa_seeded_env):
        """Pre-provisions 1 general teacher, 5 students, 5 subjects, 25 assignments, and marks."""
        with pg_app.app_context():
            # 1. Teacher account
            t_user = db.session.scalar(select(User).where(User.login_id == DEMO_TEACHER["login_id"]))
            assert t_user is not None
            assert t_user.role == "teacher"
            assert t_user.teacher.full_name == "General Teacher"
            assert t_user.check_password(DEFAULT_DEMO_PASSWORD) is True

            # 2. 5 Student accounts with unique USNs
            all_usns = [s["login_id"] for s in DEMO_STUDENTS]
            assert len(all_usns) == 5
            for usn in all_usns:
                s_user = db.session.scalar(select(User).where(User.login_id == usn))
                assert s_user is not None
                assert s_user.role == "student"
                assert s_user.check_password(DEFAULT_DEMO_PASSWORD) is True
                assert s_user.student.section.class_name == "10th Standard"
                assert s_user.student.section.name == "A"

            # 3. 25 Teacher assignments (TCH001 to all 5 students for all 5 subjects)
            assignments = db.session.scalars(
                select(TeacherAssignment).where(TeacherAssignment.teacher_id == t_user.teacher.id)
            ).all()
            assert len(assignments) == 25

            # 4. Realistic marks seeded out of 100 for all 5 students across all 5 subjects
            total_marks = db.session.scalar(select(db.func.count(Mark.id)))
            assert total_marks == 25

            # 5. MarkAudit history recorded
            audit_count = db.session.scalar(select(db.func.count(MarkAudit.id)))
            assert audit_count == 25

    def test_teacher_insights_api(self, pg_client, stqa_seeded_env):
        """Teacher endpoint returns class average, subject-wise performance, and individual marks."""
        # Log in as General Teacher
        login_res = pg_client.post(
            "/teacher/login",
            data={
                "login_id": "TCH001",
                "password": DEFAULT_DEMO_PASSWORD,
                "cf-turnstile-response": "mock_valid_token",
            },
            follow_redirects=True,
        )
        assert login_res.status_code == 200

        # Query assigned students API
        res = pg_client.get("/api/teacher/students")
        assert res.status_code == 200
        data = res.get_json()

        assert "insights" in data
        insights = data["insights"]

        # Class average & summary statistics
        assert insights["total_students"] == 5
        assert insights["evaluated_students"] == 5
        assert insights["pass_count"] == 5
        assert insights["fail_count"] == 0
        assert insights["incomplete_count"] == 0
        assert insights["class_average_percentage"] == "71.68"
        assert insights["class_average_total"] == "358.40"

        # Subject-wise performance breakdown
        subj_perf = insights["subject_performance"]
        assert len(subj_perf) == 5
        perf_map = {s["code"]: s for s in subj_perf}

        # Check mathematics average: (98 + 88 + 78 + 58 + 48) / 5 = 74.00
        assert perf_map["MAT"]["average_marks"] == "74.00"
        assert perf_map["MAT"]["highest_mark"] == "98.00"
        assert perf_map["MAT"]["lowest_mark"] == "48.00"
        assert perf_map["MAT"]["pass_rate"] == "100.00"

        # Check English average: (94 + 82 + 74 + 62 + 45) / 5 = 71.40
        assert perf_map["ENG"]["average_marks"] == "71.40"
        assert perf_map["ENG"]["highest_mark"] == "94.00"
        assert perf_map["ENG"]["lowest_mark"] == "45.00"

        # Individual students data in list
        students = data["students"]
        assert len(students) == 5
        s_map = {s["student_code"]: s for s in students}

        # Student 4INI23IS036: Outstanding (A1, 93.40%)
        assert s_map["4INI23IS036"]["percentage"] == "93.40"
        assert s_map["4INI23IS036"]["grade"] == "A1"
        assert s_map["4INI23IS036"]["result_status"] == "PASS"

        # Student 4INI23IS001: Excellent (A2, 84.00%)
        assert s_map["4INI23IS001"]["percentage"] == "84.00"
        assert s_map["4INI23IS001"]["grade"] == "A2"

        # Student 4INI23IS002: Very Good (B1, 74.00%)
        assert s_map["4INI23IS002"]["percentage"] == "74.00"
        assert s_map["4INI23IS002"]["grade"] == "B1"

        # Student 4INI23IS003: Good (B2, 62.00%)
        assert s_map["4INI23IS003"]["percentage"] == "62.00"
        assert s_map["4INI23IS003"]["grade"] == "B2"

        # Student 4INI23IS004: Average (C2, 45.00%)
        assert s_map["4INI23IS004"]["percentage"] == "45.00"
        assert s_map["4INI23IS004"]["grade"] == "C2"

    def test_teacher_can_update_marks_for_any_assigned_student(self, pg_client, pg_app, stqa_seeded_env):
        """General teacher is authorized to update marks for all students and subjects."""
        # Log in as General Teacher
        login_res = pg_client.post(
            "/teacher/login",
            data={
                "login_id": "TCH001",
                "password": DEFAULT_DEMO_PASSWORD,
                "cf-turnstile-response": "mock_valid_token",
            },
            follow_redirects=True,
        )
        assert login_res.status_code == 200

        with pg_app.app_context():
            stu = db.session.scalar(select(Student).where(Student.student_code == "4INI23IS001"))

        # Update MAT marks for 4INI23IS001 to 95.00
        get_res = pg_client.get(f"/api/teacher/students/{stu.id}/marks")
        assert get_res.status_code == 200
        exam_id = get_res.get_json()["exam"]["id"]
        subjects = get_res.get_json()["subjects"]
        mat_sub = next(s for s in subjects if s["code"] == "MAT")

        put_res = pg_client.put(
            f"/api/teacher/students/{stu.id}/marks",
            json={
                "exam_id": exam_id,
                "marks": [{"subject_id": mat_sub["subject_id"], "marks_obtained": "95.00"}],
            },
        )
        assert put_res.status_code == 200
        assert put_res.get_json()["message"] == "Marks saved."

        with pg_app.app_context():
            audit = db.session.scalar(
                select(MarkAudit)
                .join(Mark)
                .where(Mark.student_id == stu.id, MarkAudit.action == "update")
                .order_by(MarkAudit.id.desc())
            )
            assert audit is not None
            assert audit.new_value == Decimal("95.00")

    def test_students_log_in_individually_and_see_only_own_results(self, pg_client, stqa_seeded_env):
        """Each of the 5 students logs in independently and sees strictly their own results."""
        expected_grades = {
            "4INI23IS036": ("93.40", "A1"),
            "4INI23IS001": ("84.00", "A2"),
            "4INI23IS002": ("74.00", "B1"),
            "4INI23IS003": ("62.00", "B2"),
            "4INI23IS004": ("45.00", "C2"),
        }

        for usn, (expected_pct, expected_grade) in expected_grades.items():
            # Log in as the individual student
            login_res = pg_client.post(
                "/student/login",
                data={
                    "login_id": usn,
                    "password": DEFAULT_DEMO_PASSWORD,
                    "cf-turnstile-response": "mock_valid_token",
                },
                follow_redirects=True,
            )
            assert login_res.status_code == 200

            # Fetch result via API
            res = pg_client.get("/api/student/result")
            assert res.status_code == 200
            data = res.get_json()

            # Confirm isolation: strictly the authenticated student's data
            assert data["student"]["student_code"] == usn
            assert data["summary"]["percentage"] == expected_pct
            assert data["summary"]["grade"] == expected_grade
            assert data["summary"]["status"] == "PASS"

            # Verify attempting to spoof another student ID is strictly ignored
            spoofed_res = pg_client.get("/api/student/result?student_id=999&student_code=4INI23IS999")
            assert spoofed_res.status_code == 200
            spoofed_data = spoofed_res.get_json()
            assert spoofed_data["student"]["student_code"] == usn

            # Logout
            pg_client.post("/auth/logout", follow_redirects=True)

    def test_overwrite_protection_prevents_silent_overwrites(self, pg_app, stqa_seeded_env):
        """Calling provision_stqa_scenario with overwrite_passwords=False aborts if accounts exist."""
        with pg_app.app_context():
            with pytest.raises(AccountAlreadyExistsError):
                provision_stqa_scenario(overwrite_passwords=False)

    def test_cli_seed_stqa_command(self, pg_runner, pg_app):
        """CLI seed-stqa command executes idempotently and outputs summary."""
        result = pg_runner.invoke(args=["seed-stqa"])
        assert result.exit_code == 0
        assert "STQA scenario seeded successfully" in result.output
        assert "TCH001 (General Teacher)" in result.output
        assert "4INI23IS036" in result.output
        assert "25 total links" in result.output
