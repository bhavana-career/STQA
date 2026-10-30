"""Unit tests for grading calculations and result determination rules (TDD).

Tests:
- Percentage calculation with Half-Up rounding (TC-CALC-10, TC-CALC-11)
- Grade assignment at every boundary condition (TC-CALC-12, TC-BB-09, TC-WB-01..05)
- Subject-level pass/fail and grades (TC-BB-07, TC-CALC-17)
- Incomplete result detection (TC-CALC-06, TC-WB-09)
- Student failing one subject despite high aggregate percentage (TC-CALC-13d)
- Boundary Value Analysis and Decision Table rules (TC-BB-10)
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from app.services.grading import (
    GradingConfig,
    SubjectResult,
    compute_result,
    grade_for_percentage,
    percentage,
    subject_grade,
)


@pytest.mark.unit
class TestPercentageCalculation:
    """Tests for exact Decimal percentage calculation and Half-Up rounding."""

    def test_standard_percentage(self):
        # 330 out of 500 = 66.00%
        assert percentage(Decimal("330"), Decimal("500")) == Decimal("66.00")

    def test_non_uniform_maxima_percentage(self):
        # TC-CALC-10: 145 out of 230 = 63.043478... -> 63.04%
        assert percentage(Decimal("145"), Decimal("230")) == Decimal("63.04")

    def test_rounding_half_up_behavior(self):
        # TC-CALC-11: 1 out of 160 = 0.00625 -> 0.625% -> 0.63% (half-up, not bankers)
        assert percentage(Decimal("1"), Decimal("160")) == Decimal("0.63")
        # 2 out of 3 = 66.666... -> 66.67%
        assert percentage(Decimal("2"), Decimal("3")) == Decimal("66.67")

    def test_zero_obtained_gives_zero_percent(self):
        assert percentage(Decimal("0"), Decimal("500")) == Decimal("0.00")

    def test_full_marks_gives_hundred_percent(self):
        assert percentage(Decimal("500"), Decimal("500")) == Decimal("100.00")

    def test_invalid_max_marks_rejected(self):
        # TC-WB-06
        with pytest.raises(ValueError, match="Total maximum marks must be greater than zero"):
            percentage(Decimal("50"), Decimal("0"))
        with pytest.raises(ValueError, match="Total maximum marks must be greater than zero"):
            percentage(Decimal("50"), Decimal("-100"))

    def test_obtained_marks_out_of_range_rejected(self):
        # TC-WB-07
        with pytest.raises(ValueError, match="Total obtained marks cannot be negative"):
            percentage(Decimal("-1"), Decimal("100"))
        with pytest.raises(ValueError, match="Total obtained marks cannot exceed total maximum"):
            percentage(Decimal("101"), Decimal("100"))

    def test_non_numeric_percentage_inputs_rejected(self):
        with pytest.raises(ValueError, match="Invalid numeric input"):
            percentage("invalid", Decimal("100"))
        with pytest.raises(ValueError, match="Invalid numeric input"):
            percentage(Decimal("50"), "invalid")


@pytest.mark.unit
class TestGradeForPercentage:
    """Tests for grade assignment across all boundary conditions (TC-CALC-12, TC-BB-09)."""

    @pytest.mark.parametrize(
        "pct_val, expected_grade",
        [
            # A1 band: 90.00 to 100.00
            (Decimal("100.00"), "A1"),
            (Decimal("95.50"), "A1"),
            (Decimal("90.00"), "A1"),  # lower boundary inclusive
            # A2 band: 80.00 to 89.99
            (Decimal("89.99"), "A2"),  # upper boundary
            (Decimal("85.00"), "A2"),
            (Decimal("80.00"), "A2"),  # lower boundary
            # B1 band: 70.00 to 79.99
            (Decimal("79.99"), "B1"),
            (Decimal("75.00"), "B1"),
            (Decimal("70.00"), "B1"),
            # B2 band: 60.00 to 69.99
            (Decimal("69.99"), "B2"),
            (Decimal("65.00"), "B2"),
            (Decimal("60.00"), "B2"),
            # C1 band: 50.00 to 59.99
            (Decimal("59.99"), "C1"),
            (Decimal("55.00"), "C1"),
            (Decimal("50.00"), "C1"),
            # C2 band: 40.00 to 49.99
            (Decimal("49.99"), "C2"),
            (Decimal("45.00"), "C2"),
            (Decimal("40.00"), "C2"),
            # D band: 35.00 to 39.99 (Pass mark lower bound)
            (Decimal("39.99"), "D"),
            (Decimal("37.50"), "D"),
            (Decimal("35.00"), "D"),
            # E band: Below 35.00
            (Decimal("34.99"), "E"),  # just below pass boundary
            (Decimal("20.00"), "E"),
            (Decimal("0.00"), "E"),
        ],
    )
    def test_grade_boundaries(self, pct_val, expected_grade):
        assert grade_for_percentage(pct_val) == expected_grade

    def test_percentage_out_of_range_raises_value_error(self):
        # TC-WB-01, TC-WB-02
        with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
            grade_for_percentage(Decimal("-0.01"))
        with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
            grade_for_percentage(Decimal("100.01"))

    def test_non_numeric_percentage_for_grade_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid percentage value"):
            grade_for_percentage("not-a-number")


@pytest.mark.unit
class TestSubjectGrade:
    """Tests for single subject percentage and grade (TC-CALC-17)."""

    def test_subject_grade_calculation(self):
        # 89.5 out of 100 -> 89.50% -> A2
        pct, gr, passed = subject_grade(Decimal("89.5"), Decimal("100"), Decimal("35"))
        assert pct == Decimal("89.50")
        assert gr == "A2"
        assert passed is True

    def test_subject_pass_boundary(self):
        # TC-BB-07: 34.5 (fail), 35.0 (pass), 35.5 (pass)
        _, gr1, p1 = subject_grade(Decimal("34.5"), Decimal("100"), Decimal("35"))
        assert p1 is False
        assert gr1 == "E"

        _, gr2, p2 = subject_grade(Decimal("35.0"), Decimal("100"), Decimal("35"))
        assert p2 is True
        assert gr2 == "D"

        _, gr3, p3 = subject_grade(Decimal("35.5"), Decimal("100"), Decimal("35"))
        assert p3 is True
        assert gr3 == "D"


@pytest.mark.unit
class TestComputeResult:
    """Tests for overall examination result calculation and status."""

    @pytest.fixture
    def standard_subjects(self):
        """5 standard subjects of 100 marks each, 35 pass mark."""
        return [
            ("ENG", "English", Decimal("100"), Decimal("35")),
            ("HIN", "Hindi", Decimal("100"), Decimal("35")),
            ("MAT", "Mathematics", Decimal("100"), Decimal("35")),
            ("SCI", "Science", Decimal("100"), Decimal("35")),
            ("SST", "Social Science", Decimal("100"), Decimal("35")),
        ]

    def test_all_subjects_at_maximum(self, standard_subjects):
        # TC-CALC-07
        entries = [
            SubjectResult(code=c, name=n, max_marks=m, pass_marks=p, marks_obtained=Decimal("100.00"))
            for c, n, m, p in standard_subjects
        ]
        res = compute_result(entries)
        assert res.status == "PASS"
        assert res.total_obtained == Decimal("500.00")
        assert res.total_max == Decimal("500.00")
        assert res.percentage == Decimal("100.00")
        assert res.grade == "A1"
        assert len(res.subjects) == 5

    def test_all_subjects_at_zero(self, standard_subjects):
        # TC-CALC-08
        entries = [
            SubjectResult(code=c, name=n, max_marks=m, pass_marks=p, marks_obtained=Decimal("0.00"))
            for c, n, m, p in standard_subjects
        ]
        res = compute_result(entries)
        assert res.status == "FAIL"
        assert res.total_obtained == Decimal("0.00")
        assert res.total_max == Decimal("500.00")
        assert res.percentage == Decimal("0.00")
        assert res.grade == "E"

    def test_student_passing_all_subjects(self, standard_subjects):
        # TC-CALC-09: 78, 65, 90, 55, 42 -> Total: 330 -> 66.00% -> B2 -> PASS
        marks = [Decimal("78"), Decimal("65"), Decimal("90"), Decimal("55"), Decimal("42")]
        entries = [
            SubjectResult(code=c, name=n, max_marks=m, pass_marks=p, marks_obtained=marks[i])
            for i, (c, n, m, p) in enumerate(standard_subjects)
        ]
        res = compute_result(entries)
        assert res.status == "PASS"
        assert res.total_obtained == Decimal("330.00")
        assert res.total_max == Decimal("500.00")
        assert res.percentage == Decimal("66.00")
        assert res.grade == "B2"

    def test_student_fails_one_subject_despite_high_overall_percentage(self, standard_subjects):
        # Requirement 6 & TC-CALC-13d:
        # ENG: 100, HIN: 100, MAT: 100, SCI: 100, SST: 0
        # Total: 400/500 = 80.00% (A2 level), but FAIL because SST < 35 -> Grade must be E
        marks = [Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100"), Decimal("0")]
        entries = [
            SubjectResult(code=c, name=n, max_marks=m, pass_marks=p, marks_obtained=marks[i])
            for i, (c, n, m, p) in enumerate(standard_subjects)
        ]
        res = compute_result(entries)
        assert res.status == "FAIL"
        assert res.total_obtained == Decimal("400.00")
        assert res.percentage == Decimal("80.00")
        assert res.grade == "E"  # overall grade is E because status is FAIL

    def test_student_fails_with_one_subject_just_below_pass_mark(self, standard_subjects):
        # TC-CALC-13a: One subject 34.50, rest 100.00
        marks = [Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100"), Decimal("34.5")]
        entries = [
            SubjectResult(code=c, name=n, max_marks=m, pass_marks=p, marks_obtained=marks[i])
            for i, (c, n, m, p) in enumerate(standard_subjects)
        ]
        res = compute_result(entries)
        assert res.status == "FAIL"
        assert res.grade == "E"

    def test_student_passes_with_all_subjects_at_exact_pass_mark(self, standard_subjects):
        # TC-CALC-13b: All subjects 35.00 -> Total 175 -> 35.00% -> PASS -> D
        entries = [
            SubjectResult(code=c, name=n, max_marks=m, pass_marks=p, marks_obtained=Decimal("35.00"))
            for c, n, m, p in standard_subjects
        ]
        res = compute_result(entries)
        assert res.status == "PASS"
        assert res.total_obtained == Decimal("175.00")
        assert res.percentage == Decimal("35.00")
        assert res.grade == "D"

    def test_missing_marks_yields_incomplete_status(self, standard_subjects):
        # TC-CALC-06, TC-WB-09: One subject has None -> status is INCOMPLETE
        entries = [
            SubjectResult(code="ENG", name="English", max_marks=Decimal("100"), pass_marks=Decimal("35"), marks_obtained=Decimal("80")),
            SubjectResult(code="HIN", name="Hindi", max_marks=Decimal("100"), pass_marks=Decimal("35"), marks_obtained=None),
            SubjectResult(code="MAT", name="Mathematics", max_marks=Decimal("100"), pass_marks=Decimal("35"), marks_obtained=Decimal("95")),
        ]
        res = compute_result(entries)
        assert res.status == "INCOMPLETE"
        assert res.total_obtained is None
        assert res.percentage is None
        assert res.grade is None
        assert res.total_max == Decimal("300.00")
        # Check individual subject results
        assert res.subjects[1].marks_obtained is None
        assert res.subjects[1].grade is None
        assert res.subjects[1].passed is None

    def test_custom_grading_config_thresholds(self):
        # Test with custom config (e.g. min overall percentage 40.00)
        custom_cfg = GradingConfig(min_overall_percentage=Decimal("40.00"))
        entries = [
            SubjectResult(code="S1", name="Sub1", max_marks=Decimal("100"), pass_marks=Decimal("30"), marks_obtained=Decimal("35")),
        ]
        # Passed subject (35 >= 30), but percentage is 35.00% < 40.00% overall threshold
        res = compute_result(entries, config=custom_cfg)
        assert res.status == "FAIL"
        assert res.grade == "E"

    def test_empty_entries_raises_value_error(self):
        with pytest.raises(ValueError, match="Cannot compute result for empty subjects list"):
            compute_result([])
