"""Exercise 5: Top-Down Integration Testing Framework for SRMS.

Demonstrates hierarchical top-down integration testing with incremental stub replacement:
- Level 1: ReportModule (Top-level orchestrator)
- Level 2: GradeModule (Business grading core)
- Level 3: MarksRepository (Data access layer)

Integration Sequence:
Step 1: Test ReportModule using GradeModuleStub and MarksRepositoryStub.
Step 2: Replace GradeModuleStub with real GradeModule, keeping MarksRepositoryStub.
Step 3: Replace MarksRepositoryStub with real in-memory MarksRepository (complete integration).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Protocol


# ============================================================================
# Interfaces (Protocols)
# ============================================================================

class MarksRepositoryInterface(Protocol):
    def get_student_marks(self, student_id: int) -> List[Dict[str, Decimal]]:
        ...


class GradeModuleInterface(Protocol):
    def compute_result(self, marks: List[Dict[str, Decimal]]) -> Dict[str, str]:
        ...


# ============================================================================
# Stubs (Used during Top-Down Incremental Integration)
# ============================================================================

class MarksRepositoryStub:
    """Stub returning predetermined marks without database access."""

    def __init__(self, predefined_marks: Optional[List[Dict[str, Decimal]]] = None) -> None:
        self.predefined_marks = predefined_marks or [
            {"subject": "ENG", "max": Decimal("100"), "obtained": Decimal("80.00")},
            {"subject": "MAT", "max": Decimal("100"), "obtained": Decimal("90.00")},
        ]

    def get_student_marks(self, student_id: int) -> List[Dict[str, Decimal]]:
        return self.predefined_marks


class GradeModuleStub:
    """Stub returning predetermined grade and pass status without calculation."""

    def __init__(self, stub_status: str = "PASS", stub_grade: str = "A2") -> None:
        self.stub_status = stub_status
        self.stub_grade = stub_grade

    def compute_result(self, marks: List[Dict[str, Decimal]]) -> Dict[str, str]:
        return {
            "total_obtained": "170.00",
            "total_max": "200.00",
            "percentage": "85.00%",
            "grade": self.stub_grade,
            "status": self.stub_status,
        }


# ============================================================================
# Real Implementations
# ============================================================================

class RealGradeModule:
    """Real business grading logic using SRMS core rules."""

    def compute_result(self, marks: List[Dict[str, Decimal]]) -> Dict[str, str]:
        if not marks:
            return {"status": "EMPTY", "grade": "—", "percentage": "—"}

        total_obtained = sum(m["obtained"] for m in marks if m.get("obtained") is not None)
        total_max = sum(m["max"] for m in marks)

        if any(m.get("obtained") is None for m in marks):
            return {"status": "INCOMPLETE", "grade": "—", "percentage": "—"}

        pct = (total_obtained / total_max) * Decimal("100")
        pct_rounded = round(pct, 2)

        # Check individual subject pass (pass mark = 35% of max)
        all_passed = all(m["obtained"] >= (m["max"] * Decimal("0.35")) for m in marks)

        if not all_passed or pct_rounded < Decimal("35.00"):
            status = "FAIL"
            grade = "E"
        else:
            status = "PASS"
            if pct_rounded >= Decimal("90.00"):
                grade = "A1"
            elif pct_rounded >= Decimal("80.00"):
                grade = "A2"
            elif pct_rounded >= Decimal("70.00"):
                grade = "B1"
            elif pct_rounded >= Decimal("60.00"):
                grade = "B2"
            elif pct_rounded >= Decimal("50.00"):
                grade = "C1"
            elif pct_rounded >= Decimal("40.00"):
                grade = "C2"
            else:
                grade = "D"

        return {
            "total_obtained": str(total_obtained),
            "total_max": str(total_max),
            "percentage": f"{pct_rounded}%",
            "grade": grade,
            "status": status,
        }


class RealInMemoryMarksRepository:
    """Real in-memory repository simulating persistence operations."""

    def __init__(self) -> None:
        self._store: Dict[int, List[Dict[str, Decimal]]] = {}

    def save_student_marks(self, student_id: int, marks: List[Dict[str, Decimal]]) -> None:
        self._store[student_id] = marks

    def get_student_marks(self, student_id: int) -> List[Dict[str, Decimal]]:
        return self._store.get(student_id, [])


# ============================================================================
# Top-Level Orchestrator Module
# ============================================================================

class ReportModule:
    """Top-level module orchestrating result retrieval, grading, and formatting."""

    def __init__(
        self,
        marks_repo: MarksRepositoryInterface,
        grade_module: GradeModuleInterface,
    ) -> None:
        self.marks_repo = marks_repo
        self.grade_module = grade_module

    def generate_student_report(self, student_id: int, student_name: str) -> Dict[str, str]:
        """Fetch marks from data layer, pass through grading module, format report."""
        raw_marks = self.marks_repo.get_student_marks(student_id)
        evaluation = self.grade_module.compute_result(raw_marks)

        return {
            "student_id": str(student_id),
            "student_name": student_name,
            "status": evaluation["status"],
            "grade": evaluation["grade"],
            "percentage": evaluation["percentage"],
            "subject_count": str(len(raw_marks)),
        }
