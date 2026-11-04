"""Configuration module for the Student Result Management System (SRMS)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SUBJECTS = [
    "Physics",
    "Chemistry",
    "Mathematics",
    "Computer Science",
    "Kannada",
    "English",
]

MAX_SUBJECT_MARKS = 100
MIN_SUBJECT_MARKS = 0
PASSING_SUBJECT_MARKS = 35
MAX_TOTAL_MARKS = 600
VALID_SECTIONS = ["A", "B", "C"]
DEFAULT_CLASS = "10"
EXAMINATION_NAME = "Class 10 Secondary Board Examination — Academic Year 2026–27"

GRADING_MATRIX = [
    {"min": 90, "max": 100, "grade": "O", "status": "Pass", "description": "Outstanding"},
    {"min": 85, "max": 89, "grade": "A+", "status": "Pass", "description": "Excellent"},
    {"min": 80, "max": 84, "grade": "A", "status": "Pass", "description": "Very Good"},
    {"min": 70, "max": 79, "grade": "B+", "status": "Pass", "description": "Good"},
    {"min": 60, "max": 69, "grade": "B", "status": "Pass", "description": "Above Average"},
    {"min": 50, "max": 59, "grade": "C+", "status": "Pass", "description": "Average"},
    {"min": 35, "max": 49, "grade": "C", "status": "Pass", "description": "Satisfactory Pass"},
    {"min": 0, "max": 34, "grade": "F", "status": "Fail", "description": "Fail"},
]

CLASSIFICATION_MATRIX = [
    {"min_pct": 75.0, "max_pct": 100.0, "classification": "Distinction"},
    {"min_pct": 60.0, "max_pct": 74.99, "classification": "First Class"},
    {"min_pct": 50.0, "max_pct": 59.99, "classification": "Second Class"},
    {"min_pct": 35.0, "max_pct": 49.99, "classification": "Pass"},
    {"min_pct": 0.0, "max_pct": 34.99, "classification": "Fail"},
]


class Config:
    """Flask application configuration."""

    SECRET_KEY = os.environ.get("SRMS_SECRET_KEY", "srms-local-academic-secret-key-2026")
    STUDENTS_FILE = str(DATA_DIR / "students.json")
    TEACHERS_FILE = str(DATA_DIR / "teachers.json")
    TESTING = False
