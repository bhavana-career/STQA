"""Pure domain service for calculation of marks, percentages, grades, and pass/fail rules.

Rules from docs/requirements.md (§4.4.1):
1. Total obtained = sum of marks obtained across subjects.
2. Total maximum = sum of subject maximum marks.
3. Percentage = (total_obtained / total_max) * 100, calculated with Decimal, ROUND_HALF_UP to 2 decimal places.
4. Subject pass <=> marks_obtained >= subject.pass_marks.
5. Overall PASS <=> every subject passed AND overall percentage >= min_overall_percentage (35.00%).
6. If any subject is failed, overall status is FAIL and overall grade is E.
7. If any subject mark is None (missing), overall status is INCOMPLETE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Sequence

DEFAULT_GRADE_BANDS: tuple[tuple[str, Decimal], ...] = (
    ("A1", Decimal("90.00")),
    ("A2", Decimal("80.00")),
    ("B1", Decimal("70.00")),
    ("B2", Decimal("60.00")),
    ("C1", Decimal("50.00")),
    ("C2", Decimal("40.00")),
    ("D", Decimal("35.00")),
)


@dataclass(frozen=True)
class GradingConfig:
    """Configurable grade thresholds and pass criteria."""

    grade_bands: tuple[tuple[str, Decimal], ...] = DEFAULT_GRADE_BANDS
    min_overall_percentage: Decimal = Decimal("35.00")
    fallback_grade: str = "E"


DEFAULT_GRADING_CONFIG = GradingConfig()


@dataclass
class SubjectResult:
    """Subject marks input and computed per-subject outcome."""

    code: str
    name: str
    max_marks: Decimal
    pass_marks: Decimal
    marks_obtained: Decimal | None
    percentage: Decimal | None = None
    grade: str | None = None
    passed: bool | None = None


@dataclass
class ExamResultSummary:
    """Consolidated examination result summary."""

    status: str  # "PASS", "FAIL", "INCOMPLETE"
    total_obtained: Decimal | None
    total_max: Decimal
    percentage: Decimal | None
    grade: str | None
    subjects: list[SubjectResult] = field(default_factory=list)


def percentage(obtained: Decimal | int | float, maximum: Decimal | int | float) -> Decimal:
    """Calculate percentage with exact Decimal arithmetic, rounded Half-Up to 2 decimal places."""
    try:
        obt_dec = Decimal(str(obtained))
        max_dec = Decimal(str(maximum))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid numeric input for percentage: {obtained!r}, {maximum!r}") from exc

    if max_dec <= Decimal("0"):
        raise ValueError("Total maximum marks must be greater than zero")

    if obt_dec < Decimal("0"):
        raise ValueError("Total obtained marks cannot be negative")

    if obt_dec > max_dec:
        raise ValueError("Total obtained marks cannot exceed total maximum")

    pct = (obt_dec / max_dec) * Decimal("100")
    return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def grade_for_percentage(
    pct: Decimal | int | float,
    config: GradingConfig | None = None,
) -> str:
    """Return the grade corresponding to a percentage value.

    Grade boundaries are inclusive of the lower bound:
    - 90.00 <= pct <= 100.00 -> A1
    - 80.00 <= pct < 90.00  -> A2
    - 70.00 <= pct < 80.00  -> B1
    - 60.00 <= pct < 70.00  -> B2
    - 50.00 <= pct < 60.00  -> C1
    - 40.00 <= pct < 50.00  -> C2
    - 35.00 <= pct < 40.00  -> D
    - Below 35.00           -> E
    """
    cfg = config or DEFAULT_GRADING_CONFIG

    try:
        pct_dec = Decimal(str(pct))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid percentage value: {pct!r}") from exc

    if pct_dec < Decimal("0") or pct_dec > Decimal("100"):
        raise ValueError("Percentage must be between 0 and 100")

    for grade_name, lower_bound in cfg.grade_bands:
        if pct_dec >= lower_bound:
            return grade_name

    return cfg.fallback_grade


def subject_grade(
    marks_obtained: Decimal | int | float,
    max_marks: Decimal | int | float,
    pass_marks: Decimal | int | float,
    config: GradingConfig | None = None,
) -> tuple[Decimal, str, bool]:
    """Compute per-subject percentage, grade, and pass status.

    :return: (percentage, grade, passed)
    """
    obt_dec = Decimal(str(marks_obtained))
    max_dec = Decimal(str(max_marks))
    pass_dec = Decimal(str(pass_marks))

    sub_pct = percentage(obt_dec, max_dec)
    passed = obt_dec >= pass_dec
    grade = grade_for_percentage(sub_pct, config)

    return sub_pct, grade, passed


def compute_result(
    entries: Sequence[SubjectResult],
    config: GradingConfig | None = None,
) -> ExamResultSummary:
    """Compute full examination result from subject entries.

    - Returns status 'INCOMPLETE' if any subject mark is None.
    - Returns status 'PASS' only if all subjects are passed and aggregate percentage >= 35.00%.
    - Returns status 'FAIL' and grade 'E' if any subject is failed.
    """
    cfg = config or DEFAULT_GRADING_CONFIG

    if not entries:
        raise ValueError("Cannot compute result for empty subjects list")

    total_max = sum((Decimal(str(e.max_marks)) for e in entries), Decimal("0"))
    evaluated_subjects: list[SubjectResult] = []
    has_missing = False

    for e in entries:
        if e.marks_obtained is None:
            has_missing = True
            evaluated_subjects.append(
                SubjectResult(
                    code=e.code,
                    name=e.name,
                    max_marks=Decimal(str(e.max_marks)),
                    pass_marks=Decimal(str(e.pass_marks)),
                    marks_obtained=None,
                    percentage=None,
                    grade=None,
                    passed=None,
                )
            )
        else:
            pct_val, gr_val, pass_val = subject_grade(
                e.marks_obtained, e.max_marks, e.pass_marks, config=cfg
            )
            evaluated_subjects.append(
                SubjectResult(
                    code=e.code,
                    name=e.name,
                    max_marks=Decimal(str(e.max_marks)),
                    pass_marks=Decimal(str(e.pass_marks)),
                    marks_obtained=Decimal(str(e.marks_obtained)),
                    percentage=pct_val,
                    grade=gr_val,
                    passed=pass_val,
                )
            )

    if has_missing:
        return ExamResultSummary(
            status="INCOMPLETE",
            total_obtained=None,
            total_max=total_max,
            percentage=None,
            grade=None,
            subjects=evaluated_subjects,
        )

    total_obtained = sum((s.marks_obtained for s in evaluated_subjects if s.marks_obtained is not None), Decimal("0"))
    overall_pct = percentage(total_obtained, total_max)

    all_passed = all(s.passed is True for s in evaluated_subjects)
    meets_min_overall = overall_pct >= cfg.min_overall_percentage

    if all_passed and meets_min_overall:
        status = "PASS"
        overall_grade = grade_for_percentage(overall_pct, cfg)
    else:
        status = "FAIL"
        overall_grade = cfg.fallback_grade

    return ExamResultSummary(
        status=status,
        total_obtained=total_obtained,
        total_max=total_max,
        percentage=overall_pct,
        grade=overall_grade,
        subjects=evaluated_subjects,
    )
