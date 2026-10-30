"""Result Modal Page Component for Student detailed marks statement."""
from __future__ import annotations

from typing import Dict, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from tests.e2e.pages.base_page import BasePage


class ResultModal(BasePage):
    """Encapsulates the accessible student detailed statement of marks modal."""

    BACKDROP = (By.ID, "result-modal-backdrop")
    DIALOG = (By.ID, "result-modal")
    TITLE = (By.ID, "result-modal-title")
    CLOSE_BTN = (By.ID, "modal-close-btn")
    LOADING = (By.ID, "modal-loading")
    ERROR = (By.ID, "modal-error")
    CONTENT = (By.ID, "modal-result-content")
    TOTAL_MARKS = (By.ID, "res-total")
    PERCENTAGE = (By.ID, "res-percentage")
    GRADE = (By.ID, "res-grade")
    STATUS = (By.ID, "res-status")
    SUBJECT_ROWS = (By.CSS_SELECTOR, "#subjects-table-body tr")

    def wait_for_open(self) -> ResultModal:
        """Wait until modal dialog is visible and backdrop active."""
        self.find_visible_element(self.BACKDROP)
        self.find_visible_element(self.DIALOG)
        return self

    def wait_for_results_loaded(self, timeout: int = 10) -> ResultModal:
        """Wait until loading spinner disappears and result table is rendered."""
        self.wait_until_invisible(self.LOADING, timeout=timeout)
        self.find_visible_element(self.CONTENT, timeout=timeout)
        return self

    def is_active(self) -> bool:
        """Return True if modal backdrop has 'is-active' class and is visible."""
        el = self.find_present_element(self.BACKDROP)
        classes = el.get_attribute("class") or ""
        return "is-active" in classes and el.is_displayed()

    def close_via_button(self) -> None:
        """Close modal by clicking the X close button."""
        self.click(self.CLOSE_BTN)
        self.wait_for_closed()

    def close_via_escape(self) -> None:
        """Send Escape key to close the accessible modal."""
        dialog = self.find_visible_element(self.DIALOG)
        dialog.send_keys(Keys.ESCAPE)
        self.wait_for_closed()

    def close_via_backdrop(self) -> None:
        """Click outside modal dialog on the backdrop."""
        self.click(self.BACKDROP)
        self.wait_for_closed()

    def wait_for_closed(self, timeout: int = 5) -> bool:
        """Wait until backdrop is hidden or inactive."""
        return self.wait_until_invisible(self.BACKDROP, timeout=timeout)

    def get_summary(self) -> Dict[str, str]:
        """Extract computed summary values (total, percentage, grade, status)."""
        return {
            "total": self.get_text(self.TOTAL_MARKS),
            "percentage": self.get_text(self.PERCENTAGE),
            "grade": self.get_text(self.GRADE),
            "status": self.get_text(self.STATUS),
        }

    def get_subject_rows(self) -> List[Dict[str, str]]:
        """Extract structured subject-wise rows from table."""
        rows = self.find_elements(self.SUBJECT_ROWS)
        results = []
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 5:
                results.append({
                    "subject": cells[0].text.strip(),
                    "max_marks": cells[1].text.strip(),
                    "pass_marks": cells[2].text.strip(),
                    "obtained": cells[3].text.strip(),
                    "status": cells[4].text.strip(),
                })
        return results

    def get_error_message(self) -> str:
        """Return text of modal error banner if present."""
        return self.get_text(self.ERROR)
