"""Login Page Object for Student and Teacher authentication portals."""
from __future__ import annotations

from typing import Optional
from selenium.webdriver.common.by import By
from tests.e2e.pages.base_page import BasePage


class LoginPage(BasePage):
    """Encapsulates student and teacher login forms and interactions."""

    PORTAL_TITLE = (By.CLASS_NAME, "portal-title")
    LOGIN_ID_INPUT = (By.ID, "login_id")
    PASSWORD_INPUT = (By.ID, "password")
    SUBMIT_BTN = (By.ID, "btn-submit-login")
    ALERT_ERROR = (By.ID, "auth-error-alert")
    ALERT_DANGER = (By.CLASS_NAME, "alert-danger")
    DEMO_HINT = (By.CLASS_NAME, "demo-hint")
    SKIP_LINK = (By.CLASS_NAME, "skip-link")

    def load_student(self, base_url: str) -> LoginPage:
        """Navigate to Student Portal login page."""
        self.navigate_to(f"{base_url}/student/login")
        self.wait_for_title_contains("Student Portal Sign In")
        return self

    def load_teacher(self, base_url: str) -> LoginPage:
        """Navigate to Teacher Portal login page."""
        self.navigate_to(f"{base_url}/teacher/login")
        self.wait_for_title_contains("Teacher Portal Sign In")
        return self

    def enter_login_id(self, login_id: str) -> LoginPage:
        """Fill in login ID input."""
        self.type_text(self.LOGIN_ID_INPUT, login_id)
        return self

    def enter_password(self, password: str) -> LoginPage:
        """Fill in password input."""
        self.type_text(self.PASSWORD_INPUT, password)
        return self

    def click_submit(self) -> None:
        """Click Sign In button."""
        self.click(self.SUBMIT_BTN)

    def login(self, login_id: str, password: str) -> None:
        """Complete login action by entering credentials and clicking submit."""
        self.enter_login_id(login_id)
        self.enter_password(password)
        self.click_submit()

    def get_error_message(self, timeout: int = 5) -> str:
        """Return text from the error alert box."""
        return self.get_text(self.ALERT_ERROR, timeout=timeout)

    def is_error_displayed(self, timeout: int = 5) -> bool:
        """Check if an error alert is visible on the page."""
        return self.is_visible(self.ALERT_ERROR, timeout=timeout)

    def is_submit_disabled(self) -> bool:
        """Check whether the submit button is disabled."""
        el = self.find_present_element(self.SUBMIT_BTN)
        return el.get_attribute("disabled") is not None

    def get_submit_text(self) -> str:
        """Get current text of the submit button (e.g. 'Sign In' or 'Signing In...')."""
        return self.get_text(self.SUBMIT_BTN)

    def get_login_id_placeholder(self) -> Optional[str]:
        """Return placeholder attribute of login ID input."""
        return self.get_attribute(self.LOGIN_ID_INPUT, "placeholder")

    def get_password_input_type(self) -> Optional[str]:
        """Return type attribute of password input."""
        return self.get_attribute(self.PASSWORD_INPUT, "type")
