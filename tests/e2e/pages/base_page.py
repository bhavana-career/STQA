"""Base Page Object class encapsulating common Selenium interactions and explicit waits."""
from __future__ import annotations

from typing import List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    """Base class for all Page Objects in the SRMS Selenium test suite."""

    def __init__(self, driver: WebDriver, timeout: int = 10) -> None:
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    def navigate_to(self, url: str) -> None:
        """Navigate to a target URL."""
        self.driver.get(url)

    def get_current_url(self) -> str:
        """Return the current browser URL."""
        return self.driver.current_url

    def get_title(self) -> str:
        """Return current browser window title."""
        return self.driver.title

    def wait_for_title_contains(self, text: str, timeout: Optional[int] = None) -> bool:
        """Wait until browser title contains specific text."""
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return bool(wait.until(lambda d: text in d.title))

    def wait_for_url_contains(self, fragment: str, timeout: Optional[int] = None) -> bool:
        """Wait until current URL contains fragment."""
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return bool(wait.until(lambda d: fragment in d.current_url))

    def find_visible_element(self, locator: Tuple[By, str], timeout: Optional[int] = None) -> WebElement:
        """Wait for an element to be visible and return it."""
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return wait.until(EC.visibility_of_element_located(locator))

    def find_clickable_element(self, locator: Tuple[By, str], timeout: Optional[int] = None) -> WebElement:
        """Wait for an element to be clickable and return it."""
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return wait.until(EC.element_to_be_clickable(locator))

    def find_present_element(self, locator: Tuple[By, str], timeout: Optional[int] = None) -> WebElement:
        """Wait for an element to be present in DOM and return it."""
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return wait.until(EC.presence_of_element_located(locator))

    def find_elements(self, locator: Tuple[By, str]) -> List[WebElement]:
        """Find all matching elements present in DOM."""
        return self.driver.find_elements(*locator)

    def click(self, locator: Tuple[By, str], timeout: Optional[int] = None) -> None:
        """Click an element once it is clickable."""
        el = self.find_clickable_element(locator, timeout)
        el.click()

    def type_text(self, locator: Tuple[By, str], text: str, clear: bool = True, timeout: Optional[int] = None) -> None:
        """Type text into an input element with optional clearing."""
        el = self.find_visible_element(locator, timeout)
        if clear:
            el.clear()
        el.send_keys(text)

    def get_text(self, locator: Tuple[By, str], timeout: Optional[int] = None) -> str:
        """Retrieve inner text of an element once visible."""
        el = self.find_visible_element(locator, timeout)
        return el.text.strip()

    def get_attribute(self, locator: Tuple[By, str], attribute_name: str, timeout: Optional[int] = None) -> Optional[str]:
        """Retrieve an element's HTML attribute."""
        el = self.find_present_element(locator, timeout)
        return el.get_attribute(attribute_name)

    def is_visible(self, locator: Tuple[By, str], timeout: int = 2) -> bool:
        """Check if an element is currently visible within a short timeout."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.visibility_of_element_located(locator))
            return True
        except Exception:
            return False

    def wait_until_invisible(self, locator: Tuple[By, str], timeout: Optional[int] = None) -> bool:
        """Wait until an element becomes invisible or absent from DOM."""
        wait = WebDriverWait(self.driver, timeout or self.timeout)
        return bool(wait.until(EC.invisibility_of_element_located(locator)))

    def accept_alert_or_confirm(self, timeout: int = 3) -> str:
        """Wait for JavaScript alert/confirm dialog, accept it, and return its text."""
        wait = WebDriverWait(self.driver, timeout)
        alert = wait.until(EC.alert_is_present())
        text = alert.text
        alert.accept()
        return text

    def dismiss_confirm(self, timeout: int = 3) -> str:
        """Wait for JavaScript confirm dialog, dismiss (cancel) it, and return its text."""
        wait = WebDriverWait(self.driver, timeout)
        alert = wait.until(EC.alert_is_present())
        text = alert.text
        alert.dismiss()
        return text
