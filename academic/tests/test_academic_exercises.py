"""Academic STQA Unit & Integration Test Suite covering Exercises 1–6."""
from __future__ import annotations

from decimal import Decimal
import pytest

from academic.division.corrected import safe_divide
from academic.division.faulty import divide_faulty
from academic.age_validator import validate_age, AgeValidationError
from academic.atm import (
    Account,
    ATMController,
    CardLockedError,
    DailyLimitExceededError,
    InsufficientFundsError,
    InvalidAmountError,
    InvalidPINError,
)
from academic.coverage_demo import classify_number
from academic.metrics import (
    DefectDensityMetric,
    ProductivityMetric,
    compute_assignment_sample_metrics,
    compare_sdlc_models,
)
from academic.top_down_integration import (
    GradeModuleStub,
    MarksRepositoryStub,
    RealGradeModule,
    RealInMemoryMarksRepository,
    ReportModule,
)


# ============================================================================
# Exercise 1 Tests: Division & SDLC
# ============================================================================

class TestExercise1Division:
    """Tests for Exercise 1: Division validation and SDLC models."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (10, 2, Decimal("5.0000")),
            (-9, 3, Decimal("-3.0000")),
            (7, 2, Decimal("3.5000")),
            (0, 5, Decimal("0.0000")),
            ("22", "7", Decimal("3.1429")),
        ],
    )
    def test_tc_acad_02_corrected_division_valid_inputs(self, a, b, expected):
        """TC-ACAD-02: Corrected division handles integers, decimals, and negative values cleanly."""
        assert safe_divide(a, b) == expected

    def test_tc_acad_02_division_by_zero_raises_value_error(self):
        """TC-ACAD-02: Division by zero raises domain-specific ValueError with informative message."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            safe_divide(10, 0)

    @pytest.mark.parametrize("invalid_input", ["abc", None, [], {}])
    def test_tc_acad_02_non_numeric_raises_type_error(self, invalid_input):
        """TC-ACAD-02: Malformed or non-numeric inputs raise TypeError."""
        with pytest.raises(TypeError, match="Invalid numeric input"):
            safe_divide(invalid_input, 2)

    def test_sdlc_comparison_metrics(self):
        """Verifies Agile vs Waterfall timeline models."""
        models = compare_sdlc_models(120)
        assert "Waterfall" in models
        assert "Agile" in models
        assert models["Waterfall"]["total_duration_weeks"] == "24 weeks"
        assert models["Agile"]["total_duration_weeks"] == "12 weeks (6 sprints of 2 weeks each)"


# ============================================================================
# Exercise 3 Tests: Age Field EP & BVA
# ============================================================================

class TestExercise3AgeValidation:
    """Tests for Exercise 3: Age Field Validation (18–60) via EP and BVA."""

    @pytest.mark.parametrize(
        ("age_input", "expected_age"),
        [
            (18, 18),        # BVA Minimum boundary
            (19, 19),        # BVA Just above minimum
            (35, 35),        # EP Nominal valid
            (59, 59),        # BVA Just below maximum
            (60, 60),        # BVA Maximum boundary
            ("18", 18),      # Valid numeric string
            ("60", 60),      # Valid numeric string
            (45.0, 45),      # Integral float
        ],
    )
    def test_tc_acad_03_valid_age_boundaries_and_partitions(self, age_input, expected_age):
        """TC-ACAD-03: Valid age inputs within [18, 60] are parsed successfully."""
        assert validate_age(age_input) == expected_age

    @pytest.mark.parametrize(
        "invalid_age",
        [
            17,      # BVA Just below minimum (18 - 1)
            16,      # EP Below range
            0,       # EP Zero
            -1,      # EP Negative
            61,      # BVA Just above maximum (60 + 1)
            75,      # EP Above range
            "17",    # BVA string below
            "61",    # BVA string above
        ],
    )
    def test_tc_acad_03_out_of_range_age_rejected(self, invalid_age):
        """TC-ACAD-03: Values outside [18, 60] fail validation with range errors."""
        with pytest.raises(AgeValidationError):
            validate_age(invalid_age)

    @pytest.mark.parametrize(
        "malformed_input",
        [
            "",          # Blank empty string
            "   ",       # Whitespace
            None,        # NoneType
            True,        # Boolean
            False,       # Boolean
            "abc",       # Non-numeric string
            "18.5",      # Decimal string
            25.5,        # Non-integral float
            [25],        # Array
        ],
    )
    def test_tc_acad_03_malformed_age_rejected(self, malformed_input):
        """TC-ACAD-03: Non-numeric, boolean, empty, and decimal inputs fail validation."""
        with pytest.raises(AgeValidationError):
            validate_age(malformed_input)


