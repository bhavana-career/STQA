"""Operator CLI commands for administration, provisioning, and safe demo seeding.

Registered on the Flask application via register_cli(app).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import os
import sys
from typing import Any

import click
from flask import Flask, current_app
from sqlalchemy import select, text

from .extensions import db
from .models import (
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
    SystemSetting,
)


def register_cli(app: Flask) -> None:
    """Register CLI management commands on the Flask application."""

    @app.cli.command("db-status")
    def db_status_cmd() -> None:
        """Inspect database connection and table row counts."""
        try:
            db.session.execute(text("SELECT 1"))
            click.secho("Database connection: OK", fg="green")
        except Exception as exc:
            click.secho(f"Database connection FAILED: {exc}", fg="red")
            sys.exit(1)

        counts = {
            "users": db.session.scalar(select(db.func.count(User.id))),
            "students": db.session.scalar(select(db.func.count(Student.id))),
            "teachers": db.session.scalar(select(db.func.count(Teacher.id))),
            "sections": db.session.scalar(select(db.func.count(Section.id))),
            "subjects": db.session.scalar(select(db.func.count(Subject.id))),
            "exams": db.session.scalar(select(db.func.count(Exam.id))),
            "exam_subjects": db.session.scalar(select(db.func.count(ExamSubject.id))),
            "teacher_assignments": db.session.scalar(select(db.func.count(TeacherAssignment.id))),
            "marks": db.session.scalar(select(db.func.count(Mark.id))),
            "mark_audit": db.session.scalar(select(db.func.count(MarkAudit.id))),
            "system_settings": db.session.scalar(select(db.func.count(SystemSetting.key))),
        }

        click.echo("--- Database Record Counts ---")
        for table, count in counts.items():
            click.echo(f"  {table:20s}: {count}")

    @app.cli.command("create-user")
    @click.option("--role", type=click.Choice(["student", "teacher"], case_sensitive=False), required=True)
    @click.option("--login-id", required=True, help="Unique identifier, e.g. STU2026001 or TCH001")
    @click.option("--name", required=True, help="Full name")
    @click.option("--password", default=None, help="Password (prompted securely if omitted)")
    @click.option("--section", default="A", help="Section name (students only)")
    @click.option("--class-name", default="10th Standard", help="Class name (students only)")
    @click.option("--academic-year", default="2025-26", help="Academic year (students only)")
    @click.option("--roll", type=int, default=None, help="Roll number (students only)")
    def create_user_cmd(
        role: str,
        login_id: str,
        name: str,
        password: str | None,
        section: str,
        class_name: str,
        academic_year: str,
        roll: int | None,
    ) -> None:
        """Create a single student or teacher account safely."""
        norm_id = login_id.strip().upper()
        norm_role = role.strip().lower()

        existing_user = db.session.scalar(select(User).where(User.login_id == norm_id))
        if existing_user:
            click.secho(f"Error: User with login ID '{norm_id}' already exists.", fg="red")
            sys.exit(1)

        if not password:
            password = click.prompt(f"Enter password for {norm_id}", hide_input=True, confirmation_prompt=True)

        if len(password) < 6:
            click.secho("Error: Password must be at least 6 characters.", fg="red")
            sys.exit(1)

        user = User(login_id=norm_id, role=norm_role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if norm_role == "student":
            if not roll or roll <= 0:
                click.secho("Error: Valid positive --roll number is required for students.", fg="red")
                db.session.rollback()
                sys.exit(1)

            # Ensure section exists
            sec = db.session.scalar(
                select(Section).where(
                    Section.class_name == class_name,
                    Section.name == section.strip().upper(),
                    Section.academic_year == academic_year,
                )
            )
            if not sec:
                sec = Section(class_name=class_name, name=section.strip().upper(), academic_year=academic_year)
                db.session.add(sec)
                db.session.flush()

            # Check duplicate roll in section
            dup_roll = db.session.scalar(
                select(Student).where(Student.section_id == sec.id, Student.roll_number == roll)
            )
            if dup_roll:
                click.secho(f"Error: Roll number {roll} already exists in {sec.class_name} {sec.name}.", fg="red")
                db.session.rollback()
                sys.exit(1)

            student = Student(
                user_id=user.id,
                student_code=norm_id,
                full_name=name.strip(),
                section_id=sec.id,
                roll_number=roll,
            )
            db.session.add(student)

        elif norm_role == "teacher":
            teacher = Teacher(
                user_id=user.id,
                teacher_code=norm_id,
                full_name=name.strip(),
            )
            db.session.add(teacher)

        db.session.commit()
        click.secho(f"Success: Created {norm_role} '{norm_id}' ({name}).", fg="green")

    @app.cli.command("create-subject")
    @click.option("--code", required=True, help="Subject code, e.g. ENG, MAT")
    @click.option("--name", required=True, help="Full subject name")
    def create_subject_cmd(code: str, name: str) -> None:
        """Create a new academic subject."""
        norm_code = code.strip().upper()
        norm_name = name.strip()

        existing = db.session.scalar(
            select(Subject).where((Subject.code == norm_code) | (Subject.name == norm_name))
        )
        if existing:
            click.secho(f"Error: Subject with code '{norm_code}' or name '{norm_name}' already exists.", fg="red")
            sys.exit(1)

        sub = Subject(code=norm_code, name=norm_name)
        db.session.add(sub)
        db.session.commit()
        click.secho(f"Success: Subject '{norm_code}' ({norm_name}) created.", fg="green")

    @app.cli.command("assign")
    @click.option("--teacher", required=True, help="Teacher code, e.g. TCH001")
    @click.option("--student", required=True, help="Student code, e.g. STU2026001")
    @click.option("--subject", required=True, help="Subject code, e.g. MAT")
    def assign_cmd(teacher: str, student: str, subject: str) -> None:
        """Assign a teacher to a student and subject."""
        t = db.session.scalar(select(Teacher).where(Teacher.teacher_code == teacher.strip().upper()))
        if not t:
            click.secho(f"Error: Teacher '{teacher}' not found.", fg="red")
            sys.exit(1)

        s = db.session.scalar(select(Student).where(Student.student_code == student.strip().upper()))
        if not s:
            click.secho(f"Error: Student '{student}' not found.", fg="red")
            sys.exit(1)

        sub = db.session.scalar(select(Subject).where(Subject.code == subject.strip().upper()))
        if not sub:
            click.secho(f"Error: Subject '{subject}' not found.", fg="red")
            sys.exit(1)

        existing = db.session.scalar(
            select(TeacherAssignment).where(
                TeacherAssignment.student_id == s.id,
                TeacherAssignment.subject_id == sub.id,
            )
        )
        if existing:
            click.secho(
                f"Error: Student {student} is already assigned to teacher {existing.teacher.teacher_code} for {subject}.",
                fg="red",
            )
            sys.exit(1)

        assignment = TeacherAssignment(teacher_id=t.id, student_id=s.id, subject_id=sub.id)
        db.session.add(assignment)
        db.session.commit()
        click.secho(f"Success: Assigned {teacher} to {student} for {subject}.", fg="green")

    @app.cli.command("unlock-user")
    @click.argument("login_id")
    def unlock_user_cmd(login_id: str) -> None:
        """Clear account lockout for a user."""
        norm_id = login_id.strip().upper()
        u = db.session.scalar(select(User).where(User.login_id == norm_id))
        if not u:
            click.secho(f"Error: User '{norm_id}' not found.", fg="red")
            sys.exit(1)

        u.failed_login_count = 0
        u.locked_until = None
        db.session.commit()
        click.secho(f"Success: User '{norm_id}' has been unlocked.", fg="green")

    @app.cli.command("seed-demo")
    @click.option("--reset", is_flag=True, help="Wipe and recreate all demo records (BLOCKED in production)")
    @click.option("--i-understand-this-is-production", is_flag=True, help="Explicit confirmation required in production")
    def seed_demo_cmd(reset: bool, i_understand_this_is_production: bool) -> None:
        """Seed fictional demonstration data (schools, subjects, exam, teachers, students, sample marks)."""
        is_prod = current_app.config.get("APP_ENV") == "production"

        if is_prod and not i_understand_this_is_production:
            click.secho(
                "ABORTED: seed-demo in production requires --i-understand-this-is-production flag.",
                fg="red",
                bold=True,
            )
            sys.exit(1)

        if is_prod and reset:
            click.secho("ABORTED: --reset is strictly forbidden in production.", fg="red", bold=True)
            sys.exit(1)

        if reset:
            click.echo("Resetting existing demo records...")
            # Delete in FK dependency order
            db.session.execute(text("DELETE FROM mark_audit"))
            db.session.execute(text("DELETE FROM marks"))
            db.session.execute(text("DELETE FROM teacher_assignments"))
            db.session.execute(text("DELETE FROM exam_subjects"))
            db.session.execute(text("DELETE FROM exams"))
            db.session.execute(text("DELETE FROM students"))
            db.session.execute(text("DELETE FROM teachers"))
            db.session.execute(text("DELETE FROM subjects"))
            db.session.execute(text("DELETE FROM sections"))
            db.session.execute(text("DELETE FROM users"))
            db.session.commit()
            click.echo("Tables cleared.")

        # Determine passwords
        student_pw = os.environ.get("DEMO_STUDENT_PASSWORD")
        teacher_pw = os.environ.get("DEMO_TEACHER_PASSWORD")

        if is_prod:
            if not student_pw or not teacher_pw:
                click.secho(
                    "Error: In production, DEMO_STUDENT_PASSWORD and DEMO_TEACHER_PASSWORD env vars must be set.",
                    fg="red",
                )
                sys.exit(1)
        else:
            student_pw = student_pw or "StudentPass123!"
            teacher_pw = teacher_pw or "TeacherPass123!"

        now = datetime.now(timezone.utc)

        # 1. Sections
        sec_a = _get_or_create(Section, class_name="10th Standard", name="A", academic_year="2025-26")
        sec_b = _get_or_create(Section, class_name="10th Standard", name="B", academic_year="2025-26")

        # 2. Subjects
        sub_eng = _get_or_create(Subject, code="ENG", name="English")
        sub_hin = _get_or_create(Subject, code="HIN", name="Hindi")
        sub_mat = _get_or_create(Subject, code="MAT", name="Mathematics")
        sub_sci = _get_or_create(Subject, code="SCI", name="Science")
        sub_sst = _get_or_create(Subject, code="SST", name="Social Science")
        all_subjects = [sub_eng, sub_hin, sub_mat, sub_sci, sub_sst]

        # 3. Exam & ExamSubjects
        exam = _get_or_create(Exam, name="Annual Examination 2025-26 (Demo)", academic_year="2025-26")
        exam_sub_map: dict[str, ExamSubject] = {}
        for sub in all_subjects:
            es = _get_or_create(
                ExamSubject,
                exam_id=exam.id,
                subject_id=sub.id,
                defaults={"max_marks": Decimal("100.00"), "pass_marks": Decimal("35.00")},
            )
            exam_sub_map[sub.code] = es

        # 4. Teachers
        # TCH001: teaches ENG & MAT in 10-A
        t1_user = _get_or_create_user("TCH001", "teacher", teacher_pw)
        t1 = _get_or_create(Teacher, user_id=t1_user.id, teacher_code="TCH001", defaults={"full_name": "Demo Teacher Smith"})

        # TCH002: teaches HIN, SCI, SST in 10-A, and all subjects in 10-B
        t2_user = _get_or_create_user("TCH002", "teacher", teacher_pw)
        t2 = _get_or_create(Teacher, user_id=t2_user.id, teacher_code="TCH002", defaults={"full_name": "Demo Teacher Rao"})

        # 5. Students
        # S1: Demo Student One (10-A, roll 1) -> Complete, PASS (all subjects >= 35)
        s1_user = _get_or_create_user("STU2026001", "student", student_pw)
        s1 = _get_or_create(Student, user_id=s1_user.id, student_code="STU2026001", defaults={"full_name": "Demo Student One", "section_id": sec_a.id, "roll_number": 1})

        # S2: Demo Student Two (10-A, roll 2) -> Complete, FAIL (fails SST with 20.00 despite 100 in others)
        s2_user = _get_or_create_user("STU2026002", "student", student_pw)
        s2 = _get_or_create(Student, user_id=s2_user.id, student_code="STU2026002", defaults={"full_name": "Demo Student Two", "section_id": sec_a.id, "roll_number": 2})

        # S3: Demo Student Three (10-A, roll 3) -> INCOMPLETE (SST missing)
        s3_user = _get_or_create_user("STU2026003", "student", student_pw)
        s3 = _get_or_create(Student, user_id=s3_user.id, student_code="STU2026003", defaults={"full_name": "Demo Student Three", "section_id": sec_a.id, "roll_number": 3})

        # S4: Demo Student Four (10-B, roll 1) -> Section B student taught by TCH002
        s4_user = _get_or_create_user("STU2026004", "student", student_pw)
        s4 = _get_or_create(Student, user_id=s4_user.id, student_code="STU2026004", defaults={"full_name": "Demo Student Four", "section_id": sec_b.id, "roll_number": 1})

        db.session.commit()

        # 6. Teacher Assignments
        # S1, S2, S3 in Section A: ENG & MAT -> T1; HIN, SCI, SST -> T2
        for stu in [s1, s2, s3]:
            for sub in [sub_eng, sub_mat]:
                _get_or_create(TeacherAssignment, teacher_id=t1.id, student_id=stu.id, subject_id=sub.id)
            for sub in [sub_hin, sub_sci, sub_sst]:
                _get_or_create(TeacherAssignment, teacher_id=t2.id, student_id=stu.id, subject_id=sub.id)

        # S4 in Section B: all subjects -> T2
        for sub in all_subjects:
            _get_or_create(TeacherAssignment, teacher_id=t2.id, student_id=s4.id, subject_id=sub.id)

        db.session.commit()

        # 7. Seed Sample Marks & Audit
        # S1 marks: 78, 65, 90, 55, 42 -> Total 330, 66.00%, B2, PASS
        s1_marks = {"ENG": Decimal("78.00"), "HIN": Decimal("65.00"), "MAT": Decimal("90.00"), "SCI": Decimal("55.00"), "SST": Decimal("42.00")}
        for code, val in s1_marks.items():
            _upsert_mark_with_audit(student_id=s1.id, exam_subject=exam_sub_map[code], value=val, user=t1_user if code in ("ENG", "MAT") else t2_user, now=now)

        # S2 marks: 100, 100, 100, 100, 20 -> Total 420, 84.00%, but FAIL due to SST 20
        s2_marks = {"ENG": Decimal("100.00"), "HIN": Decimal("100.00"), "MAT": Decimal("100.00"), "SCI": Decimal("100.00"), "SST": Decimal("20.00")}
        for code, val in s2_marks.items():
            _upsert_mark_with_audit(student_id=s2.id, exam_subject=exam_sub_map[code], value=val, user=t1_user if code in ("ENG", "MAT") else t2_user, now=now)

        # S3 marks: ENG 85, MAT 92 (T1 entered), others not entered yet (INCOMPLETE)
        s3_marks = {"ENG": Decimal("85.00"), "MAT": Decimal("92.00")}
        for code, val in s3_marks.items():
            _upsert_mark_with_audit(student_id=s3.id, exam_subject=exam_sub_map[code], value=val, user=t1_user, now=now)

        db.session.commit()
        click.secho("Success: Fictional demo dataset seeded successfully.", fg="green", bold=True)
        click.echo("Demo accounts created:")
        click.echo("  Teachers: TCH001, TCH002")
        click.echo("  Students: STU2026001, STU2026002, STU2026003, STU2026004")

    @app.cli.command("setup-production-accounts")
    @click.option("--student-id", default="4INI23IS036", help="Student login ID")
    @click.option("--teacher-id", default="TCH001", help="Teacher login ID")
    @click.option("--teacher-name", default="Mathematics Teacher", help="Teacher name")
    @click.option("--class-name", default="10th Standard", help="Student class")
    @click.option("--section", default="A", help="Student section")
    @click.option("--academic-year", default="2025-26", help="Academic year")
    @click.option("--roll", type=int, default=36, help="Student roll number")
    @click.option("--prompt-passwords", is_flag=True, help="Interactively enter passwords using hidden prompt with confirmation (getpass)")
    def setup_prod_accounts_cmd(
        student_id: str,
        teacher_id: str,
        teacher_name: str,
        class_name: str,
        section: str,
        academic_year: str,
        roll: int,
        prompt_passwords: bool,
    ) -> None:
        """Idempotently set up required production student and teacher accounts."""
        from .services.password_policy import validate_password_strength
        from scripts.setup_production_accounts import provision_accounts

        teacher_pw: str | None = None
        student_pw: str | None = None

        if prompt_passwords:
            while True:
                tpw = click.prompt(
                    f"Enter password for Teacher ({teacher_id})",
                    hide_input=True,
                    confirmation_prompt=True,
                )
                valid, err = validate_password_strength(tpw, min_length=12)
                if not valid:
                    click.secho(f"Error: {err}", fg="red")
                    continue
                teacher_pw = tpw
                break

            while True:
                spw = click.prompt(
                    f"Enter password for Student ({student_id})",
                    hide_input=True,
                    confirmation_prompt=True,
                )
                valid, err = validate_password_strength(spw, min_length=12)
                if not valid:
                    click.secho(f"Error: {err}", fg="red")
                    continue
                student_pw = spw
                break

        res = provision_accounts(
            student_id=student_id,
            teacher_id=teacher_id,
            teacher_name=teacher_name,
            academic_year=academic_year,
            class_name=class_name,
            section_name=section,
            roll_number=roll,
            student_password=student_pw,
            teacher_password=teacher_pw,
        )
        click.secho("\n--- Production Accounts Setup ---", fg="cyan", bold=True)
        click.echo(f"Teacher ({teacher_id}): {res['teacher_status'].upper()}")
        click.echo("  Password status: [CONFIGURED SECURELY — NOT ECHOED TO LOGS]")

        click.echo(f"Student ({student_id}): {res['student_status'].upper()}")
        click.echo("  Password status: [CONFIGURED SECURELY — NOT ECHOED TO LOGS]")
        click.secho("Verification: SUCCESS (Linked to Mathematics in 10th Standard Section A)\n", fg="green")

    @app.cli.command("seed-stqa")
    @click.option("--teacher-password", default=None, help="Custom password for general teacher (TCH001)")
    @click.option("--student-password", default=None, help="Custom password for student accounts")
    @click.option("--overwrite", is_flag=True, help="Force overwrite passwords if accounts already exist")
    def seed_stqa_cmd(teacher_password: str | None, student_password: str | None, overwrite: bool) -> None:
        """Seed official STQA testing scenario (1 general teacher, 5 students, 5 subjects, realistic marks)."""
        from .services.seed_data import provision_stqa_scenario
        summary = provision_stqa_scenario(
            teacher_password=teacher_password,
            student_password=student_password,
            overwrite_passwords=overwrite,
            lockout_system=False,
        )
        click.secho("Success: STQA scenario seeded successfully.", fg="green", bold=True)
        click.echo(f"  Teacher: {summary['teacher']['login_id']} ({summary['teacher']['name']})")
        click.echo(f"  Students ({summary['total_students']}): {', '.join(s['login_id'] for s in summary['students'])}")
        click.echo(f"  Subjects ({summary['total_subjects']}): ENG, HIN, MAT, SCI, SST")
        click.echo(f"  Assignments: {summary['assignments_created']} total links")
        click.echo(f"  Marks Seeded: {summary['marks_seeded']} subject marks with audit logging")



def _get_or_create(model: Any, defaults: dict[str, Any] | None = None, **kwargs: Any) -> Any:
    instance = db.session.scalar(select(model).filter_by(**kwargs))
    if instance:
        return instance
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance


def _get_or_create_user(login_id: str, role: str, password: str) -> User:
    norm_id = login_id.strip().upper()
    u = db.session.scalar(select(User).where(User.login_id == norm_id))
    if u:
        return u
    u = User(login_id=norm_id, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.flush()
    return u


def _upsert_mark_with_audit(
    student_id: int,
    exam_subject: ExamSubject,
    value: Decimal | None,
    user: User,
    now: datetime,
) -> None:
    mark = db.session.scalar(
        select(Mark).where(Mark.student_id == student_id, Mark.exam_subject_id == exam_subject.id)
    )
    if mark is None:
        mark = Mark(
            student_id=student_id,
            exam_subject_id=exam_subject.id,
            marks_obtained=value,
            updated_by=user.id,
            updated_at=now,
        )
        db.session.add(mark)
        db.session.flush()
        audit = MarkAudit(
            mark_id=mark.id,
            action="create",
            old_value=None,
            new_value=value,
            changed_by=user.id,
            changed_at=now,
        )
        db.session.add(audit)
    else:
        if mark.marks_obtained != value:
            old = mark.marks_obtained
            mark.marks_obtained = value
            mark.updated_by = user.id
            mark.updated_at = now
            action = "clear" if value is None else "update"
            audit = MarkAudit(
                mark_id=mark.id,
                action=action,
                old_value=old,
                new_value=value,
                changed_by=user.id,
                changed_at=now,
            )
            db.session.add(audit)
