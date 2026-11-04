"""Black-box testing suite: Equivalence Partitioning (EP), Boundary Value Analysis (BVA), and Decision Table Testing."""

import pytest
from app.config import SUBJECTS
from app.services.marks_service import validate_subject_mark, MarksValidationError
from app.services.grading import calculate_subject_grade, is_subject_passed
from app.services.result_service import (
    determine_classification,
    evaluate_student_result,
    should_show_success_popup,
)
from app.services.student_service import authenticate_user


@pytest.mark.blackbox
class TestEquivalencePartitioning:
    """
    Equivalence Partitioning (EP) divides the input domain into valid and invalid partitions:
    - EP1 (Valid Partition - O Grade): 90..100 -> Representative: 95
    - EP2 (Valid Partition - A+ Grade): 85..89 -> Representative: 87
    - EP3 (Valid Partition - A Grade): 80..84 -> Representative: 82
    - EP4 (Valid Partition - B+ Grade): 70..79 -> Representative: 75
    - EP5 (Valid Partition - B Grade): 60..69 -> Representative: 65
    - EP6 (Valid Partition - C+ Grade): 50..59 -> Representative: 55
    - EP7 (Valid Partition - C Grade): 35..49 -> Representative: 42
    - EP8 (Valid Partition - F Grade): 0..34 -> Representative: 20
    - EP9 (Invalid Partition - Negative Marks): < 0 -> Representative: -25
    - EP10 (Invalid Partition - Marks > 100): > 100 -> Representative: 135
    - EP11 (Invalid Partition - Non-numeric / Missing): None, "", "eighty", 75.5
    """

    @pytest.mark.parametrize(
        "partition_id,rep_value,expected_grade,expected_pass",
        [
            ("EP1_Valid_O", 95, "O", True),
            ("EP2_Valid_A_Plus", 87, "A+", True),
            ("EP3_Valid_A", 82, "A", True),
            ("EP4_Valid_B_Plus", 75, "B+", True),
            ("EP5_Valid_B", 65, "B", True),
            ("EP6_Valid_C_Plus", 55, "C+", True),
            ("EP7_Valid_C", 42, "C", True),
            ("EP8_Valid_F", 20, "F", False),
        ],
    )
    def test_valid_equivalence_partitions(self, partition_id, rep_value, expected_grade, expected_pass):
        validated = validate_subject_mark(rep_value, "Physics")
        assert validated == rep_value
        assert calculate_subject_grade(validated) == expected_grade
        assert is_subject_passed(validated) is expected_pass

    @pytest.mark.parametrize(
        "partition_id,invalid_input",
        [
            ("EP9_Invalid_Negative", -25),
            ("EP10_Invalid_Above_100", 135),
            ("EP11a_Invalid_Missing_None", None),
            ("EP11b_Invalid_Empty_String", ""),
            ("EP11c_Invalid_Alphabetic", "eighty"),
            ("EP11d_Invalid_Decimal", 75.5),
        ],
    )
    def test_invalid_equivalence_partitions(self, partition_id, invalid_input):
        with pytest.raises(MarksValidationError):
            validate_subject_mark(invalid_input, "Physics")


