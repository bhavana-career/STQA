"""SQLAlchemy 2.x ORM models for SRMS.

Relational schema implementing 3NF normalization, foreign key cascades,
and database-level integrity constraints as defined in docs/database-schema.md.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from flask_login import UserMixin
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """User account model supporting role-based access for students and teachers."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("login_id = upper(login_id)", name="ck_users_login_id_upper"),
        CheckConstraint("role IN ('student', 'teacher')", name="ck_users_role"),
        CheckConstraint("failed_login_count >= 0", name="ck_users_failed_login_count_positive"),
    )

    # 1:1 polymorphic associations
    student: Mapped[Student | None] = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher: Mapped[Teacher | None] = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __init__(self, login_id: str, role: str, is_active: bool = True, **kwargs: Any) -> None:
        kwargs.setdefault("failed_login_count", 0)
        kwargs.setdefault("session_version", 1)
        super().__init__(login_id=login_id.strip().upper(), role=role.lower(), is_active=is_active, **kwargs)

    def set_password(self, password: str) -> None:
        """Hash password using Werkzeug's secure scrypt algorithm."""
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        """Verify candidate password against stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return str(self.id)

    def is_locked(self, now: datetime | None = None) -> bool:
        """Check whether the account is currently locked."""
        if not self.locked_until:
            return False
        current_time = now or utc_now()
        return self.locked_until > current_time

    def record_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 15) -> bool:
        """Increment failed attempts and lock account if max_attempts reached."""
        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = utc_now() + timedelta(minutes=lockout_minutes)
            return True
        return False

    def record_successful_login(self) -> None:
        """Reset failed login count and lockout status upon successful authentication."""
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = utc_now()

    def increment_session_version(self) -> int:
        """Increment session version to invalidate existing sessions across all devices."""
        self.session_version = (self.session_version or 1) + 1
        return self.session_version

    def to_dict(self) -> dict[str, Any]:
        """Safe serialization that strictly omits password_hash."""
        return {
            "id": self.id,
            "login_id": self.login_id,
            "role": self.role,
            "is_active": self.is_active,
            "failed_login_count": self.failed_login_count,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} login_id={self.login_id!r} role={self.role!r}>"


class Section(db.Model):
    """Academic class section (e.g., 10th Standard A, 2025-26)."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_name: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(8), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)

    __table_args__ = (
        UniqueConstraint("class_name", "name", "academic_year", name="uq_sections_class_name_academic_year"),
    )

    students: Mapped[list[Student]] = relationship("Student", back_populates="section")

    def __repr__(self) -> str:
        return f"<Section id={self.id} {self.class_name}-{self.name} ({self.academic_year})>"


class Student(db.Model):
    """Student profile linked 1:1 to User."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    student_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    section_id: Mapped[int] = mapped_column(Integer, ForeignKey("sections.id", ondelete="RESTRICT"), nullable=False)
    roll_number: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("roll_number > 0", name="ck_students_roll_number_positive"),
        UniqueConstraint("section_id", "roll_number", name="uq_students_section_roll_number"),
    )

    user: Mapped[User] = relationship("User", back_populates="student")
    section: Mapped[Section] = relationship("Section", back_populates="students")
    marks: Mapped[list[Mark]] = relationship("Mark", back_populates="student", cascade="all, delete-orphan")
    assignments: Mapped[list[TeacherAssignment]] = relationship(
        "TeacherAssignment", back_populates="student", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs: Any) -> None:
        if "student_code" in kwargs:
            kwargs["student_code"] = str(kwargs["student_code"]).strip().upper()
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Student id={self.id} code={self.student_code!r} roll={self.roll_number}>"


class Teacher(db.Model):
    """Teacher profile linked 1:1 to User."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    teacher_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="teacher")
    assignments: Mapped[list[TeacherAssignment]] = relationship(
        "TeacherAssignment", back_populates="teacher", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs: Any) -> None:
        if "teacher_code" in kwargs:
            kwargs["teacher_code"] = str(kwargs["teacher_code"]).strip().upper()
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Teacher id={self.id} code={self.teacher_code!r}>"


