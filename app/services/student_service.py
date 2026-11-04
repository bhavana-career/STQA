"""JSON storage, validation, and CRUD service for students and teachers."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import SUBJECTS, VALID_SECTIONS, DEFAULT_CLASS
from app.models import StudentRecord
from app.services.marks_service import validate_all_marks, MarksValidationError
from app.services.result_service import evaluate_student_result


class StudentValidationError(ValueError):
    """Raised when student record validation or CRUD constraints fail."""


def _safe_read_json(filepath: str) -> List[Dict[str, Any]]:
    """Read a JSON list from disk safely."""
    path = Path(filepath)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise StudentValidationError(f"Corrupted JSON root in {filepath}: expected a list.")
            return data
    except json.JSONDecodeError as exc:
        raise StudentValidationError(f"Failed to parse JSON file {filepath}: {exc}") from exc


def _safe_write_json(filepath: str, data: List[Dict[str, Any]]) -> None:
    """
    Atomically write a JSON list to disk using a temporary file in the same directory
    so that a failed write never corrupts the existing JSON file.
    """
    if not isinstance(data, list):
        raise StudentValidationError("Data to persist must be a list of records.")

    path = Path(filepath).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    # First serialize to string to catch any serialization error before touching disk
    serialized = json.dumps(data, indent=2, ensure_ascii=False)

    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".srms_tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(serialized)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def validate_student_payload(
    payload: Dict[str, Any],
    existing_students: List[Dict[str, Any]],
    existing_teachers: Optional[List[Dict[str, Any]]] = None,
    current_student_id: Optional[str] = None,
) -> StudentRecord:
    """
    Validate all student fields, uniqueness constraints, and subject marks.
    - If `current_student_id` is None (CREATE mode), `student_id` and `username` must be unique across all records.
    - If `current_student_id` is provided (UPDATE mode), uniqueness is checked against all other records.
    """
    if not isinstance(payload, dict):
        raise StudentValidationError("Student data must be a dictionary.")

    student_id = str(payload.get("student_id", "")).strip()
    name = str(payload.get("name", "")).strip()
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    student_class = str(payload.get("class", DEFAULT_CLASS)).strip()
    section = str(payload.get("section", "")).strip().upper()
    raw_roll = payload.get("roll_number")

    if not student_id:
        raise StudentValidationError("Student ID is required.")
    if not name:
        raise StudentValidationError("Student name is required.")
    if not username:
        raise StudentValidationError("Username is required.")
    if not password:
        raise StudentValidationError("Password is required.")
    if student_class != DEFAULT_CLASS:
        raise StudentValidationError(f"Class must be '{DEFAULT_CLASS}'.")
    if section not in VALID_SECTIONS:
        raise StudentValidationError(f"Section must be one of: {', '.join(VALID_SECTIONS)}.")

    if raw_roll is None or isinstance(raw_roll, bool) or str(raw_roll).strip() == "":
        raise StudentValidationError("Roll number is required.")
    try:
        if isinstance(raw_roll, float) or "." in str(raw_roll):
            raise ValueError("Decimal roll number not allowed")
        roll_number = int(str(raw_roll).strip())
    except ValueError as exc:
        raise StudentValidationError("Roll number must be a valid positive integer.") from exc

    if roll_number <= 0:
        raise StudentValidationError("Roll number must be greater than zero.")

    # Check teacher username collision
    if existing_teachers:
        for t in existing_teachers:
            if str(t.get("username", "")).strip().lower() == username.lower():
                raise StudentValidationError(f"Username '{username}' is reserved for a teacher account.")

    # Check student uniqueness constraints
    for s in existing_students:
        sid = str(s.get("student_id", "")).strip()
        if current_student_id is not None and sid.lower() == current_student_id.strip().lower():
            continue

        if sid.lower() == student_id.lower():
            raise StudentValidationError(f"Student ID '{student_id}' already exists.")
        if str(s.get("username", "")).strip().lower() == username.lower():
            raise StudentValidationError(f"Username '{username}' is already assigned to another student.")
        if (
            str(s.get("section", "")).strip().upper() == section
            and int(s.get("roll_number", -1)) == roll_number
        ):
            raise StudentValidationError(
                f"Roll number {roll_number} is already assigned in Section {section}."
            )

    raw_marks = payload.get("marks")
    if raw_marks is None:
        raise StudentValidationError("Subject marks dictionary is required.")

    try:
        validated_marks = validate_all_marks(raw_marks)
    except MarksValidationError as exc:
        raise StudentValidationError(str(exc)) from exc

    return StudentRecord(
        student_id=student_id,
        name=name,
        username=username,
        password=password,
        student_class=student_class,
        section=section,
        roll_number=roll_number,
        marks=validated_marks,
    )


def enrich_student_with_result(student_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Attach computed `result` dictionary to a copy of the student record."""
    enriched = dict(student_dict)
    result_obj = evaluate_student_result(enriched.get("marks", {}))
    enriched["result"] = result_obj.to_dict()
    return enriched


def get_all_teachers(teachers_file: str) -> List[Dict[str, Any]]:
    """Return all teacher records from JSON."""
    return _safe_read_json(teachers_file)


def get_all_students(students_file: str, include_results: bool = True) -> List[Dict[str, Any]]:
    """Return all student records from JSON, optionally enriched with calculated results."""
    records = _safe_read_json(students_file)
    if not include_results:
        return records
    return [enrich_student_with_result(r) for r in records]


