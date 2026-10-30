"""Comprehensive End-to-End Tests for Teacher User Journeys using Page Object Model."""
from __future__ import annotations

from decimal import Decimal
import pytest
from app.extensions import db
from app.models import Exam, ExamSubject, Mark, MarkAudit, Student, Subject, User
from tests.e2e.pages import (
    LoginPage,
    StudentDashboardPage,
    TeacherDashboardPage,
)


@pytest.mark.e2e
class TestTeacherEndToEndJourneys:
    """Automates end-to-end teacher marks entry, permission checks, and audit verification."""

    def test_teacher_complete_workflow_and_audit_persistence(
        self, live_server, selenium_driver, e2e_seeded_data, e2e_db_session
    ):
        """TC-TEACHER-01: Teacher edits marks, verifies UI feedback, checks DB persistence and audit trail, and student views update."""
        driver = selenium_driver

        # 1. Teacher opens teacher login page and signs in
        login_page = LoginPage(driver).load_teacher(live_server)
        login_page.login("TCH001", "TeacherPass123!")

        # 2. Teacher dashboard loads with assigned students
        dashboard = TeacherDashboardPage(driver).wait_for_load()
        assert dashboard.get_teacher_code() == "TCH001"

        # Verify teacher sees assigned student (STU2026001) but NOT unassigned student (STU2026002)
        assert dashboard.is_student_in_list("STU2026001")
        assert not dashboard.is_student_in_list("STU2026002")

        # 3. Open marks modal for STU2026001
        modal = dashboard.open_marks_modal("STU2026001")
        assert modal.is_active()

        # Verify permission isolation: ENG and MAT are editable; HIN, SCI, SST are read-only
        assert modal.is_subject_editable("ENG")
        assert modal.is_subject_editable("MAT")
        assert not modal.is_subject_editable("HIN")
        assert not modal.is_subject_editable("SCI")
        assert not modal.is_subject_editable("SST")

        # 4. Teacher enters valid updated marks for ENG (85.5) and MAT (95.0)
        modal.enter_mark("ENG", "85.5")
        modal.enter_mark("MAT", "95.0")

        # 5. Teacher submits form
        modal.save_marks()

        # 6. UI displays success feedback and updated preview
        success_msg = modal.get_success_message()
        assert "Marks saved successfully!" in success_msg

        summary = modal.get_summary()
        assert "PASS" in summary["status"]

        # Close modal
        modal.close_via_button()
        dashboard.logout()

        # 7. Database Verification: Check PostgreSQL tables directly using isolated session
        exam_id = e2e_seeded_data["exam_id"]
        student = e2e_db_session.query(Student).filter_by(student_code="STU2026001").first()
        sub_eng = e2e_db_session.query(Subject).filter_by(code="ENG").first()
        sub_mat = e2e_db_session.query(Subject).filter_by(code="MAT").first()
        teacher_user = e2e_db_session.query(User).filter_by(login_id="TCH001").first()

        es_eng = e2e_db_session.query(ExamSubject).filter_by(exam_id=exam_id, subject_id=sub_eng.id).first()
        es_mat = e2e_db_session.query(ExamSubject).filter_by(exam_id=exam_id, subject_id=sub_mat.id).first()

        # Verify Marks updated
        mark_eng = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_eng.id).first()
        mark_mat = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_mat.id).first()
        assert mark_eng.marks_obtained == Decimal("85.50")
        assert mark_mat.marks_obtained == Decimal("95.00")

        # Verify Audit records exist with old and new values
        audits_eng = e2e_db_session.query(MarkAudit).filter_by(mark_id=mark_eng.id).all()
        assert len(audits_eng) >= 1
        latest_audit = audits_eng[-1]
        assert latest_audit.old_value == Decimal("78.50")
        assert latest_audit.new_value == Decimal("85.50")
        assert latest_audit.changed_by == teacher_user.id
        assert latest_audit.action.lower() == "update"

        # 8. Cross-Verification: Student logs in and verifies updated marks
        login_page = LoginPage(driver).load_student(live_server)
        login_page.login("STU2026001", "StudentPass123!")

        student_dash = StudentDashboardPage(driver).wait_for_load()
        student_modal = student_dash.open_result_modal()
        student_modal.wait_for_results_loaded()

        student_summary = student_modal.get_summary()
        # Old total was 330.50. ENG increased by 7.00, MAT increased by 5.00 -> New total = 342.50
        assert "342.5" in student_summary["total"]
        assert "68.5" in student_summary["percentage"]
        assert student_summary["grade"] == "B2"

        student_modal.close_via_button()
        student_dash.logout()

    def test_teacher_marks_clearing_confirmation_and_cancellation(
        self, live_server, selenium_driver, e2e_seeded_data, e2e_db_session
    ):
        """TC-TEACHER-02: Clearing marks triggers confirmation alert; cancelling preserves original values."""
        driver = selenium_driver

        login_page = LoginPage(driver).load_teacher(live_server)
        login_page.login("TCH001", "TeacherPass123!")

        dashboard = TeacherDashboardPage(driver).wait_for_load()
        modal = dashboard.open_marks_modal("STU2026001")

        # Clear ENG mark
        modal.clear_mark("ENG")

        # Case A: Teacher cancels confirmation -> form not submitted
        modal.save_marks(handle_confirmation=False)

        # Modal is still open, no success alert displayed
        assert not modal.is_visible(modal.SUCCESS_ALERT, timeout=1)

        # Database mark is unchanged
        exam_id = e2e_seeded_data["exam_id"]
        student = e2e_db_session.query(Student).filter_by(student_code="STU2026001").first()
        sub_eng = e2e_db_session.query(Subject).filter_by(code="ENG").first()
        es_eng = e2e_db_session.query(ExamSubject).filter_by(exam_id=exam_id, subject_id=sub_eng.id).first()
        mark_eng = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_eng.id).first()
        assert mark_eng.marks_obtained == Decimal("78.50")

        # Case B: Teacher accepts confirmation -> marks cleared, student result becomes INCOMPLETE
        modal.save_marks(handle_confirmation=True)
        success_msg = modal.get_success_message()
        assert "Marks saved successfully!" in success_msg

        # Summary in modal reflects INCOMPLETE
        summary = modal.get_summary()
        assert "INCOMPLETE" in summary["status"]

        # Database mark is now NULL (refresh session to pick up changes committed by live_server)
        e2e_db_session.expire_all()
        mark_eng = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_eng.id).first()
        assert mark_eng.marks_obtained is None

        modal.close_via_button()
        dashboard.logout()

    def test_teacher_cannot_modify_unassigned_student_via_api(
        self, live_server, selenium_driver, e2e_seeded_data, e2e_db_session
    ):
        """TC-TEACHER-03: Attempting to send a PUT request for an unassigned student is blocked with 404/403."""
        driver = selenium_driver

        login_page = LoginPage(driver).load_teacher(live_server)
        login_page.login("TCH001", "TeacherPass123!")
        dashboard = TeacherDashboardPage(driver).wait_for_load()

        # STU2026002 (Bob) is not assigned to TCH001
        bob_id = e2e_seeded_data["student2_id"]
        exam_id = e2e_seeded_data["exam_id"]
        eng_id = e2e_seeded_data["subjects"]["ENG"]
        es_eng = e2e_db_session.query(ExamSubject).filter_by(exam_id=exam_id, subject_id=eng_id).first()

        script = f"""
        const callback = arguments[arguments.length - 1];
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        fetch('/api/teacher/students/{bob_id}/marks', {{
            method: 'PUT',
            headers: {{
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRFToken': csrfToken
            }},
            body: JSON.stringify({{
                exam_id: {exam_id},
                marks: [{{subject_id: {eng_id}, marks_obtained: "99.00"}}]
            }})
        }})
        .then(res => res.json().then(data => callback({{status: res.status, body: data}})))
        .catch(err => callback({{status: 500, error: err.toString()}}));
        """
        response = driver.execute_async_script(script)

        # Verify operation is rejected with 404 (Not Found / Not assigned) or 403
        assert response["status"] in (403, 404)
        assert "not assigned" in response["body"]["error"]["message"].lower()

        # Verify Bob's marks in DB were NOT altered
        e2e_db_session.expire_all()
        mark = e2e_db_session.query(Mark).filter_by(student_id=bob_id, exam_subject_id=es_eng.id).first()
        assert mark.marks_obtained == Decimal("65.00")
        assert mark.marks_obtained != Decimal("99.00")

        dashboard.logout()