class Subject(db.Model):
    """Academic subject specification (e.g. ENG, MAT)."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    exam_subjects: Mapped[list[ExamSubject]] = relationship("ExamSubject", back_populates="subject")
    assignments: Mapped[list[TeacherAssignment]] = relationship("TeacherAssignment", back_populates="subject")

    def __init__(self, code: str, name: str, **kwargs: Any) -> None:
        super().__init__(code=code.strip().upper(), name=name.strip(), **kwargs)

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.code!r} name={self.name!r}>"


class Exam(db.Model):
    """Examination term (e.g. Annual Examination 2025-26)."""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)
    held_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("name", "academic_year", name="uq_exams_name_academic_year"),
    )

    exam_subjects: Mapped[list[ExamSubject]] = relationship("ExamSubject", back_populates="exam", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Exam id={self.id} name={self.name!r} ({self.academic_year})>"


class ExamSubject(db.Model):
    """Subjects included in an examination along with maximum and pass marks."""

    __tablename__ = "exam_subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    max_marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    pass_marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("max_marks > 0", name="ck_exam_subjects_max_marks_positive"),
        CheckConstraint("pass_marks >= 0 AND pass_marks <= max_marks", name="ck_exam_subjects_pass_marks_valid"),
        UniqueConstraint("exam_id", "subject_id", name="uq_exam_subjects_exam_subject"),
    )

    exam: Mapped[Exam] = relationship("Exam", back_populates="exam_subjects")
    subject: Mapped[Subject] = relationship("Subject", back_populates="exam_subjects")
    marks: Mapped[list[Mark]] = relationship("Mark", back_populates="exam_subject")

    def __repr__(self) -> str:
        return f"<ExamSubject id={self.id} exam_id={self.exam_id} subject_id={self.subject_id} max={self.max_marks}>"


class TeacherAssignment(db.Model):
    """Granular assignment of a teacher to a student and subject."""

    __tablename__ = "teacher_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", name="uq_teacher_assignments_student_subject"),
        Index("ix_teacher_assignments_lookup", "teacher_id", "student_id", "subject_id"),
    )

    teacher: Mapped[Teacher] = relationship("Teacher", back_populates="assignments")
    student: Mapped[Student] = relationship("Student", back_populates="assignments")
    subject: Mapped[Subject] = relationship("Subject", back_populates="assignments")

    def __repr__(self) -> str:
        return f"<TeacherAssignment teacher_id={self.teacher_id} student_id={self.student_id} subject_id={self.subject_id}>"


class Mark(db.Model):
    """Student subject mark for a specific exam subject."""

    __tablename__ = "marks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    exam_subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("exam_subjects.id", ondelete="RESTRICT"), nullable=False)
    marks_obtained: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    updated_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("marks_obtained IS NULL OR marks_obtained >= 0", name="ck_marks_obtained_non_negative"),
        UniqueConstraint("student_id", "exam_subject_id", name="uq_marks_student_exam_subject"),
    )

    student: Mapped[Student] = relationship("Student", back_populates="marks")
    exam_subject: Mapped[ExamSubject] = relationship("ExamSubject", back_populates="marks")
    updater: Mapped[User] = relationship("User", foreign_keys=[updated_by])
    audit_logs: Mapped[list[MarkAudit]] = relationship("MarkAudit", back_populates="mark", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Mark id={self.id} student_id={self.student_id} exam_subject_id={self.exam_subject_id} marks={self.marks_obtained}>"


class MarkAudit(db.Model):
    """Audit trail for all marks additions, edits, and deletions."""

    __tablename__ = "mark_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mark_id: Mapped[int] = mapped_column(Integer, ForeignKey("marks.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    old_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    new_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("action IN ('create', 'update', 'clear')", name="ck_mark_audit_action"),
    )

    mark: Mapped[Mark] = relationship("Mark", back_populates="audit_logs")
    actor: Mapped[User] = relationship("User", foreign_keys=[changed_by])

    def __repr__(self) -> str:
        return f"<MarkAudit id={self.id} mark_id={self.mark_id} action={self.action!r} {self.old_value}->{self.new_value}>"
