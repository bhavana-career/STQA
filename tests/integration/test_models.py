"""PostgreSQL integration tests for SQLAlchemy models, constraints, and transactions.

Verified against real PostgreSQL container (srms-postgres / srms_test).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Exam,
    ExamSubject,
    Mark,
    MarkAudit,
    Section,
    Student,
    Subject,
    Teacher,
    TeacherAssignment,
    User,
)


@pytest.mark.integration
class TestUserModelAndSecurity:
    """Tests for User model, scrypt password hashing, and role security."""

    def test_user_creation_and_password_hashing(self, pg_app):
        user = User(login_id="STU2026001", role="student")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.login_id == "STU2026001"
        assert user.role == "student"
        assert user.is_active is True
        assert user.session_version == 1
        assert user.failed_login_count == 0

        # Password must be hashed with scrypt, never plaintext
        assert user.password_hash.startswith("scrypt:")
        assert "SecurePass123!" not in user.password_hash
        assert user.check_password("SecurePass123!") is True
        assert user.check_password("WrongPassword!") is False

    def test_user_serialization_omits_password_hash(self, pg_app):
        user = User(login_id="TCH001", role="teacher")
        user.set_password("TeacherSecret!")
        db.session.add(user)
        db.session.commit()

        data = user.to_dict()
        assert "password_hash" not in data
        assert "password" not in data
        assert data["login_id"] == "TCH001"
        assert data["role"] == "teacher"

    def test_short_password_rejected(self, pg_app):
        user = User(login_id="STU001", role="student")
        with pytest.raises(ValueError, match="at least 6 characters"):
            user.set_password("123")

    def test_duplicate_login_id_rejected_by_db(self, pg_app):
        u1 = User(login_id="DUPLICATE", role="student")
        u1.set_password("Pass123!")
        db.session.add(u1)
        db.session.commit()

        u2 = User(login_id="DUPLICATE", role="teacher")
        u2.set_password("Pass123!")
        db.session.add(u2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_invalid_role_rejected_by_db_constraint(self, pg_app):
        # Database CHECK constraint: role IN ('student', 'teacher')
        u = User(login_id="ADMIN01", role="admin")
        u.set_password("Pass123!")
        db.session.add(u)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


@pytest.mark.integration
class TestModelRelationshipsAndCascades:
    """Tests for entity associations and foreign key cascades."""

    def test_student_and_section_association(self, pg_app):
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        u = User(login_id="STU001", role="student")
        u.set_password("Pass123!")
        db.session.add(u)
        db.session.flush()

        stu = Student(
            user_id=u.id,
            student_code="STU001",
            full_name="Alice Smith",
            section_id=sec.id,
            roll_number=1,
        )
        db.session.add(stu)
        db.session.commit()

        assert stu.user.login_id == "STU001"
        assert stu.section.name == "A"
        assert u.student.full_name == "Alice Smith"

    def test_teacher_association(self, pg_app):
        u = User(login_id="TCH001", role="teacher")
        u.set_password("Pass123!")
        db.session.add(u)
        db.session.flush()

        t = Teacher(user_id=u.id, teacher_code="TCH001", full_name="Robert Brown")
        db.session.add(t)
        db.session.commit()

        assert t.user.login_id == "TCH001"
        assert u.teacher.full_name == "Robert Brown"

    def test_exam_and_exam_subjects_cascade(self, pg_app):
        exam = Exam(name="Midterm 2025-26", academic_year="2025-26", held_on=date(2025, 10, 15))
        sub1 = Subject(code="ENG", name="English")
        sub2 = Subject(code="MAT", name="Mathematics")
        db.session.add_all([exam, sub1, sub2])
        db.session.flush()

        es1 = ExamSubject(exam_id=exam.id, subject_id=sub1.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
        es2 = ExamSubject(exam_id=exam.id, subject_id=sub2.id, max_marks=Decimal("80"), pass_marks=Decimal("28"))
        db.session.add_all([es1, es2])
        db.session.commit()

        assert len(exam.exam_subjects) == 2

        # Deleting exam cascades to its exam_subjects
        exam_id = exam.id
        db.session.delete(exam)
        db.session.commit()

        remaining_es = db.session.scalars(select(ExamSubject).where(ExamSubject.exam_id == exam_id)).all()
        assert len(remaining_es) == 0


@pytest.mark.integration
class TestDatabaseIntegrityConstraints:
    """Tests verifying PostgreSQL-level database integrity constraints."""

    def test_duplicate_roll_number_in_same_section_rejected(self, pg_app):
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        db.session.add(sec)
        db.session.flush()

        u1 = User(login_id="STU001", role="student")
        u1.set_password("Pass123!")
        u2 = User(login_id="STU002", role="student")
        u2.set_password("Pass123!")
        db.session.add_all([u1, u2])
        db.session.flush()

        s1 = Student(user_id=u1.id, student_code="STU001", full_name="Student One", section_id=sec.id, roll_number=10)
        s2 = Student(user_id=u2.id, student_code="STU002", full_name="Student Two", section_id=sec.id, roll_number=10)
        db.session.add(s1)
        db.session.commit()

        db.session.add(s2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_negative_roll_number_rejected_by_db_constraint(self, pg_app):
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        u = User(login_id="STU001", role="student")
        u.set_password("Pass123!")
        db.session.add_all([sec, u])
        db.session.flush()

        # Database CHECK: roll_number > 0
        s = Student(user_id=u.id, student_code="STU001", full_name="Student One", section_id=sec.id, roll_number=-5)
        db.session.add(s)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_duplicate_teacher_assignment_rejected(self, pg_app):
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        u_t1 = User(login_id="TCH001", role="teacher")
        u_t1.set_password("Pass123!")
        u_t2 = User(login_id="TCH002", role="teacher")
        u_t2.set_password("Pass123!")
        u_s = User(login_id="STU001", role="student")
        u_s.set_password("Pass123!")
        sub = Subject(code="MAT", name="Mathematics")
        db.session.add_all([sec, u_t1, u_t2, u_s, sub])
        db.session.flush()

        t1 = Teacher(user_id=u_t1.id, teacher_code="TCH001", full_name="Teacher 1")
        t2 = Teacher(user_id=u_t2.id, teacher_code="TCH002", full_name="Teacher 2")
        stu = Student(user_id=u_s.id, student_code="STU001", full_name="Student 1", section_id=sec.id, roll_number=1)
        db.session.add_all([t1, t2, stu])
        db.session.flush()

        # Assign T1 to Student for MAT
        a1 = TeacherAssignment(teacher_id=t1.id, student_id=stu.id, subject_id=sub.id)
        db.session.add(a1)
        db.session.commit()

        # Attempt to assign T2 to same Student for MAT -> must fail unique(student_id, subject_id)
        a2 = TeacherAssignment(teacher_id=t2.id, student_id=stu.id, subject_id=sub.id)
        db.session.add(a2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_negative_marks_rejected_by_db_constraint(self, pg_app):
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        u_s = User(login_id="STU001", role="student")
        u_s.set_password("Pass123!")
        u_t = User(login_id="TCH001", role="teacher")
        u_t.set_password("Pass123!")
        sub = Subject(code="MAT", name="Mathematics")
        exam = Exam(name="Annual 2025-26", academic_year="2025-26")
        db.session.add_all([sec, u_s, u_t, sub, exam])
        db.session.flush()

        stu = Student(user_id=u_s.id, student_code="STU001", full_name="Student", section_id=sec.id, roll_number=1)
        es = ExamSubject(exam_id=exam.id, subject_id=sub.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
        db.session.add_all([stu, es])
        db.session.flush()

        # Database CHECK: marks_obtained IS NULL OR marks_obtained >= 0
        mark = Mark(student_id=stu.id, exam_subject_id=es.id, marks_obtained=Decimal("-10.00"), updated_by=u_t.id)
        db.session.add(mark)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_pass_marks_exceeding_max_marks_rejected(self, pg_app):
        exam = Exam(name="Test Exam", academic_year="2025-26")
        sub = Subject(code="ENG", name="English")
        db.session.add_all([exam, sub])
        db.session.flush()

        # Database CHECK: pass_marks >= 0 AND pass_marks <= max_marks
        es = ExamSubject(exam_id=exam.id, subject_id=sub.id, max_marks=Decimal("50"), pass_marks=Decimal("60"))
        db.session.add(es)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_duplicate_student_code_rejected(self, pg_app):
        # TC-DB-01: unique student_code enforced
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        u1 = User(login_id="STU001", role="student")
        u1.set_password("Pass123!")
        u2 = User(login_id="STU002", role="student")
        u2.set_password("Pass123!")
        db.session.add_all([sec, u1, u2])
        db.session.flush()

        s1 = Student(user_id=u1.id, student_code="STU001", full_name="Student 1", section_id=sec.id, roll_number=1)
        db.session.add(s1)
        db.session.commit()

        s2 = Student(user_id=u2.id, student_code="STU001", full_name="Student 2", section_id=sec.id, roll_number=2)
        db.session.add(s2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_invalid_foreign_key_rejected(self, pg_app):
        # TC-DB-03: Invalid FK reference raises IntegrityError
        mark = Mark(student_id=999999, exam_subject_id=999999, marks_obtained=Decimal("50.00"), updated_by=999999)
        db.session.add(mark)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_duplicate_mark_same_student_exam_subject_rejected(self, pg_app):
        # TC-DB-09: Unique (student_id, exam_subject_id)
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        u_s = User(login_id="STU001", role="student")
        u_s.set_password("Pass123!")
        u_t = User(login_id="TCH001", role="teacher")
        u_t.set_password("Pass123!")
        sub = Subject(code="MAT", name="Mathematics")
        exam = Exam(name="Annual 2025-26", academic_year="2025-26")
        db.session.add_all([sec, u_s, u_t, sub, exam])
        db.session.flush()

        stu = Student(user_id=u_s.id, student_code="STU001", full_name="Student", section_id=sec.id, roll_number=1)
        es = ExamSubject(exam_id=exam.id, subject_id=sub.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
        db.session.add_all([stu, es])
        db.session.flush()

        m1 = Mark(student_id=stu.id, exam_subject_id=es.id, marks_obtained=Decimal("80.00"), updated_by=u_t.id)
        db.session.add(m1)
        db.session.commit()

        m2 = Mark(student_id=stu.id, exam_subject_id=es.id, marks_obtained=Decimal("90.00"), updated_by=u_t.id)
        db.session.add(m2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


@pytest.mark.integration
class TestDatabaseTransactions:
    """Tests verifying ACID transactions and atomic rollbacks."""

    def test_marks_save_and_audit_creation(self, pg_app):
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        u_s = User(login_id="STU001", role="student")
        u_s.set_password("Pass123!")
        u_t = User(login_id="TCH001", role="teacher")
        u_t.set_password("Pass123!")
        sub = Subject(code="MAT", name="Mathematics")
        exam = Exam(name="Annual 2025-26", academic_year="2025-26")
        db.session.add_all([sec, u_s, u_t, sub, exam])
        db.session.flush()

        stu = Student(user_id=u_s.id, student_code="STU001", full_name="Student", section_id=sec.id, roll_number=1)
        es = ExamSubject(exam_id=exam.id, subject_id=sub.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
        db.session.add_all([stu, es])
        db.session.flush()

        # Step 1: Create Mark with audit in single transaction
        mark = Mark(student_id=stu.id, exam_subject_id=es.id, marks_obtained=Decimal("78.50"), updated_by=u_t.id)
        db.session.add(mark)
        db.session.flush()

        audit = MarkAudit(mark_id=mark.id, action="create", old_value=None, new_value=Decimal("78.50"), changed_by=u_t.id)
        db.session.add(audit)
        db.session.commit()

        assert mark.id is not None
        assert len(mark.audit_logs) == 1
        assert mark.audit_logs[0].action == "create"
        assert mark.audit_logs[0].new_value == Decimal("78.50")

    def test_failed_transaction_rolls_back_completely(self, pg_app):
        # TC-DB-06: No partial data when a multi-step operation fails
        sec = Section(class_name="10th Standard", name="A", academic_year="2025-26")
        u_s = User(login_id="STU001", role="student")
        u_s.set_password("Pass123!")
        u_t = User(login_id="TCH001", role="teacher")
        u_t.set_password("Pass123!")
        sub1 = Subject(code="ENG", name="English")
        sub2 = Subject(code="MAT", name="Mathematics")
        exam = Exam(name="Annual 2025-26", academic_year="2025-26")
        db.session.add_all([sec, u_s, u_t, sub1, sub2, exam])
        db.session.flush()

        stu = Student(user_id=u_s.id, student_code="STU001", full_name="Student", section_id=sec.id, roll_number=1)
        es1 = ExamSubject(exam_id=exam.id, subject_id=sub1.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
        es2 = ExamSubject(exam_id=exam.id, subject_id=sub2.id, max_marks=Decimal("100"), pass_marks=Decimal("35"))
        db.session.add_all([stu, es1, es2])
        db.session.commit()

        # Begin transaction: save mark 1 (valid), save mark 2 (invalid - negative)
        try:
            m1 = Mark(student_id=stu.id, exam_subject_id=es1.id, marks_obtained=Decimal("80.00"), updated_by=u_t.id)
            db.session.add(m1)
            db.session.flush()

            # Second item intentionally violates constraint
            m2 = Mark(student_id=stu.id, exam_subject_id=es2.id, marks_obtained=Decimal("-5.00"), updated_by=u_t.id)
            db.session.add(m2)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

        # Verify rollback: NEITHER mark must exist
        saved_marks = db.session.scalars(select(Mark).where(Mark.student_id == stu.id)).all()
        assert len(saved_marks) == 0


@pytest.mark.integration
class TestDatabaseMigrations:
    """TC-DB-10: Verifying migrations up and down cycle."""

    def test_migration_downgrade_and_upgrade_cycle(self, pg_app):
        from flask_migrate import downgrade, upgrade
        # Downgrade to base
        downgrade(revision="base")
        # Upgrade back to head
        upgrade(revision="head")
        # Verify tables exist and schema is operational
        count = db.session.scalar(select(db.func.count(User.id)))
        assert count == 0

