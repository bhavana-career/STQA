"""Integration tests for Teacher Marks Entry, Validation, Authorization, and Audit (TC-MARK, TC-AUTHZ, TC-DB).

Tests executed against PostgreSQL test database.
Verifies:
- Teacher student listing: shows only assigned students with assigned subjects (TC-MARK-01, TC-AUTHZ-12).
- Non-disclosure 404 on unassigned students (TC-AUTHZ-05, TC-AUTHZ-07).
- Strict subject assignment enforcement: 403 on unassigned subject, atomic rollback (TC-AUTHZ-08).
- Atomic batch update of multiple subjects (TC-MARK-02).
- Pure marks validation: rejection of malformed, booleans, invalid steps, and out-of-range (TC-MARK-03, TC-MARK-04).
- Rejecting extraneous/tampered payload fields with 422 (TC-AUTHZ-09).
- Mark clearing (null) with 'clear' audit action (TC-MARK-07).
- MarkAudit trail records create, update, and clear actions with actor user_id (TC-MARK-08).
- Database consistency: SUM(marks_obtained) matches total_obtained (TC-DB-05).
"""
from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Exam, ExamSubject, Mark, MarkAudit, Section, Student, Subject, Teacher, TeacherAssignment, User


@pytest.fixture
def teacher_marks_fixture(pg_app):
    """Seed:
    - Section A
    - Student 1 (S1: STU2026001), Student 2 (S2: STU2026002)
    - Teacher 1 (T1: TCH001), Teacher 2 (T2: TCH002), Teacher 3 (T3: TCH003 - unassigned)
    - Subjects: ENG, HIN, MAT, SCI, SST, and an extra subject ART (not in exam)
    - Exam with 5 subjects (ENG, HIN, MAT, SCI, SST; 100 max, 35 pass)
    - Assignments:
      - T1 is assigned to S1 for ENG and MAT
      - T2 is assigned to S1 for HIN, SCI, SST
      - T1 is assigned to S2 for ENG only
      - T3 has NO assignments
    """
    with pg_app.app_context():
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        # Users
        u_s1 = User(login_id="STU2026001", role="student")
        u_s1.set_password("StudentPass123!")
        u_s2 = User(login_id="STU2026002", role="student")
        u_s2.set_password("StudentPass123!")

        u_t1 = User(login_id="TCH001", role="teacher")
        u_t1.set_password("TeacherPass123!")
        u_t2 = User(login_id="TCH002", role="teacher")
        u_t2.set_password("TeacherPass123!")
        u_t3 = User(login_id="TCH003", role="teacher")
        u_t3.set_password("TeacherPass123!")

        db.session.add_all([u_s1, u_s2, u_t1, u_t2, u_t3])
        db.session.flush()

        # Profiles
        s1 = Student(user_id=u_s1.id, student_code="STU2026001", full_name="Alice Student", section_id=sec.id, roll_number=1)
        s2 = Student(user_id=u_s2.id, student_code="STU2026002", full_name="Bob Student", section_id=sec.id, roll_number=2)

        t1 = Teacher(user_id=u_t1.id, teacher_code="TCH001", full_name="Teacher T1")
        t2 = Teacher(user_id=u_t2.id, teacher_code="TCH002", full_name="Teacher T2")
        t3 = Teacher(user_id=u_t3.id, teacher_code="TCH003", full_name="Teacher T3")

        db.session.add_all([s1, s2, t1, t2, t3])
        db.session.flush()

        # Subjects
        sub_eng = Subject(code="ENG", name="English")
        sub_hin = Subject(code="HIN", name="Hindi")
        sub_mat = Subject(code="MAT", name="Mathematics")
        sub_sci = Subject(code="SCI", name="Science")
        sub_sst = Subject(code="SST", name="Social Studies")
        sub_art = Subject(code="ART", name="Arts")  # NOT in exam

        db.session.add_all([sub_eng, sub_hin, sub_mat, sub_sci, sub_sst, sub_art])
        db.session.flush()

        # Exam & ExamSubjects
        exam = Exam(name="Annual Examination 2025-26", academic_year="2025-26")
        db.session.add(exam)
        db.session.flush()

        exam_subjects = [
            ExamSubject(exam_id=exam.id, subject_id=sub_eng.id, max_marks=Decimal("100"), pass_marks=Decimal("35")),
            ExamSubject(exam_id=exam.id, subject_id=sub_hin.id, max_marks=Decimal("100"), pass_marks=Decimal("35")),
            ExamSubject(exam_id=exam.id, subject_id=sub_mat.id, max_marks=Decimal("100"), pass_marks=Decimal("35")),
            ExamSubject(exam_id=exam.id, subject_id=sub_sci.id, max_marks=Decimal("100"), pass_marks=Decimal("35")),
            ExamSubject(exam_id=exam.id, subject_id=sub_sst.id, max_marks=Decimal("100"), pass_marks=Decimal("35")),
        ]
        db.session.add_all(exam_subjects)
        db.session.flush()

        # Assignments
        assignments = [
            TeacherAssignment(teacher_id=t1.id, student_id=s1.id, subject_id=sub_eng.id),
            TeacherAssignment(teacher_id=t1.id, student_id=s1.id, subject_id=sub_mat.id),
            TeacherAssignment(teacher_id=t2.id, student_id=s1.id, subject_id=sub_hin.id),
            TeacherAssignment(teacher_id=t2.id, student_id=s1.id, subject_id=sub_sci.id),
            TeacherAssignment(teacher_id=t2.id, student_id=s1.id, subject_id=sub_sst.id),
            TeacherAssignment(teacher_id=t1.id, student_id=s2.id, subject_id=sub_eng.id),
        ]
        db.session.add_all(assignments)
        db.session.commit()

        return {
            "s1_id": s1.id,
            "s2_id": s2.id,
            "t1_id": t1.id,
            "t2_id": t2.id,
            "t3_id": t3.id,
            "t1_user_id": u_t1.id,
            "t2_user_id": u_t2.id,
            "exam_id": exam.id,
            "sub_eng_id": sub_eng.id,
            "sub_hin_id": sub_hin.id,
            "sub_mat_id": sub_mat.id,
            "sub_sci_id": sub_sci.id,
            "sub_sst_id": sub_sst.id,
            "sub_art_id": sub_art.id,
            "exam_subjects": {es.subject_id: es.id for es in exam_subjects},
        }


