"""STQA scenario seed data and account provisioning service.

Pre-provisions:
- 1 General Teacher account: TCH001 (not subject-specific).
- 5 Individual Student accounts with unique USNs:
  1. 4INI23IS036 (Roll 36, Section A) -> Grade A1 (Outstanding / Distinction, 93.40%)
  2. 4INI23IS001 (Roll 1, Section A)  -> Grade A2 (Excellent, 84.00%)
  3. 4INI23IS002 (Roll 2, Section A)  -> Grade B1 (Very Good, 74.00%)
  4. 4INI23IS003 (Roll 3, Section A)  -> Grade B2 (Good, 62.00%)
  5. 4INI23IS004 (Roll 4, Section A)  -> Grade C2 (Average / Pass, 45.00%)
- 5 Academic Subjects:
  - ENG (English, max 100, pass 35)
  - HIN (Hindi, max 100, pass 35)
  - MAT (Mathematics, max 100, pass 35)
  - SCI (Science, max 100, pass 35)
  - SST (Social Science, max 100, pass 35)
- Examination: Annual Examination 2025-26
- Teacher Assignments: TCH001 assigned to all 5 students for all 5 subjects (25 total assignments).
- Realistic Marks: Seeded out of 100 with full MarkAudit trail.
- Security: Stores only scrypt password hashes; never overwrites existing passwords silently.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from ..extensions import db
from ..models import (
    Exam,
    ExamSubject,
    Mark,
    MarkAudit,
    Section,
    Student,
    Subject,
    SystemSetting,
    Teacher,
    TeacherAssignment,
    User,
    utc_now,
)
from .password_policy import validate_password_strength

DEMO_TEACHER = {
    "login_id": "TCH001",
    "full_name": "General Teacher",
}

DEMO_STUDENTS = [
    {
        "login_id": "4INI23IS036",
        "full_name": "Student 4INI23IS036",
        "roll_number": 36,
        "marks": {
            "ENG": Decimal("94.00"),
            "HIN": Decimal("88.00"),
            "MAT": Decimal("98.00"),
            "SCI": Decimal("95.00"),
            "SST": Decimal("92.00"),
        },
    },
    {
        "login_id": "4INI23IS001",
        "full_name": "Student 4INI23IS001",
        "roll_number": 1,
        "marks": {
            "ENG": Decimal("82.00"),
            "HIN": Decimal("85.00"),
            "MAT": Decimal("88.00"),
            "SCI": Decimal("84.00"),
            "SST": Decimal("81.00"),
        },
    },
    {
        "login_id": "4INI23IS002",
        "full_name": "Student 4INI23IS002",
        "roll_number": 2,
        "marks": {
            "ENG": Decimal("74.00"),
            "HIN": Decimal("72.00"),
            "MAT": Decimal("78.00"),
            "SCI": Decimal("76.00"),
            "SST": Decimal("70.00"),
        },
    },
    {
        "login_id": "4INI23IS003",
        "full_name": "Student 4INI23IS003",
        "roll_number": 3,
        "marks": {
            "ENG": Decimal("62.00"),
            "HIN": Decimal("64.00"),
            "MAT": Decimal("58.00"),
            "SCI": Decimal("66.00"),
            "SST": Decimal("60.00"),
        },
    },
    {
        "login_id": "4INI23IS004",
        "full_name": "Student 4INI23IS004",
        "roll_number": 4,
        "marks": {
            "ENG": Decimal("45.00"),
            "HIN": Decimal("42.00"),
            "MAT": Decimal("48.00"),
            "SCI": Decimal("50.00"),
            "SST": Decimal("40.00"),
        },
    },
]

DEMO_SUBJECTS = [
    {"code": "ENG", "name": "English", "max_marks": Decimal("100.00"), "pass_marks": Decimal("35.00")},
    {"code": "HIN", "name": "Hindi", "max_marks": Decimal("100.00"), "pass_marks": Decimal("35.00")},
    {"code": "MAT", "name": "Mathematics", "max_marks": Decimal("100.00"), "pass_marks": Decimal("35.00")},
    {"code": "SCI", "name": "Science", "max_marks": Decimal("100.00"), "pass_marks": Decimal("35.00")},
    {"code": "SST", "name": "Social Science", "max_marks": Decimal("100.00"), "pass_marks": Decimal("35.00")},
]

DEMO_EXAM_NAME = "Annual Examination 2025-26"
DEMO_ACADEMIC_YEAR = "2025-26"
DEMO_CLASS_NAME = "10th Standard"
DEMO_SECTION_NAME = "A"


class AccountAlreadyExistsError(Exception):
    """Raised when an existing account already has an active password and overwrite is disallowed."""
    pass


def provision_stqa_scenario(
    teacher_password: str,
    student_password: str,
    overwrite_passwords: bool = False,
    lockout_system: bool = True,
) -> dict[str, Any]:
    """Execute reproducible provisioning for STQA demo testing scenario atomically.

    :param teacher_password: Explicit password for TCH001 (min 12 chars).
    :param student_password: Explicit password for all 5 students (min 12 chars).
    :param overwrite_passwords: If False, raises AccountAlreadyExistsError on active accounts.
    :param lockout_system: If True, writes SystemSetting("bootstrap_completed") = "true".
    :return: Summary dictionary of provisioned entities and credentials status.
    """
    if not teacher_password or not str(teacher_password).strip():
        raise ValueError("Teacher password must be explicitly provided.")
    if not student_password or not str(student_password).strip():
        raise ValueError("Student password must be explicitly provided.")

    t_pass = str(teacher_password).strip()
    s_pass = str(student_password).strip()

    # Validate password complexity
    valid_t, err_t = validate_password_strength(t_pass, min_length=12)
    if not valid_t:
        raise ValueError(f"Teacher password does not meet policy: {err_t}")

    valid_s, err_s = validate_password_strength(s_pass, min_length=12)
    if not valid_s:
        raise ValueError(f"Student password does not meet policy: {err_s}")

    try:
        summary = _execute_seeding(
            t_pass=t_pass,
            s_pass=s_pass,
            overwrite_passwords=overwrite_passwords,
            lockout_system=lockout_system,
        )
        db.session.commit()
        return summary
    except Exception:
        db.session.rollback()
        raise


def _execute_seeding(
    t_pass: str,
    s_pass: str,
    overwrite_passwords: bool,
    lockout_system: bool,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    # 1. Check existing accounts for silent overwrite protection
    teacher_user = db.session.scalar(select(User).where(User.login_id == DEMO_TEACHER["login_id"]))
    if teacher_user and teacher_user.password_hash and not overwrite_passwords:
        raise AccountAlreadyExistsError(
            f"Teacher account {DEMO_TEACHER['login_id']} already exists with an active password."
        )

    for stu_info in DEMO_STUDENTS:
        existing_stu = db.session.scalar(select(User).where(User.login_id == stu_info["login_id"]))
        if existing_stu and existing_stu.password_hash and not overwrite_passwords:
            raise AccountAlreadyExistsError(
                f"Student account {stu_info['login_id']} already exists with an active password."
            )

    # 2. Section: 10th Standard Section A (2025-26)
    sec = db.session.scalar(
        select(Section).where(
            Section.class_name == DEMO_CLASS_NAME,
            Section.name == DEMO_SECTION_NAME,
            Section.academic_year == DEMO_ACADEMIC_YEAR,
        )
    )
    if not sec:
        sec = Section(class_name=DEMO_CLASS_NAME, name=DEMO_SECTION_NAME, academic_year=DEMO_ACADEMIC_YEAR)
        db.session.add(sec)
        db.session.flush()

    # 3. Subjects
    subjects_map: dict[str, Subject] = {}
    for sub_data in DEMO_SUBJECTS:
        sub = db.session.scalar(select(Subject).where(Subject.code == sub_data["code"]))
        if not sub:
            sub = Subject(code=sub_data["code"], name=sub_data["name"])
            db.session.add(sub)
            db.session.flush()
        subjects_map[sub_data["code"]] = sub

    # 4. Exam & ExamSubjects
    exam = db.session.scalar(select(Exam).where(Exam.academic_year == DEMO_ACADEMIC_YEAR))
    if not exam:
        exam = Exam(name=DEMO_EXAM_NAME, academic_year=DEMO_ACADEMIC_YEAR)
        db.session.add(exam)
        db.session.flush()

    exam_subjects_map: dict[str, ExamSubject] = {}
    for sub_data in DEMO_SUBJECTS:
        sub = subjects_map[sub_data["code"]]
        es = db.session.scalar(
            select(ExamSubject).where(ExamSubject.exam_id == exam.id, ExamSubject.subject_id == sub.id)
        )
        if not es:
            es = ExamSubject(
                exam_id=exam.id,
                subject_id=sub.id,
                max_marks=sub_data["max_marks"],
                pass_marks=sub_data["pass_marks"],
            )
            db.session.add(es)
            db.session.flush()
        exam_subjects_map[sub_data["code"]] = es

    # 5. Teacher Account (TCH001 - General Teacher)
    if not teacher_user:
        teacher_user = User(login_id=DEMO_TEACHER["login_id"], role="teacher")
        teacher_user.set_password(t_pass)
        db.session.add(teacher_user)
        db.session.flush()

        teacher_record = Teacher(
            user_id=teacher_user.id,
            teacher_code=DEMO_TEACHER["login_id"],
            full_name=DEMO_TEACHER["full_name"],
        )
        db.session.add(teacher_record)
        db.session.flush()
    else:
        teacher_record = teacher_user.teacher
        if overwrite_passwords or not teacher_user.password_hash:
            teacher_user.set_password(t_pass)
        if not teacher_record:
            teacher_record = Teacher(
                user_id=teacher_user.id,
                teacher_code=DEMO_TEACHER["login_id"],
                full_name=DEMO_TEACHER["full_name"],
            )
            db.session.add(teacher_record)
            db.session.flush()

    # 6. Student Accounts & Profiles
    students_records: list[Student] = []
    for stu_info in DEMO_STUDENTS:
        stu_user = db.session.scalar(select(User).where(User.login_id == stu_info["login_id"]))
        if not stu_user:
            stu_user = User(login_id=stu_info["login_id"], role="student")
            stu_user.set_password(s_pass)
            db.session.add(stu_user)
            db.session.flush()

            stu_record = Student(
                user_id=stu_user.id,
                student_code=stu_info["login_id"],
                full_name=stu_info["full_name"],
                section_id=sec.id,
                roll_number=stu_info["roll_number"],
            )
            db.session.add(stu_record)
            db.session.flush()
        else:
            stu_record = stu_user.student
            if overwrite_passwords or not stu_user.password_hash:
                stu_user.set_password(s_pass)
            if not stu_record:
                stu_record = Student(
                    user_id=stu_user.id,
                    student_code=stu_info["login_id"],
                    full_name=stu_info["full_name"],
                    section_id=sec.id,
                    roll_number=stu_info["roll_number"],
                )
                db.session.add(stu_record)
                db.session.flush()

        students_records.append(stu_record)

    # 7. Teacher Assignments (TCH001 assigned to all 5 students for all 5 subjects)
    assignment_count = 0
    for stu_record in students_records:
        for sub_data in DEMO_SUBJECTS:
            sub = subjects_map[sub_data["code"]]
            assignment = db.session.scalar(
                select(TeacherAssignment).where(
                    TeacherAssignment.teacher_id == teacher_record.id,
                    TeacherAssignment.student_id == stu_record.id,
                    TeacherAssignment.subject_id == sub.id,
                )
            )
            if not assignment:
                assignment = TeacherAssignment(
                    teacher_id=teacher_record.id,
                    student_id=stu_record.id,
                    subject_id=sub.id,
                )
                db.session.add(assignment)
                assignment_count += 1

    # 8. Seed Realistic Marks & MarkAudit
    marks_seeded = 0
    for idx, stu_info in enumerate(DEMO_STUDENTS):
        stu_record = students_records[idx]
        for sub_code, mark_val in stu_info["marks"].items():
            es = exam_subjects_map[sub_code]
            mark = db.session.scalar(
                select(Mark).where(
                    Mark.student_id == stu_record.id,
                    Mark.exam_subject_id == es.id,
                )
            )
            if not mark:
                mark = Mark(
                    student_id=stu_record.id,
                    exam_subject_id=es.id,
                    marks_obtained=mark_val,
                    updated_by=teacher_user.id,
                )
                db.session.add(mark)
                db.session.flush()

                audit = MarkAudit(
                    mark_id=mark.id,
                    action="create",
                    old_value=None,
                    new_value=mark_val,
                    changed_by=teacher_user.id,
                    changed_at=now,
                )
                db.session.add(audit)
                marks_seeded += 1
            elif mark.marks_obtained != mark_val and overwrite_passwords:
                old_val = mark.marks_obtained
                mark.marks_obtained = mark_val
                mark.updated_by = teacher_user.id
                audit = MarkAudit(
                    mark_id=mark.id,
                    action="update",
                    old_value=old_val,
                    new_value=mark_val,
                    changed_by=teacher_user.id,
                    changed_at=now,
                )
                db.session.add(audit)

    # 9. Optional System Lockout Setting
    if lockout_system:
        setting = db.session.scalar(
            select(SystemSetting).where(SystemSetting.key == "bootstrap_completed")
        )
        if setting:
            setting.value = "true"
            setting.updated_at = utc_now()
        else:
            setting = SystemSetting(key="bootstrap_completed", value="true")
            db.session.add(setting)

    db.session.flush()

    return {
        "teacher": {
            "login_id": DEMO_TEACHER["login_id"],
            "name": DEMO_TEACHER["full_name"],
            "role": "teacher",
        },
        "students": [
            {
                "login_id": s["login_id"],
                "name": s["full_name"],
                "roll_number": s["roll_number"],
                "role": "student",
            }
            for s in DEMO_STUDENTS
        ],
        "total_students": len(DEMO_STUDENTS),
        "total_subjects": len(DEMO_SUBJECTS),
        "assignments_created": assignment_count,
        "marks_seeded": marks_seeded,
        "exam_name": DEMO_EXAM_NAME,
        "academic_year": DEMO_ACADEMIC_YEAR,
        "class_name": DEMO_CLASS_NAME,
        "section_name": DEMO_SECTION_NAME,
    }
