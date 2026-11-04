"""Data models and schema structures for SRMS."""

from dataclasses import dataclass, field
from typing import Dict, Any, List
from app.config import SUBJECTS, DEFAULT_CLASS


@dataclass
class StudentRecord:
    """Represents a Class 10 student record stored in JSON."""

    student_id: str
    name: str
    username: str
    password: str
    student_class: str = DEFAULT_CLASS
    section: str = "A"
    roll_number: int = 1
    marks: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize student record to dictionary for JSON storage."""
        return {
            "student_id": self.student_id,
            "name": self.name,
            "username": self.username,
            "password": self.password,
            "class": self.student_class,
            "section": self.section,
            "roll_number": self.roll_number,
            "marks": {subj: int(self.marks[subj]) for subj in SUBJECTS if subj in self.marks},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentRecord":
        """Deserialize dictionary from JSON into a StudentRecord instance."""
        return cls(
            student_id=str(data.get("student_id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            username=str(data.get("username", "")).strip(),
            password=str(data.get("password", "")),
            student_class=str(data.get("class", DEFAULT_CLASS)).strip(),
            section=str(data.get("section", "A")).strip().upper(),
            roll_number=int(data.get("roll_number", 1)),
            marks=dict(data.get("marks", {})),
        )


@dataclass
class SubjectResult:
    """Computed result for an individual subject."""

    subject: str
    marks_obtained: int
    max_marks: int
    grade: str
    status: str  # "Pass" or "Fail"
    passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "marks_obtained": self.marks_obtained,
            "max_marks": self.max_marks,
            "grade": self.grade,
            "status": self.status,
            "passed": self.passed,
        }


@dataclass
class OverallResult:
    """Computed overall examination result for a student."""

    total_marks: int
    max_marks: int
    percentage: float
    formatted_percentage: str
    classification: str
    overall_status: str  # "PASS" or "FAIL"
    passed_all: bool
    failed_subjects: List[str]
    subject_results: List[SubjectResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_marks": self.total_marks,
            "max_marks": self.max_marks,
            "percentage": self.percentage,
            "formatted_percentage": self.formatted_percentage,
            "classification": self.classification,
            "overall_status": self.overall_status,
            "passed_all": self.passed_all,
            "failed_subjects": self.failed_subjects,
            "subject_results": [sr.to_dict() for sr in self.subject_results],
        }
