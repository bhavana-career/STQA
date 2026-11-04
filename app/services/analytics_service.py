"""Analytics and class/section performance calculation service for SRMS."""

from typing import Dict, Any, List, Optional
from app.config import SUBJECTS, VALID_SECTIONS
from app.services.student_service import get_all_students


def calculate_dashboard_overview(students_file: str) -> Dict[str, int]:
    """
    Compute overview metrics for the Teacher Dashboard:
    - Total students
    - Number of students in Section A, B, C
    - Total passed students
    - Total failed students
    - Number of distinction students
    """
    students = get_all_students(students_file, include_results=True)

    total_students = len(students)
    section_counts = {sec: 0 for sec in VALID_SECTIONS}
    passed_count = 0
    failed_count = 0
    distinction_count = 0

    for s in students:
        sec = str(s.get("section", "")).upper()
        if sec in section_counts:
            section_counts[sec] += 1

        res = s.get("result", {})
        if res.get("passed_all"):
            passed_count += 1
        else:
            failed_count += 1

        if res.get("classification") == "Distinction":
            distinction_count += 1

    return {
        "total_students": total_students,
        "section_a_count": section_counts["A"],
        "section_b_count": section_counts["B"],
        "section_c_count": section_counts["C"],
        "total_passed": passed_count,
        "total_failed": failed_count,
        "distinction_count": distinction_count,
    }


def calculate_section_analytics(
    students_file: str, section: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate analytics strictly for the selected section (`'A'`, `'B'`, or `'C'`),
    or across all sections only if `section` is None or `'ALL'`.

    When a specific section (e.g., `'A'`) is selected:
    Section A average percentage = Sum of percentages of all Section A students / Number of Section A students.
    Students from Section B or Section C are strictly excluded.
    """
    all_students = get_all_students(students_file, include_results=True)

    normalized_section = section.strip().upper() if section and section.strip() else "ALL"
    if normalized_section in VALID_SECTIONS:
        filtered = [
            s for s in all_students if str(s.get("section", "")).upper() == normalized_section
        ]
    else:
        normalized_section = "ALL"
        filtered = all_students

    count = len(filtered)
    if count == 0:
        return {
            "section": normalized_section,
            "student_count": 0,
            "average_total_marks": 0.0,
            "average_percentage": 0.0,
            "subject_averages": {subj: 0.0 for subj in SUBJECTS},
            "passing_students": 0,
            "failing_students": 0,
            "distinction_students": 0,
            "classification_distribution": {
                "Distinction": 0,
                "First Class": 0,
                "Second Class": 0,
                "Pass": 0,
                "Fail": 0,
            },
            "pass_rate": 0.0,
        }

    total_marks_sum = 0
    percentage_sum = 0.0
    subject_sums = {subj: 0 for subj in SUBJECTS}
    passing_students = 0
    failing_students = 0
    distinction_students = 0
    classification_dist = {
        "Distinction": 0,
        "First Class": 0,
        "Second Class": 0,
        "Pass": 0,
        "Fail": 0,
    }

    for s in filtered:
        res = s["result"]
        total_marks_sum += res["total_marks"]
        percentage_sum += res["percentage"]

        for subj in SUBJECTS:
            subject_sums[subj] += int(s["marks"][subj])

        if res["passed_all"]:
            passing_students += 1
        else:
            failing_students += 1

        cls_name = res["classification"]
        if cls_name in classification_dist:
            classification_dist[cls_name] += 1
        if cls_name == "Distinction":
            distinction_students += 1

    avg_total = round(total_marks_sum / count, 2)
    avg_percentage = round(percentage_sum / count, 2)
    subject_averages = {subj: round(subject_sums[subj] / count, 2) for subj in SUBJECTS}
    pass_rate = round((passing_students / count) * 100.0, 2)

    return {
        "section": normalized_section,
        "student_count": count,
        "average_total_marks": avg_total,
        "average_percentage": avg_percentage,
        "subject_averages": subject_averages,
        "passing_students": passing_students,
        "failing_students": failing_students,
        "distinction_students": distinction_students,
        "classification_distribution": classification_dist,
        "pass_rate": pass_rate,
    }


def calculate_all_sections_comparison(students_file: str) -> Dict[str, Dict[str, Any]]:
    """Return independent analytics dictionaries for Section A, Section B, and Section C."""
    return {sec: calculate_section_analytics(students_file, sec) for sec in VALID_SECTIONS}
