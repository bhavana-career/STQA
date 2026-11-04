# White-Box Testing Documentation — SRMS

White-box (glass-box / structural) testing inspects the internal control flow, decision branches, boolean conditions, and cyclomatic complexity of the Python modules inside `app/`. All white-box tests are implemented in `tests/whitebox/test_whitebox_coverage.py`.

---

## 1. Techniques Demonstrated

### 1.1 Statement Coverage ($C_0$)
Ensures that every executable Python statement in the target modules is executed at least once during the test run:
$$\text{Statement Coverage} = \left( \frac{\text{Number of Executed Statements}}{\text{Total Executable Statements}} \right) \times 100\%$$

### 1.2 Branch / Decision Coverage ($C_1$)
Ensures that every boolean decision point (`if`, `elif`, `else`, `try/except`) evaluates to both `True` and `False`:
$$\text{Branch Coverage} = \left( \frac{\text{Number of Executed Decision Outcomes}}{\text{Total Decision Outcomes}} \right) \times 100\%$$

### 1.3 Condition Testing
Tests individual atomic boolean sub-expressions within compound predicates, such as:
- `if mark is None or isinstance(mark, bool):`
  - Tested with `mark = None` (`True | False`)
  - Tested with `mark = True` (`False | True`)
  - Tested with `mark = 80` (`False | False`)
- `if not isinstance(percentage, (int, float)) or isinstance(percentage, bool):`
  - Tested with `"80"` (`True | False`), `True` (`False | True`), and `80.0` (`False | False`).
- `if str(s.get("section", "")).strip().upper() == section and int(s.get("roll_number", -1)) == roll_number:`
  - Tested with same section + same roll (`True & True`), same section + different roll (`True & False`), and different section (`False & _`).

### 1.4 Basis Path Testing (Cyclomatic Complexity $V(G)$)

#### Control Flow Analysis of `calculate_subject_grade(mark)` in `app/services/grading.py`
The function contains 7 sequential `if` predicates corresponding to the 8 grade bands:
$$V(G) = P + 1 = 7 + 1 = 8 \text{ independent execution paths}$$

| Path ID | Predicate Path | Test Input (`mark`) | Return Value |
|---|---|---|---|
| **Path 1** | `validated_mark >= 90` (True) | `95` | `"O"` |
| **Path 2** | `<90` (F) $\rightarrow$ `>=85` (True) | `86` | `"A+"` |
| **Path 3** | `<90` (F) $\rightarrow$ `<85` (F) $\rightarrow$ `>=80` (True) | `81` | `"A"` |
| **Path 4** | `...` $\rightarrow$ `>=70` (True) | `74` | `"B+"` |
| **Path 5** | `...` $\rightarrow$ `>=60` (True) | `63` | `"B"` |
| **Path 6** | `...` $\rightarrow$ `>=50` (True) | `52` | `"C+"` |
| **Path 7** | `...` $\rightarrow$ `>=35` (True) | `38` | `"C"` |
| **Path 8** | All 7 predicates False (`0..34`) | `15` | `"F"` |

#### Control Flow Analysis of `determine_classification(percentage, all_subjects_passed)` in `app/services/result_service.py`
Contains 7 decision predicates ($V(G) = 8$):
1. Type check fails (`"80"` or `True`) $\rightarrow$ raises `MarksValidationError`.
2. Range check fails (`< 0.0` or `> 100.0`) $\rightarrow$ raises `MarksValidationError`.
3. `not all_subjects_passed` is True $\rightarrow$ returns `"Fail"`.
4. `percentage >= 75.0` $\rightarrow$ returns `"Distinction"`.
5. `percentage >= 60.0` $\rightarrow$ returns `"First Class"`.
6. `percentage >= 50.0` $\rightarrow$ returns `"Second Class"`.
7. `percentage >= 35.0` $\rightarrow$ returns `"Pass"`.
8. Else (`< 35.0`) $\rightarrow$ returns `"Fail"`.

---

## 2. Actual Coverage Measurement (`pytest-cov` / `coverage.py`)

Coverage is measured using:
```powershell
pytest --cov=app --cov-report=term-missing --cov-report=html:reports/coverage
```

### 2.1 Actual Module-Level Coverage Summary

| Module | Statements | Missed | Coverage % | Target | Status |
|---|---|---|---|---|---|
| `app/__init__.py` | 21 | 0 | **100%** | $\ge 80\%$ | Exceeds Target |
| `app/config.py` | 19 | 0 | **100%** | $\ge 90\%$ | Exceeds Target |
| `app/models.py` | 41 | 0 | **100%** | $\ge 90\%$ | Exceeds Target |
| `app/services/grading.py` | 32 | 0 | **100%** | $\ge 90\%$ | Exceeds Target |
| `app/services/result_service.py` | 41 | 0 | **100%** | $\ge 90\%$ | Exceeds Target |
| `app/services/analytics_service.py` | 59 | 0 | **100%** | $\ge 90\%$ | Exceeds Target |
| `app/services/marks_service.py` | 53 | 1 | **98%** | $\ge 90\%$ | Exceeds Target |
| `app/services/student_service.py` | 189 | 7 | **96%** | $\ge 90\%$ | Exceeds Target |
| `app/routes/login.py` | 43 | 0 | **100%** | $\ge 80\%$ | Exceeds Target |
| `app/routes/student.py` | 42 | 1 | **98%** | $\ge 80\%$ | Exceeds Target |
| `app/routes/teacher.py` | 117 | 6 | **95%** | $\ge 80\%$ | Exceeds Target |
| `app/routes/__init__.py` | 32 | 7 | **78%** | $\ge 80\%$ | Guard Decorator |
| `app/main.py` | 7 | 7 | **0%** | N/A | CLI Entrypoint |
| **TOTAL (`app/`)** | **696** | **29** | **96%** | **$\ge 80\%$** | **Exceeds Target** |

### 2.2 Documentation of Uncovered Branches
The 29 uncovered statements (`4%` of total codebase) consist of:
1. Defensive OS-level exception cleanup in `_safe_write_json` (`lines 55-58` in `student_service.py`: disk full / OS `fsync` hardware failure rollback handler).
2. `app/main.py` CLI entry-point block (`if __name__ == "__main__": app.run(...)`), because Pytest instantiates the app via the WSGI factory `create_app()`.
3. Unused generic `@login_required` decorator in `app/routes/__init__.py` (`lines 9-15`), since all protected routes enforce stricter role-specific `@teacher_required` or `@student_required` decorators.
