"""Home Page Object for landing page interactions."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from tests.e2e.pages.base_page import BasePage
from tests.e2e.pages.login_page import LoginPage


class HomePage(BasePage):
    """Encapsulates landing page locators and user interactions."""

    PORTAL_TITLE = (By.CLASS_NAME, "portal-title")
    DEMO_BADGE = (By.CLASS_NAME, "demo-badge")
    STUDENT_LOGIN_LINK = (By.ID, "student-login-link")
    TEACHER_LOGIN_LINK = (By.ID, "teacher-login-link")
    ACADEMIC_SYSTEM_CARD = (By.CLASS_NAME, "system-card")
    SKIP_LINK = (By.CLASS_NAME, "skip-link")

    def load(self, base_url: str) -> HomePage:
        """Navigate to the SRMS root landing page."""
        self.navigate_to(base_url)
        self.wait_for_title_contains("Student Result Management System")
        return self

    def get_portal_title(self) -> str:
        """Return main portal title text."""
        return self.get_text(self.PORTAL_TITLE)

    def is_student_link_visible(self) -> bool:
        """Check if student portal navigation link is displayed."""
        return self.is_visible(self.STUDENT_LOGIN_LINK)

    def is_teacher_link_visible(self) -> bool:
        """Check if teacher portal navigation link is displayed."""
        return self.is_visible(self.TEACHER_LOGIN_LINK)

    def click_student_portal(self) -> LoginPage:
        """Click the student portal entry button and return LoginPage."""
        self.click(self.STUDENT_LOGIN_LINK)
        page = LoginPage(self.driver, self.timeout)
        page.wait_for_title_contains("Student Portal Sign In")
        return page

    def click_teacher_portal(self) -> LoginPage:
        """Click the teacher portal entry button and return LoginPage."""
        self.click(self.TEACHER_LOGIN_LINK)
        page = LoginPage(self.driver, self.timeout)
        page.wait_for_title_contains("Teacher Portal Sign In")
        return page
