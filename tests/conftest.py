"""Shared Pytest fixtures for Unit, Functional, Integration, Black-box, White-box, and E2E Selenium tests."""

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Dict, Any, List

import pytest
from werkzeug.serving import make_server

from app import create_app


SAMPLE_TEACHERS: List[Dict[str, Any]] = [
    {
        "teacher_id": "TCH001",
        "name": "Prof. Rajesh Sharma",
        "username": "teacher01",
        "password": "Teacher@123",
        "role": "teacher",
        "designation": "Senior Examination Coordinator — Class 10",
    }
]

SAMPLE_STUDENTS: List[Dict[str, Any]] = [
    {
        "student_id": "STU001",
        "name": "Aarav Kulkarni",
        "username": "student01",
        "password": "Student@123",
        "class": "10",
        "section": "A",
        "roll_number": 101,
        "marks": {
            "Physics": 92,
            "Chemistry": 88,
            "Mathematics": 95,
            "Computer Science": 96,
            "Kannada": 85,
            "English": 90,
        },
    },
    {
        "student_id": "STU002",
        "name": "Diya Nair",
        "username": "student02",
        "password": "Student@123",
        "class": "10",
        "section": "B",
        "roll_number": 201,
        "marks": {
            "Physics": 68,
            "Chemistry": 72,
            "Mathematics": 65,
            "Computer Science": 74,
            "Kannada": 64,
            "English": 69,
        },
    },
    {
        "student_id": "STU003",
        "name": "Rohan Deshmukh",
        "username": "student03",
        "password": "Student@123",
        "class": "10",
        "section": "C",
        "roll_number": 301,
        "marks": {
            "Physics": 82,
            "Chemistry": 78,
            "Mathematics": 28,
            "Computer Science": 85,
            "Kannada": 74,
            "English": 79,
        },
    },
    {
        "student_id": "STU004",
        "name": "Sneha Hegde",
        "username": "student04",
        "password": "Student@123",
        "class": "10",
        "section": "A",
        "roll_number": 102,
        "marks": {
            "Physics": 54,
            "Chemistry": 58,
            "Mathematics": 52,
            "Computer Science": 60,
            "Kannada": 55,
            "English": 57,
        },
    },
    {
        "student_id": "STU005",
        "name": "Karthik Gowda",
        "username": "student05",
        "password": "Student@123",
        "class": "10",
        "section": "A",
        "roll_number": 103,
        "marks": {
            "Physics": 42,
            "Chemistry": 38,
            "Mathematics": 40,
            "Computer Science": 48,
            "Kannada": 44,
            "English": 43,
        },
    },
]


@pytest.fixture
def temp_data_files(tmp_path: Path):
    """
    Create isolated temporary students.json and teachers.json files for a test.
    Guarantees that production demonstration files in app/data/ are never modified.
    """
    students_path = tmp_path / "students.json"
    teachers_path = tmp_path / "teachers.json"

    students_path.write_text(json.dumps(SAMPLE_STUDENTS, indent=2), encoding="utf-8")
    teachers_path.write_text(json.dumps(SAMPLE_TEACHERS, indent=2), encoding="utf-8")

    return {
        "students_file": str(students_path),
        "teachers_file": str(teachers_path),
    }


@pytest.fixture
def test_app(temp_data_files):
    """Create a configured Flask application instance using temporary JSON files."""
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-srms",
            "STUDENTS_FILE": temp_data_files["students_file"],
            "TEACHERS_FILE": temp_data_files["teachers_file"],
        }
    )
    return app


@pytest.fixture
def client(test_app):
    """Provide a Flask test client for functional and integration HTTP testing."""
    return test_app.test_client()


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server_url(test_app):
    """
    Start the Flask app in a background thread on a free localhost port for Selenium E2E tests.
    Automatically shuts down after the test completes.
    """
    port = _get_free_port()
    server = make_server("127.0.0.1", port, test_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    thread.join(timeout=3)


@pytest.fixture
def browser():
    """
    Initialize Selenium Chrome WebDriver.
    Defaults to headless mode unless SRMS_HEADLESS=false is set in environment variables
    for visible browser demonstrations.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions

    headless = os.environ.get("SRMS_HEADLESS", "true").lower() != "false"
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    yield driver
    driver.quit()