@pytest.mark.blackbox
class TestBoundaryValueAnalysis:
    """
    Boundary Value Analysis (BVA) testing every exact boundary cluster required:
    - [-1, 0, 1]
    - [33, 34, 35, 36]
    - [48, 49, 50, 51]
    - [58, 59, 60, 61]
    - [68, 69, 70, 71]
    - [78, 79, 80, 81]
    - [83, 84, 85, 86]
    - [88, 89, 90, 91]
    - [99, 100, 101]
    """

    @pytest.mark.parametrize(
        "mark,is_valid,expected_grade,expected_pass",
        [
            # Lower domain boundary: -1, 0, 1
            (-1, False, None, None),
            (0, True, "F", False),
            (1, True, "F", False),
            # Pass/Fail & F-to-C boundary: 33, 34, 35, 36
            (33, True, "F", False),
            (34, True, "F", False),
            (35, True, "C", True),
            (36, True, "C", True),
            # C to C+ boundary: 48, 49, 50, 51
            (48, True, "C", True),
            (49, True, "C", True),
            (50, True, "C+", True),
            (51, True, "C+", True),
            # C+ to B boundary: 58, 59, 60, 61
            (58, True, "C+", True),
            (59, True, "C+", True),
            (60, True, "B", True),
            (61, True, "B", True),
            # B to B+ boundary: 68, 69, 70, 71
            (68, True, "B", True),
            (69, True, "B", True),
            (70, True, "B+", True),
            (71, True, "B+", True),
            # B+ to A boundary: 78, 79, 80, 81
            (78, True, "B+", True),
            (79, True, "B+", True),
            (80, True, "A", True),
            (81, True, "A", True),
            # A to A+ boundary: 83, 84, 85, 86
            (83, True, "A", True),
            (84, True, "A", True),
            (85, True, "A+", True),
            (86, True, "A+", True),
            # A+ to O boundary: 88, 89, 90, 91
            (88, True, "A+", True),
            (89, True, "A+", True),
            (90, True, "O", True),
            (91, True, "O", True),
            # Upper domain boundary: 99, 100, 101
            (99, True, "O", True),
            (100, True, "O", True),
            (101, False, None, None),
        ],
    )
    def test_bva_all_required_clusters(self, mark, is_valid, expected_grade, expected_pass):
        if not is_valid:
            with pytest.raises(MarksValidationError):
                validate_subject_mark(mark)
        else:
            assert validate_subject_mark(mark) == mark
            assert calculate_subject_grade(mark) == expected_grade
            assert is_subject_passed(mark) is expected_pass

    def test_bva_minimum_passing_mark_35_grade_c_defect_demo(self):
        """
        Dedicated Boundary Value Analysis (BVA) test for Defect Demonstration (DEF-SRMS-BVA-035):
        According to the SRMS Grading Matrix, marks in the range 35–49 must receive Grade 'C'.
        - Boundary value under test: mark = 35 (lower inclusive boundary of Grade 'C').
        - Expected Result: 'C'
        - Actual Result (with off-by-one '>' bug in calculate_subject_grade): 'F'
        """
        actual_grade = calculate_subject_grade(35, subject_name="Mathematics")
        assert actual_grade == "C", (
            f"BVA Defect Detected at mark=35: Expected grade 'C' (35-49 band), "
            f"but calculate_subject_grade(35) returned '{actual_grade}'."
        )