# ============================================================================
# Exercise 4 Tests: Statement vs Branch Coverage & ATM
# ============================================================================

class TestExercise4CoverageAndATM:
    """Tests for Exercise 4: Statement/Branch coverage demo and ATM black-box cases."""

    def test_tc_acad_05_coverage_subsets(self):
        """TC-ACAD-05: Demonstrates statement vs branch coverage distinction on classify_number."""
        # Test Suite A: Covers every line (1, 2, 3, 4, 5, 6) -> 100% Statement Coverage
        assert classify_number(5, True) == "positive-flagged"
        assert classify_number(5, False) == "positive-unflagged"

        # Test Suite B: Adds negative value to take False branch of Decision 1 -> 100% Branch Coverage
        assert classify_number(-1, False) == "non-positive"

    def test_tc_acad_04_atm_valid_withdrawal(self):
        """TC-ACAD-04: Valid withdrawal within limits deducts balance and updates daily total."""
        acc = Account(account_number="1001", pin="1234", balance=15000)
        atm = ATMController(acc)

        new_bal = atm.withdraw(amount=2500, entered_pin="1234")
        assert new_bal == 12500
        assert acc.balance == 12500
        assert acc.daily_withdrawn == 2500

    def test_tc_acad_04_atm_insufficient_funds_rejected(self):
        """TC-ACAD-04: Withdrawal exceeding balance is rejected without mutating state."""
        acc = Account(account_number="1001", pin="1234", balance=1000)
        atm = ATMController(acc)

        with pytest.raises(InsufficientFundsError):
            atm.withdraw(amount=2000, entered_pin="1234")
        assert acc.balance == 1000
        assert acc.daily_withdrawn == 0

    @pytest.mark.parametrize(
        "invalid_amount",
        [
            50,     # Below minimum Rs. 100
            150,    # Not multiple of 100
            10500,  # Exceeds per-transaction limit Rs. 10,000
            -500,   # Negative
            0,      # Zero
        ],
    )
    def test_tc_acad_04_atm_invalid_amount_rules_rejected(self, invalid_amount):
        """TC-ACAD-04: Amounts violating minimums, multiples of 100, or transaction caps are rejected."""
        acc = Account(account_number="1001", pin="1234", balance=50000)
        atm = ATMController(acc)

        with pytest.raises(InvalidAmountError):
            atm.withdraw(amount=invalid_amount, entered_pin="1234")

    def test_tc_acad_04_atm_daily_limit_enforced(self):
        """TC-ACAD-04: Cumulative withdrawals exceeding Rs. 20,000 daily limit are blocked."""
        acc = Account(account_number="1001", pin="1234", balance=50000, daily_withdrawn=15000)
        atm = ATMController(acc)

        # Attempting 6000 would result in 15000 + 6000 = 21000 > 20000
        with pytest.raises(DailyLimitExceededError):
            atm.withdraw(amount=6000, entered_pin="1234")

        # Withdrawing 5000 exactly reaches 20000 limit
        new_bal = atm.withdraw(amount=5000, entered_pin="1234")
        assert new_bal == 45000
        assert acc.daily_withdrawn == 20000

    def test_tc_acad_04_atm_pin_lockout_after_3_attempts(self):
        """TC-ACAD-04: 3 consecutive invalid PIN attempts permanently lock the card."""
        acc = Account(account_number="1001", pin="1234", balance=5000)
        atm = ATMController(acc)

        with pytest.raises(InvalidPINError):
            atm.verify_pin("9999")  # Attempt 1
        assert not acc.is_locked

        with pytest.raises(InvalidPINError):
            atm.verify_pin("8888")  # Attempt 2
        assert not acc.is_locked

        with pytest.raises(CardLockedError):
            atm.verify_pin("7777")  # Attempt 3 -> Locked
        assert acc.is_locked

        # Subsequent attempts are immediately rejected as locked
        with pytest.raises(CardLockedError):
            atm.verify_pin("1234")


