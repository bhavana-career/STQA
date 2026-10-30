"""Integration tests for Student Result Calculation API (TC-CALC, TC-AUTHZ).

Tests executed against PostgreSQL test database.
Verifies:
- Strict student isolation: Cannot view other students' results (TC-AUTHZ-03).
- Missing marks produce INCOMPLETE status (TC-CALC-06).
- Complete marks produce PASS/FAIL with accurate calculations (TC-CALC-14, TC-CALC-15).
- Role segregation: Teacher cannot access student result endpoint (403).
- Unauthenticated access returns 401.
"""
from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Exam, ExamSubject, Mark, Section, Student, Subject, Teacher, TeacherAssignment, User


@pytest.fixture
def student_results_fixture(pg_app):
    """Seed two students (S1, S2), 5 subjects, and an exam with initial marks."""
    with pg_app.app_context():
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        # Student 1
        u1 = User(login_id="STU2026001", role="student")
        u1.set_password("StudentPass123!")
        db.session.add(u1)
        db.session.flush()

        s1 = Student(
            user_id=u1.id,
            student_code="STU2026001",
            full_name="Alice Student",
            section_id=sec.id,
            roll_number=1,
        )
        db.session.add(s1)

        # Student 2
        u2 = User(login_id="STU2026002", role="student")
        u2.set_password("StudentPass123!")
        db.session.add(u2)
        db.session.flush()

        s2 = Student(
            user_id=u2.id,
            student_code="STU2026002",
            full_name="Bob Student",
            section_id=sec.id,
            roll_number=2,
        )
        db.session.add(s2)

        # Teacher user (updater)
        u_t = User(login_id="TCH001", role="teacher")
        u_t.set_password("TeacherPass123!")
        db.session.add(u_t)

        # 5 Subjects
        subjects = [
            Subject(code="ENG", name="English"),
            Subject(code="HIN", name="Hindi"),
            Subject(code="MAT", name="Mathematics"),
            Subject(code="SCI", name="Science"),
            Subject(code="SST", name="Social Studies"),
        ]
        db.session.add_all(subjects)
        db.session.flush()

        # Exam
        exam = Exam(name="Annual Examination 2025-26", academic_year="2025-26")
        db.session.add(exam)
        db.session.flush()

        # Exam subjects (100 max, 35 pass)
        exam_subjects = []
        for sub in subjects:
            es = ExamSubject(exam_id=exam.id, subject_id=sub.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
            exam_subjects.append(es)
        db.session.add_all(exam_subjects)
        db.session.flush()

        # Initial Marks for Student 1: 5 subjects (78, 65, 90, 55, 42) -> Total 330/500, 66.00%, B2, PASS
        marks_s1 = [
            Mark(student_id=s1.id, exam_subject_id=exam_subjects[0].id, marks_obtained=Decimal("78.00"), updated_by=u_t.id),
            Mark(student_id=s1.id, exam_subject_id=exam_subjects[1].id, marks_obtained=Decimal("65.00"), updated_by=u_t.id),
            Mark(student_id=s1.id, exam_subject_id=exam_subjects[2].id, marks_obtained=Decimal("90.00"), updated_by=u_t.id),
            Mark(student_id=s1.id, exam_subject_id=exam_subjects[3].id, marks_obtained=Decimal("55.00"), updated_by=u_t.id),
            Mark(student_id=s1.id, exam_subject_id=exam_subjects[4].id, marks_obtained=Decimal("42.00"), updated_by=u_t.id),
        ]
        db.session.add_all(marks_s1)

        # Student 2 has only 3 marks entered (ENG: 95, MAT: 98, SCI: 92; HIN and SST missing -> INCOMPLETE)
        marks_s2 = [
            Mark(student_id=s2.id, exam_subject_id=exam_subjects[0].id, marks_obtained=Decimal("95.00"), updated_by=u_t.id),
            Mark(student_id=s2.id, exam_subject_id=exam_subjects[2].id, marks_obtained=Decimal("98.00"), updated_by=u_t.id),
            Mark(student_id=s2.id, exam_subject_id=exam_subjects[3].id, marks_obtained=Decimal("92.00"), updated_by=u_t.id),
        ]
        db.session.add_all(marks_s2)
        t = Teacher(user_id=u_t.id, teacher_code="TCH001", full_name="Robert Brown")
        db.session.add(t)
        db.session.flush()

        ta = TeacherAssignment(teacher_id=t.id, student_id=s1.id, subject_id=subjects[2].id)  # MAT
        db.session.add(ta)
        db.session.commit()

        return {
            "s1_id": s1.id,
            "s2_id": s2.id,
            "exam_id": exam.id,
            "u1_id": u1.id,
            "u2_id": u2.id,
            "teacher_user_id": u_t.id,
            "sub_mat_id": subjects[2].id,
        }


@pytest.mark.integration
class TestStudentResultAPI:
    """Tests for GET /api/student/result and isolation rules."""

    def test_tc_authz_03_student_cannot_view_other_student_result(self, pg_client, student_results_fixture):
        """TC-AUTHZ-03: Student requesting another student's result via param gets their OWN data only."""
        # Log in as Alice (S1)
        login_resp = pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock-pass"},
        )
        assert login_resp.status_code == 302

        # S1 attempts to request S2's result by tampering with query params
        s2_id = student_results_fixture["s2_id"]
        resp = pg_client.get(f"/api/student/result?student_id={s2_id}&student_code=STU2026002")

        assert resp.status_code == 200
        data = resp.get_json()

        # Must return Alice's (S1) result ONLY
        assert data["student"]["student_code"] == "STU2026001"
        assert data["student"]["full_name"] == "Alice Student"
        assert data["summary"]["status"] == "PASS"
        assert data["summary"]["total_obtained"] == "330.00"
        assert data["summary"]["percentage"] == "66.00"
        assert data["summary"]["grade"] == "B2"

        # Bob's data must not be present anywhere in the payload
        assert "Bob" not in resp.get_data(as_text=True)
        assert "STU2026002" not in resp.get_data(as_text=True)

    def test_tc_calc_06_missing_marks_returns_incomplete_status(self, pg_client, student_results_fixture):
        """TC-CALC-06: Student with missing marks receives INCOMPLETE result."""
        # Log in as Bob (S2)
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026002", "password": "StudentPass123!", "cf-turnstile-response": "mock-pass"},
        )

        resp = pg_client.get("/api/student/result")
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["student"]["student_code"] == "STU2026002"
        assert data["summary"]["status"] == "INCOMPLETE"
        assert data["summary"]["total_obtained"] is None
        assert data["summary"]["percentage"] is None
        assert data["summary"]["grade"] is None

        # Verify subject items
        subs_by_code = {s["code"]: s for s in data["subjects"]}
        assert subs_by_code["ENG"]["marks_obtained"] == "95.00"
        assert subs_by_code["ENG"]["grade"] == "A1"
        assert subs_by_code["ENG"]["passed"] is True

        # Missing subjects
        assert subs_by_code["HIN"]["marks_obtained"] is None
        assert subs_by_code["HIN"]["grade"] is None
        assert subs_by_code["HIN"]["passed"] is None

        assert subs_by_code["SST"]["marks_obtained"] is None
        assert subs_by_code["SST"]["grade"] is None
        assert subs_by_code["SST"]["passed"] is None

    def test_tc_calc_15_server_side_result_calculation_integrity(self, pg_client, student_results_fixture):
        """TC-CALC-15: Server calculates all aggregates; client input is ignored."""
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock-pass"},
        )

        # GET request with fake client calculations attached in params
        resp = pg_client.get("/api/student/result?total=500&percentage=100.00&grade=A1&status=PASS")
        assert resp.status_code == 200
        data = resp.get_json()

        # Calculation MUST match DB rows (330.00 / 66.00% / B2)
        assert data["summary"]["total_obtained"] == "330.00"
        assert data["summary"]["percentage"] == "66.00"
        assert data["summary"]["grade"] == "B2"
        assert data["summary"]["status"] == "PASS"

    def test_unknown_exam_id_returns_404(self, pg_client, student_results_fixture):
        """Requesting an unknown exam_id returns 404."""
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock-pass"},
        )

        resp = pg_client.get("/api/student/result?exam_id=999999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"]["code"] == "not_found"

    def test_invalid_exam_id_param_returns_400(self, pg_client, student_results_fixture):
        """Requesting with malformed exam_id param returns 400."""
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock-pass"},
        )

        resp = pg_client.get("/api/student/result?exam_id=not-a-number")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "bad_request"

    def test_unauthenticated_access_returns_401(self, pg_client):
        """Unauthenticated call to /api/student/result returns 401."""
        resp = pg_client.get("/api/student/result")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "unauthenticated"

    def test_teacher_blocked_from_student_result_api(self, pg_client, student_results_fixture):
        """Teacher cannot access student result API (role segregation -> 403)."""
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        resp = pg_client.get("/api/student/result")
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error"]["code"] == "forbidden"

    def test_tc_calc_14_updated_marks_reflected_in_result(self, pg_client, student_results_fixture):
        """TC-CALC-14: Updated marks saved by teacher are immediately reflected in student result."""
        fx = student_results_fixture

        # Step 1: Teacher T1 logs in and updates S1's Mathematics from 90.00 to 95.00 (+5.00)
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        put_resp = pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={
                "exam_id": fx["exam_id"],
                "marks": [{"subject_id": fx["sub_mat_id"], "marks_obtained": "95.00"}],
            },
        )
        assert put_resp.status_code == 200

        # Step 2: Teacher logs out, Student S1 logs in
        pg_client.post("/logout")
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock-pass"},
        )

        # Step 3: S1 gets their result -> total increases from 330 to 335 (67.00%)
        res = pg_client.get("/api/student/result")
        assert res.status_code == 200
        data = res.get_json()

        assert data["summary"]["total_obtained"] == "335.00"
        assert data["summary"]["percentage"] == "67.00"
        assert data["summary"]["grade"] == "B2"
        assert data["summary"]["status"] == "PASS"

        mat_sub = next(s for s in data["subjects"] if s["code"] == "MAT")
        assert mat_sub["marks_obtained"] == "95.00"
        assert mat_sub["percentage"] == "95.00"
        assert mat_sub["grade"] == "A1"

    def test_student_dashboard_page_renders_successfully(self, pg_client, student_results_fixture):
        """Student dashboard page loads with student profile, exam details, and result modal markup."""
        pg_client.post(
            "/student/login",
            data={"login_id": "STU2026001", "password": "StudentPass123!", "cf-turnstile-response": "mock-pass"},
        )
        resp = pg_client.get("/student/dashboard")
        assert resp.status_code == 200
        assert b"Student Portal" in resp.data
        assert b"STU2026001" in resp.data
        assert b"Alice Student" in resp.data
        assert b"View Detailed Result" in resp.data
        assert b"result-modal" in resp.data


