"""Cloudflare Turnstile CAPTCHA verification service.

Supports production Turnstile verification, test credentials, and offline mock verification for unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import uuid
from typing import Any

from flask import current_app
import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaptchaResult:
    """Result of CAPTCHA verification."""

    ok: bool
    error_codes: list[str] = field(default_factory=list)
    unavailable: bool = False
    hostname: str | None = None
    action: str | None = None

    @property
    def primary_error(self) -> str:
        """First error code if present, else empty string."""
        return self.error_codes[0] if self.error_codes else ""


def verify_captcha(token: str | None, remote_ip: str | None = None) -> CaptchaResult:
    """Verify a Turnstile response token.

    :param token: The `cf-turnstile-response` token from the client form.
    :param remote_ip: Client IP address (optional).
    :return: CaptchaResult indicating success, failures, or service unavailability.
    """
    if not token or not token.strip():
        # TC-CAP-02: Blank or missing token short-circuits without network call
        return CaptchaResult(ok=False, error_codes=["missing-input-response"])

    clean_token = token.strip()
    mode = current_app.config.get("CAPTCHA_MODE", "turnstile").lower()

    if mode == "mock":
        return _verify_mock(clean_token)

    return _verify_turnstile(clean_token, remote_ip)


def _verify_mock(token: str) -> CaptchaResult:
    """Offline mock verification for unit and offline integration testing."""
    if token in ("mock-fail", "invalid-token"):
        return CaptchaResult(ok=False, error_codes=["invalid-input-response"])
    if token in ("mock-expired", "timeout-or-duplicate"):
        return CaptchaResult(ok=False, error_codes=["timeout-or-duplicate"])
    if token in ("mock-unavailable", "service-error"):
        return CaptchaResult(ok=False, unavailable=True)
    if token == "hostname-fail":
        return CaptchaResult(ok=False, error_codes=["hostname-mismatch"])
    if token == "action-fail":
        return CaptchaResult(ok=False, error_codes=["action-mismatch"])

    # Default mock pass for 'mock-pass', dummy tokens, or arbitrary testing tokens
    return CaptchaResult(ok=True, hostname="localhost", action="login")


def _verify_turnstile(token: str, remote_ip: str | None = None) -> CaptchaResult:
    """Live verification against Cloudflare Turnstile endpoint."""
    secret = current_app.config.get("TURNSTILE_SECRET_KEY")
    verify_url = current_app.config.get(
        "TURNSTILE_VERIFY_URL", "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    )
    timeout = current_app.config.get("TURNSTILE_TIMEOUT_SECONDS", 5)
    allowed_hostnames = current_app.config.get("TURNSTILE_ALLOWED_HOSTNAMES", ())
    expected_action = current_app.config.get("TURNSTILE_EXPECTED_ACTION", "login")

    payload: dict[str, Any] = {
        "secret": secret,
        "response": token,
        "idempotency_key": str(uuid.uuid4()),
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(verify_url, data=payload, timeout=timeout)
    except requests.RequestException as exc:
        # TC-CAP-07: Network errors and timeouts fail closed
        logger.warning("Turnstile verification network failure: %s", exc)
        return CaptchaResult(ok=False, unavailable=True)

    # TC-CAP-08: Non-200 responses or invalid JSON
    if response.status_code != 200:
        logger.warning("Turnstile returned non-200 HTTP status: %d", response.status_code)
        return CaptchaResult(ok=False, unavailable=True)

    try:
        data = response.json()
    except Exception:
        logger.warning("Turnstile returned invalid non-JSON body: %s", response.text[:200])
        return CaptchaResult(ok=False, unavailable=True)

    if not isinstance(data, dict) or "success" not in data:
        logger.warning("Turnstile response JSON missing 'success' key: %r", data)
        return CaptchaResult(ok=False, unavailable=True)

    if not data.get("success"):
        # TC-CAP-03, TC-CAP-04
        error_codes = data.get("error-codes") or ["invalid-input-response"]
        return CaptchaResult(ok=False, error_codes=list(error_codes))

    resp_hostname = data.get("hostname")
    resp_action = data.get("action")

    # TC-CAP-05: Hostname validation if configured
    if allowed_hostnames and resp_hostname:
        if resp_hostname.lower() not in allowed_hostnames:
            logger.warning("Turnstile hostname mismatch: got %r, allowed %r", resp_hostname, allowed_hostnames)
            return CaptchaResult(ok=False, error_codes=["hostname-mismatch"], hostname=resp_hostname)

    # TC-CAP-06: Action validation if configured
    if expected_action and resp_action:
        if resp_action != expected_action:
            logger.warning("Turnstile action mismatch: got %r, expected %r", resp_action, expected_action)
            return CaptchaResult(ok=False, error_codes=["action-mismatch"], action=resp_action)

    return CaptchaResult(ok=True, hostname=resp_hostname, action=resp_action)
