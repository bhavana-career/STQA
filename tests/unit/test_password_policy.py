"""Unit tests for password strength validation and generator."""
from __future__ import annotations

import pytest

from app.services.password_policy import generate_secure_password, validate_password_strength


@pytest.mark.unit
class TestPasswordPolicy:
    """Test suite for password policy enforcement."""

    def test_valid_strong_password(self):
        ok, err = validate_password_strength("StrongP@ssw0rd!")
        assert ok is True
        assert err is None

    def test_password_too_short(self):
        ok, err = validate_password_strength("Short1!", min_length=12)
        assert ok is False
        assert "at least 12 characters" in err

    def test_missing_uppercase(self):
        ok, err = validate_password_strength("weakpassword123!", min_length=12)
        assert ok is False
        assert "uppercase" in err

    def test_missing_lowercase(self):
        ok, err = validate_password_strength("WEAKPASSWORD123!", min_length=12)
        assert ok is False
        assert "lowercase" in err

    def test_missing_digit(self):
        ok, err = validate_password_strength("WeakPassword!!", min_length=12)
        assert ok is False
        assert "number" in err

    def test_missing_special(self):
        ok, err = validate_password_strength("WeakPassword123", min_length=12)
        assert ok is False
        assert "special character" in err

    def test_generated_passwords_meet_policy(self):
        for _ in range(20):
            pw = generate_secure_password(length=16)
            assert len(pw) >= 16
            ok, err = validate_password_strength(pw, min_length=16)
            assert ok is True
            assert err is None
