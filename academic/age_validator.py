"""Exercise 3: Age Field Validation (Inclusive range 18–60).

Demonstrates Equivalence Partitioning (EP) and Boundary Value Analysis (BVA).
"""
from __future__ import annotations

from typing import Any, Tuple


class AgeValidationError(ValueError):
    """Raised when an age input fails validation."""
    pass


def validate_age(raw_age: Any) -> int:
    """Validate that raw_age is an integer within the inclusive range [18, 60].

    Valid partitions:
    - EP-Valid: Integer 18 <= age <= 60

    Invalid partitions:
    - EP-Low: Integer < 18 (e.g. 17, 0, -5)
    - EP-High: Integer > 60 (e.g. 61, 100)
    - EP-Type: Non-integer numeric (e.g. 25.5, Decimal("30.2"))
    - EP-String: Non-numeric string (e.g. "abc", "eighteen")
    - EP-Empty: None, empty string, or whitespace

    Boundary Values (BVA):
    - 17 (Just below minimum: Invalid)
    - 18 (Minimum valid boundary: Valid)
    - 19 (Just above minimum: Valid)
    - 59 (Just below maximum: Valid)
    - 60 (Maximum valid boundary: Valid)
    - 61 (Just above maximum: Invalid)

    Returns:
        int: Validated integer age.

    Raises:
        AgeValidationError: If input is invalid, out of range, or non-integral.
    """
    if raw_age is None:
        raise AgeValidationError("Age is required and cannot be None or empty.")

    if isinstance(raw_age, bool):
        raise AgeValidationError("Age cannot be a boolean value.")

    if isinstance(raw_age, str):
        val_str = raw_age.strip()
        if not val_str:
            raise AgeValidationError("Age cannot be empty or whitespace.")
        if not (val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit())):
            raise AgeValidationError(f"Age must be a valid integer string: got {raw_age!r}")
        try:
            val_int = int(val_str)
        except ValueError as exc:
            raise AgeValidationError(f"Malformed integer input: {raw_age!r}") from exc
    elif isinstance(raw_age, int):
        val_int = raw_age
    elif isinstance(raw_age, float):
        if not raw_age.is_integer():
            raise AgeValidationError(f"Age must be an integer, got decimal: {raw_age}")
        val_int = int(raw_age)
    else:
        raise AgeValidationError(f"Unsupported age type: {type(raw_age).__name__}")

    if val_int < 18:
        raise AgeValidationError(f"Age must be at least 18 years: got {val_int}")
    if val_int > 60:
        raise AgeValidationError(f"Age cannot exceed 60 years: got {val_int}")

    return val_int
