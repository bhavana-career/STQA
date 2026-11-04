"""Unit tests for marks validation, total calculation, percentage, grading, and overall classification."""

import pytest
from app.config import SUBJECTS
from app.services.marks_service import (
    validate_subject_mark,
    validate_all_marks,
    calculate_total_marks,
    calculate_percentage,
    format_percentage,
    MarksValidationError,
)
from app.services.grading import (
    calculate_subject_grade,
    is_subject_passed,
    evaluate_subject,
    get_grading_matrix,
)
from app.services.result_service import (
    determine_classification,
    evaluate_student_result,
    should_show_success_popup,
)


@pytest.mark.unit
class TestMarksValidation:
    """Test individual subject mark validation across valid, boundary, and invalid inputs."""

    @pytest.mark.parametrize(
        "valid_mark",
        [0, 1, 34, 35, 49, 50, 59, 60, 69, 70, 79, 80, 84, 85, 89, 90, 100],
    )
    def test_valid_boundary_and_partition_marks(self, valid_mark):
        assert validate_subject_mark(valid_mark, "Physics") == valid_mark
        assert validate_subject_mark(str(valid_mark), "Physics") == valid_mark

    @pytest.mark.parametrize("invalid_mark", [-1, -50, 101, 150, 999])
    def test_out_of_range_marks_rejected(self, invalid_mark):
        with pytest.raises(MarksValidationError):
            validate_subject_mark(invalid_mark, "Mathematics")

    @pytest.mark.parametrize("missing_or_empty", [None, "", "   "])
    def test_missing_or_empty_marks_never_become_zero(self, missing_or_empty):
        with pytest.raises(MarksValidationError):
            validate_subject_mark(missing_or_empty, "Chemistry")

    @pytest.mark.parametrize("decimal_mark", [75.5, 34.99, 0.0, "85.5", "35.0"])
    def test_decimal_marks_rejected(self, decimal_mark):
        with pytest.raises(MarksValidationError):
            validate_subject_mark(decimal_mark, "English")

    @pytest.mark.parametrize("invalid_type", [True, False, "abc", "75a", [80], {"m": 80}])
    def test_invalid_data_types_rejected(self, invalid_type):
        with pytest.raises(MarksValidationError):
            validate_subject_mark(invalid_type, "Kannada")

    def test_validate_all_marks_success(self):
        marks = {subj: 75 for subj in SUBJECTS}
        validated = validate_all_marks(marks)
        assert validated == marks

    def test_validate_all_marks_missing_subject(self):
        marks = {subj: 75 for subj in SUBJECTS if subj != "Kannada"}
        with pytest.raises(MarksValidationError, match="Missing marks"):
            validate_all_marks(marks)

    def test_validate_all_marks_extra_subject(self):
        marks = {subj: 75 for subj in SUBJECTS}
        marks["Biology"] = 80
        with pytest.raises(MarksValidationError, match="Unrecognized subjects"):
            validate_all_marks(marks)

    def test_validate_all_marks_non_dict(self):
        with pytest.raises(MarksValidationError, match="dictionary"):
            validate_all_marks([80, 80, 80, 80, 80, 80])


@pytest.mark.unit
class TestMarksCalculations:
    """Test total marks and percentage calculation logic."""

    def test_calculate_total_marks_typical(self):
        marks = {
            "Physics": 92,
            "Chemistry": 88,
            "Mathematics": 95,
            "Computer Science": 96,
            "Kannada": 85,
            "English": 90,
        }
        assert calculate_total_marks(marks) == 546

    def test_calculate_total_marks_zero(self):
        marks = {subj: 0 for subj in SUBJECTS}
        assert calculate_total_marks(marks) == 0

    def test_calculate_total_marks_maximum(self):
        marks = {subj: 100 for subj in SUBJECTS}
        assert calculate_total_marks(marks) == 600

    def test_calculate_percentage_rounding(self):
        # 412 / 600 = 68.6666... -> 68.67
        assert calculate_percentage(412) == 68.67
        # 255 / 600 = 42.5 -> 42.5
        assert calculate_percentage(255) == 42.5
        assert format_percentage(42.5) == "42.50%"
        # 0 / 600 = 0.0
        assert calculate_percentage(0) == 0.0
        # 600 / 600 = 100.0
        assert calculate_percentage(600) == 100.0

    @pytest.mark.parametrize("bad_total", [-1, 601, "400", True, None])
    def test_calculate_percentage_invalid_total(self, bad_total):
        with pytest.raises(MarksValidationError):
            calculate_percentage(bad_total)

    def test_calculate_percentage_invalid_max_marks(self):
        with pytest.raises(MarksValidationError):
            calculate_percentage(300, max_marks=0)


