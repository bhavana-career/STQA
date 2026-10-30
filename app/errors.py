"""Error handlers: friendly HTML pages for browser routes, JSON envelope for /api/*."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

from .extensions import db

_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "locked",
    500: "internal_error",
    503: "service_unavailable",
}

_MESSAGES = {
    400: "The request could not be processed.",
    401: "Please sign in to continue.",
    403: "You do not have permission to access this resource.",
    404: "The requested resource was not found.",
    405: "Method not allowed.",
    409: "The request conflicts with existing data.",
    422: "The submitted data is invalid.",
    429: "Too many attempts. Please try again later.",
    500: "An unexpected error occurred.",
    503: "The service is temporarily unavailable.",
}


def wants_json() -> bool:
    return request.path.startswith("/api/")


def error_response(status: int, code: str | None = None, message: str | None = None, details=None):
    if wants_json():
        body = {"error": {"code": code or _CODES.get(status, "error"), "message": message or _MESSAGES.get(status, "Error")}}
        if details:
            body["error"]["details"] = details
        return jsonify(body), status
    return (
        render_template("error.html", status=status, message=message or _MESSAGES.get(status, "Error")),
        status,
    )


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CSRFError)
    def handle_csrf(err):  # type: ignore[no-untyped-def]
        return error_response(400, "csrf_failed", "Your session form token is missing or invalid. Reload the page and try again.")

    @app.errorhandler(HTTPException)
    def handle_http(err: HTTPException):  # type: ignore[no-untyped-def]
        status = err.code or 500
        return error_response(status)

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):  # type: ignore[no-untyped-def]
        db.session.rollback()
        app.logger.exception("Unhandled error on %s %s", request.method, request.path)
        return error_response(500)
