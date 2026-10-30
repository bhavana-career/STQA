"""Unit tests for User authentication helpers and safe URL validation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.auth import is_safe_url
from app.models import User, utc_now


@pytest.mark.unit
class TestUserAuthHelpers:
    """Unit tests for User model lockout, login recording, and session versioning."""

    def test_is_locked_behavior(self):
        u = User(login_id="STU001", role="student")
        u.set_password("Pass123456")
        assert u.is_locked() is False

        # Set lockout 15 minutes into future
        now = utc_now()
        u.locked_until = now + timedelta(minutes=15)
        assert u.is_locked(now=now) is True

        # Test past lockout expired
        past = now + timedelta(minutes=16)
        assert u.is_locked(now=past) is False

    def test_record_failed_login_and_lockout(self):
        u = User(login_id="STU001", role="student")
        u.set_password("Pass123456")

        # 4 failed attempts should not lock
        for i in range(1, 5):
            locked = u.record_failed_login(max_attempts=5, lockout_minutes=15)
            assert locked is False
            assert u.failed_login_count == i
            assert u.locked_until is None

        # 5th attempt triggers lockout
        locked = u.record_failed_login(max_attempts=5, lockout_minutes=15)
        assert locked is True
        assert u.failed_login_count == 5
        assert u.locked_until is not None
        assert u.is_locked() is True

    def test_record_successful_login_resets_counters(self):
        u = User(login_id="STU001", role="student")
        u.set_password("Pass123456")
        u.failed_login_count = 3
        u.locked_until = utc_now() + timedelta(minutes=10)

        u.record_successful_login()
        assert u.failed_login_count == 0
        assert u.locked_until is None
        assert u.last_login_at is not None

    def test_increment_session_version(self):
        u = User(login_id="STU001", role="student")
        u.set_password("Pass123456")
        assert u.session_version == 1

        v2 = u.increment_session_version()
        assert v2 == 2
        assert u.session_version == 2


@pytest.mark.unit
class TestSafeUrlValidation:
    """TC-SEC-09: Unit tests for is_safe_url preventing open redirects."""

    @pytest.mark.parametrize(
        "target,expected",
        [
            ("/student/dashboard", True),
            ("/teacher/dashboard", True),
            ("/api/student/result?exam_id=1", True),
            ("/", True),
            ("", False),
            (None, False),
            ("https://evil.example.com", False),
            ("http://evil.example.com", False),
            ("//evil.example.com", False),
            ("\\\\evil.example.com", False),
            ("javascript:alert(1)", False),
            ("student/dashboard", False),  # Relative without leading slash
        ],
    )
    def test_is_safe_url_cases(self, target, expected):
        assert is_safe_url(target) is expected
