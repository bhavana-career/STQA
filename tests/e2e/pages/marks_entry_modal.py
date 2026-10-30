"""Marks Entry Modal Page Component for Teacher marks entry and editing."""
from __future__ import annotations

from typing import Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from tests.e2e.pages.base_page import BasePage


class MarksEntryModal(BasePage):
    """Encapsulates the Teacher marks entry dialog component."""

    BACKDROP = (By.ID, "marks-modal-backdrop")
    DIALOG = (By.ID, "marks-modal")
    TITLE = (By.ID, "marks-modal-title")
    SUBTITLE = (By.ID, "marks-modal-subtitle")
    CLOSE_BTN = (By.ID, "marks-modal-close-btn")
    CANCEL_BTN = (By.ID, "btn-marks-cancel")
    SAVE_BTN = (By.ID, "btn-save-marks")
    LOADING = (By.ID, "marks-modal-loading")
    ERROR_ALERT = (By.ID, "marks-modal-error")
    SUCCESS_ALERT = (By.ID, "marks-modal-success")
    CONTENT = (By.ID, "marks-modal-content")
    TOTAL_MARKS = (By.ID, "modal-res-total")
    PERCENTAGE = (By.ID, "modal-res-percentage")
    GRADE = (By.ID, "modal-res-grade")
    STATUS = (By.ID, "modal-res-status")

    def wait_for_open(self) -> MarksEntryModal:
        """Wait until modal dialog is visible in DOM."""
        self.find_visible_element(self.BACKDROP)
        self.find_visible_element(self.DIALOG)
        return self

    def wait_for_content_loaded(self, timeout: int = 10) -> MarksEntryModal:
        """Wait until loading spinner disappears and form table is visible."""
        self.wait_until_invisible(self.LOADING, timeout=timeout)
        self.find_visible_element(self.CONTENT, timeout=timeout)
        return self

    def is_active(self) -> bool:
        """Return True if modal backdrop has 'is-active' class and is visible."""
        el = self.find_present_element(self.BACKDROP)
        classes = el.get_attribute("class") or ""
        return "is-active" in classes and el.is_displayed()

    def close_via_button(self) -> None:
        """Close dialog by clicking the X close button."""
        self.click(self.CLOSE_BTN)
        self.wait_for_closed()

    def close_via_cancel(self) -> None:
        """Close dialog by clicking the Cancel button."""
        self.click(self.CANCEL_BTN)
        self.wait_for_closed()

    def close_via_escape(self) -> None:
        """Send Escape key to close the dialog."""
        dialog = self.find_visible_element(self.DIALOG)
        dialog.send_keys(Keys.ESCAPE)
        self.wait_for_closed()

    def close_via_backdrop(self) -> None:
        """Click on backdrop outside dialog."""
        self.click(self.BACKDROP)
        self.wait_for_closed()

    def wait_for_closed(self, timeout: int = 5) -> bool:
        """Wait until modal dialog backdrop is hidden or inactive."""
        return self.wait_until_invisible(self.BACKDROP, timeout=timeout)

    def get_subject_input_locator(self, subject_code: str) -> tuple[By, str]:
        """Generate locator for subject mark input by code."""
        return (By.CSS_SELECTOR, f"input[data-sub-code='{subject_code}']")

    def enter_mark(self, subject_code: str, value: str) -> MarksEntryModal:
        """Enter a mark value for a specific assigned subject."""
        loc = self.get_subject_input_locator(subject_code)
        self.type_text(loc, value)
        return self

    def clear_mark(self, subject_code: str) -> MarksEntryModal:
        """Clear the mark input for a specific subject."""
        loc = self.get_subject_input_locator(subject_code)
        el = self.find_visible_element(loc)
        el.clear()
        return self

    def get_mark_value(self, subject_code: str) -> str:
        """Get the current input value for a subject."""
        loc = self.get_subject_input_locator(subject_code)
        return self.get_attribute(loc, "value") or ""

    def is_subject_editable(self, subject_code: str) -> bool:
        """Check whether a subject input is enabled or disabled (read-only)."""
        loc = self.get_subject_input_locator(subject_code)
        try:
            el = self.find_present_element(loc, timeout=3)
            return el.get_attribute("disabled") is None
        except Exception:
            return False

    def click_save(self) -> None:
        """Click Save Marks button."""
        self.click(self.SAVE_BTN)

    def save_marks(self, handle_confirmation: Optional[bool] = None) -> None:
        """Click Save Marks and optionally handle clearing confirmation alert."""
        self.click_save()
        if handle_confirmation is True:
            self.accept_alert_or_confirm()
        elif handle_confirmation is False:
            self.dismiss_confirm()

    def get_success_message(self, timeout: int = 5) -> str:
        """Get text from the success alert message."""
        return self.get_text(self.SUCCESS_ALERT, timeout=timeout)

    def get_error_message(self, timeout: int = 5) -> str:
        """Get text from the modal-level error alert."""
        return self.get_text(self.ERROR_ALERT, timeout=timeout)

    def get_field_error(self, subject_code: str) -> str:
        """Get inline field error text for a subject."""
        # Find input first to get data-sub-id
        loc = self.get_subject_input_locator(subject_code)
        input_el = self.find_present_element(loc)
        sub_id = input_el.get_attribute("data-sub-id")
        error_loc = (By.ID, f"error-sub-{sub_id}")
        return self.get_text(error_loc)

    def is_save_disabled(self) -> bool:
        """Check if Save Marks button is disabled."""
        el = self.find_present_element(self.SAVE_BTN)
        return el.get_attribute("disabled") is not None

    def get_save_button_text(self) -> str:
        """Get current text of Save Marks button."""
        return self.get_text(self.SAVE_BTN)

    def get_summary(self) -> Dict[str, str]:
        """Extract computed summary preview from within modal."""
        return {
            "total": self.get_text(self.TOTAL_MARKS),
            "percentage": self.get_text(self.PERCENTAGE),
            "grade": self.get_text(self.GRADE),
            "status": self.get_text(self.STATUS),
        }
