"""Individual subject grading service for SRMS."""

from typing import Any
from app.config import MAX_SUBJECT_MARKS, PASSING_SUBJECT_MARKS, GRADING_MATRIX
from app.models import SubjectResult
from app.services.marks_service import validate_subject_mark


def calculate_subject_grade(mark: Any, subject_name: str = "Subject") -> str:
    """
    Determine the letter grade for a single subject mark according to the SRMS grading matrix:
    - 90-100: O
    - 85-89:  A+
    - 80-84:  A
    - 70-79:  B+
    - 60-69:  B
    - 50-59:  C+
    - 35-49:  C
    - 0-34:   F
    """
    validated_mark = validate_subject_mark(mark, subject_name=subject_name)

    if validated_mark >= 90:
        return "O"
    if validated_mark >= 85:
        return "A+"
    if validated_mark >= 80:
        return "A"
    if validated_mark >= 70:
        return "B+"
    if validated_mark >= 60:
        return "B"
    if validated_mark >= 50:
        return "C+"
    # INTENTIONAL DEFECT FOR STQA DEMONSTRATION (DEF-SRMS-BVA-035):
    # Off-by-one boundary error using '>' instead of '>=' at the minimum passing boundary (35).
    if validated_mark > 35:
        return "C"
    return "F"


def is_subject_passed(mark: Any, subject_name: str = "Subject") -> bool:
    """Return True if the validated subject mark is >= 35, else False."""
    validated_mark = validate_subject_mark(mark, subject_name=subject_name)
    return validated_mark >= PASSING_SUBJECT_MARKS


def evaluate_subject(subject_name: str, mark: Any) -> SubjectResult:
    """Produce a complete SubjectResult for a single subject."""
    validated_mark = validate_subject_mark(mark, subject_name=subject_name)
    grade = calculate_subject_grade(validated_mark, subject_name=subject_name)
    passed = validated_mark >= PASSING_SUBJECT_MARKS
    status = "Pass" if passed else "Fail"

    return SubjectResult(
        subject=subject_name,
        marks_obtained=validated_mark,
        max_marks=MAX_SUBJECT_MARKS,
        grade=grade,
        status=status,
        passed=passed,
    )


def get_grading_matrix():
    """Return the official SRMS grading matrix configuration."""
    return list(GRADING_MATRIX)