# ============================================================================
# Exercise 5 Tests: Top-Down Integration Sequence
# ============================================================================

class TestExercise5TopDownIntegration:
    """Tests for Exercise 5: Hierarchical Top-Down Integration with Stubs."""

    def test_tc_acad_06_step_1_report_module_with_stubs(self):
        """Step 1: Test ReportModule in isolation using GradeModuleStub and MarksRepositoryStub."""
        repo_stub = MarksRepositoryStub()
        grade_stub = GradeModuleStub(stub_status="PASS", stub_grade="A2")

        orchestrator = ReportModule(marks_repo=repo_stub, grade_module=grade_stub)
        report = orchestrator.generate_student_report(student_id=1, student_name="Alice")

        assert report["student_name"] == "Alice"
        assert report["status"] == "PASS"
        assert report["grade"] == "A2"
        assert report["percentage"] == "85.00%"
        assert report["subject_count"] == "2"

    def test_tc_acad_06_step_2_real_grading_with_repo_stub(self):
        """Step 2: Replace GradeModuleStub with real GradeModule, keeping MarksRepositoryStub."""
        repo_stub = MarksRepositoryStub([
            {"subject": "ENG", "max": Decimal("100"), "obtained": Decimal("85.00")},
            {"subject": "MAT", "max": Decimal("100"), "obtained": Decimal("95.00")},
        ])
        real_grading = RealGradeModule()

        orchestrator = ReportModule(marks_repo=repo_stub, grade_module=real_grading)
        report = orchestrator.generate_student_report(student_id=1, student_name="Alice")

        # 180 / 200 = 90.00% -> Grade A1
        assert report["status"] == "PASS"
        assert report["grade"] == "A1"
        assert report["percentage"] == "90.00%"

    def test_tc_acad_06_step_3_full_integration(self):
        """Step 3: Replace MarksRepositoryStub with real in-memory repository (fully integrated)."""
        real_repo = RealInMemoryMarksRepository()
        real_grading = RealGradeModule()

        # Seed data into real repository
        real_repo.save_student_marks(
            student_id=42,
            marks=[
                {"subject": "ENG", "max": Decimal("100"), "obtained": Decimal("75.00")},
                {"subject": "SCI", "max": Decimal("100"), "obtained": Decimal("30.00")},  # Failed subject
            ],
        )

        orchestrator = ReportModule(marks_repo=real_repo, grade_module=real_grading)
        report = orchestrator.generate_student_report(student_id=42, student_name="Bob")

        # Total 105 / 200 = 52.50%, but failed Science (< 35%) -> Overall FAIL, Grade E
        assert report["status"] == "FAIL"
        assert report["grade"] == "E"
        assert report["percentage"] == "52.50%"


# ============================================================================
# Exercise 6 Tests: Software Metrics Calculations
# ============================================================================

class TestExercise6SoftwareMetrics:
    """Tests for Exercise 6: Defect density and productivity metrics."""

    def test_assignment_sample_metrics_exact_values(self):
        """Verify calculations on assignment sample: 100 KLOC, 50 defects, 500 effort hours."""
        metrics = compute_assignment_sample_metrics()

        # 50 defects / 100 KLOC = 0.5 defects/KLOC
        assert metrics["defect_density_per_kloc"] == "0.5000 defects/KLOC"
        # 100,000 LOC / 500 hours = 200 LOC/hour
        assert metrics["loc_productivity"] == "200.00 LOC/person-hour"
        # 50 defects / 500 hours = 0.1 defects/hour
        assert metrics["defect_detection_rate"] == "0.1000 defects/hour"
        # 500 hours / 50 defects = 10 hours/defect
        assert metrics["hours_per_defect"] == "10.00 hours/defect"

    def test_metrics_handles_zero_safely(self):
        """Zero values do not trigger divide-by-zero crashes."""
        dd = DefectDensityMetric(total_defects=0, lines_of_code=0)
        assert dd.density == Decimal(0)

        prod = ProductivityMetric(lines_of_code=0, total_defects=0, total_effort_hours=Decimal(0))
        assert prod.loc_per_hour == Decimal(0)
        assert prod.defects_per_hour == Decimal(0)