@pytest.mark.blackbox
class TestDecisionTables:
    """
    Decision Table Testing for:
    1. Login validation
    2. Subject pass/fail
    3. Overall result determination (including critical rule)
    4. Student access permissions
    5. Teacher access permissions
    6. Result popup behaviour
    """

    @pytest.mark.parametrize(
        "rule_id,username,password,expected_role",
        [
            ("DT_LOGIN_R1_ValidTeacher", "teacher01", "Teacher@123", "teacher"),
            ("DT_LOGIN_R2_ValidStudent", "student01", "Student@123", "student"),
            ("DT_LOGIN_R3_ValidUserWrongPass", "teacher01", "WrongPass", None),
            ("DT_LOGIN_R4_UnknownUser", "unknown99", "Student@123", None),
            ("DT_LOGIN_R5_EmptyUsername", "", "Student@123", None),
            ("DT_LOGIN_R6_EmptyPassword", "student01", "", None),
        ],
    )
    def test_decision_table_login_validation(self, temp_data_files, rule_id, username, password, expected_role):
        res = authenticate_user(
            username,
            password,
            students_file=temp_data_files["students_file"],
            teachers_file=temp_data_files["teachers_file"],
        )
        if expected_role is None:
            assert res is None
        else:
            assert res is not None
            assert res["role"] == expected_role

    @pytest.mark.parametrize(
        "rule_id,marks_map,expected_status,expected_classification,expected_failed_count",
        [
            (
                "DT_OVERALL_R1_AllPass_Distinction",
                {subj: 85 for subj in SUBJECTS},
                "PASS",
                "Distinction",
                0,
            ),
            (
                "DT_OVERALL_R2_AllPass_FirstClass",
                {subj: 65 for subj in SUBJECTS},
                "PASS",
                "First Class",
                0,
            ),
            (
                "DT_OVERALL_R3_AllPass_SecondClass",
                {subj: 55 for subj in SUBJECTS},
                "PASS",
                "Second Class",
                0,
            ),
            (
                "DT_OVERALL_R4_AllPass_PassClass",
                {subj: 40 for subj in SUBJECTS},
                "PASS",
                "Pass",
                0,
            ),
            (
                "DT_OVERALL_R5_HighAggregate_OneFailedSubject",
                {
                    "Physics": 95,
                    "Chemistry": 95,
                    "Mathematics": 25,
                    "Computer Science": 95,
                    "Kannada": 95,
                    "English": 95,
                },
                "FAIL",
                "Fail",
                1,
            ),
            (
                "DT_OVERALL_R6_LowAggregate_AllFailed",
                {subj: 20 for subj in SUBJECTS},
                "FAIL",
                "Fail",
                6,
            ),
        ],
    )
    def test_decision_table_overall_result(
        self, rule_id, marks_map, expected_status, expected_classification, expected_failed_count
    ):
        res = evaluate_student_result(marks_map)
        assert res.overall_status == expected_status
        assert res.classification == expected_classification
        assert len(res.failed_subjects) == expected_failed_count

    @pytest.mark.parametrize(
        "rule_id,passed_all,already_shown,expected_popup",
        [
            ("DT_POPUP_R1_PassedAll_FirstVisit", True, False, True),
            ("DT_POPUP_R2_PassedAll_SubsequentVisit", True, True, False),
            ("DT_POPUP_R3_FailedSubject_FirstVisit", False, False, False),
            ("DT_POPUP_R4_FailedSubject_SubsequentVisit", False, True, False),
        ],
    )
    def test_decision_table_popup_behaviour(self, rule_id, passed_all, already_shown, expected_popup):
        marks = {subj: (80 if passed_all else 25) for subj in SUBJECTS}
        result = evaluate_student_result(marks)
        assert should_show_success_popup(result, popup_already_shown=already_shown) is expected_popup

    def test_decision_table_access_permissions(self, client):
        # Unauthenticated user -> redirected to /login (302)
        assert client.get("/teacher/dashboard").status_code == 302
        assert client.get("/student/dashboard").status_code == 302

        # Log in as student01 (STU001)
        client.post("/login", data={"username": "student01", "password": "Student@123"})
        assert client.get("/student/dashboard").status_code == 200
        assert client.get("/student/view/STU001").status_code == 200
        # Student attempting to access another student's record -> 403
        assert client.get("/student/view/STU002").status_code == 403
        # Student attempting to access teacher routes -> 403
        assert client.get("/teacher/dashboard").status_code == 403
        assert client.get("/teacher/students").status_code == 403
        assert client.get("/teacher/marks").status_code == 403
        assert client.get("/teacher/analytics").status_code == 403
        client.get("/logout")

        # Log in as teacher01
        client.post("/login", data={"username": "teacher01", "password": "Teacher@123"})
        assert client.get("/teacher/dashboard").status_code == 200
        assert client.get("/teacher/students").status_code == 200
        assert client.get("/teacher/marks").status_code == 200
        assert client.get("/teacher/analytics").status_code == 200
        assert client.get("/teacher/students/STU001/result").status_code == 200
        # Teacher attempting to access student-only route -> 403
        assert client.get("/student/dashboard").status_code == 403
