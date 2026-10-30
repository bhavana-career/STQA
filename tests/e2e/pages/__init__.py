"""Page Object Model (POM) package for Selenium End-to-End tests."""
from tests.e2e.pages.base_page import BasePage
from tests.e2e.pages.home_page import HomePage
from tests.e2e.pages.login_page import LoginPage
from tests.e2e.pages.marks_entry_modal import MarksEntryModal
from tests.e2e.pages.result_modal import ResultModal
from tests.e2e.pages.student_dashboard_page import StudentDashboardPage
from tests.e2e.pages.teacher_dashboard_page import TeacherDashboardPage

__all__ = [
    "BasePage",
    "HomePage",
    "LoginPage",
    "StudentDashboardPage",
    "TeacherDashboardPage",
    "ResultModal",
    "MarksEntryModal",
]
