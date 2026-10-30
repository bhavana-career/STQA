# Exercise 1: Division Program, Intentional Defect Injection & SDLC Testing Comparison

---

## 1. Exercise Objective

1. Implement a simple, pure mathematical division program.
2. Formulate test cases demonstrating an intentional fault: **division by zero (DEF-006)**.
3. Provide an isolated faulty implementation and a defensive, robust corrected implementation.
4. Execute tests and record before-and-after evidence.
5. Provide a critical, structured comparison of Software Development Life Cycle (SDLC) models—specifically **Waterfall** versus **Agile**—with explicit emphasis on their implications for Software Testing and Quality Assurance (STQA).

---

## 2. Implementation Overview

To isolate intentional defects from production code, the exercise code is partitioned cleanly into:
- Faulty Implementation: [`academic/division/faulty.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/division/faulty.py)
- Corrected Implementation: [`academic/division/corrected.py`](file:///c:/Users/bhava/Downloads/ST&QA/academic/division/corrected.py)

### 2.1 Faulty Implementation (`faulty.py`)
```python
def divide_faulty(a: float, b: float) -> float:
    """Faulty division without zero guarding or proper input type handling."""
    # Defect: Directly divides without checking if b == 0, causing unhandled crash
    return a / b
```

### 2.2 Corrected Implementation (`corrected.py`)
```python
def divide(a: float, b: float) -> float:
    """Safely divide a by b with defensive type checking and zero-divisor guard."""
    if isinstance(a, bool) or isinstance(b, bool):
        raise TypeError("Operands must be numeric (int or float), not boolean")
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Operands must be numeric (int or float)")
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

---

## 3. Test Cases (TC-ACAD-01 & TC-ACAD-02)

| Test Case ID | Test Category | Operand A (`a`) | Operand B (`b`) | Expected Result | Status | Automated Test Location |
|---|---|---|---|---|---|---|
| **TC-ACAD-01-F** | Fault Demonstration | `10` | `0` | Raises domain `ValueError("Cannot divide by zero")` | **FAILS on faulty** (Crashes with `ZeroDivisionError`) | `fault_injection/tests/test_failing_faults.py::test_def_006_failing_on_division_by_zero` |
| **TC-ACAD-02-01** | Equivalence - Positive | `10` | `2` | `5.0` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |
| **TC-ACAD-02-02** | Equivalence - Negative | `-9` | `3` | `-3.0` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |
| **TC-ACAD-02-03** | Equivalence - Decimal | `7` | `2` | `3.5` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |
| **TC-ACAD-02-04** | Boundary - Zero Dividend | `0` | `5` | `0.0` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |
| **TC-ACAD-02-05** | Boundary - Zero Divisor | `10` | `0` | Raises `ValueError("Cannot divide by zero")` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |
| **TC-ACAD-02-06** | Invalid Type - String | `"abc"` | `2` | Raises `TypeError` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |
| **TC-ACAD-02-07** | Invalid Type - None | `None` | `2` | Raises `TypeError` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |
| **TC-ACAD-02-08** | Invalid Type - Boolean | `True` | `2` | Raises `TypeError` | **PASS** | `academic/tests/test_academic_exercises.py::TestExercise1Division` |

---

## 4. Execution Evidence & Defect Lifecycle (DEF-006)

### Before Fix (Faulty Code Execution)
- **Command:** `pytest fault_injection/tests/test_failing_faults.py -k test_def_006`
- **Output:**
  ```text
  fault_injection\tests\test_failing_faults.py:60: 
  >       divide_faulty(10, 0)
  E       ZeroDivisionError: division by zero
  FAILED fault_injection/tests/test_failing_faults.py::test_def_006_failing_on_division_by_zero
  ```
- **Evidence File:** [`docs/evidence/faults/DEF-006-before.txt`](file:///c:/Users/bhava/Downloads/ST&QA/docs/evidence/faults/DEF-006-before.txt)

### After Fix (Corrected Code Execution)
- **Command:** `pytest tests/unit/test_fault_demo.py -k test_def_006 -v`
- **Output:**
  ```text
  tests/unit/test_fault_demo.py::TestDefect006DivisionByZero::test_def_006_faulty_crashes_with_zero_division_error PASSED [ 50%]
  tests/unit/test_fault_demo.py::TestDefect006DivisionByZero::test_def_006_corrected_implementation_passes PASSED [100%]
  ======================= 2 passed in 0.05s =======================
  ```
- **Evidence File:** [`docs/evidence/faults/DEF-006-after.txt`](file:///c:/Users/bhava/Downloads/ST&QA/docs/evidence/faults/DEF-006-after.txt)

---

## 5. Structured SDLC Comparison: Waterfall vs. Agile in STQA

The choice of Software Development Life Cycle model fundamentally alters how quality assurance is structured, when defects are detected, and the economic cost of defect resolution.

```
Cost of Defect Resolution across SDLC Phases (Boehm's Curve):
Requirements ($1x) -> Design ($5x) -> Coding ($10x) -> Integration/System Test ($50x) -> Production ($100x+)
```

### 5.1 Comparative Dimensions Matrix

| Dimension | Classical Waterfall Model | Agile (Scrum / Extreme Programming) |
|---|---|---|
| **Testing Philosophy** | Verification at the end of the development lifecycle ("Big-Bang" phase). Quality is inspected into the product. | Continuous Quality Assurance. Quality is baked into the product via TDD, CI/CD, and peer reviews. |
| **Requirements Evolution** | Frozen upfront in SRS document. Changes require formal Change Requests (CR) and extensive impact analysis. | Iterative and emergent. Captured as User Stories with clear Acceptance Criteria in a dynamic backlog. |
| **Test Planning Timing** | Test Plan and Test Cases written during or after architectural design, executed months later. | Test cases and automated scenarios written concurrently with or before code (TDD / BDD). |
| **Defect Detection Timing** | Late in the lifecycle (during the formal System Testing phase). High defect latency. | Early in the lifecycle (at unit test, pull-request, and sprint-demo levels). Low defect latency. |
| **Cost of Defect Fixing** | **Exponentially high**. Architectural defects found in System Testing require rewriting large swaths of code. | **Linear and low**. Defects are captured within hours of introduction by automated test suites. |
| **QA Role Definition** | Segregated Quality Control (QC) department acting as gatekeepers before release. | Integrated QA Engineers embedded in cross-functional squads collaborating with developers. |
| **Automation Strategy** | Often manual regression testing or delayed automation passes created post-implementation. | Test automation pyramid (70% Unit, 20% Integration, 10% E2E) run on every Git commit in CI. |
| **Documentation & Artifacts**| Heavyweight: IEEE 829 Test Plans, Formal Test Logs, Traceability Matrices, Sign-off Memos. | Living documentation: Executable specifications, automated test reports, markdown test plans. |
| **Suitability for SRMS** | Inappropriate: User feedback on result calculation and teacher workflow would arrive too late. | Highly suited: Facilitated incremental milestone delivery (M1 -> M8) with 100% regression verification. |

### 5.2 Academic Conclusion & Lesson Learned
In Exercise 1, defect **DEF-006** represents an elementary edge-case omission. Under a Waterfall methodology, if unit testing is neglected or conducted manually without strict edge-case verification, this unhandled division by zero could cascade into production web endpoints, crashing server threads when computing percentages with 0 total marks. 
Under Agile and Test-Driven Development (TDD), the failing test case is formulated *first*, ensuring the defensive guard is incorporated before the code is merged to main.