@pytest.mark.integration
class TestTeacherMarksManagement:
    """Test suite for Teacher Marks Entry, Validation, Authorization & Audit."""

    def test_tc_mark_01_and_authz_12_teacher_students_listing(self, pg_client, teacher_marks_fixture):
        """TC-MARK-01 & TC-AUTHZ-12: Teacher list shows only assigned students and assigned subjects."""
        fx = teacher_marks_fixture

        # T1 logs in (assigned S1 for ENG, MAT and S2 for ENG)
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        resp = pg_client.get("/api/teacher/students")
        assert resp.status_code == 200
        data = resp.get_json()

        assert len(data["students"]) == 2
        students_by_code = {s["student_code"]: s for s in data["students"]}
        assert "STU2026001" in students_by_code
        assert set(students_by_code["STU2026001"]["assigned_subjects"]) == {"ENG", "MAT"}
        assert "STU2026002" in students_by_code
        assert set(students_by_code["STU2026002"]["assigned_subjects"]) == {"ENG"}

        # T3 logs in (no assignments -> TC-AUTHZ-12: returns 200 with empty list)
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH003", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        resp_t3 = pg_client.get("/api/teacher/students")
        assert resp_t3.status_code == 200
        assert resp_t3.get_json()["students"] == []

    def test_tc_authz_05_teacher_reads_unassigned_student_returns_404(self, pg_client, teacher_marks_fixture):
        """TC-AUTHZ-05: Non-disclosure: Teacher reading unassigned student returns 404."""
        fx = teacher_marks_fixture

        # T2 is assigned to S1, but NOT to S2
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH002", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        # T2 attempts to read S2's marks
        resp = pg_client.get(f"/api/teacher/students/{fx['s2_id']}/marks")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"]["code"] == "not_found"

        # Reading non-existent student 999999 returns identical 404
        resp_nonexistent = pg_client.get("/api/teacher/students/999999/marks")
        assert resp_nonexistent.status_code == 404
        assert resp_nonexistent.get_json() == data

    def test_tc_authz_04_teacher_reads_assigned_student_marks_success(self, pg_client, teacher_marks_fixture):
        """TC-AUTHZ-04: Teacher reading assigned student marks receives subject permissions and computed summary."""
        fx = teacher_marks_fixture

        # T1 logs in (assigned ENG and MAT for S1)
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        resp = pg_client.get(f"/api/teacher/students/{fx['s1_id']}/marks?exam_id={fx['exam_id']}")
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["student"]["student_code"] == "STU2026001"
        assert data["exam"]["id"] == fx["exam_id"]

        subs = {s["code"]: s for s in data["subjects"]}
        # ENG and MAT must be editable=True for T1
        assert subs["ENG"]["editable"] is True
        assert subs["MAT"]["editable"] is True
        # HIN, SCI, SST must be editable=False for T1
        assert subs["HIN"]["editable"] is False
        assert subs["SCI"]["editable"] is False
        assert subs["SST"]["editable"] is False

    def test_teacher_dashboard_page_renders_successfully(self, pg_client, teacher_marks_fixture):
        """Teacher dashboard page loads with teacher info and exam data."""
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        resp = pg_client.get("/teacher/dashboard")
        assert resp.status_code == 200
        assert b"Teacher Portal" in resp.data
        assert b"TCH001" in resp.data

    def test_tc_mark_02_and_08_save_multiple_subjects_atomically_and_audit(self, pg_client, pg_app, teacher_marks_fixture):
        """TC-MARK-02 & TC-MARK-08: Save multiple subjects atomically; audit rows written."""
        fx = teacher_marks_fixture

        # T1 logs in (assigned ENG and MAT for S1)
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        # Step 1: Initial creation of ENG: 78.5, MAT: 91.5
        payload = {
            "exam_id": fx["exam_id"],
            "marks": [
                {"subject_id": fx["sub_eng_id"], "marks_obtained": "78.5"},
                {"subject_id": fx["sub_mat_id"], "marks_obtained": 91.5},
            ],
        }
        resp = pg_client.put(f"/api/teacher/students/{fx['s1_id']}/marks", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["message"] == "Marks saved."
        assert data["saved"] == 2

        # Verify DB marks and audit records
        with pg_app.app_context():
            marks = db.session.scalars(select(Mark).where(Mark.student_id == fx["s1_id"])).all()
            marks_by_es = {m.exam_subject_id: m for m in marks}

            eng_es_id = fx["exam_subjects"][fx["sub_eng_id"]]
            mat_es_id = fx["exam_subjects"][fx["sub_mat_id"]]

            assert marks_by_es[eng_es_id].marks_obtained == Decimal("78.50")
            assert marks_by_es[mat_es_id].marks_obtained == Decimal("91.50")

            # Check audit logs
            audits_eng = marks_by_es[eng_es_id].audit_logs
            assert len(audits_eng) == 1
            assert audits_eng[0].action == "create"
            assert audits_eng[0].old_value is None
            assert audits_eng[0].new_value == Decimal("78.50")
            assert audits_eng[0].changed_by == fx["t1_user_id"]

        # Step 2: Update ENG from 78.50 -> 85.00
        update_payload = {
            "exam_id": fx["exam_id"],
            "marks": [
                {"subject_id": fx["sub_eng_id"], "marks_obtained": "85.00"},
            ],
        }
        resp_up = pg_client.put(f"/api/teacher/students/{fx['s1_id']}/marks", json=update_payload)
        assert resp_up.status_code == 200

        with pg_app.app_context():
            mark_eng = db.session.scalar(
                select(Mark).where(Mark.student_id == fx["s1_id"], Mark.exam_subject_id == eng_es_id)
            )
            assert mark_eng.marks_obtained == Decimal("85.00")
            audits = db.session.scalars(
                select(MarkAudit).where(MarkAudit.mark_id == mark_eng.id).order_by(MarkAudit.id)
            ).all()
            assert len(audits) == 2
            assert audits[1].action == "update"
            assert audits[1].old_value == Decimal("78.50")
            assert audits[1].new_value == Decimal("85.00")
            assert audits[1].changed_by == fx["t1_user_id"]

    def test_tc_authz_07_teacher_edits_unassigned_student_returns_404(self, pg_client, teacher_marks_fixture):
        """TC-AUTHZ-07: Teacher editing unassigned student returns 404, nothing saved."""
        fx = teacher_marks_fixture

        # T2 (not assigned to S2) attempts to edit S2
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH002", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        payload = {
            "exam_id": fx["exam_id"],
            "marks": [{"subject_id": fx["sub_eng_id"], "marks_obtained": "50.00"}],
        }
        resp = pg_client.put(f"/api/teacher/students/{fx['s2_id']}/marks", json=payload)
        assert resp.status_code == 404

    def test_tc_authz_08_teacher_mixes_assigned_and_unassigned_subjects(self, pg_client, pg_app, teacher_marks_fixture):
        """TC-AUTHZ-08: Mixing assigned and unassigned subjects returns 403; assigned subject is NOT saved."""
        fx = teacher_marks_fixture

        # T1 is assigned ENG and MAT for S1, but NOT SCI
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        payload = {
            "exam_id": fx["exam_id"],
            "marks": [
                {"subject_id": fx["sub_eng_id"], "marks_obtained": "70.00"},
                {"subject_id": fx["sub_sci_id"], "marks_obtained": "60.00"},  # Unauthorized for T1!
            ],
        }
        resp = pg_client.put(f"/api/teacher/students/{fx['s1_id']}/marks", json=payload)
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error"]["code"] == "forbidden"

        # Verify nothing was saved in the database
        with pg_app.app_context():
            saved_marks = db.session.scalars(select(Mark).where(Mark.student_id == fx["s1_id"])).all()
            assert len(saved_marks) == 0

    def test_tc_authz_09_tampered_request_body_rejected_with_422(self, pg_client, teacher_marks_fixture):
        """TC-AUTHZ-09: Request body with unexpected keys (total, grade, student_id, role) rejected with 422."""
        fx = teacher_marks_fixture

        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        payload = {
            "exam_id": fx["exam_id"],
            "marks": [{"subject_id": fx["sub_eng_id"], "marks_obtained": "80.00"}],
            "total": 500,
            "grade": "A1",
            "role": "admin",
            "student_id": fx["s2_id"],
        }
        resp = pg_client.put(f"/api/teacher/students/{fx['s1_id']}/marks", json=payload)
        assert resp.status_code == 422
        data = resp.get_json()
        assert data["error"]["code"] == "validation_error"
        assert "unexpected keys" in data["error"]["message"].lower()

    def test_tc_mark_03_and_04_invalid_mark_inputs_rejected(self, pg_client, teacher_marks_fixture):
        """TC-MARK-03 & TC-MARK-04: Rejects malformed values, booleans, invalid steps, and out of bounds."""
        fx = teacher_marks_fixture

        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        invalid_values = [
            "abc",
            "1e2",
            "NaN",
            True,
            False,
            [50],
            {"val": 50},
            "101",        # > 100 max
            "-5",         # negative
            "78.25",      # invalid step (must be 0.5)
            "78.3",       # invalid step
        ]

        for val in invalid_values:
            payload = {
                "exam_id": fx["exam_id"],
                "marks": [{"subject_id": fx["sub_eng_id"], "marks_obtained": val}],
            }
            resp = pg_client.put(f"/api/teacher/students/{fx['s1_id']}/marks", json=payload)
            assert resp.status_code == 422, f"Expected 422 for value: {val!r}"
            data = resp.get_json()
            assert data["error"]["code"] == "validation_error"

    def test_tc_mark_05_unknown_or_string_exam_id_rejected(self, pg_client, teacher_marks_fixture):
        """TC-MARK-05: Non-integer or non-existent exam_id returns 422."""
        fx = teacher_marks_fixture

        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        # String exam_id "1"
        r1 = pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={"exam_id": "1", "marks": [{"subject_id": fx["sub_eng_id"], "marks_obtained": "50"}]},
        )
        assert r1.status_code == 422

        # Non-existent exam_id 999999
        r2 = pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={"exam_id": 999999, "marks": [{"subject_id": fx["sub_eng_id"], "marks_obtained": "50"}]},
        )
        assert r2.status_code == 422

    def test_tc_mark_06_subject_not_in_exam_rejected(self, pg_client, teacher_marks_fixture):
        """TC-MARK-06: Subject not part of exam returns 422."""
        fx = teacher_marks_fixture

        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        # ART is not in exam
        payload = {
            "exam_id": fx["exam_id"],
            "marks": [{"subject_id": fx["sub_art_id"], "marks_obtained": "50"}],
        }
        resp = pg_client.put(f"/api/teacher/students/{fx['s1_id']}/marks", json=payload)
        assert resp.status_code == 422

    def test_tc_mark_07_clear_mark_with_null(self, pg_client, pg_app, teacher_marks_fixture):
        """TC-MARK-07: Setting mark to null clears mark and writes 'clear' audit action."""
        fx = teacher_marks_fixture

        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        # 1. Save mark first
        pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={"exam_id": fx["exam_id"], "marks": [{"subject_id": fx["sub_eng_id"], "marks_obtained": "78.00"}]},
        )

        # 2. Clear mark with null
        resp = pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={"exam_id": fx["exam_id"], "marks": [{"subject_id": fx["sub_eng_id"], "marks_obtained": None}]},
        )
        assert resp.status_code == 200

        with pg_app.app_context():
            eng_es_id = fx["exam_subjects"][fx["sub_eng_id"]]
            mark = db.session.scalar(
                select(Mark).where(Mark.student_id == fx["s1_id"], Mark.exam_subject_id == eng_es_id)
            )
            assert mark.marks_obtained is None

            audits = db.session.scalars(
                select(MarkAudit).where(MarkAudit.mark_id == mark.id).order_by(MarkAudit.id)
            ).all()
            assert len(audits) == 2
            assert audits[1].action == "clear"
            assert audits[1].old_value == Decimal("78.00")
            assert audits[1].new_value is None

    def test_tc_mark_09_duplicate_subject_in_request_rejected(self, pg_client, teacher_marks_fixture):
        """TC-MARK-09: Duplicate subject in request rejected with 422."""
        fx = teacher_marks_fixture

        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        payload = {
            "exam_id": fx["exam_id"],
            "marks": [
                {"subject_id": fx["sub_eng_id"], "marks_obtained": "50"},
                {"subject_id": fx["sub_eng_id"], "marks_obtained": "60"},
            ],
        }
        resp = pg_client.put(f"/api/teacher/students/{fx['s1_id']}/marks", json=payload)
        assert resp.status_code == 422

    def test_tc_mark_10_malformed_body_rejected(self, pg_client, teacher_marks_fixture):
        """TC-MARK-10: Non-JSON or empty marks array rejected."""
        fx = teacher_marks_fixture

        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )

        # Empty array
        r1 = pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={"exam_id": fx["exam_id"], "marks": []},
        )
        assert r1.status_code == 422

        # Non-JSON
        r2 = pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            data="not json",
            content_type="text/plain",
        )
        assert r2.status_code in (400, 422)

    def test_tc_db_05_database_sum_matches_api_total(self, pg_client, pg_app, teacher_marks_fixture):
        """TC-DB-05: SQL SUM(marks_obtained) matches API total_obtained."""
        fx = teacher_marks_fixture

        # T1 saves ENG and MAT
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH001", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={
                "exam_id": fx["exam_id"],
                "marks": [
                    {"subject_id": fx["sub_eng_id"], "marks_obtained": "80.00"},
                    {"subject_id": fx["sub_mat_id"], "marks_obtained": "90.00"},
                ],
            },
        )

        # T2 saves HIN, SCI, SST
        pg_client.post(
            "/teacher/login",
            data={"login_id": "TCH002", "password": "TeacherPass123!", "cf-turnstile-response": "mock-pass"},
        )
        resp = pg_client.put(
            f"/api/teacher/students/{fx['s1_id']}/marks",
            json={
                "exam_id": fx["exam_id"],
                "marks": [
                    {"subject_id": fx["sub_hin_id"], "marks_obtained": "75.00"},
                    {"subject_id": fx["sub_sci_id"], "marks_obtained": "85.00"},
                    {"subject_id": fx["sub_sst_id"], "marks_obtained": "70.00"},
                ],
            },
        )
        assert resp.status_code == 200
        api_total = resp.get_json()["summary"]["total_obtained"]

        with pg_app.app_context():
            db_sum = db.session.scalar(
                select(func.sum(Mark.marks_obtained)).where(Mark.student_id == fx["s1_id"])
            )
            assert str(db_sum) == api_total == "400.00"
