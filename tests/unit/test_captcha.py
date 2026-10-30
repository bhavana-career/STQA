"""Unit tests for Cloudflare Turnstile CAPTCHA verification service.

Covers:
- TC-CAP-01: Verifier success parsing.
- TC-CAP-02: Missing/blank token short-circuits without network call.
- TC-CAP-03: Invalid token rejection.
- TC-CAP-04: Expired / duplicate token rejection.
- TC-CAP-05: Hostname mismatch rejection.
- TC-CAP-06: Action mismatch rejection.
- TC-CAP-07: Network timeout / connection failure handled as unavailable.
- TC-CAP-08: Non-200, malformed JSON, missing 'success' key handled as unavailable.
- TC-CAP-09: Request payload structure verification.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import requests

from app.services.captcha import CaptchaResult, verify_captcha


@pytest.mark.unit
class TestCaptchaVerifierUnit:
    """TC-CAP unit test suite."""

    def test_tc_cap_02_blank_token_short_circuits(self, app):
        with patch("requests.post") as mock_post:
            res1 = verify_captcha("")
            assert res1.ok is False
            assert "missing-input-response" in res1.error_codes

            res2 = verify_captcha("   ")
            assert res2.ok is False
            assert "missing-input-response" in res2.error_codes

            res3 = verify_captcha(None)
            assert res3.ok is False
            assert "missing-input-response" in res3.error_codes

            mock_post.assert_not_called()

    def test_mock_mode_tokens(self, app):
        # App defaults to CAPTCHA_MODE=mock in test fixture
        res_pass = verify_captcha("mock-pass")
        assert res_pass.ok is True
        assert res_pass.hostname == "localhost"

        res_fail = verify_captcha("mock-fail")
        assert res_fail.ok is False
        assert "invalid-input-response" in res_fail.error_codes

        res_expired = verify_captcha("mock-expired")
        assert res_expired.ok is False
        assert "timeout-or-duplicate" in res_expired.error_codes

        res_unavail = verify_captcha("mock-unavailable")
        assert res_unavail.ok is False
        assert res_unavail.unavailable is True

        res_host = verify_captcha("hostname-fail")
        assert res_host.ok is False
        assert "hostname-mismatch" in res_host.error_codes

        res_act = verify_captcha("action-fail")
        assert res_act.ok is False
        assert "action-mismatch" in res_act.error_codes

    def test_tc_cap_01_and_09_turnstile_success_and_request_format(self, app):
        app.config["CAPTCHA_MODE"] = "turnstile"
        app.config["TURNSTILE_SECRET_KEY"] = "1x0000000000000000000000000000000AA"
        app.config["TURNSTILE_ALLOWED_HOSTNAMES"] = ("localhost", "example.com")
        app.config["TURNSTILE_EXPECTED_ACTION"] = "login"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "hostname": "localhost",
            "action": "login",
            "error-codes": [],
        }

        with patch("requests.post", return_value=mock_resp) as mock_post:
            res = verify_captcha("token123", remote_ip="192.168.1.100")
            assert res.ok is True
            assert res.hostname == "localhost"
            assert res.action == "login"
            assert res.error_codes == []

            # Verify request arguments
            mock_post.assert_called_once()
            call_args, call_kwargs = mock_post.call_args
            assert call_args[0] == "https://challenges.cloudflare.com/turnstile/v0/siteverify"
            payload = call_kwargs["data"]
            assert payload["secret"] == "1x0000000000000000000000000000000AA"
            assert payload["response"] == "token123"
            assert payload["remoteip"] == "192.168.1.100"
            assert "idempotency_key" in payload
            assert call_kwargs["timeout"] == 5

    def test_tc_cap_03_invalid_token(self, app):
        app.config["CAPTCHA_MODE"] = "turnstile"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": False,
            "error-codes": ["invalid-input-response"],
        }

        with patch("requests.post", return_value=mock_resp):
            res = verify_captcha("bad_token")
            assert res.ok is False
            assert "invalid-input-response" in res.error_codes
            assert res.primary_error == "invalid-input-response"

    def test_tc_cap_04_expired_or_duplicate_token(self, app):
        app.config["CAPTCHA_MODE"] = "turnstile"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": False,
            "error-codes": ["timeout-or-duplicate"],
        }

        with patch("requests.post", return_value=mock_resp):
            res = verify_captcha("used_token")
            assert res.ok is False
            assert "timeout-or-duplicate" in res.error_codes

    def test_tc_cap_05_hostname_mismatch(self, app):
        app.config["CAPTCHA_MODE"] = "turnstile"
        app.config["TURNSTILE_ALLOWED_HOSTNAMES"] = ("myschool.edu",)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "hostname": "evil.example.com",
            "action": "login",
        }

        with patch("requests.post", return_value=mock_resp):
            res = verify_captcha("token123")
            assert res.ok is False
            assert "hostname-mismatch" in res.error_codes

    def test_tc_cap_06_action_mismatch(self, app):
        app.config["CAPTCHA_MODE"] = "turnstile"
        app.config["TURNSTILE_EXPECTED_ACTION"] = "login"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "hostname": "localhost",
            "action": "password-reset",
        }

        with patch("requests.post", return_value=mock_resp):
            res = verify_captcha("token123")
            assert res.ok is False
            assert "action-mismatch" in res.error_codes

    def test_tc_cap_07_network_failure_or_timeout(self, app):
        app.config["CAPTCHA_MODE"] = "turnstile"

        with patch("requests.post", side_effect=requests.Timeout("Connection timed out")):
            res = verify_captcha("token123")
            assert res.ok is False
            assert res.unavailable is True

        with patch("requests.post", side_effect=requests.ConnectionError("DNS failure")):
            res = verify_captcha("token123")
            assert res.ok is False
            assert res.unavailable is True

    def test_tc_cap_08_malformed_responses(self, app):
        app.config["CAPTCHA_MODE"] = "turnstile"

        # HTTP 500 error
        mock_500 = MagicMock()
        mock_500.status_code = 500
        with patch("requests.post", return_value=mock_500):
            assert verify_captcha("token123").unavailable is True

        # Non-JSON HTML response
        mock_html = MagicMock()
        mock_html.status_code = 200
        mock_html.json.side_effect = ValueError("Invalid JSON")
        mock_html.text = "<html>502 Bad Gateway</html>"
        with patch("requests.post", return_value=mock_html):
            assert verify_captcha("token123").unavailable is True

        # JSON missing 'success'
        mock_empty = MagicMock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = {"something": "else"}
        with patch("requests.post", return_value=mock_empty):
            assert verify_captcha("token123").unavailable is True
