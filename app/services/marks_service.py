"""Marks validation and calculation service for SRMS."""

from typing import Dict, Any
from app.config import SUBJECTS, MIN_SUBJECT_MARKS, MAX_SUBJECT_MARKS, MAX_TOTAL_MARKS


class MarksValidationError(ValueError):
    """Raised when subject marks fail validation constraints."""


def validate_subject_mark(mark: Any, subject_name: str = "Subject") -> int:
    """
    Validate a single subject mark.

    Rules:
    - Minimum: 0
    - Maximum: 100
    - Must be an integer (or numeric string representing an integer).
    - Decimal marks are rejected.
    - Negative marks are rejected.
    - Marks exceeding 100 are rejected.
    - Empty/None/boolean values are rejected and never silently become zero.
    """
    if mark is None or isinstance(mark, bool):
        raise MarksValidationError(f"{subject_name} mark cannot be empty or missing.")

    if isinstance(mark, float):
        raise MarksValidationError(f"{subject_name} mark must be a whole integer, not a decimal.")

    if isinstance(mark, str):
        stripped = mark.strip()
        if stripped == "":
            raise MarksValidationError(f"{subject_name} mark cannot be empty.")
        if "." in stripped:
            raise MarksValidationError(f"{subject_name} mark must be a whole integer, not a decimal.")
        try:
            parsed = int(stripped)
        except ValueError as exc:
            raise MarksValidationError(f"{subject_name} mark must be a valid integer.") from exc
    elif isinstance(mark, int):
        parsed = mark
    else:
        raise MarksValidationError(f"{subject_name} mark has an invalid data type.")

    if parsed < MIN_SUBJECT_MARKS:
        raise MarksValidationError(f"{subject_name} mark cannot be negative (minimum is {MIN_SUBJECT_MARKS}).")

    if parsed > MAX_SUBJECT_MARKS:
        raise MarksValidationError(f"{subject_name} mark cannot exceed {MAX_SUBJECT_MARKS}.")

    return parsed


def validate_all_marks(marks_dict: Any) -> Dict[str, int]:
    """
    Validate a dictionary containing all six required subjects.
    Returns a clean dictionary mapping each subject name to its validated integer mark.
    """
    if not isinstance(marks_dict, dict):
        raise MarksValidationError("Marks data must be provided as a dictionary of subjects.")

    missing = [subj for subj in SUBJECTS if subj not in marks_dict]
    if missing:
        raise MarksValidationError(f"Missing marks for subjects: {', '.join(missing)}.")

    extra = [subj for subj in marks_dict if subj not in SUBJECTS]
    if extra:
        raise MarksValidationError(f"Unrecognized subjects provided: {', '.join(extra)}.")

    validated: Dict[str, int] = {}
    for subj in SUBJECTS:
        validated[subj] = validate_subject_mark(marks_dict[subj], subject_name=subj)

    return validated


def calculate_total_marks(marks_dict: Dict[str, Any]) -> int:
    """
    Validate all six subject marks and compute total marks out of 600.
    Total Marks = Physics + Chemistry + Mathematics + Computer Science + Kannada + English.
    """
    validated = validate_all_marks(marks_dict)
    return sum(validated[subj] for subj in SUBJECTS)


def calculate_percentage(total_marks: int, max_marks: int = MAX_TOTAL_MARKS) -> float:
    """
    Calculate percentage = (Total Marks / 600) * 100 rounded to 2 decimal places.
    """
    if not isinstance(total_marks, int) or isinstance(total_marks, bool):
        raise MarksValidationError("Total marks must be an integer.")
    if total_marks < 0 or total_marks > max_marks:
        raise MarksValidationError(f"Total marks must be between 0 and {max_marks}.")
    if max_marks <= 0:
        raise MarksValidationError("Maximum marks must be greater than zero.")

    raw_percentage = (total_marks / max_marks) * 100.0
    return round(raw_percentage, 2)


def format_percentage(percentage: float) -> str:
    """Format a percentage float to exactly two decimal places with % suffix."""
    return f"{percentage:.2f}%"
