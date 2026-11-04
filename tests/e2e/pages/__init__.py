"""Page Object Model (POM) classes for Selenium End-to-End automation."""

from typing import Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


class BasePage:
    """Base Page Object encapsulating explicit waits, navigation, and shared layout elements."""

    def __init__(self, driver: WebDriver, base_url: str, timeout: int = 10):
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.wait = WebDriverWait(driver, timeout)

    def open_path(self, path: str = "/"):
        url = f"{self.base_url}/{path.lstrip('/')}"
        self.driver.get(url)

    def find_visible(self, locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def find_clickable(self, locator):
        return self.wait.until(EC.element_to_be_clickable(locator))

    def click(self, locator):
        el = self.find_clickable(locator)
        self.driver.execute_script("arguments[0].click();", el)

    def submit_form(self, form_locator):
        form_el = self.find_visible(form_locator)
        form_el.submit()

    def type_text(self, locator, text: str):
        el = self.find_visible(locator)
        self.driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            el,
            str(text),
        )

    def get_text(self, locator) -> str:
        return self.find_visible(locator).text.strip()

    def is_element_present(self, locator) -> bool:
        return len(self.driver.find_elements(*locator)) > 0

    def get_flash_text(self) -> str:
        locator = (By.ID, "flashMessages")
        el = self.wait.until(EC.visibility_of_element_located(locator))
        return el.text.strip()

    def logout(self):
        self.click((By.ID, "logoutBtn"))
        self.wait.until(EC.visibility_of_element_located((By.ID, "loginForm")))


class LoginPage(BasePage):
    """Page Object for the SRMS Login Page."""

    USERNAME_INPUT = (By.ID, "username")
    PASSWORD_INPUT = (By.ID, "password")
    TOGGLE_PASSWORD_BTN = (By.ID, "togglePasswordBtn")
    SUBMIT_BTN = (By.ID, "loginSubmitBtn")
    ERROR_ALERT = (By.ID, "loginErrorAlert")

    def open(self):
        self.open_path("/login")
        self.find_visible(self.USERNAME_INPUT)

    def login(self, username: str, password: str):
        self.type_text(self.USERNAME_INPUT, username)
        self.type_text(self.PASSWORD_INPUT, password)
        self.click(self.SUBMIT_BTN)

    def toggle_password_visibility(self) -> str:
        self.click(self.TOGGLE_PASSWORD_BTN)
        return self.find_visible(self.PASSWORD_INPUT).get_attribute("type")

    def get_error_message(self) -> str:
        return self.get_text(self.ERROR_ALERT)


class TeacherDashboardPage(BasePage):
    """Page Object for the Teacher Dashboard Overview."""

    OVERVIEW_GRID = (By.ID, "dashboardOverviewGrid")
    TOTAL_STUDENTS = (By.ID, "statTotalStudents")
    NAV_STUDENTS = (By.ID, "navStudents")
    NAV_MARKS = (By.ID, "navMarks")
    NAV_ANALYTICS = (By.ID, "navAnalytics")

    def verify_loaded(self) -> bool:
        return self.find_visible(self.OVERVIEW_GRID).is_displayed()

    def get_total_students_count(self) -> int:
        return int(self.get_text(self.TOTAL_STUDENTS))

    def go_to_student_management(self):
        self.click(self.NAV_STUDENTS)

    def go_to_marks_management(self):
        self.click(self.NAV_MARKS)

    def go_to_analytics(self):
        self.click(self.NAV_ANALYTICS)


