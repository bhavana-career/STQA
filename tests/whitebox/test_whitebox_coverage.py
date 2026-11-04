"""White-box testing suite: Statement coverage, Branch coverage, Condition testing, and Independent Execution Paths."""

from pathlib import Path
import pytest

from app.config import SUBJECTS
from app.models import StudentRecord
from app.services.marks_service import (
    validate_subject_mark,
    validate_all_marks,
    calculate_percentage,
    MarksValidationError,
)
from app.services.grading import calculate_subject_grade
from app.services.result_service import determine_classification
from app.services.student_service import (
    validate_student_payload,
    create_student,
    update_student,
    delete_student,
    get_student_by_id,
    get_student_by_username,
    authenticate_user,
    StudentValidationError,
    _safe_read_json,
    _safe_write_json,
)
from app.services.analytics_service import calculate_section_analytics


@pytest.mark.whitebox
class TestWhiteBoxStatementAndBranchCoverage:
    """
    White-box tests exercising every decision branch and condition in:
    - marks_service.py
    - grading.py
    - result_service.py
    - student_service.py
    - analytics_service.py
    """

    def test_validate_subject_mark_all_branches(self):
        # Branch 1: None or bool
        with pytest.raises(MarksValidationError):
            validate_subject_mark(None)
        with pytest.raises(MarksValidationError):
            validate_subject_mark(True)
        # Branch 2: float
        with pytest.raises(MarksValidationError):
            validate_subject_mark(45.6)
        # Branch 3: string branches (empty, decimal string, non-numeric string, valid numeric string)
        with pytest.raises(MarksValidationError):
            validate_subject_mark("   ")
        with pytest.raises(MarksValidationError):
            validate_subject_mark("50.0")
        with pytest.raises(MarksValidationError):
            validate_subject_mark("fifty")
        assert validate_subject_mark(" 88 ") == 88
        # Branch 4: int branch
        assert validate_subject_mark(72) == 72
        # Branch 5: unsupported object type
        with pytest.raises(MarksValidationError):
            validate_subject_mark(object())
        # Branch 6 & 7: < 0 and > 100
        with pytest.raises(MarksValidationError):
            validate_subject_mark(-5)
        with pytest.raises(MarksValidationError):
            validate_subject_mark(105)

    def test_grading_all_8_independent_paths(self):
        # Basis paths through calculate_subject_grade (Cyclomatic Complexity = 8)
        assert calculate_subject_grade(95) == "O"
        assert calculate_subject_grade(86) == "A+"
        assert calculate_subject_grade(81) == "A"
        assert calculate_subject_grade(74) == "B+"
        assert calculate_subject_grade(63) == "B"
        assert calculate_subject_grade(52) == "C+"
        assert calculate_subject_grade(38) == "C"
        assert calculate_subject_grade(15) == "F"

    def test_determine_classification_all_independent_paths(self):
        # Path 1: Invalid type
        with pytest.raises(MarksValidationError):
            determine_classification("80", True)
        with pytest.raises(MarksValidationError):
            determine_classification(True, True)
        # Path 2: Out of range percentage
        with pytest.raises(MarksValidationError):
            determine_classification(-0.5, True)
        with pytest.raises(MarksValidationError):
            determine_classification(100.5, True)
        # Path 3: Not all subjects passed
        assert determine_classification(88.0, all_subjects_passed=False) == "Fail"
        # Paths 4..8: Percentage branches when all_subjects_passed=True
        assert determine_classification(80.0, True) == "Distinction"
        assert determine_classification(65.0, True) == "First Class"
        assert determine_classification(55.0, True) == "Second Class"
        assert determine_classification(40.0, True) == "Pass"
        assert determine_classification(30.0, True) == "Fail"

    def test_student_payload_validation_branches(self, temp_data_files):
        base_payload = {
            "student_id": "STU099",
            "name": "Test User",
            "username": "student99",
            "password": "Student@123",
            "class": "10",
            "section": "A",
            "roll_number": 199,
            "marks": {subj: 70 for subj in SUBJECTS},
        }

        # Non-dict payload
        with pytest.raises(StudentValidationError, match="dictionary"):
            validate_student_payload("not-a-dict", [])

        # Missing required string fields
        for field in ["student_id", "name", "username", "password"]:
            bad = dict(base_payload, **{field: "   "})
            with pytest.raises(StudentValidationError):
                validate_student_payload(bad, [])

        # Invalid class
        with pytest.raises(StudentValidationError, match="Class must be"):
            validate_student_payload(dict(base_payload, **{"class": "12"}), [])

        # Invalid section
        with pytest.raises(StudentValidationError, match="Section must be"):
            validate_student_payload(dict(base_payload, section="Z"), [])

        # Invalid roll numbers (None, bool, decimal, negative, non-int)
        for bad_roll in [None, True, "", "12.5", 12.5, "abc", 0, -5]:
            with pytest.raises(StudentValidationError, match="Roll number"):
                validate_student_payload(dict(base_payload, roll_number=bad_roll), [])

        # Reserved teacher username collision
        with pytest.raises(StudentValidationError, match="reserved for a teacher"):
            validate_student_payload(
                dict(base_payload, username="teacher01"),
                existing_students=[],
                existing_teachers=[{"username": "teacher01"}],
            )

        # Duplicate student_id, duplicate username, duplicate roll_number in same section
        existing = [
            {
                "student_id": "STU001",
                "name": "Existing",
                "username": "student01",
                "section": "A",
                "roll_number": 101,
            }
        ]
        with pytest.raises(StudentValidationError, match="already exists"):
            validate_student_payload(dict(base_payload, student_id="stu001"), existing)
        with pytest.raises(StudentValidationError, match="already assigned to another student"):
            validate_student_payload(dict(base_payload, username="STUDENT01"), existing)
        with pytest.raises(StudentValidationError, match="Roll number 101 is already assigned"):
            validate_student_payload(dict(base_payload, roll_number=101, section="A"), existing)

        # Missing marks dict
        with pytest.raises(StudentValidationError, match="Subject marks dictionary is required"):
            validate_student_payload(dict(base_payload, marks=None), [])

        # Invalid mark inside payload
        bad_marks = {subj: 70 for subj in SUBJECTS}
        bad_marks["Physics"] = 120
        with pytest.raises(StudentValidationError):
            validate_student_payload(dict(base_payload, marks=bad_marks), [])

    def test_json_storage_error_and_edge_branches(self, tmp_path: Path):
        non_existent = str(tmp_path / "missing.json")
        assert _safe_read_json(non_existent) == []

        not_a_list_file = tmp_path / "bad_root.json"
        not_a_list_file.write_text('{"key": "value"}', encoding="utf-8")
        with pytest.raises(StudentValidationError, match="expected a list"):
            _safe_read_json(str(not_a_list_file))

        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("{corrupt json", encoding="utf-8")
        with pytest.raises(StudentValidationError, match="Failed to parse JSON"):
            _safe_read_json(str(corrupt_file))

        with pytest.raises(StudentValidationError, match="must be a list"):
            _safe_write_json(str(tmp_path / "out.json"), {"not": "list"})

    def test_lookup_and_analytics_edge_branches(self, temp_data_files, tmp_path: Path):
        sf = temp_data_files["students_file"]
        tf = temp_data_files["teachers_file"]

        assert get_student_by_id(sf, "") is None
        assert get_student_by_id(sf, "NON_EXISTENT") is None
        assert get_student_by_username(sf, "") is None
        assert get_student_by_username(sf, "non_existent") is None
        assert authenticate_user("   ", "pass", sf, tf) is None
        assert authenticate_user(123, "pass", sf, tf) is None

        with pytest.raises(StudentValidationError, match="not found"):
            update_student(sf, "NON_EXISTENT", {"name": "Nobody"})

        with pytest.raises(StudentValidationError, match="not found"):
            delete_student(sf, "NON_EXISTENT")

        # Empty students file analytics branch
        empty_sf = str(tmp_path / "empty_students.json")
        _safe_write_json(empty_sf, [])
        empty_stats = calculate_section_analytics(empty_sf, "A")
        assert empty_stats["student_count"] == 0
        assert empty_stats["average_percentage"] == 0.0

        # All sections analytics branch (section=None)
        all_stats = calculate_section_analytics(sf, None)
        assert all_stats["section"] == "ALL"
        assert all_stats["student_count"] == 5

        # StudentRecord model serialization roundtrip
        rec = StudentRecord.from_dict(
            {
                "student_id": "STU500",
                "name": "Model Test",
                "username": "model500",
                "password": "Pass",
                "class": "10",
                "section": "B",
                "roll_number": 210,
                "marks": {subj: 80 for subj in SUBJECTS},
            }
        )
        assert rec.to_dict()["student_id"] == "STU500"
