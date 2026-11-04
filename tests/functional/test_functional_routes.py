"""Functional tests covering all SRMS application features and user roles."""

import pytest
from app.config import SUBJECTS


@pytest.mark.functional
class TestAuthenticationAndAccessControl:
    """Test teacher login, student login, invalid login, logout, and route access restrictions."""

    def test_root_redirects_to_login_when_logged_out(self, client):
        res = client.get("/", follow_redirects=False)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]

    def test_teacher_login_and_logout(self, client):
        res = client.post(
            "/login",
            data={"username": "teacher01", "password": "Teacher@123"},
            follow_redirects=True,
        )
        assert res.status_code == 200
        assert b"Teacher Dashboard Overview" in res.data
        assert b"Prof. Rajesh Sharma" in res.data

        # Root redirect while logged in as teacher
        root_res = client.get("/", follow_redirects=False)
        assert "/teacher/dashboard" in root_res.headers["Location"]

        # Visiting /login while logged in as teacher redirects to dashboard
        login_res = client.get("/login", follow_redirects=False)
        assert "/teacher/dashboard" in login_res.headers["Location"]

        # Logout
        out = client.get("/logout", follow_redirects=True)
        assert out.status_code == 200
        assert b"You have been logged out successfully" in out.data

    def test_student_login_and_popup_session_behavior(self, client):
        # Passing student (student01) sees celebratory popup on first visit
        res = client.post(
            "/login",
            data={"username": "student01", "password": "Student@123"},
            follow_redirects=True,
        )
        assert res.status_code == 200
        assert b"Aarav Kulkarni" in res.data
        assert b'id="resultSuccessPopup"' in res.data

        # Navigating to dashboard again in the same session does NOT repeat the popup
        res_second = client.get("/student/dashboard")
        assert res_second.status_code == 200
        assert b'id="resultSuccessPopup"' not in res_second.data

        # Navigating to My Results and Grading Matrix works
        assert client.get("/student/results").status_code == 200
        assert client.get("/student/grading-matrix").status_code == 200

        # Root and /login redirect to /student/dashboard while logged in as student
        assert "/student/dashboard" in client.get("/").headers["Location"]
        assert "/student/dashboard" in client.get("/login").headers["Location"]

    def test_failing_student_does_not_see_success_popup(self, client):
        # student03 has 28 in Mathematics -> FAIL overall, no celebratory popup
        res = client.post(
            "/login",
            data={"username": "student03", "password": "Student@123"},
            follow_redirects=True,
        )
        assert res.status_code == 200
        assert b"Rohan Deshmukh" in res.data
        assert b'id="resultSuccessPopup"' not in res.data
        assert b"OVERALL RESULT: FAIL" in res.data
        assert b"Mathematics" in res.data

    def test_invalid_login_credentials_rejected(self, client):
        res1 = client.post("/login", data={"username": "teacher01", "password": "BadPassword"})
        assert res1.status_code == 401
        assert b"Invalid username or password" in res1.data

        res2 = client.post("/login", data={"username": "", "password": ""})
        assert res2.status_code == 401
        assert b"Both username and password are required" in res2.data


@pytest.mark.functional
class TestTeacherStudentCRUDAndMarks:
    """Test Student CRUD, search, section filtering, marks modification, and analytics."""

    def _login_teacher(self, client):
        client.post("/login", data={"username": "teacher01", "password": "Teacher@123"})

    def test_create_search_filter_update_delete_student(self, client):
        self._login_teacher(client)

        # Create a new student STU050
        create_data = {
            "student_id": "STU050",
            "name": "Kiran Rao",
            "username": "student50",
            "password": "Student@123",
            "class": "10",
            "section": "B",
            "roll_number": "250",
            **{f"mark_{subj}": "82" for subj in SUBJECTS},
        }
        res_create = client.post("/teacher/students/add", data=create_data, follow_redirects=True)
        assert res_create.status_code == 200
        assert b"Kiran Rao" in res_create.data
        assert b"created successfully" in res_create.data

        # Duplicate student ID should fail gracefully with flash error
        res_dup = client.post("/teacher/students/add", data=create_data, follow_redirects=True)
        assert b"Failed to create student" in res_dup.data

        # Search by name
        res_search = client.get("/teacher/students?q=Kiran")
        assert b"STU050" in res_search.data
        assert b"Aarav Kulkarni" not in res_search.data

        # Filter by section B
        res_sec = client.get("/teacher/students?section=B")
        assert b"STU050" in res_sec.data
        assert b"STU002" in res_sec.data
        assert b"STU001" not in res_sec.data

        # Open edit mode
        res_edit_page = client.get("/teacher/students?edit=STU050")
        assert res_edit_page.status_code == 200
        assert b"Edit Student Record: Kiran Rao" in res_edit_page.data

        # Submit update
        update_data = {
            "name": "Kiran K. Rao",
            "username": "student50",
            "password": "Student@123",
            "class": "10",
            "section": "C",
            "roll_number": "350",
            **{f"mark_{subj}": "90" for subj in SUBJECTS},
        }
        res_upd = client.post(
            "/teacher/students/STU050/edit", data=update_data, follow_redirects=True
        )
        assert b"Kiran K. Rao" in res_upd.data
        assert b"updated successfully" in res_upd.data

        # View individual result as teacher
        res_view = client.get("/teacher/students/STU050/result")
        assert res_view.status_code == 200
        assert b"Kiran K. Rao" in res_view.data
        assert b"540 / 600" in res_view.data

        # Non-existent student result returns 404
        assert client.get("/teacher/students/STU999/result").status_code == 404

        # Delete student
        res_del = client.post("/teacher/students/STU050/delete", follow_redirects=True)
        assert b"deleted permanently" in res_del.data
        assert b"Kiran K. Rao" not in res_del.data

        # Deleting again shows flash error
        res_del_again = client.post("/teacher/students/STU050/delete", follow_redirects=True)
        assert b"Failed to delete student" in res_del_again.data

    def test_marks_management_and_validation(self, client):
        self._login_teacher(client)

        # Valid marks update for STU002
        valid_marks = {
            "student_id": "STU002",
            "mark_Physics": "95",
            "mark_Chemistry": "90",
            "mark_Mathematics": "92",
            "mark_Computer Science": "98",
            "mark_Kannada": "88",
            "mark_English": "91",
        }
        res = client.post("/teacher/marks", data=valid_marks, follow_redirects=True)
        assert res.status_code == 200
        assert b"554 / 600" in res.data
        assert b"92.33%" in res.data
        assert b"Distinction" in res.data

        # Invalid marks (>100) rejected
        invalid_marks = dict(valid_marks, mark_Physics="108")
        res_bad = client.post("/teacher/marks", data=invalid_marks, follow_redirects=True)
        assert b"Marks validation error" in res_bad.data

    def test_class_analytics_section_isolation(self, client):
        self._login_teacher(client)

        # Section A has STU001 (91.00%), STU004 (56.00%), STU005 (42.50%) -> Avg = 63.17%
        res_a = client.get("/teacher/analytics?section=A")
        assert res_a.status_code == 200
        assert b"Section A Performance Metrics" in res_a.data
        assert b"63.17%" in res_a.data

        # Section B has STU002 (68.67%) -> Avg = 68.67%
        res_b = client.get("/teacher/analytics?section=B")
        assert res_b.status_code == 200
        assert b"Section B Performance Metrics" in res_b.data
        assert b"68.67%" in res_b.data

        # Invalid section param defaults safely to Section A
        res_invalid = client.get("/teacher/analytics?section=INVALID")
        assert res_invalid.status_code == 200
        assert b"Section A Performance Metrics" in res_invalid.data