def get_student_by_id(
    students_file: str, student_id: str, include_results: bool = True
) -> Optional[Dict[str, Any]]:
    """Find a single student by Student ID (case-insensitive)."""
    if not student_id:
        return None
    target = str(student_id).strip().lower()
    records = _safe_read_json(students_file)
    for r in records:
        if str(r.get("student_id", "")).strip().lower() == target:
            return enrich_student_with_result(r) if include_results else r
    return None


def get_student_by_username(
    students_file: str, username: str, include_results: bool = True
) -> Optional[Dict[str, Any]]:
    """Find a single student by username (case-insensitive)."""
    if not username:
        return None
    target = str(username).strip().lower()
    records = _safe_read_json(students_file)
    for r in records:
        if str(r.get("username", "")).strip().lower() == target:
            return enrich_student_with_result(r) if include_results else r
    return None


def search_and_filter_students(
    students_file: str,
    search_query: Optional[str] = None,
    section_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search students by name or student_id (case-insensitive substring match)
    and/or filter by section ('A', 'B', 'C').
    """
    students = get_all_students(students_file, include_results=True)

    if section_filter and section_filter.strip().upper() in VALID_SECTIONS:
        sec = section_filter.strip().upper()
        students = [s for s in students if str(s.get("section", "")).upper() == sec]

    if search_query and search_query.strip():
        q = search_query.strip().lower()
        students = [
            s
            for s in students
            if q in str(s.get("student_id", "")).lower() or q in str(s.get("name", "")).lower()
        ]

    return students


def create_student(
    students_file: str,
    payload: Dict[str, Any],
    teachers_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new student record, validate it, persist to JSON, and return enriched record."""
    existing_students = _safe_read_json(students_file)
    existing_teachers = _safe_read_json(teachers_file) if teachers_file else []

    record = validate_student_payload(
        payload,
        existing_students=existing_students,
        existing_teachers=existing_teachers,
        current_student_id=None,
    )
    record_dict = record.to_dict()
    existing_students.append(record_dict)
    _safe_write_json(students_file, existing_students)
    return enrich_student_with_result(record_dict)


def update_student(
    students_file: str,
    student_id: str,
    payload: Dict[str, Any],
    teachers_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing student record (including info, section, credentials, or marks)."""
    existing_students = _safe_read_json(students_file)
    existing_teachers = _safe_read_json(teachers_file) if teachers_file else []

    target_index = -1
    target_id = str(student_id).strip().lower()
    for idx, s in enumerate(existing_students):
        if str(s.get("student_id", "")).strip().lower() == target_id:
            target_index = idx
            break

    if target_index == -1:
        raise StudentValidationError(f"Student with ID '{student_id}' not found.")

    current_record = existing_students[target_index]
    merged_payload = {
        "student_id": payload.get("student_id", current_record["student_id"]),
        "name": payload.get("name", current_record["name"]),
        "username": payload.get("username", current_record["username"]),
        "password": (
            payload["password"]
            if payload.get("password") and str(payload.get("password")).strip() != ""
            else current_record["password"]
        ),
        "class": payload.get("class", current_record.get("class", DEFAULT_CLASS)),
        "section": payload.get("section", current_record["section"]),
        "roll_number": payload.get("roll_number", current_record["roll_number"]),
        "marks": payload.get("marks", current_record["marks"]),
    }

    validated_record = validate_student_payload(
        merged_payload,
        existing_students=existing_students,
        existing_teachers=existing_teachers,
        current_student_id=current_record["student_id"],
    )
    updated_dict = validated_record.to_dict()
    existing_students[target_index] = updated_dict
    _safe_write_json(students_file, existing_students)
    return enrich_student_with_result(updated_dict)


def update_student_marks(
    students_file: str,
    student_id: str,
    marks_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Update only the six subject marks of an existing student and recalculate results."""
    try:
        validated_marks = validate_all_marks(marks_dict)
    except MarksValidationError as exc:
        raise StudentValidationError(str(exc)) from exc

    return update_student(students_file, student_id, {"marks": validated_marks})


def delete_student(students_file: str, student_id: str) -> bool:
    """Delete a student record by Student ID and persist immediately."""
    existing_students = _safe_read_json(students_file)
    target_id = str(student_id).strip().lower()

    filtered = [
        s for s in existing_students if str(s.get("student_id", "")).strip().lower() != target_id
    ]
    if len(filtered) == len(existing_students):
        raise StudentValidationError(f"Student with ID '{student_id}' not found.")

    _safe_write_json(students_file, filtered)
    return True


def authenticate_user(
    username: str,
    password: str,
    students_file: str,
    teachers_file: str,
) -> Optional[Dict[str, Any]]:
    """
    Validate credentials against teachers.json and students.json.
    Returns user session identity dict on match, or None on invalid credentials.
    """
    if not username or not password:
        return None
    if not isinstance(username, str) or not isinstance(password, str):
        return None

    clean_user = username.strip()
    if not clean_user:
        return None

    teachers = _safe_read_json(teachers_file)
    for t in teachers:
        if str(t.get("username", "")).strip() == clean_user and str(t.get("password", "")) == password:
            return {
                "role": "teacher",
                "username": clean_user,
                "name": t.get("name", "Teacher"),
                "teacher_id": t.get("teacher_id", "TCH001"),
            }

    students = _safe_read_json(students_file)
    for s in students:
        if str(s.get("username", "")).strip() == clean_user and str(s.get("password", "")) == password:
            return {
                "role": "student",
                "username": clean_user,
                "name": s.get("name", "Student"),
                "student_id": s.get("student_id"),
            }

    return None
