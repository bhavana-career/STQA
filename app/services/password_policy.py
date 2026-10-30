"""Password strength validation and secure password generation utilities.

Enforces:
- Minimum length (default: 12 characters).
- Uppercase, lowercase, numeric, and special character requirements.
- Cryptographically secure generation with secrets module.
"""
from __future__ import annotations

import re
import secrets
import string

MIN_PASSWORD_LENGTH = 12
SPECIAL_CHARACTERS = "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"


def validate_password_strength(
    password: str, min_length: int = MIN_PASSWORD_LENGTH
) -> tuple[bool, str | None]:
    """Validate password against complexity policy.

    :param password: Candidate password string.
    :param min_length: Minimum required length (default 12).
    :return: (True, None) if valid, or (False, error_message) if invalid.
    """
    if not password or len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number (0-9)."

    if not re.search(r"[!@#$%^&*()_\-+=\[\]{}|;:,.<>?/~`]", password):
        return False, "Password must contain at least one special character."

    return True, None


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password meeting all policy requirements."""
    length = max(length, MIN_PASSWORD_LENGTH)
    specials = "!@#$%^&*()-_=+[]{}|;:,.<>?"

    # Ensure at least 2 of each category
    chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(string.digits),
        secrets.choice(specials),
        secrets.choice(specials),
    ]

    all_allowed = string.ascii_letters + string.digits + specials
    while len(chars) < length:
        chars.append(secrets.choice(all_allowed))

    rng = secrets.SystemRandom()
    rng.shuffle(chars)
    candidate = "".join(chars)

    valid, _ = validate_password_strength(candidate, min_length=length)
    if not valid:
        return generate_secure_password(length)

    return candidate
