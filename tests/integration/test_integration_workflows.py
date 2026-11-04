"""Integration tests verifying end-to-end service and application workflows."""

import pytest
from app import create_app
from app.config import SUBJECTS
from app.services.analytics_service import calculate_section_analytics


@pytest.mark.integration
class TestIntegrationWorkflows:
    """
    Verify the 4 core integration workflows specified in Section 17:
    - Workflow 1: Marks to result
    - Workflow 2: Student creation and login
    - Workflow 3: Marks update and student dashboard reflection
    - Workflow 4: Section analytics isolation
    Plus JSON persistence across application restarts.
    """

    def test_workflow_1_and_3_marks_entry_to_student_dashboard(self, client):
        """
        Workflow 1 & 3:
        Teacher enters/updates marks -> marks validated -> total & percentage calculated ->
        individual grades assigned -> overall classification determined -> JSON updated ->
        student logs in and sees updated results on dashboard.
        """
        # 1. Teacher logs in and updates STU003 (who previously failed Mathematics with 28)
        client.post("/login", data={"username": "teacher01", "password": "Teacher@123"})
        new_marks = {
            "student_id": "STU003",
            "mark_Physics": "85",
            "mark_Chemistry": "80",
            "mark_Mathematics": "78",
            "mark_Computer Science": "90",
            "mark_Kannada": "75",
            "mark_English": "72",
        }
        res_update = client.post("/teacher/marks", data=new_marks, follow_redirects=True)
        assert res_update.status_code == 200
        assert b"480 / 600" in res_update.data
        assert b"80.00%" in res_update.data
        assert b"Distinction" in res_update.data
        client.get("/logout")

        # 2. Student STU003 (student03) logs in and sees new passing Distinction result + popup
        res_stu = client.post(
            "/login",
            data={"username": "student03", "password": "Student@123"},
            follow_redirects=True,
        )
        assert res_stu.status_code == 200
        assert b"480 / 600" in res_stu.data
        assert b"80.00%" in res_stu.data
        assert b"Distinction" in res_stu.data
        assert b"OVERALL RESULT: PASS" in res_stu.data
        assert b'id="resultSuccessPopup"' in res_stu.data

    def test_workflow_2_student_creation_and_persistence_across_restart(self, temp_data_files):
        """
        Workflow 2 + Persistence:
        Teacher creates a student -> record validated -> JSON file updated ->
        new Flask app instance started (simulating server restart) ->
        student logs in using assigned credentials and views results.
        """
        app1 = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "secret-1",
                "STUDENTS_FILE": temp_data_files["students_file"],
                "TEACHERS_FILE": temp_data_files["teachers_file"],
            }
        )
        client1 = app1.test_client()
        client1.post("/login", data={"username": "teacher01", "password": "Teacher@123"})

        payload = {
            "student_id": "STU077",
            "name": "Neha Kulkarni",
            "username": "neha77",
            "password": "NehaPassword@1",
            "class": "10",
            "section": "C",
            "roll_number": "377",
            "mark_Physics": "70",
            "mark_Chemistry": "72",
            "mark_Mathematics": "68",
            "mark_Computer Science": "75",
            "mark_Kannada": "65",
            "mark_English": "70",
        }
        res_create = client1.post("/teacher/students/add", data=payload, follow_redirects=True)
        assert res_create.status_code == 200
        assert b"Neha Kulkarni" in res_create.data

        # Simulate application restart by creating a brand-new Flask application instance
        # reading from the same JSON file path
        app2 = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "secret-2",
                "STUDENTS_FILE": temp_data_files["students_file"],
                "TEACHERS_FILE": temp_data_files["teachers_file"],
            }
        )
        client2 = app2.test_client()

        # Student logs in on the restarted application instance
        res_login = client2.post(
            "/login",
            data={"username": "neha77", "password": "NehaPassword@1"},
            follow_redirects=True,
        )
        assert res_login.status_code == 200
        assert b"Neha Kulkarni" in res_login.data
        assert b"420 / 600" in res_login.data
        assert b"70.00%" in res_login.data
        assert b"First Class" in res_login.data

    def test_workflow_4_section_analytics_strict_isolation(self, temp_data_files):
        """
        Workflow 4:
        Verify that Section A average percentage equals:
        Sum of percentages of all Section A students / Number of Section A students,
        and never includes Section B or Section C students.
        """
        sf = temp_data_files["students_file"]
        stats_a = calculate_section_analytics(sf, "A")
        stats_b = calculate_section_analytics(sf, "B")
        stats_c = calculate_section_analytics(sf, "C")

        # In fixture SAMPLE_STUDENTS:
        # Section A has 3 students:
        # STU001: 546/600 = 91.00%
        # STU004: 336/600 = 56.00%
        # STU005: 255/600 = 42.50%
        # Sum of percentages = 189.50% -> / 3 = 63.17%
        assert stats_a["student_count"] == 3
        assert stats_a["average_percentage"] == 63.17
        assert stats_a["passing_students"] == 3
        assert stats_a["failing_students"] == 0
        assert stats_a["distinction_students"] == 1

        # Section B has 1 student: STU002: 412/600 = 68.67%
        assert stats_b["student_count"] == 1
        assert stats_b["average_percentage"] == 68.67

        # Section C has 1 student: STU003: 426/600 = 71.00% (Failed Math with 28)
        assert stats_c["student_count"] == 1
        assert stats_c["average_percentage"] == 71.0
        assert stats_c["passing_students"] == 0
        assert stats_c["failing_students"] == 1
        assert stats_c["distinction_students"] == 0
