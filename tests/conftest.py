"""Pytest fixtures for SRMS test suite."""
from __future__ import annotations

from decimal import Decimal
import os
import socket
import threading
import time
from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy import text

from app import create_app
from app.extensions import db as _db
from app.models import Exam, ExamSubject, Mark, Section, Student, Subject, Teacher, TeacherAssignment, User

DEFAULT_PG_TEST_URL = "postgresql+psycopg://srms:srms_local_pw@localhost:5433/srms_test"

# Default test environment dictionary for testing
DEFAULT_TEST_ENV = {
    "APP_ENV": "testing",
    "SECRET_KEY": "test-secret-key-for-unit-and-integration-tests",
    "DATABASE_URL": "sqlite:///:memory:",
    "TEST_DATABASE_URL": "sqlite:///:memory:",
    "CAPTCHA_MODE": "mock",
    "TURNSTILE_SITE_KEY": "1x00000000000000000000AA",
    "TURNSTILE_SECRET_KEY": "1x0000000000000000000000000000000AA",
    "TURNSTILE_ALLOWED_HOSTNAMES": "localhost,127.0.0.1",
    "WTF_CSRF_ENABLED": "0",
}


def _truncate_all_tables():
    """Truncate PostgreSQL test tables to guarantee isolation with timeout protection."""
    try:
        _db.session.execute(text("SET lock_timeout = '5s'"))
        _db.session.execute(
            text(
                "TRUNCATE TABLE mark_audit, marks, teacher_assignments, "
                "exam_subjects, exams, students, teachers, subjects, sections, users, system_settings CASCADE"
            )
        )
        _db.session.commit()
    except Exception:
        _db.session.rollback()
        try:
            _db.session.execute(text("SET lock_timeout = '5s'"))
            _db.session.execute(
                text(
                    "DELETE FROM mark_audit; DELETE FROM marks; DELETE FROM teacher_assignments; "
                    "DELETE FROM exam_subjects; DELETE FROM exams; DELETE FROM students; "
                    "DELETE FROM teachers; DELETE FROM subjects; DELETE FROM sections; DELETE FROM users; "
                    "DELETE FROM system_settings;"
                )
            )
            _db.session.commit()
        except Exception:
            _db.session.rollback()


@pytest.fixture
def app() -> Flask:
    """Create a Flask application configured for in-memory test execution."""
    test_env = dict(DEFAULT_TEST_ENV)
    test_app = create_app(
        overrides={
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        },
        env=test_env,
    )

    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for HTTP requests on the in-memory app."""
    return app.test_client()


@pytest.fixture(scope="session")
def pg_test_db_url() -> str:
    """Resolve and validate PostgreSQL test database URL."""
    url = os.environ.get("TEST_DATABASE_URL", DEFAULT_PG_TEST_URL).strip()
    prod_url = os.environ.get("DATABASE_URL", "").strip()

    # Safety Guard (TC-DB-07): Ensure test DB is distinct from production and contains 'test'
    if prod_url and url == prod_url:
        pytest.fail(f"SAFETY ABORT: TEST_DATABASE_URL matches DATABASE_URL: {url}")
    if "test" not in url.lower():
        pytest.fail(f"SAFETY ABORT: Test database name must contain 'test': {url}")

    return url


@pytest.fixture
def pg_app(pg_test_db_url: str) -> Generator[Flask, None, None]:
    """Create a Flask application connected to PostgreSQL test database."""
    test_env = dict(DEFAULT_TEST_ENV)
    test_env["DATABASE_URL"] = pg_test_db_url
    test_env["TEST_DATABASE_URL"] = pg_test_db_url

    test_app = create_app(
        overrides={
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        },
        env=test_env,
    )

    with test_app.app_context():
        _truncate_all_tables()
        yield test_app
        _db.session.remove()
        _truncate_all_tables()


@pytest.fixture
def pg_client(pg_app: Flask) -> FlaskClient:
    """Test client for PostgreSQL-backed tests."""
    return pg_app.test_client()


@pytest.fixture
def pg_runner(pg_app: Flask) -> FlaskCliRunner:
    """CLI runner for testing Flask commands against PostgreSQL."""
    return pg_app.test_cli_runner()


# =========================================================================
# Selenium & E2E Testing Fixtures
# =========================================================================

@pytest.fixture
def live_server(pg_test_db_url: str) -> Generator[str, None, None]:
    """Run Flask application in a background daemon thread for Selenium browser testing."""
    from werkzeug.serving import make_server

    test_env = dict(DEFAULT_TEST_ENV)
    test_env["DATABASE_URL"] = pg_test_db_url
    test_env["TEST_DATABASE_URL"] = pg_test_db_url
    test_env["WTF_CSRF_ENABLED"] = "0"

    test_app = create_app(
        overrides={
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        },
        env=test_env,
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = make_server("127.0.0.1", port, test_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Wait until live test server is actively accepting TCP connections
    start_time = time.time()
    while time.time() - start_time < 5.0:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)

    with test_app.app_context():
        _truncate_all_tables()

    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    with test_app.app_context():
        _db.session.remove()
        _truncate_all_tables()

    server.shutdown()
    thread.join(timeout=3)


@pytest.fixture
def e2e_db_session(pg_test_db_url: str):
    """Provide an isolated, read-only/verification SQLAlchemy session for E2E tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    engine = create_engine(pg_test_db_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)
    yield session
    session.remove()
    engine.dispose()