@pytest.mark.unit
class TestSubjectGrading:
    """Test individual subject grading across all grade boundaries."""

    @pytest.mark.parametrize(
        "mark,expected_grade,expected_passed",
        [
            (100, "O", True),
            (90, "O", True),
            (89, "A+", True),
            (85, "A+", True),
            (84, "A", True),
            (80, "A", True),
            (79, "B+", True),
            (70, "B+", True),
            (69, "B", True),
            (60, "B", True),
            (59, "C+", True),
            (50, "C+", True),
            (49, "C", True),
            (35, "C", True),
            (34, "F", False),
            (1, "F", False),
            (0, "F", False),
        ],
    )
    def test_grade_boundaries(self, mark, expected_grade, expected_passed):
        assert calculate_subject_grade(mark) == expected_grade
        assert is_subject_passed(mark) is expected_passed
        sr = evaluate_subject("Physics", mark)
        assert sr.grade == expected_grade
        assert sr.passed is expected_passed
        assert sr.status == ("Pass" if expected_passed else "Fail")
        assert sr.max_marks == 100

    def test_grading_matrix_structure(self):
        matrix = get_grading_matrix()
        assert len(matrix) == 8
        assert matrix[0]["grade"] == "O"
        assert matrix[-1]["grade"] == "F"


@pytest.mark.unit
class TestOverallClassification:
    """Test overall classification boundaries and the critical single-subject fail rule."""

    @pytest.mark.parametrize(
        "pct,all_passed,expected_class",
        [
            (100.0, True, "Distinction"),
            (75.0, True, "Distinction"),
            (74.99, True, "First Class"),
            (60.0, True, "First Class"),
            (59.99, True, "Second Class"),
            (50.0, True, "Second Class"),
            (49.99, True, "Pass"),
            (35.0, True, "Pass"),
            (34.99, True, "Fail"),
            (0.0, True, "Fail"),
            # Critical rule: high aggregate with any failed subject MUST be Fail
            (90.0, False, "Fail"),
            (75.0, False, "Fail"),
            (65.0, False, "Fail"),
            (55.0, False, "Fail"),
            (40.0, False, "Fail"),
        ],
    )
    def test_determine_classification_boundaries(self, pct, all_passed, expected_class):
        assert determine_classification(pct, all_subjects_passed=all_passed) == expected_class

    def test_high_aggregate_with_one_failed_subject_fails_overall(self):
        # 5 subjects at 100, 1 subject at 34 -> Total = 534/600 (89.00%)
        marks = {
            "Physics": 100,
            "Chemistry": 100,
            "Mathematics": 34,
            "Computer Science": 100,
            "Kannada": 100,
            "English": 100,
        }
        result = evaluate_student_result(marks)
        assert result.total_marks == 534
        assert result.percentage == 89.0
        assert result.passed_all is False
        assert result.overall_status == "FAIL"
        assert result.classification == "Fail"
        assert result.failed_subjects == ["Mathematics"]
        assert should_show_success_popup(result, popup_already_shown=False) is False

    def test_passing_student_popup_and_classification(self):
        marks = {subj: 80 for subj in SUBJECTS}
        result = evaluate_student_result(marks)
        assert result.total_marks == 480
        assert result.percentage == 80.0
        assert result.passed_all is True
        assert result.overall_status == "PASS"
        assert result.classification == "Distinction"
        assert result.failed_subjects == []
        assert should_show_success_popup(result, popup_already_shown=False) is True
        assert should_show_success_popup(result, popup_already_shown=True) is False
