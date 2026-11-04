"""Overall result and classification engine for SRMS."""

from typing import Dict, Any, List
from app.config import SUBJECTS, MAX_TOTAL_MARKS
from app.models import OverallResult, SubjectResult
from app.services.marks_service import (
    validate_all_marks,
    calculate_total_marks,
    calculate_percentage,
    format_percentage,
    MarksValidationError,
)
from app.services.grading import evaluate_subject


def determine_classification(percentage: float, all_subjects_passed: bool = True) -> str:
    """
    Determine overall classification based on percentage and critical subject pass rule.

    Critical rule:
    If even one subject has fewer than 35 marks (`all_subjects_passed=False`),
    overall classification MUST be 'Fail', regardless of aggregate percentage.

    Classification table (when all subjects are passed):
    - 75% and above: Distinction
    - 60%–74.99%:    First Class
    - 50%–59.99%:    Second Class
    - 35%–49.99%:    Pass
    - Below 35%:     Fail
    """
    if not isinstance(percentage, (int, float)) or isinstance(percentage, bool):
        raise MarksValidationError("Percentage must be a numeric value.")
    if percentage < 0.0 or percentage > 100.0:
        raise MarksValidationError("Percentage must be between 0.0 and 100.0.")

    if not all_subjects_passed:
        return "Fail"

    if percentage >= 75.0:
        return "Distinction"
    if percentage >= 60.0:
        return "First Class"
    if percentage >= 50.0:
        return "Second Class"
    if percentage >= 35.0:
        return "Pass"
    return "Fail"


def evaluate_student_result(marks_dict: Dict[str, Any]) -> OverallResult:
    """
    Evaluate all six subjects for a student, compute total, percentage,
    subject-wise grades, failed subjects, overall status, and classification.
    """
    validated_marks = validate_all_marks(marks_dict)

    subject_results: List[SubjectResult] = []
    failed_subjects: List[str] = []

    for subj in SUBJECTS:
        sr = evaluate_subject(subj, validated_marks[subj])
        subject_results.append(sr)
        if not sr.passed:
            failed_subjects.append(subj)

    total_marks = calculate_total_marks(validated_marks)
    percentage = calculate_percentage(total_marks, MAX_TOTAL_MARKS)
    formatted_pct = format_percentage(percentage)

    passed_all = len(failed_subjects) == 0 and percentage >= 35.0
    classification = determine_classification(percentage, all_subjects_passed=(len(failed_subjects) == 0))
    overall_status = "PASS" if passed_all else "FAIL"

    return OverallResult(
        total_marks=total_marks,
        max_marks=MAX_TOTAL_MARKS,
        percentage=percentage,
        formatted_percentage=formatted_pct,
        classification=classification,
        overall_status=overall_status,
        passed_all=passed_all,
        failed_subjects=failed_subjects,
        subject_results=subject_results,
    )


def should_show_success_popup(result: OverallResult, popup_already_shown: bool = False) -> bool:
    """
    Determine whether the celebratory result announcement popup should be shown
    on the student dashboard.
    - Shown only if the student passed all six subjects (`result.passed_all` is True)
      and it has not already been displayed during the current session.
    """
    if popup_already_shown:
        return False
    return bool(result.passed_all)
