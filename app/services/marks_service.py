"""Marks parsing, validation, and batch input checks.

Pure, side-effect free validation functions designed for high testability.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Sequence

# Allowed pattern: optional sign, digits, and optional 1 or 2 decimal digits
# Examples: "0", "78", "78.5", "100", "99.50", "-5"
MARK_FORMAT_RE = re.compile(r"^-?\d+(\.\d{1,2})?$")


class ValidationError(ValueError):
    """Raised when marks data fails business validation rules."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


def parse_mark(raw_value: Any, max_marks: Decimal | int | float) -> Decimal | None:
    """Parse and validate a single mark against subject maximum and step constraints.

    Rules:
    - None or blank string -> None (treated as "not entered" or cleared)
    - 0 <= mark <= max_marks
    - Step must be a multiple of 0.5 (e.g. 78, 78.5, 78.50 valid; 78.25 invalid)
    - Malformed values, booleans, arrays, exponentials, or negatives raise ValidationError
    - Quantized to 2 decimal places (Decimal("0.00"))
    """
    try:
        max_dec = Decimal(str(max_marks))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid maximum marks specification: {max_marks!r}") from exc

    if max_dec <= Decimal("0"):
        raise ValueError("Maximum marks must be greater than zero")

    if raw_value is None:
        return None

    # Python booleans are subclasses of int, so explicitly reject True/False
    if isinstance(raw_value, bool):
        raise ValidationError("Marks value must be a valid number, not boolean")

    if not isinstance(raw_value, (int, float, str, Decimal)):
        raise ValidationError(f"Invalid mark type: {type(raw_value).__name__}")

    raw_str = str(raw_value).strip()
    if not raw_str:
        return None

    if not MARK_FORMAT_RE.match(raw_str):
        raise ValidationError(
            f"Marks format invalid: {raw_str!r}. Must be a non-negative number formatted as integer or up to 2 decimal places."
        )

    try:
        val = Decimal(raw_str)
    except InvalidOperation as exc:
        raise ValidationError(f"Invalid numeric value: {raw_str!r}") from exc

    if val < Decimal("0") or val > max_dec:
        raise ValidationError(
            f"Marks value {val} must be between 0 and {max_dec}"
        )

    # Check 0.5 step constraint: val * 2 must be an integer
    doubled = val * 2
    if doubled != doubled.to_integral_value():
        raise ValidationError(
            f"Marks must be in steps of 0.5 (received {val})"
        )

    return val.quantize(Decimal("0.01"))


def validate_mark_input(
    items: Sequence[Mapping[str, Any]],
    subject_max_marks: Mapping[int, Decimal | int | float],
) -> dict[int, Decimal | None]:
    """Validate a batch of marks entries for a student.

    :param items: sequence of dicts with keys 'subject_id' and 'marks_obtained'
    :param subject_max_marks: mapping of subject_id -> max_marks
    :return: dict mapping subject_id -> parsed Decimal or None
    """
    if not items:
        raise ValidationError("Marks submission cannot be empty")

    seen_subjects: set[int] = set()
    result: dict[int, Decimal | None] = {}

    for idx, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ValidationError(f"Entry at index {idx} must be a JSON object")

        if "subject_id" not in item:
            raise ValidationError(f"Missing 'subject_id' at index {idx}")

        try:
            sub_id = int(item["subject_id"])
        except (ValueError, TypeError) as exc:
            raise ValidationError(f"Invalid subject_id at index {idx}") from exc

        if sub_id in seen_subjects:
            raise ValidationError(f"Duplicate subject ID {sub_id} in marks submission")
        seen_subjects.add(sub_id)

        if sub_id not in subject_max_marks:
            raise ValidationError(f"Unknown subject ID {sub_id}")

        max_mark = subject_max_marks[sub_id]
        raw_mark = item.get("marks_obtained")

        try:
            parsed = parse_mark(raw_mark, max_marks=max_mark)
        except ValidationError as exc:
            raise ValidationError(f"Subject {sub_id}: {exc.message}", field=str(sub_id)) from exc

        result[sub_id] = parsed

    return result
