"""Selenium End-to-End automation for the complete Teacher Journey and validation scenarios."""

import pytest
from app.config import SUBJECTS
from tests.e2e.pages import (
    LoginPage,
    TeacherDashboardPage,
    StudentManagementPage,
    MarksEntryPage,
    AnalyticsPage,
)


@pytest.mark.e2e
class TestTeacherSeleniumJourney:
    """
    Automates the 15-step Teacher Journey specified in Section 18:
    1. Open localhost application.
    2. Log in as teacher.
    3. Verify teacher dashboard.
    4. Navigate to student management.
    5. Add a student.
    6. Search for the student.
    7. Update student details.
    8. Enter marks.
    9. Verify automatic calculations.
    10. Verify individual grades.
    11. Verify overall classification.
    12. Navigate to class analytics.
    13. Verify section averages.
    14. Delete the test student.
    15. Log out.
    """

    def test_complete_teacher_journey_e2e(self, browser, live_server_url):
        login_page = LoginPage(browser, live_server_url)
        dashboard_page = TeacherDashboardPage(browser, live_server_url)
        students_page = StudentManagementPage(browser, live_server_url)
        marks_page = MarksEntryPage(browser, live_server_url)
        analytics_page = AnalyticsPage(browser, live_server_url)

        # Step 1: Open localhost application
        login_page.open()

        # Verify password toggle works
        assert login_page.toggle_password_visibility() == "text"
        assert login_page.toggle_password_visibility() == "password"

        # Step 2: Log in as teacher
        login_page.login("teacher01", "Teacher@123")

        # Step 3: Verify teacher dashboard
        assert dashboard_page.verify_loaded() is True
        initial_total = dashboard_page.get_total_students_count()
        assert initial_total == 5

        # Step 4: Navigate to student management
        dashboard_page.go_to_student_management()

        # Step 5: Add a student
        initial_marks = {subj: 70 for subj in SUBJECTS}
        students_page.add_student(
            student_id="STU888",
            name="Siddharth Menon",
            username="siddharth888",
            password="Student@123",
            section="B",
            roll_number=288,
            marks=initial_marks,
        )
        assert "created successfully" in students_page.get_flash_text()

        # Step 6: Search for the student
        students_page.search_student("Siddharth")
        assert students_page.is_student_in_table("STU888") is True
        assert students_page.is_student_in_table("STU001") is False

        # Step 7: Update student details
        students_page.open_edit_for_student("STU888")
        students_page.update_student_details(
            new_name="Siddharth V. Menon",
            new_section="B",
            new_roll=289,
        )
        assert "updated successfully" in students_page.get_flash_text()

        # Step 8: Navigate to marks management & enter updated marks
        dashboard_page.go_to_marks_management()
        marks_page.select_student("STU888")

        updated_marks = {
            "Physics": 92,          # O
            "Chemistry": 86,        # A+
            "Mathematics": 81,      # A
            "Computer Science": 75, # B+
            "Kannada": 65,          # B
            "English": 81,          # A
        }
        # Total = 92 + 86 + 81 + 75 + 65 + 81 = 480 / 600 -> 80.00% -> Distinction
        marks_page.enter_marks(updated_marks)

        # Step 9: Verify automatic calculations
        assert marks_page.get_calculated_total() == "480 / 600"
        assert marks_page.get_calculated_percentage() == "80.00%"

        # Step 10: Verify individual grades
        assert marks_page.get_subject_grade("Physics") == "O"
        assert marks_page.get_subject_grade("Chemistry") == "A+"
        assert marks_page.get_subject_grade("Mathematics") == "A"
        assert marks_page.get_subject_grade("Computer Science") == "B+"
        assert marks_page.get_subject_grade("Kannada") == "B"
        assert marks_page.get_subject_grade("English") == "A"

        # Step 11: Verify overall classification
        assert "Distinction" in marks_page.get_calculated_classification()

        # Step 12: Navigate to class analytics
        dashboard_page.go_to_analytics()

        # Step 13: Verify section averages (Section A has 3 students, average 63.17%)
        analytics_page.select_section("A")
        metrics_a = analytics_page.get_section_metrics()
        assert metrics_a["student_count"] == "3"
        assert metrics_a["avg_pct"] == "63.17%"

        # Verify Section B now has 2 students (STU002 at 68.67% + STU888 at 80.00% -> Avg 74.34%)
        analytics_page.select_section("B")
        metrics_b = analytics_page.get_section_metrics()
        assert metrics_b["student_count"] == "2"
        assert metrics_b["avg_pct"] == "74.34%"

        # Step 14: Delete the test student
        dashboard_page.go_to_student_management()
        students_page.delete_student("STU888")
        assert "deleted permanently" in students_page.get_flash_text()
        assert students_page.is_student_in_table("STU888") is False

        # Step 15: Log out
        students_page.logout()

    def test_invalid_credentials_and_invalid_marks_in_browser(self, browser, live_server_url):
        login_page = LoginPage(browser, live_server_url)
        dashboard_page = TeacherDashboardPage(browser, live_server_url)
        marks_page = MarksEntryPage(browser, live_server_url)

        # Invalid login in browser
        login_page.open()
        login_page.login("teacher01", "WrongPass999")
        assert "Invalid username or password" in login_page.get_error_message()

        # Log in as teacher and attempt to submit out-of-range marks via server validation
        login_page.login("teacher01", "Teacher@123")
        dashboard_page.go_to_marks_management()
        marks_page.select_student("STU001")

        # Bypass HTML5 max attribute via JS to test backend validation error feedback in browser
        physics_input = browser.find_element("id", "input_mark_Physics")
        browser.execute_script("arguments[0].removeAttribute('max');", physics_input)
        marks_page.enter_marks(
            {
                "Physics": 145,
                "Chemistry": 80,
                "Mathematics": 80,
                "Computer Science": 80,
                "Kannada": 80,
                "English": 80,
            }
        )
        assert "Marks validation error" in marks_page.get_flash_text()
        marks_page.logout()
