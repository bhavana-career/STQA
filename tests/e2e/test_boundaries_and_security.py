"""End-to-End Tests for Boundary Values, Negative Input Validation, and Security Interlocks."""
from __future__ import annotations

from decimal import Decimal
import pytest
from app.extensions import db
from app.models import Exam, ExamSubject, Mark, MarkAudit, Student, Subject
from tests.e2e.pages import (
    LoginPage,
    StudentDashboardPage,
    TeacherDashboardPage,
)


@pytest.mark.e2e
class TestBoundariesAndSecurity:
    """Automates boundary marks testing, malformed inputs, audit safety, and role boundary enforcement."""

    def test_marks_valid_boundary_values(self, live_server, selenium_driver, e2e_seeded_data, e2e_db_session):
        """TC-BOUND-01: Valid boundary values 0.0 (min), 100.0 (max), and 55.5 (0.5 step) are saved and audited."""
        driver = selenium_driver

        login_page = LoginPage(driver).load_teacher(live_server)
        login_page.login("TCH001", "TeacherPass123!")

        dashboard = TeacherDashboardPage(driver).wait_for_load()
        modal = dashboard.open_marks_modal("STU2026001")

        # Enter boundary marks: ENG = 0.0, MAT = 100.0
        modal.enter_mark("ENG", "0")
        modal.enter_mark("MAT", "100")
        modal.save_marks()

        success_msg = modal.get_success_message()
        assert "Marks saved successfully!" in success_msg

        # Verify values in database
        exam_id = e2e_seeded_data["exam_id"]
        student = e2e_db_session.query(Student).filter_by(student_code="STU2026001").first()
        sub_eng = e2e_db_session.query(Subject).filter_by(code="ENG").first()
        sub_mat = e2e_db_session.query(Subject).filter_by(code="MAT").first()
        es_eng = e2e_db_session.query(ExamSubject).filter_by(exam_id=exam_id, subject_id=sub_eng.id).first()
        es_mat = e2e_db_session.query(ExamSubject).filter_by(exam_id=exam_id, subject_id=sub_mat.id).first()

        mark_eng = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_eng.id).first()
        mark_mat = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_mat.id).first()
        assert mark_eng.marks_obtained == Decimal("0.00")
        assert mark_mat.marks_obtained == Decimal("100.00")

        # Now test 0.5 decimal boundary: ENG = 55.5
        modal.enter_mark("ENG", "55.5")
        modal.save_marks()
        assert "Marks saved successfully!" in modal.get_success_message()

        e2e_db_session.expire_all()
        mark_eng = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_eng.id).first()
        assert mark_eng.marks_obtained == Decimal("55.50")

        modal.close_via_button()
        dashboard.logout()

    def test_marks_invalid_boundary_values_rejected(self, live_server, selenium_driver, e2e_seeded_data, e2e_db_session):
        """TC-BOUND-02: Invalid boundary values (-0.5, 100.5, step 55.25, and 'abc') are rejected with no audit records."""
        driver = selenium_driver

        login_page = LoginPage(driver).load_teacher(live_server)
        login_page.login("TCH001", "TeacherPass123!")

        dashboard = TeacherDashboardPage(driver).wait_for_load()
        modal = dashboard.open_marks_modal("STU2026001")

        # Count baseline audit records
        baseline_audit_count = e2e_db_session.query(MarkAudit).count()

        # Case 1: Value below minimum (-0.5)
        modal.enter_mark("ENG", "-0.5")
        modal.save_marks()
        assert modal.is_visible(modal.ERROR_ALERT) or modal.get_field_error("ENG") != ""

        # Case 2: Value above maximum (100.5)
        modal.enter_mark("ENG", "100.5")
        modal.save_marks()
        assert modal.is_visible(modal.ERROR_ALERT) or modal.get_field_error("ENG") != ""

        # Case 3: Invalid step increment (55.25)
        modal.enter_mark("ENG", "55.25")
        modal.save_marks()
        assert modal.is_visible(modal.ERROR_ALERT) or modal.get_field_error("ENG") != ""

        # Case 4: Non-numeric malformed string ('abc')
        modal.enter_mark("ENG", "abc")
        modal.save_marks()
        assert modal.is_visible(modal.ERROR_ALERT) or modal.get_field_error("ENG") != ""

        # Verification: Failed submissions NEVER create audit records in database
        exam_id = e2e_seeded_data["exam_id"]
        student = e2e_db_session.query(Student).filter_by(student_code="STU2026001").first()
        sub_eng = e2e_db_session.query(Subject).filter_by(code="ENG").first()
        es_eng = e2e_db_session.query(ExamSubject).filter_by(exam_id=exam_id, subject_id=sub_eng.id).first()
        current_audit_count = e2e_db_session.query(MarkAudit).count()
        mark_eng = e2e_db_session.query(Mark).filter_by(student_id=student.id, exam_subject_id=es_eng.id).first()

        assert current_audit_count == baseline_audit_count
        # Original value is intact
        assert mark_eng.marks_obtained == Decimal("78.50")

        modal.close_via_button()
        dashboard.logout()

    def test_portal_role_boundary_enforcement(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-BOUND-03: Cross-portal access between student and teacher routes returns 403 Forbidden."""
        driver = selenium_driver

        # 1. Student attempts to access teacher dashboard
        login_page = LoginPage(driver).load_student(live_server)
        login_page.login("STU2026001", "StudentPass123!")
        StudentDashboardPage(driver).wait_for_load()

        driver.get(f"{live_server}/teacher/dashboard")
        assert "403" in driver.page_source or "Access Denied" in driver.page_source

        # Logout student
        driver.get(f"{live_server}/student/dashboard")
        StudentDashboardPage(driver).wait_for_load().logout()

        # 2. Teacher attempts to access student dashboard
        login_page.load_teacher(live_server)
        login_page.login("TCH001", "TeacherPass123!")
        TeacherDashboardPage(driver).wait_for_load()

        driver.get(f"{live_server}/student/dashboard")
        assert "403" in driver.page_source or "Access Denied" in driver.page_source

        driver.get(f"{live_server}/teacher/dashboard")
        TeacherDashboardPage(driver).wait_for_load().logout()

    def test_unauthenticated_protected_route_redirection(self, live_server, selenium_driver):
        """TC-BOUND-04: Direct unauthenticated access to dashboards redirects to corresponding login pages."""
        driver = selenium_driver

        # Try accessing student dashboard directly
        driver.get(f"{live_server}/student/dashboard")
        login_page = LoginPage(driver)
        login_page.wait_for_title_contains("Student Portal Sign In")
        assert "/student/login" in driver.current_url

        # Try accessing teacher dashboard directly
        driver.get(f"{live_server}/teacher/dashboard")
        login_page.wait_for_title_contains("Teacher Portal Sign In")
        assert "/teacher/login" in driver.current_url
