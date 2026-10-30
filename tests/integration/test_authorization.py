"""Integration tests for Role-Based Authorization and Access Control (TC-AUTHZ).

Tests execute against PostgreSQL test database.
"""
from __future__ import annotations

import pytest
from app.extensions import db
from app.models import Section, Student, Teacher, User


@pytest.fixture
def auth_users(pg_app):
    """Seed student and teacher accounts."""
    with pg_app.app_context():
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        s_user = User(login_id="STU2026001", role="student")
        s_user.set_password("StudentPass123!")
        db.session.add(s_user)
        db.session.flush()

        student = Student(
            user_id=s_user.id,
            student_code="STU2026001",
            full_name="Test Student One",
            section_id=sec.id,
            roll_number=1,
        )
        db.session.add(student)

        t_user = User(login_id="TCH001", role="teacher")
        t_user.set_password("TeacherPass123!")
        db.session.add(t_user)
        db.session.flush()

        teacher = Teacher(
            user_id=t_user.id,
            teacher_code="TCH001",
            full_name="Test Teacher Smith",
        )
        db.session.add(teacher)
        db.session.commit()
        return {"student_id": s_user.id, "teacher_id": t_user.id}


@pytest.mark.integration
class TestRoleBasedAuthorization:
    """TC-AUTHZ: Role-based authorization test suite."""

    def test_tc_authz_01_student_blocked_from_teacher_routes(self, pg_client, auth_users):
        # 1. Log in as Student
        pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )

        # 2. Student attempts to load Teacher HTML dashboard -> 403 Forbidden
        page_resp = pg_client.get("/teacher/dashboard")
        assert page_resp.status_code == 403

        # 3. Student attempts to access Teacher API -> 403 JSON envelope
        api_resp = pg_client.get("/api/teacher/students")
        assert api_resp.status_code == 403
        data = api_resp.get_json()
        assert data["error"]["code"] == "forbidden"
        assert "Access denied" in data["error"]["message"]

    def test_tc_authz_02_and_04_student_cannot_access_or_edit_marks_api(self, pg_client, auth_users):
        # Log in as Student
        pg_client.post(
            "/student/login",
            data={
                "login_id": "STU2026001",
                "password": "StudentPass123!",
                "cf-turnstile-response": "mock-pass",
            },
        )

        # TC-AUTHZ-04: Student GET teacher marks API -> 403
        get_resp = pg_client.get("/api/teacher/students/1/marks")
        assert get_resp.status_code == 403
        assert get_resp.get_json()["error"]["code"] == "forbidden"

        # TC-AUTHZ-02: Student PUT teacher marks API -> 403
        put_resp = pg_client.put(
            "/api/teacher/students/1/marks",
            json={"marks": [{"subject_id": 1, "marks_obtained": "95.00"}]},
        )
        assert put_resp.status_code == 403
        assert put_resp.get_json()["error"]["code"] == "forbidden"

    @pytest.mark.parametrize(
        "endpoint,method,payload",
        [
            ("/api/teacher/students", "GET", None),
            ("/api/teacher/students/1/marks", "GET", None),
            ("/api/teacher/students/1/marks", "PUT", {"marks": []}),
        ],
    )
    def test_tc_authz_10_unauthenticated_protected_apis_return_401(self, pg_client, endpoint, method, payload):
        # Anonymous client request to protected API
        if method == "GET":
            resp = pg_client.get(endpoint)
        elif method == "PUT":
            resp = pg_client.put(endpoint, json=payload)
        else:
            resp = pg_client.post(endpoint, json=payload)

        assert resp.status_code == 401
        data = resp.get_json()
        assert data is not None
        assert data["error"]["code"] == "unauthenticated"
        assert "Authentication required" in data["error"]["message"]

    def test_tc_authz_11_no_registration_route_exists(self, pg_client):
        # System does not support public registration; operator CLI provisioning only
        assert pg_client.get("/register").status_code == 404
        assert pg_client.post("/register").status_code == 404
        assert pg_client.get("/signup").status_code == 404
        assert pg_client.post("/signup").status_code == 404
