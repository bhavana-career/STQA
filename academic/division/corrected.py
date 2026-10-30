"""Exercise 1: Corrected Division Program.

Implements robust numeric validation, type checks, and guarded division by zero.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Union

Number = Union[int, float, Decimal, str]


def safe_divide(numerator: Number, denominator: Number, precision: int = 4) -> Decimal:
    """Safely divide numerator by denominator with explicit zero guard and type safety.

    Args:
        numerator: Dividend (int, float, Decimal, or numeric str).
        denominator: Divisor (int, float, Decimal, or numeric str).
        precision: Decimal decimal places to round (default 4).

    Returns:
        Decimal quotient rounded half-up.

    Raises:
        TypeError: If numerator or denominator cannot be parsed as a number.
        ValueError: If denominator is zero.
    """
    try:
        num_d = Decimal(str(numerator).strip())
        den_d = Decimal(str(denominator).strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TypeError(f"Invalid numeric input: numerator={numerator!r}, denominator={denominator!r}") from exc

    if den_d == Decimal(0):
        raise ValueError("Cannot divide by zero: denominator must not be zero.")

    quotient = num_d / den_d
    return round(quotient, precision)