@pytest.fixture
def selenium_driver(request) -> Generator[webdriver.Chrome, None, None]:
    """Headless Chrome WebDriver configured with explicit waits and failure screenshots."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(0)

    yield driver

    driver.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Automatically capture screenshot and browser console logs on test failure for Selenium tests."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("selenium_driver")
        if driver:
            screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "reports", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshots_dir, f"{item.name}.png")
            try:
                driver.save_screenshot(screenshot_path)
            except Exception:
                pass
            log_path = os.path.join(screenshots_dir, f"{item.name}_browser.log")
            try:
                logs = driver.get_log("browser")
                with open(log_path, "w", encoding="utf-8") as f:
                    for entry in logs:
                        f.write(f"{entry}\n")
            except Exception:
                pass


@pytest.fixture
def e2e_seeded_data(live_server: str, pg_test_db_url: str):
    """Seed test student (STU2026001), incomplete student (STU2026002), teacher (TCH001), 5 subjects, exam, and marks."""
    test_env = dict(DEFAULT_TEST_ENV)
    test_env["DATABASE_URL"] = pg_test_db_url
    test_env["TEST_DATABASE_URL"] = pg_test_db_url

    test_app = create_app(
        overrides={"TESTING": True, "WTF_CSRF_ENABLED": False},
        env=test_env,
    )

    with test_app.app_context():
        _truncate_all_tables()

        # Section
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        _db.session.add(sec)
        _db.session.flush()

        # Users
        u_student = User(login_id="STU2026001", role="student")
        u_student.set_password("StudentPass123!")
        u_student2 = User(login_id="STU2026002", role="student")
        u_student2.set_password("StudentPass123!")
        u_teacher = User(login_id="TCH001", role="teacher")
        u_teacher.set_password("TeacherPass123!")
        _db.session.add_all([u_student, u_student2, u_teacher])
        _db.session.flush()

        # Profiles
        student = Student(
            user_id=u_student.id,
            student_code="STU2026001",
            full_name="Alice Student",
            section_id=sec.id,
            roll_number=1,
        )
        student2 = Student(
            user_id=u_student2.id,
            student_code="STU2026002",
            full_name="Bob Student",
            section_id=sec.id,
            roll_number=2,
        )
        teacher = Teacher(
            user_id=u_teacher.id,
            teacher_code="TCH001",
            full_name="Robert Teacher",
        )
        _db.session.add_all([student, student2, teacher])
        _db.session.flush()

        # Subjects
        subjects = [
            Subject(code="ENG", name="English"),
            Subject(code="HIN", name="Hindi"),
            Subject(code="MAT", name="Mathematics"),
            Subject(code="SCI", name="Science"),
            Subject(code="SST", name="Social Studies"),
        ]
        _db.session.add_all(subjects)
        _db.session.flush()

        # Exam & ExamSubjects
        exam = Exam(name="Annual Examination 2025-26", academic_year="2025-26")
        _db.session.add(exam)
        _db.session.flush()

        exam_subjects = []
        for s in subjects:
            es = ExamSubject(exam_id=exam.id, subject_id=s.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
            exam_subjects.append(es)
        _db.session.add_all(exam_subjects)
        _db.session.flush()

        # Teacher Assignments (TCH001 assigned to STU2026001 for ENG and MAT ONLY; NOT assigned to STU2026002)
        assignments = [
            TeacherAssignment(teacher_id=teacher.id, student_id=student.id, subject_id=subjects[0].id),
            TeacherAssignment(teacher_id=teacher.id, student_id=student.id, subject_id=subjects[2].id),
        ]
        _db.session.add_all(assignments)

        # Initial Marks for Alice (STU2026001) - Complete (Total: 330.50 / 500, PASS)
        marks = [
            Mark(student_id=student.id, exam_subject_id=exam_subjects[0].id, marks_obtained=Decimal("78.50"), updated_by=u_teacher.id),
            Mark(student_id=student.id, exam_subject_id=exam_subjects[1].id, marks_obtained=Decimal("65.00"), updated_by=u_teacher.id),
            Mark(student_id=student.id, exam_subject_id=exam_subjects[2].id, marks_obtained=Decimal("90.00"), updated_by=u_teacher.id),
            Mark(student_id=student.id, exam_subject_id=exam_subjects[3].id, marks_obtained=Decimal("55.00"), updated_by=u_teacher.id),
            Mark(student_id=student.id, exam_subject_id=exam_subjects[4].id, marks_obtained=Decimal("42.00"), updated_by=u_teacher.id),
        ]

        # Partial Marks for Bob (STU2026002) - Incomplete (Only ENG and MAT entered)
        partial_marks = [
            Mark(student_id=student2.id, exam_subject_id=exam_subjects[0].id, marks_obtained=Decimal("65.00"), updated_by=u_teacher.id),
            Mark(student_id=student2.id, exam_subject_id=exam_subjects[2].id, marks_obtained=Decimal("75.00"), updated_by=u_teacher.id),
        ]

        _db.session.add_all(marks + partial_marks)
        _db.session.commit()

        yield {
            "student_id": student.id,
            "student2_id": student2.id,
            "teacher_id": teacher.id,
            "student_user_id": u_student.id,
            "student2_user_id": u_student2.id,
            "teacher_user_id": u_teacher.id,
            "exam_id": exam.id,
            "subjects": {s.code: s.id for s in subjects},
        }

        _db.session.remove()
        _truncate_all_tables()