class StudentManagementPage(BasePage):
    """Page Object for Teacher Student Management (CRUD, search, section filter)."""

    FORM = (By.ID, "studentCrudForm")
    STUDENT_ID = (By.ID, "student_id")
    NAME = (By.ID, "name")
    USERNAME = (By.ID, "username")
    PASSWORD = (By.ID, "student_password")
    SECTION = (By.ID, "section")
    ROLL_NUMBER = (By.ID, "roll_number")
    SAVE_BTN = (By.ID, "saveStudentBtn")
    SEARCH_INPUT = (By.ID, "searchQueryInput")
    SEARCH_BTN = (By.ID, "searchFilterBtn")
    RESET_BTN = (By.ID, "resetFilterBtn")
    TABLE = (By.ID, "studentsManagementTable")

    def add_student(
        self,
        student_id: str,
        name: str,
        username: str,
        password: str,
        section: str,
        roll_number: int,
        marks: Dict[str, int],
    ):
        self.type_text(self.STUDENT_ID, student_id)
        self.type_text(self.NAME, name)
        self.type_text(self.USERNAME, username)
        self.type_text(self.PASSWORD, password)
        Select(self.find_visible(self.SECTION)).select_by_value(section)
        self.type_text(self.ROLL_NUMBER, str(roll_number))
        for subj, mark in marks.items():
            self.type_text((By.ID, f"mark_{subj}"), str(mark))
        self.click(self.SAVE_BTN)
        self.wait.until(EC.visibility_of_element_located((By.ID, f"student-row-{student_id}")))

    def search_student(self, query: str):
        self.type_text(self.SEARCH_INPUT, query)
        self.click(self.SEARCH_BTN)

    def reset_filters(self):
        self.click(self.RESET_BTN)

    def is_student_in_table(self, student_id: str) -> bool:
        return self.is_element_present((By.ID, f"student-row-{student_id}"))

    def open_edit_for_student(self, student_id: str):
        self.click((By.ID, f"editStudent-{student_id}"))
        self.find_visible(self.NAME)

    def update_student_details(self, new_name: str, new_section: str, new_roll: int):
        self.type_text(self.NAME, new_name)
        Select(self.find_visible(self.SECTION)).select_by_value(new_section)
        self.type_text(self.ROLL_NUMBER, str(new_roll))
        self.click(self.SAVE_BTN)
        self.wait.until(EC.text_to_be_present_in_element(self.TABLE, new_name))

    def delete_student(self, student_id: str):
        self.driver.execute_script("window.confirm = function() { return true; };")
        self.click((By.ID, f"deleteStudent-{student_id}"))
        self.wait.until(EC.invisibility_of_element_located((By.ID, f"student-row-{student_id}")))


class MarksEntryPage(BasePage):
    """Page Object for Teacher Marks Entry & Calculation Engine."""

    STUDENT_SELECT = (By.ID, "marksStudentSelect")
    LOAD_BTN = (By.ID, "loadStudentMarksBtn")
    SUBMIT_BTN = (By.ID, "submitMarksBtn")
    CALC_TOTAL = (By.ID, "calculatedTotalMarks")
    CALC_PCT = (By.ID, "calculatedPercentage")
    CALC_CLASS = (By.ID, "calculatedClassification")

    def select_student(self, student_id: str):
        select_el = Select(self.find_visible(self.STUDENT_SELECT))
        select_el.select_by_value(student_id)
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "marksTargetStudentName"), student_id))

    def enter_marks(self, marks: Dict[str, int]):
        for subj, val in marks.items():
            self.type_text((By.ID, f"input_mark_{subj}"), str(val))
        self.click(self.SUBMIT_BTN)

    def get_calculated_total(self) -> str:
        return self.get_text(self.CALC_TOTAL)

    def get_calculated_percentage(self) -> str:
        return self.get_text(self.CALC_PCT)

    def get_calculated_classification(self) -> str:
        return self.get_text(self.CALC_CLASS)

    def get_subject_grade(self, subject: str) -> str:
        return self.get_text((By.ID, f"grade_{subject}"))


