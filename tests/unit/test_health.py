"""Unit tests for the Flask application factory, /health endpoint, and security headers."""
from __future__ import annotations

from unittest.mock import patch
import pytest
from flask import Flask
from sqlalchemy.exc import OperationalError

from app import create_app


@pytest.mark.unit
class TestAppFactory:
    """Tests for application factory initialization."""

    def test_create_app_in_testing_mode(self, app: Flask):
        assert app is not None
        assert app.config["TESTING"] is True
        assert "main" in app.blueprints

    def test_security_headers_present_on_response(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "same-origin"


@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for the /health endpoint (TC-OPS-01, TC-OPS-02)."""

    def test_health_endpoint_healthy(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert "version" in data
        assert "password" not in response.text
        assert "secret" not in response.text

    def test_health_endpoint_degraded_when_db_fails(self, app: Flask, client):
        with patch("app.views.main.db.session.execute", side_effect=OperationalError("connection failed", None, None)):
            response = client.get("/health")
            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "degraded"
            assert data["database"] == "error"
            # Ensure no internal error trace or credential leaked
            assert "connection failed" not in response.text


@pytest.mark.unit
class TestErrorHandlers:
    """Tests for HTML and JSON error handlers."""

    def test_api_404_returns_json(self, client):
        response = client.get("/api/unknown-endpoint")
        assert response.status_code == 404
        assert response.is_json
        data = response.get_json()
        assert "error" in data
        assert data["error"]["code"] == "not_found"

    def test_page_404_returns_html(self, client):
        response = client.get("/unknown-page")
        assert response.status_code == 404
        assert "text/html" in response.content_type
        assert b"404" in response.data
