"""End-to-End Selenium Smoke Tests (Milestone M6).

Uses headless Chrome, real HTTP server thread, and PostgreSQL test database.
Verifies critical student and teacher UI journeys and accessibility behaviors:
1. Home page loads.
2. Student login page renders.
3. Teacher login page renders.
4. Invalid login displays appropriate error.
5. Student dashboard is protected against unauthorized access.
6. Teacher dashboard is protected against unauthorized access.
7. Student can view their examination result in an accessible modal.
8. Teacher can view assigned students list.
9. Teacher can enter and submit valid marks for an assigned student.
10. Result modal opens and closes accessibly via keyboard (Escape key).
"""
from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@pytest.mark.e2e
class TestSeleniumSmokeSuite:
    """Selenium smoke test suite verifying end-to-end browser workflows."""

    def test_01_home_page_loads(self, live_server, selenium_driver):
        """TC-SMOKE-01: Home page loads with branding, headings, and portal login buttons."""
        driver = selenium_driver
        driver.get(live_server)

        wait = WebDriverWait(driver, 10)
        title = wait.until(lambda d: "Student Result Management System" in d.title)
        assert title

        header = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "portal-title")))
        assert "10th Standard Result Portal" in header.text

        student_btn = wait.until(EC.element_to_be_clickable((By.ID, "student-login-link")))
        teacher_btn = wait.until(EC.element_to_be_clickable((By.ID, "teacher-login-link")))

        assert student_btn.is_displayed()
        assert teacher_btn.is_displayed()

    def test_02_student_login_page_renders(self, live_server, selenium_driver):
        """TC-SMOKE-02: Student login page renders with form, labels, inputs, and submit button."""
        driver = selenium_driver
        driver.get(f"{live_server}/student/login")

        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: "Student Portal Sign In" in d.title)

        login_input = wait.until(EC.visibility_of_element_located((By.ID, "login_id")))
        password_input = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        submit_btn = wait.until(EC.visibility_of_element_located((By.ID, "btn-submit-login")))

        assert login_input.get_attribute("placeholder") == "STU2026001"
        assert password_input.get_attribute("type") == "password"
        assert submit_btn.text == "Sign In"

    def test_03_teacher_login_page_renders(self, live_server, selenium_driver):
        """TC-SMOKE-03: Teacher login page renders with form, labels, inputs, and submit button."""
        driver = selenium_driver
        driver.get(f"{live_server}/teacher/login")

        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: "Teacher Portal Sign In" in d.title)

        login_input = wait.until(EC.visibility_of_element_located((By.ID, "login_id")))
        password_input = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        submit_btn = wait.until(EC.visibility_of_element_located((By.ID, "btn-submit-login")))

        assert login_input.get_attribute("placeholder") == "TCH001"
        assert password_input.get_attribute("type") == "password"
        assert submit_btn.text == "Sign In"

    def test_04_invalid_login_displays_error(self, live_server, selenium_driver):
        """TC-SMOKE-04: Submitting invalid credentials renders non-revealing error in alert region."""
        driver = selenium_driver
        driver.get(f"{live_server}/student/login")

        wait = WebDriverWait(driver, 10)
        login_input = wait.until(EC.visibility_of_element_located((By.ID, "login_id")))
        password_input = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-submit-login")))

        login_input.send_keys("STU999999")
        password_input.send_keys("WrongPassword123!")
        submit_btn.click()

        error_alert = wait.until(EC.visibility_of_element_located((By.ID, "auth-error-alert")))
        assert "Invalid ID or password." in error_alert.text

    def test_05_student_dashboard_is_protected(self, live_server, selenium_driver):
        """TC-SMOKE-05: Anonymous access to student dashboard redirects to login."""
        driver = selenium_driver
        driver.get(f"{live_server}/student/dashboard")

        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: "/student/login" in d.current_url)
        assert "/student/login" in driver.current_url

    def test_06_teacher_dashboard_is_protected(self, live_server, selenium_driver):
        """TC-SMOKE-06: Anonymous access to teacher dashboard redirects to login."""
        driver = selenium_driver
        driver.get(f"{live_server}/teacher/dashboard")

        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: "/teacher/login" in d.current_url)
        assert "/teacher/login" in driver.current_url

    def test_07_student_can_view_result(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-SMOKE-07: Student logs in, opens dashboard, and views detailed result modal."""
        driver = selenium_driver
        driver.get(f"{live_server}/student/login")

        wait = WebDriverWait(driver, 10)
        login_input = wait.until(EC.visibility_of_element_located((By.ID, "login_id")))
        password_input = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-submit-login")))

        login_input.send_keys("STU2026001")
        password_input.send_keys("StudentPass123!")
        submit_btn.click()

        # Wait for student dashboard
        wait.until(lambda d: "/student/dashboard" in d.current_url)
        name_el = wait.until(EC.visibility_of_element_located((By.ID, "student-name")))
        assert "Alice Student" in name_el.text

        # Click View Detailed Result button
        view_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-view-result")))
        view_btn.click()

        # Modal becomes visible
        modal_content = wait.until(EC.visibility_of_element_located((By.ID, "modal-result-content")))
        assert modal_content.is_displayed()

        # Check total marks & PASS badge
        status_el = wait.until(EC.visibility_of_element_located((By.ID, "res-status")))
        assert "PASS" in status_el.text

        # Verify subjects table contains rows
        rows = driver.find_elements(By.CSS_SELECTOR, "#subjects-table-body tr")
        assert len(rows) == 5

    def test_08_teacher_can_view_assigned_students(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-SMOKE-08: Teacher logs in and sees list of assigned students with subject pills."""
        driver = selenium_driver
        driver.get(f"{live_server}/teacher/login")

        wait = WebDriverWait(driver, 10)
        login_input = wait.until(EC.visibility_of_element_located((By.ID, "login_id")))
        password_input = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-submit-login")))

        login_input.send_keys("TCH001")
        password_input.send_keys("TeacherPass123!")
        submit_btn.click()

        wait.until(lambda d: "/teacher/dashboard" in d.current_url)

        # Wait for students table to load
        table = wait.until(EC.visibility_of_element_located((By.ID, "students-table-container")))
        assert table.is_displayed()

        # Check student row
        student_cell = wait.until(EC.visibility_of_element_located((By.XPATH, "//td[contains(., 'STU2026001')]")))
        assert student_cell.is_displayed()

    def test_09_teacher_can_submit_valid_marks(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-SMOKE-09: Teacher enters marks for an assigned student and receives success feedback."""
        driver = selenium_driver
        driver.get(f"{live_server}/teacher/login")

        wait = WebDriverWait(driver, 10)
        login_input = wait.until(EC.visibility_of_element_located((By.ID, "login_id")))
        password_input = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-submit-login")))

        login_input.send_keys("TCH001")
        password_input.send_keys("TeacherPass123!")
        submit_btn.click()

        wait.until(lambda d: "/teacher/dashboard" in d.current_url)

        # Click Enter Marks for Alice
        enter_marks_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-edit-student")))
        enter_marks_btn.click()

        # Modal opens
        wait.until(EC.visibility_of_element_located((By.ID, "marks-modal-content")))

        # Locate editable input for ENG
        eng_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[data-sub-code='ENG']")))
        eng_input.clear()
        eng_input.send_keys("88.5")

        # Save marks
        save_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-save-marks")))
        save_btn.click()

        # Wait for success message
        success_alert = wait.until(EC.visibility_of_element_located((By.ID, "marks-modal-success")))
        assert "Marks saved successfully!" in success_alert.text

    def test_10_result_modal_opens_and_closes_accessibly(self, live_server, selenium_driver, e2e_seeded_data):
        """TC-SMOKE-10: Result modal opens with focus and closes accessibly via Escape key."""
        driver = selenium_driver
        driver.get(f"{live_server}/student/login")

        wait = WebDriverWait(driver, 10)
        login_input = wait.until(EC.visibility_of_element_located((By.ID, "login_id")))
        password_input = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-submit-login")))

        login_input.send_keys("STU2026001")
        password_input.send_keys("StudentPass123!")
        submit_btn.click()

        wait.until(lambda d: "/student/dashboard" in d.current_url)

        view_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-view-result")))
        view_btn.click()

        # Modal is active
        backdrop = wait.until(EC.visibility_of_element_located((By.ID, "result-modal-backdrop")))
        assert "is-active" in backdrop.get_attribute("class")

        # Press Escape key to close accessibly
        modal = driver.find_element(By.ID, "result-modal")
        modal.send_keys(Keys.ESCAPE)

        # Wait until modal is closed
        wait.until(lambda d: "is-active" not in backdrop.get_attribute("class"))
        assert "is-active" not in backdrop.get_attribute("class")
