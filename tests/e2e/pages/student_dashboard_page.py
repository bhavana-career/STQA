"""Student Dashboard Page Object for student profile and exam views."""
from __future__ import annotations

from typing import Optional
from selenium.webdriver.common.by import By
from tests.e2e.pages.base_page import BasePage
from tests.e2e.pages.result_modal import ResultModal


class StudentDashboardPage(BasePage):
    """Encapsulates the Student Portal dashboard and result actions."""

    PORTAL_TITLE = (By.CLASS_NAME, "portal-title")
    STUDENT_NAME = (By.ID, "student-name")
    STUDENT_CODE = (By.ID, "student-code")
    VIEW_RESULT_BTN = (By.ID, "btn-view-result")
    LOGOUT_BTN = (By.ID, "btn-logout")
    EMPTY_STATE = (By.CLASS_NAME, "empty-state")
    HEADER_USER_INFO = (By.CLASS_NAME, "header-user-info")

    def wait_for_load(self) -> StudentDashboardPage:
        """Wait until student dashboard URL and elements are loaded."""
        self.wait_for_url_contains("/student/dashboard")
        self.wait_for_title_contains("Student Dashboard")
        self.find_visible_element(self.PORTAL_TITLE)
        return self

    def get_student_name(self) -> str:
        """Return student full name displayed on profile card."""
        return self.get_text(self.STUDENT_NAME)

    def get_student_code(self) -> str:
        """Return student code / ID displayed on profile card."""
        return self.get_text(self.STUDENT_CODE)

    def is_view_result_button_available(self) -> bool:
        """Check whether 'View Detailed Result' button is visible."""
        return self.is_visible(self.VIEW_RESULT_BTN)

    def open_result_modal(self) -> ResultModal:
        """Click 'View Detailed Result' and return ResultModal instance."""
        self.click(self.VIEW_RESULT_BTN)
        modal = ResultModal(self.driver, self.timeout)
        modal.wait_for_open()
        return modal

    def is_empty_state_displayed(self) -> bool:
        """Check if empty state banner is displayed when no exam is published."""
        return self.is_visible(self.EMPTY_STATE)

    def logout(self) -> None:
        """Click logout button to terminate session."""
        self.click(self.LOGOUT_BTN)
        self.wait_for_url_contains("/")
