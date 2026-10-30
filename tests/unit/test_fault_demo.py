"""Demonstration tests for intentional defects DEF-001 and DEF-002.

Illustrates:
1. Expected failure on the intentionally faulty implementation.
2. Verified success on the corrected production implementation.
3. Regression prevention guards.
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from app.services.grading import grade_for_percentage, percentage
from fault_injection.faulty_grading import (
    faulty_grade_for_percentage_strict_greater,
    faulty_percentage_fixed_denominator,
)


@pytest.mark.fault_demo
class TestDefect001PercentageDenominator:
    """DEF-001: Incorrect percentage denominator assumption."""

    def test_def_001_faulty_produces_incorrect_percentage(self):
        """Demonstrates DEF-001:

        Three subjects with max marks: 100, 80, 50 -> Actual total max = 230.
        Marks obtained: 80 + 40 + 25 = 145.
        Expected correct percentage: 145 / 230 * 100 = 63.04%.
        Faulty function assumes denominator is 3 * 100 = 300 -> 145 / 300 * 100 = 48.33%.
        """
        obtained = Decimal("145")
        subject_count = 3
        expected_correct = Decimal("63.04")

        faulty_val = faulty_percentage_fixed_denominator(obtained, subject_count)
        # Demonstrates the defect: faulty calculation diverges from expected
        assert faulty_val != expected_correct
        assert faulty_val == Decimal("48.33")

    def test_def_001_corrected_implementation_passes(self):
        """Regression test for DEF-001:

        Verified against corrected production service using actual total maximum.
        """
        obtained = Decimal("145")
        actual_total_max = Decimal("230")
        assert percentage(obtained, actual_total_max) == Decimal("63.04")


@pytest.mark.fault_demo
class TestDefect002GradeBoundaryComparison:
    """DEF-002: Off-by-one boundary comparison ('>' instead of '>=')."""

    def test_def_002_faulty_fails_at_lower_bounds(self):
        """Demonstrates DEF-002:

        90.00% is the lower bound for A1.
        Due to '>' check, 90.00% fails to match A1 (> 90.00 is False) and demotes to A2.
        35.00% is the pass mark (D). Due to '>' check, it demotes to E (FAIL).
        """
        # Lower bound for A1
        faulty_a1 = faulty_grade_for_percentage_strict_greater(Decimal("90.00"))
        assert faulty_a1 != "A1"
        assert faulty_a1 == "A2"

        # Pass threshold lower bound
        faulty_pass = faulty_grade_for_percentage_strict_greater(Decimal("35.00"))
        assert faulty_pass != "D"
        assert faulty_pass == "E"

    def test_def_002_corrected_implementation_passes(self):
        """Regression test for DEF-002:

        Verified against corrected production service using '>=' lower bound.
        """
        assert grade_for_percentage(Decimal("90.00")) == "A1"
        assert grade_for_percentage(Decimal("35.00")) == "D"
