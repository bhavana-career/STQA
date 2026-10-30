"""Unit tests for marks parsing and validation rules (TDD).

Tests Equivalence Partitioning (EP) and Boundary Value Analysis (BVA) as defined in:
- docs/requirements.md (§4.3)
- docs/test-cases.md (TC-CALC-01 to TC-CALC-05, TC-BB-01 to TC-BB-08, TC-WB-13)
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from app.services.marks_service import (
    ValidationError,
    parse_mark,
    validate_mark_input,
)


@pytest.mark.unit
class TestParseMarkValidInputs:
    """Tests for valid marks inputs (EP-M1, EP-M6)."""

    def test_none_or_empty_returns_none(self):
        # Blank / null = "not entered"
        assert parse_mark(None, max_marks=100) is None
        assert parse_mark("", max_marks=100) is None
        assert parse_mark("   ", max_marks=100) is None

    def test_zero_mark_accepted(self):
        # TC-CALC-01, TC-BB-02
        res = parse_mark(0, max_marks=100)
        assert res == Decimal("0.00")
        assert parse_mark("0", max_marks=100) == Decimal("0.00")
        assert parse_mark("0.0", max_marks=100) == Decimal("0.00")
        assert parse_mark("0.00", max_marks=100) == Decimal("0.00")

    def test_maximum_mark_accepted(self):
        # TC-CALC-02, TC-BB-05
        assert parse_mark(100, max_marks=100) == Decimal("100.00")
        assert parse_mark("100", max_marks=100) == Decimal("100.00")
        assert parse_mark("100.00", max_marks=100) == Decimal("100.00")
        # Non-100 max marks
        assert parse_mark(80, max_marks=80) == Decimal("80.00")
        assert parse_mark("50.0", max_marks=50) == Decimal("50.00")

    def test_boundary_step_marks_accepted(self):
        # TC-BB-03 (0.5), TC-BB-04 (max - 0.5)
        assert parse_mark(0.5, max_marks=100) == Decimal("0.50")
        assert parse_mark("0.5", max_marks=100) == Decimal("0.50")
        assert parse_mark(99.5, max_marks=100) == Decimal("99.50")
        assert parse_mark("99.50", max_marks=100) == Decimal("99.50")

    def test_decimal_marks_half_step_accepted(self):
        # TC-CALC-05
        assert parse_mark("78.5", max_marks=100) == Decimal("78.50")
        assert parse_mark(42.5, max_marks=100) == Decimal("42.50")
        assert parse_mark(Decimal("65.0"), max_marks=100) == Decimal("65.00")


@pytest.mark.unit
class TestParseMarkInvalidBoundariesAndValues:
    """Boundary Value Analysis and Negative Tests (TC-CALC-03, TC-CALC-04, TC-BB-01, TC-BB-06)."""

    def test_negative_marks_rejected(self):
        # TC-CALC-03, TC-BB-01
        with pytest.raises(ValidationError, match="must be between 0 and"):
            parse_mark(-0.5, max_marks=100)
        with pytest.raises(ValidationError, match="must be between 0 and"):
            parse_mark("-1", max_marks=100)
        with pytest.raises(ValidationError, match="must be between 0 and"):
            parse_mark("-10.0", max_marks=100)

    def test_marks_exceeding_maximum_rejected(self):
        # TC-CALC-04, TC-BB-06 (max + 0.5 rejected)
        with pytest.raises(ValidationError, match="must be between 0 and 100"):
            parse_mark(100.5, max_marks=100)
        with pytest.raises(ValidationError, match="must be between 0 and 100"):
            parse_mark("101", max_marks=100)
        with pytest.raises(ValidationError, match="must be between 0 and 100"):
            parse_mark(1000, max_marks=100)
        with pytest.raises(ValidationError, match="must be between 0 and 80"):
            parse_mark(80.5, max_marks=80)

    def test_invalid_decimal_step_rejected(self):
        # TC-MARK-04, EP-M5 (0.5 steps only)
        with pytest.raises(ValidationError, match="0.5"):
            parse_mark(78.25, max_marks=100)
        with pytest.raises(ValidationError, match="0.5"):
            parse_mark("78.3", max_marks=100)
        with pytest.raises(ValidationError, match="0.5"):
            parse_mark("0.1", max_marks=100)
        with pytest.raises(ValidationError, match="0.5"):
            parse_mark(45.75, max_marks=100)

    def test_malformed_values_rejected(self):
        # TC-MARK-03, EP-M4
        malformed_inputs = [
            "abc",
            "1e2",
            "NaN",
            "Infinity",
            "-Infinity",
            True,  # booleans should not masquerade as 1 / 0
            False,
            [],
            {},
            "12,5",
            "0x10",
            "10.5.5",
        ]
        for val in malformed_inputs:
            with pytest.raises(ValidationError):
                parse_mark(val, max_marks=100)

    def test_invalid_max_marks_config(self):
        with pytest.raises(ValueError, match="Maximum marks must be greater than zero"):
            parse_mark(50, max_marks=0)
        with pytest.raises(ValueError, match="Maximum marks must be greater than zero"):
            parse_mark(50, max_marks=-10)
        with pytest.raises(ValueError, match="Invalid maximum marks specification"):
            parse_mark(50, max_marks="invalid")


@pytest.mark.unit
class TestValidateMarkInputList:
    """Tests for validating multi-subject batch marks input."""

    def test_valid_batch_marks(self):
        items = [
            {"subject_id": 1, "marks_obtained": "78.5"},
            {"subject_id": 2, "marks_obtained": 90},
            {"subject_id": 3, "marks_obtained": None},
        ]
        limits = {1: Decimal("100"), 2: Decimal("100"), 3: Decimal("100")}
        parsed = validate_mark_input(items, subject_max_marks=limits)
        assert parsed[1] == Decimal("78.50")
        assert parsed[2] == Decimal("90.00")
        assert parsed[3] is None

    def test_duplicate_subject_in_batch_rejected(self):
        # TC-MARK-09
        items = [
            {"subject_id": 1, "marks_obtained": "78.5"},
            {"subject_id": 1, "marks_obtained": "80.0"},
        ]
        limits = {1: Decimal("100")}
        with pytest.raises(ValidationError, match="Duplicate subject"):
            validate_mark_input(items, subject_max_marks=limits)

    def test_unknown_subject_id_rejected(self):
        items = [{"subject_id": 999, "marks_obtained": "78.5"}]
        limits = {1: Decimal("100")}
        with pytest.raises(ValidationError, match="Unknown subject"):
            validate_mark_input(items, subject_max_marks=limits)

    def test_empty_batch_rejected(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_mark_input([], subject_max_marks={1: Decimal("100")})

    def test_non_dict_entry_rejected(self):
        with pytest.raises(ValidationError, match="must be a JSON object"):
            validate_mark_input(["not-a-dict"], subject_max_marks={1: Decimal("100")})

    def test_missing_subject_id_rejected(self):
        with pytest.raises(ValidationError, match="Missing 'subject_id'"):
            validate_mark_input([{"marks_obtained": 50}], subject_max_marks={1: Decimal("100")})

    def test_invalid_subject_id_type_rejected(self):
        with pytest.raises(ValidationError, match="Invalid subject_id"):
            validate_mark_input([{"subject_id": "not_an_int", "marks_obtained": 50}], subject_max_marks={1: Decimal("100")})

    def test_field_level_validation_error_propagated(self):
        items = [{"subject_id": 1, "marks_obtained": "invalid_mark"}]
        with pytest.raises(ValidationError, match="Subject 1: Marks format invalid") as exc:
            validate_mark_input(items, subject_max_marks={1: Decimal("100")})
        assert exc.value.field == "1"