class ResultPage(BasePage):
    """Page Object for viewing detailed Student Result & Grading Matrix."""

    STUDENT_NAME = (By.ID, "studentNameDisplay")
    STUDENT_ID = (By.ID, "studentIdDisplay")
    TOTAL_MARKS = (By.ID, "studentTotalMarks")
    PERCENTAGE = (By.ID, "studentPercentage")
    CLASSIFICATION = (By.ID, "studentClassification")
    OVERALL_STATUS = (By.ID, "studentOverallStatus")
    SUBJECT_TABLE = (By.ID, "studentSubjectMarksTable")
    GRADING_MATRIX_TABLE = (By.ID, "gradingMatrixTable")
    SUCCESS_POPUP = (By.ID, "resultSuccessPopup")
    CLOSE_POPUP_BTN = (By.ID, "closeSuccessPopupBtn")

    def get_summary_metrics(self) -> Dict[str, str]:
        return {
            "name": self.get_text(self.STUDENT_NAME),
            "student_id": self.get_text(self.STUDENT_ID),
            "total": self.get_text(self.TOTAL_MARKS),
            "percentage": self.get_text(self.PERCENTAGE),
            "classification": self.get_text(self.CLASSIFICATION),
            "status": self.get_text(self.OVERALL_STATUS),
        }

    def get_subject_row_details(self, subject: str) -> Dict[str, str]:
        row_id = f"subj-row-{subject.replace(' ', '_')}"
        row = self.find_visible((By.ID, row_id))
        marks = row.find_element(By.CSS_SELECTOR, ".subj-marks").text.strip()
        grade = row.find_element(By.CSS_SELECTOR, ".subj-grade").text.strip()
        return {"marks": marks, "grade": grade}

    def is_grading_matrix_displayed(self) -> bool:
        return self.find_visible(self.GRADING_MATRIX_TABLE).is_displayed()

    def is_success_popup_visible(self) -> bool:
        if not self.is_element_present(self.SUCCESS_POPUP):
            return False
        el = self.driver.find_element(*self.SUCCESS_POPUP)
        return el.is_displayed() and "hidden" not in (el.get_attribute("class") or "")

    def dismiss_success_popup(self):
        if self.is_success_popup_visible():
            self.click(self.CLOSE_POPUP_BTN)


class StudentDashboardPage(ResultPage):
    """Page Object for the Student Dashboard (inherits result inspection capabilities)."""

    NAV_MY_RESULTS = (By.ID, "navStudentResults")
    NAV_GRADING_MATRIX = (By.ID, "navGradingMatrix")

    def navigate_to_my_results(self):
        self.click(self.NAV_MY_RESULTS)

    def navigate_to_grading_matrix(self):
        self.click(self.NAV_GRADING_MATRIX)


class AnalyticsPage(BasePage):
    """Page Object for the Teacher Class Analytics page."""

    HEADING = (By.ID, "analyticsSectionHeading")
    STUDENT_COUNT = (By.ID, "secStudentCount")
    AVG_TOTAL = (By.ID, "secAvgTotal")
    AVG_PCT = (By.ID, "secAvgPercentage")
    PASSING_COUNT = (By.ID, "secPassingCount")
    FAILING_COUNT = (By.ID, "secFailingCount")
    DISTINCTION_COUNT = (By.ID, "secDistinctionCount")

    def select_section(self, section: str):
        self.click((By.ID, f"selectSectionBtn-{section}"))
        self.wait.until(
            EC.text_to_be_present_in_element(self.HEADING, f"Section {section} Performance Metrics")
        )

    def get_section_metrics(self) -> Dict[str, str]:
        return {
            "heading": self.get_text(self.HEADING),
            "student_count": self.get_text(self.STUDENT_COUNT),
            "avg_total": self.get_text(self.AVG_TOTAL),
            "avg_pct": self.get_text(self.AVG_PCT),
            "passing": self.get_text(self.PASSING_COUNT),
            "failing": self.get_text(self.FAILING_COUNT),
            "distinction": self.get_text(self.DISTINCTION_COUNT),
        }
