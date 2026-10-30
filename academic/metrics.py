"""Exercises 5 & 6: Software Testing Metrics and SDLC Estimation Models.

Implements standard IEEE/ISO software metrics:
1. Defect Density (Defects / KLOC)
2. Testing & Developer Productivity (LOC / Person-Hour, Defects Found / Hour)
3. Agile vs. Waterfall Timeline Estimations and Defect Discovery Profiles
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List


@dataclass
class DefectDensityMetric:
    """Calculates defect density per KLOC."""
    total_defects: int
    lines_of_code: int

    @property
    def kloc(self) -> Decimal:
        return Decimal(self.lines_of_code) / Decimal(1000)

    @property
    def density(self) -> Decimal:
        if self.kloc == 0:
            return Decimal(0)
        return round(Decimal(self.total_defects) / self.kloc, 4)


@dataclass
class ProductivityMetric:
    """Calculates team velocity and defect detection productivity."""
    lines_of_code: int
    total_defects: int
    total_effort_hours: Decimal

    @property
    def loc_per_hour(self) -> Decimal:
        """Development output rate (LOC per person-hour)."""
        if self.total_effort_hours == 0:
            return Decimal(0)
        return round(Decimal(self.lines_of_code) / self.total_effort_hours, 2)

    @property
    def defects_per_hour(self) -> Decimal:
        """Defect detection rate (Defects found per testing hour)."""
        if self.total_effort_hours == 0:
            return Decimal(0)
        return round(Decimal(self.total_defects) / self.total_effort_hours, 4)

    @property
    def hours_per_defect(self) -> Decimal:
        """Average testing effort spent to detect one defect."""
        if self.total_defects == 0:
            return Decimal(0)
        return round(self.total_effort_hours / Decimal(self.total_defects), 2)


def compute_assignment_sample_metrics() -> Dict[str, str]:
    """Computes exact metrics for the assignment's benchmark values:

    Given:
    - 100 KLOC (100,000 Lines of Code)
    - 50 Defects detected
    - 500 Effort hours
    """
    dd = DefectDensityMetric(total_defects=50, lines_of_code=100000)
    prod = ProductivityMetric(lines_of_code=100000, total_defects=50, total_effort_hours=Decimal(500))

    return {
        "kloc": str(dd.kloc),
        "defects": "50",
        "effort_hours": "500",
        "defect_density_per_kloc": f"{dd.density} defects/KLOC",
        "loc_productivity": f"{prod.loc_per_hour} LOC/person-hour",
        "defect_detection_rate": f"{prod.defects_per_hour} defects/hour",
        "hours_per_defect": f"{prod.hours_per_defect} hours/defect",
    }


def compare_sdlc_models(total_scope_story_points: int = 120) -> Dict[str, Dict[str, str]]:
    """Compare Agile (Scrum) vs Waterfall timelines and defect cost-of-change.

    For a 120 Story Point / 100 KLOC system:
    - Waterfall: 5 sequential phases with Big-Bang testing at Phase 4.
    - Agile: 6 incremental two-week sprints with in-sprint automated testing.
    """
    return {
        "Waterfall": {
            "total_duration_weeks": "24 weeks",
            "phases": "Requirements (4w) -> Design (4w) -> Coding (8w) -> Testing (6w) -> Deployment (2w)",
            "first_test_execution": "Week 17 (Phase 4)",
            "defect_feedback_loop": "16 weeks delay between injection and detection",
            "defect_remediation_cost_multiplier": "15x - 30x (late-phase rework)",
            "working_software_delivery": "Week 24 (End of project)",
        },
        "Agile": {
            "total_duration_weeks": "12 weeks (6 sprints of 2 weeks each)",
            "sprint_cadence": "Sprint Planning -> Daily Standup -> In-sprint TDD/CI -> Review -> Retrospective",
            "first_test_execution": "Day 1 (automated unit/TDD suites)",
            "defect_feedback_loop": "Minutes/Hours (continuous integration and pre-commit hooks)",
            "defect_remediation_cost_multiplier": "1x - 2x (fixed in-sprint)",
            "working_software_delivery": "Every 2 weeks (potentially shippable increment)",
        },
    }
