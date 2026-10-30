"""Comprehensive End-to-End Tests for Student User Journeys using Page Object Model."""
from __future__ import annotations

import pytest
from tests.e2e.pages import (
    HomePage,
    LoginPage,
    StudentDashboardPage,
    ResultModal,
)


@pytest.mark.e2e
class TestStudentEndToEndJourneys:
    """Automates end-to-end student scenarios, accessibility checks, and boundary cases."""

    def test_student_complete_success_journey(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-STUDENT-01: Complete student workflow from landing page to result inspection, modal closing, and logout."""
        driver = selenium_driver

        # 1. Student opens the application landing page
        home = HomePage(driver).load(live_server)
        assert "10th Standard Result Portal" in home.get_portal_title()
        assert home.is_student_link_visible()

        # 2. Student navigates to the student login page
        login_page = home.click_student_portal()
        assert login_page.get_login_id_placeholder() == "STU2026001"
        assert login_page.get_password_input_type() == "password"

        # 3. Student logs in with valid credentials
        login_page.login("STU2026001", "StudentPass123!")

        # 4. Student dashboard loads with correct student identity
        dashboard = StudentDashboardPage(driver).wait_for_load()
        assert dashboard.get_student_name() == "Alice Student"
        assert "STU2026001" in dashboard.get_student_code()
        assert dashboard.is_view_result_button_available()

        # 5. Student opens detailed result modal
        modal = dashboard.open_result_modal()
        modal.wait_for_results_loaded()
        assert modal.is_active()

        # 6. Student verifies summary metrics and subject marks
        summary = modal.get_summary()
        assert "330.5" in summary["total"] and "500" in summary["total"]
        assert "66.1" in summary["percentage"]
        assert summary["grade"] == "B2"
        assert "PASS" in summary["status"]

        subjects = modal.get_subject_rows()
        assert len(subjects) == 5
        subject_names = [s["subject"] for s in subjects]
        assert any("English" in name for name in subject_names)
        assert any("Mathematics" in name for name in subject_names)

        # 7. Student closes the modal using the close button
        modal.close_via_button()
        assert not modal.is_active()

        # 8. Student opens modal again and closes accessibly using the Escape key
        modal = dashboard.open_result_modal()
        modal.wait_for_results_loaded()
        assert modal.is_active()
        modal.close_via_escape()
        assert not modal.is_active()

        # 9. Student logs out successfully
        dashboard.logout()
        home.wait_for_title_contains("Student Result Management System")

        # 10. Student cannot access protected dashboard after logout
        driver.get(f"{live_server}/student/dashboard")
        login_page.wait_for_title_contains("Student Portal Sign In")
        assert "/student/login" in driver.current_url

    def test_student_invalid_credentials_rejected(self, live_server, selenium_driver):
        """TC-STUDENT-02: Submitting incorrect password displays non-revealing error banner."""
        driver = selenium_driver
        login_page = LoginPage(driver).load_student(live_server)

        login_page.login("STU2026001", "IncorrectPassword123!")

        assert login_page.is_error_displayed()
        assert "Invalid ID or password." in login_page.get_error_message()
        assert "/student/login" in driver.current_url

    def test_student_portal_rejects_teacher_credentials(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-STUDENT-03: Attempting to use teacher credentials on student login portal is rejected."""
        driver = selenium_driver
        login_page = LoginPage(driver).load_student(live_server)

        login_page.login("TCH001", "TeacherPass123!")

        assert login_page.is_error_displayed()
        assert "Invalid ID or password." in login_page.get_error_message()
        assert "/student/login" in driver.current_url

    def test_student_incomplete_result_state(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-STUDENT-04: Student with missing/incomplete subject marks sees INCOMPLETE status banner."""
        driver = selenium_driver

        login_page = LoginPage(driver).load_student(live_server)
        login_page.login("STU2026002", "StudentPass123!")

        dashboard = StudentDashboardPage(driver).wait_for_load()
        assert dashboard.get_student_name() == "Bob Student"

        modal = dashboard.open_result_modal()
        modal.wait_for_results_loaded()

        summary = modal.get_summary()
        assert "INCOMPLETE" in summary["status"]
        assert summary["percentage"] == "—" or "—" in summary["percentage"]

        modal.close_via_button()
        dashboard.logout()

    def test_student_cannot_access_another_students_result(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-STUDENT-05: Authenticated student cannot tamper request to inspect another student's marks."""
        driver = selenium_driver

        # Alice (STU2026001) logs in
        login_page = LoginPage(driver).load_student(live_server)
        login_page.login("STU2026001", "StudentPass123!")
        dashboard = StudentDashboardPage(driver).wait_for_load()

        # Alice attempts to query the student result API with query parameters targeting Bob (STU2026002)
        script = """
        const callback = arguments[arguments.length - 1];
        fetch('/api/student/result?student_id=9999&student_code=STU2026002', {
            headers: {'Accept': 'application/json'}
        })
        .then(res => res.json())
        .then(data => callback(data))
        .catch(err => callback({error: err.toString()}));
        """
        response_data = driver.execute_async_script(script)

        # Ensure server securely ignores query parameters and returns ONLY Alice's own result
        assert response_data.get("student", {}).get("student_code") == "STU2026001"
        assert response_data.get("student", {}).get("student_code") != "STU2026002"
        assert response_data.get("summary", {}).get("status") == "PASS"

        dashboard.logout()
