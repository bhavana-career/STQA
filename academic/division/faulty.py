"""Exercise 1: Faulty Division Program (DEF-006).

Defects:
1. No zero check: allows division by zero to crash with raw ZeroDivisionError rather than domain-specific ValueError.
2. Truncates non-integer divisions incorrectly via integer division or string coercion.
"""
from __future__ import annotations


def divide_faulty(a: float, b: float) -> float:
    """Faulty division without zero guarding or proper input type handling."""
    # Defect: Directly divides without checking if b == 0, causing unhandled crash
    return a / b
