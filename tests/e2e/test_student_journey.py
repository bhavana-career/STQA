"""Selenium End-to-End automation for the complete Student Journey (passing & failing students)."""

import pytest
from app.config import SUBJECTS
from tests.e2e.pages import LoginPage, StudentDashboardPage


@pytest.mark.e2e
class TestStudentSeleniumJourney:
    """
    Automates the 14-step Student Journey specified in Section 18:
    1. Open localhost application.
    2. Log in as student.
    3. Verify student dashboard.
    4. Verify personal details.
    5. Verify six subject marks.
    6. Verify subject grades.
    7. Verify total marks.
    8. Verify percentage.
    9. Verify overall classification.
    10. Verify grading matrix.
    11. Verify success popup for a passing student.
    12. Verify no success popup for a failing student.
    13. Verify student cannot access teacher functions.
    14. Log out.
    """

    def test_complete_student_journey_passing_and_failing_e2e(self, browser, live_server_url):
        login_page = LoginPage(browser, live_server_url)
        student_page = StudentDashboardPage(browser, live_server_url)

        # --- PART A: Passing Student (student01 / Aarav Kulkarni) ---
        # Step 1 & 2: Open localhost application and log in as student01
        login_page.open()
        login_page.login("student01", "Student@123")

        # Step 11: Verify success popup appears for a passing student on initial login
        assert student_page.is_success_popup_visible() is True
        student_page.dismiss_success_popup()
        assert student_page.is_success_popup_visible() is False

        # Step 3 & 4: Verify student dashboard and personal details
        summary = student_page.get_summary_metrics()
        assert summary["name"] == "Aarav Kulkarni"
        assert summary["student_id"] == "STU001"

        # Step 5 & 6: Verify six subject marks and subject grades
        expected_subjects = {
            "Physics": ("92", "O"),
            "Chemistry": ("88", "A+"),
            "Mathematics": ("95", "O"),
            "Computer Science": ("96", "O"),
            "Kannada": ("85", "A+"),
            "English": ("90", "O"),
        }
        for subj in SUBJECTS:
            exp_marks, exp_grade = expected_subjects[subj]
            details = student_page.get_subject_row_details(subj)
            assert details["marks"] == exp_marks
            assert details["grade"] == exp_grade

        # Step 7, 8, 9: Verify total marks, percentage, overall classification
        assert summary["total"] == "546 / 600"
        assert summary["percentage"] == "91.00%"
        assert summary["classification"] == "Distinction"
        assert summary["status"] == "PASS"

        # Step 10: Verify grading matrix is displayed and navigation does not re-trigger popup
        assert student_page.is_grading_matrix_displayed() is True
        student_page.navigate_to_my_results()
        assert student_page.is_success_popup_visible() is False
        student_page.navigate_to_grading_matrix()
        assert student_page.is_success_popup_visible() is False

        # Step 13: Verify student cannot access teacher functions or another student's record
        student_page.open_path("/teacher/dashboard")
        assert "403" in browser.page_source
        assert "Access Denied" in browser.page_source

        student_page.open_path("/student/view/STU002")
        assert "403" in browser.page_source

        # Return to student dashboard and Step 14: Log out
        student_page.open_path("/student/dashboard")
        student_page.logout()

        # --- PART B: Failing Student (student03 / Rohan Deshmukh) ---
        # Step 12: Verify no success popup for a failing student (failed Mathematics with 28)
        login_page.login("student03", "Student@123")
        assert student_page.is_success_popup_visible() is False

        fail_summary = student_page.get_summary_metrics()
        assert fail_summary["name"] == "Rohan Deshmukh"
        assert fail_summary["total"] == "426 / 600"
        assert fail_summary["percentage"] == "71.00%"
        assert fail_summary["classification"] == "Fail"
        assert fail_summary["status"] == "FAIL"

        math_details = student_page.get_subject_row_details("Mathematics")
        assert math_details["marks"] == "28"
        assert math_details["grade"] == "F"

        student_page.logout()
