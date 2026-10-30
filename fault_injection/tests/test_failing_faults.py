"""Failing test suite for intentional faults DEF-001 and DEF-002.

Running this module directly executes tests that EXPECT correct business rules
against the faulty implementations, resulting in genuine test FAILURES.
This provides the 'Before Fix' execution evidence for STQA defect tracking.
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from fault_injection.faulty_grading import (
    faulty_grade_for_percentage_strict_greater,
    faulty_percentage_fixed_denominator,
)


@pytest.mark.fault_demo
def test_def_001_failing_on_faulty_percentage():
    """DEF-001 Before-Fix Test: Expects 63.04% for 145/230 marks.

    FAILS on faulty_percentage_fixed_denominator because it divides by 300.
    """
    obtained = Decimal("145")
    subject_count = 3
    expected_correct = Decimal("63.04")

    # This assertion fails because faulty function returns 48.33
    actual = faulty_percentage_fixed_denominator(obtained, subject_count)
    assert actual == expected_correct, (
        f"DEF-001 Failure: Expected {expected_correct}%, got {actual}%"
    )


@pytest.mark.fault_demo
def test_def_002_failing_on_faulty_grade_boundary():
    """DEF-002 Before-Fix Test: Expects A1 for exact 90.00% lower bound.

    FAILS on faulty_grade_for_percentage_strict_greater because '>' causes demotion to A2.
    """
    pct = Decimal("90.00")
    expected_grade = "A1"

    # This assertion fails because faulty function returns "A2"
    actual = faulty_grade_for_percentage_strict_greater(pct)
    assert actual == expected_grade, (
        f"DEF-002 Failure: Expected grade {expected_grade} for {pct}%, got {actual}"
    )


@pytest.mark.fault_demo
def test_def_006_failing_on_division_by_zero():
    """DEF-006 Before-Fix Test: Expects domain-specific ValueError on division by zero.

    FAILS on divide_faulty because it lacks zero guarding and raises raw ZeroDivisionError.
    """
    from academic.division.faulty import divide_faulty

    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide_faulty(10, 0)

