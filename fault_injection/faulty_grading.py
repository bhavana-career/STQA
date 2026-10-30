"""Controlled faulty implementation of grading rules for STQA defect lifecycle demonstration.

DEF-001: Incorrect percentage denominator assumption.
DEF-002: Off-by-one boundary comparison ('>' instead of '>=').
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

DEFAULT_GRADE_BANDS: tuple[tuple[str, Decimal], ...] = (
    ("A1", Decimal("90.00")),
    ("A2", Decimal("80.00")),
    ("B1", Decimal("70.00")),
    ("B2", Decimal("60.00")),
    ("C1", Decimal("50.00")),
    ("C2", Decimal("40.00")),
    ("D", Decimal("35.00")),
)


def faulty_percentage_fixed_denominator(
    obtained: Decimal,
    subject_count: int,
) -> Decimal:
    """DEF-001 FAULTY implementation:

    Assumes every subject has 100 maximum marks.
    denominator = subject_count * 100.
    Fails when subject maximum marks vary (e.g. 100, 80, 50 -> total 230).
    """
    assumed_max = Decimal(str(subject_count * 100))
    pct = (obtained / assumed_max) * Decimal("100")
    return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def faulty_grade_for_percentage_strict_greater(pct: Decimal) -> str:
    """DEF-002 FAULTY implementation:

    Uses '>' instead of '>=' on inclusive lower bounds.
    Causes exactly 90.00% to evaluate to 'A2' instead of 'A1',
    and 35.00% to evaluate to 'E' (FAIL) instead of 'D' (PASS).
    """
    for grade_name, lower_bound in DEFAULT_GRADE_BANDS:
        # BUG: Off-by-one boundary condition using '>' instead of '>='
        if pct > lower_bound:
            return grade_name
    return "E"
