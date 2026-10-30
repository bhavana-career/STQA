"""Teacher Dashboard Page Object for student roster management and marks actions."""
from __future__ import annotations

from typing import Dict, List
from selenium.webdriver.common.by import By
from tests.e2e.pages.base_page import BasePage
from tests.e2e.pages.marks_entry_modal import MarksEntryModal


class TeacherDashboardPage(BasePage):
    """Encapsulates the Teacher Portal dashboard and student list interactions."""

    PORTAL_TITLE = (By.CLASS_NAME, "portal-title")
    TEACHER_NAME = (By.XPATH, "//div[span[contains(text(), 'Teacher Name')]]/p")
    TEACHER_CODE = (By.XPATH, "//div[span[contains(text(), 'Teacher Code')]]/p")
    STUDENTS_CONTAINER = (By.ID, "students-table-container")
    STUDENTS_ROWS = (By.CSS_SELECTOR, "#students-table-body tr")
    LOGOUT_BTN = (By.ID, "btn-logout")
    LOADING = (By.ID, "students-loading")
    ERROR = (By.ID, "students-error")

    def wait_for_load(self) -> TeacherDashboardPage:
        """Wait until teacher dashboard loads and student table container is visible."""
        self.wait_for_url_contains("/teacher/dashboard")
        self.wait_for_title_contains("Teacher Dashboard")
        self.wait_until_invisible(self.LOADING, timeout=10)
        self.find_visible_element(self.STUDENTS_CONTAINER)
        return self

    def get_teacher_name(self) -> str:
        """Return teacher name from profile card."""
        return self.get_text(self.TEACHER_NAME)

    def get_teacher_code(self) -> str:
        """Return teacher code from profile card."""
        return self.get_text(self.TEACHER_CODE)

    def get_assigned_students_data(self) -> List[Dict[str, str]]:
        """Return structured data of all students listed in table."""
        rows = self.find_elements(self.STUDENTS_ROWS)
        results = []
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 6:
                results.append({
                    "code": cells[0].text.strip(),
                    "name": cells[1].text.strip(),
                    "section": cells[2].text.strip(),
                    "roll": cells[3].text.strip(),
                    "assigned_subjects": cells[4].text.strip(),
                    "status": cells[5].text.strip(),
                })
        return results

    def is_student_in_list(self, student_code: str) -> bool:
        """Check if a specific student code is visible in the student list."""
        loc = (By.CSS_SELECTOR, f"button.btn-edit-student[data-code='{student_code}']")
        return self.is_visible(loc, timeout=3)

    def open_marks_modal(self, student_code: str) -> MarksEntryModal:
        """Click 'Enter Marks' button for student matching student_code."""
        btn_loc = (By.CSS_SELECTOR, f"button.btn-edit-student[data-code='{student_code}']")
        self.click(btn_loc)
        modal = MarksEntryModal(self.driver, self.timeout)
        modal.wait_for_open()
        modal.wait_for_content_loaded()
        return modal

    def logout(self) -> None:
        """Click logout button to terminate session."""
        self.click(self.LOGOUT_BTN)
        self.wait_for_url_contains("/")
