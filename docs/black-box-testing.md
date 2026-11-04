# Black-Box Testing Documentation — SRMS

Black-box testing evaluates the Student Result Management System (SRMS) against its functional specifications without relying on internal code structure. All test cases documented here are implemented and executed in `tests/blackbox/test_blackbox_techniques.py`.

---

## 1. Equivalence Partitioning (EP)

Equivalence Partitioning divides the input domain of subject marks into classes of data from which test cases can be derived, such that every value in a partition is expected to be treated identically by the system.

### 1.1 Subject Marks Equivalence Partitions (`0–100` integer domain)

| Partition ID | Partition Type | Input Domain / Condition | Representative Test Value | Expected Validation | Expected Grade | Expected Status |
|---|---|---|---|---|---|---|
| **EP-01** | Valid | `90 <= mark <= 100` | `95` | Valid (`95`) | `O` | `Pass` |
| **EP-02** | Valid | `85 <= mark <= 89` | `87` | Valid (`87`) | `A+` | `Pass` |
| **EP-03** | Valid | `80 <= mark <= 84` | `82` | Valid (`82`) | `A` | `Pass` |
| **EP-04** | Valid | `70 <= mark <= 79` | `75` | Valid (`75`) | `B+` | `Pass` |
| **EP-05** | Valid | `60 <= mark <= 69` | `65` | Valid (`65`) | `B` | `Pass` |
| **EP-06** | Valid | `50 <= mark <= 59` | `55` | Valid (`55`) | `C+` | `Pass` |
| **EP-07** | Valid | `35 <= mark <= 49` | `42` | Valid (`42`) | `C` | `Pass` |
| **EP-08** | Valid | `0 <= mark <= 34` | `20` | Valid (`20`) | `F` | `Fail` |
| **EP-09** | Invalid | `mark < 0` (Negative) | `-25` | `MarksValidationError` | N/A | Rejected |
| **EP-10** | Invalid | `mark > 100` (Exceeds max) | `135` | `MarksValidationError` | N/A | Rejected |
| **EP-11** | Invalid | Missing / Empty / Non-integer | `None`, `""`, `"eighty"`, `75.5` | `MarksValidationError` | N/A | Rejected |

---

## 2. Boundary Value Analysis (BVA)

Boundary Value Analysis targets the exact edges of each equivalence partition (`min - 1`, `min`, `min + 1`, `max - 1`, `max`, `max + 1`) where off-by-one defects (`<` vs `<=`) most frequently occur.

### 2.1 Complete BVA Test Matrix (34 Boundary Test Points)

| Boundary Cluster | Test Values (`N-1, N, N+1`) | Expected Outcome |
|---|---|---|
| **Lower Domain Boundary (`0`)** | `-1`, `0`, `1` | `-1` $\rightarrow$ Rejected (`MarksValidationError`); `0` $\rightarrow$ Grade `F` (`Fail`); `1` $\rightarrow$ Grade `F` (`Fail`) |
| **Pass / Fail & `F` $\leftrightarrow$ `C` (`34 / 35`)** | `33`, `34`, `35`, `36` | `33, 34` $\rightarrow$ Grade `F` (`Fail`); `35, 36` $\rightarrow$ Grade `C` (`Pass`) |
| **`C` $\leftrightarrow$ `C+` (`49 / 50`)** | `48`, `49`, `50`, `51` | `48, 49` $\rightarrow$ Grade `C` (`Pass`); `50, 51` $\rightarrow$ Grade `C+` (`Pass`) |
| **`C+` $\leftrightarrow$ `B` (`59 / 60`)** | `58`, `59`, `60`, `61` | `58, 59` $\rightarrow$ Grade `C+` (`Pass`); `60, 61` $\rightarrow$ Grade `B` (`Pass`) |
| **`B` $\leftrightarrow$ `B+` (`69 / 70`)** | `68`, `69`, `70`, `71` | `68, 69` $\rightarrow$ Grade `B` (`Pass`); `70, 71` $\rightarrow$ Grade `B+` (`Pass`) |
| **`B+` $\leftrightarrow$ `A` (`79 / 80`)** | `78`, `79`, `80`, `81` | `78, 79` $\rightarrow$ Grade `B+` (`Pass`); `80, 81` $\rightarrow$ Grade `A` (`Pass`) |
| **`A` $\leftrightarrow$ `A+` (`84 / 85`)** | `83`, `84`, `85`, `86` | `83, 84` $\rightarrow$ Grade `A` (`Pass`); `85, 86` $\rightarrow$ Grade `A+` (`Pass`) |
| **`A+` $\leftrightarrow$ `O` (`89 / 90`)** | `88`, `89`, `90`, `91` | `88, 89` $\rightarrow$ Grade `A+` (`Pass`); `90, 91` $\rightarrow$ Grade `O` (`Pass`) |
| **Upper Domain Boundary (`100`)** | `99`, `100`, `101` | `99, 100` $\rightarrow$ Grade `O` (`Pass`); `101` $\rightarrow$ Rejected (`MarksValidationError`) |

---

## 3. Decision Table Testing

### 3.1 Decision Table 1: Login Validation

| Conditions / Actions | Rule 1 | Rule 2 | Rule 3 | Rule 4 | Rule 5 |
|---|---|---|---|---|---|
| **C1: Username exists in system?** | Yes (Teacher) | Yes (Student) | Yes | No | Empty (`""`) |
| **C2: Password matches record?** | Yes | Yes | No | — | — |
| **A1: Authenticate session?** | Yes (`role=teacher`) | Yes (`role=student`) | No | No | No |
| **A2: Redirect destination** | `/teacher/dashboard` | `/student/dashboard` | `/login` (`401`) | `/login` (`401`) | `/login` (`401`) |

### 3.2 Decision Table 2: Subject Pass/Fail & Overall Result Determination

| Conditions / Actions | Rule 1 | Rule 2 | Rule 3 | Rule 4 | Rule 5 (Critical Rule) | Rule 6 |
|---|---|---|---|---|---|---|
| **C1: All 6 subjects `>= 35`?** | Yes | Yes | Yes | Yes | **No (1+ subj `< 35`)** | **No (All `< 35`)** |
| **C2: Aggregate Percentage** | `>= 75.0%` | `60.0–74.99%` | `50.0–59.99%` | `35.0–49.99%` | `>= 75.0%` (e.g. `89%`) | `< 35.0%` |
| **A1: Overall Status** | `PASS` | `PASS` | `PASS` | `PASS` | **`FAIL`** | **`FAIL`** |
| **A2: Overall Classification** | `Distinction` | `First Class` | `Second Class` | `Pass` | **`Fail`** | **`Fail`** |
| **A3: Highlight Failed Subjects** | None | None | None | None | List failed subject(s) | List all 6 subjects |

### 3.3 Decision Table 3: Result Announcement Popup Behaviour

| Conditions / Actions | Rule 1 | Rule 2 | Rule 3 | Rule 4 |
|---|---|---|---|---|
| **C1: Student passed all 6 subjects?** | Yes | Yes | No | No |
| **C2: Popup already shown in current session?** | No | Yes | No | Yes |
| **A1: Display Celebratory Popup (`#resultSuccessPopup`)?** | **Yes** | **No** | **No** | **No** |
| **A2: Set `session["popup_shown"] = True`?** | Yes | Remains True | No | No |

### 3.4 Decision Table 4: Student & Teacher Role Access Permissions

| Conditions / Actions | Rule 1 (Logged Out) | Rule 2 (Student Own Record) | Rule 3 (Student Other Record) | Rule 4 (Student $\rightarrow$ Teacher Route) | Rule 5 (Teacher $\rightarrow$ Teacher Route) |
|---|---|---|---|---|---|
| **C1: Session Role** | `None` | `student` (`STU001`) | `student` (`STU001`) | `student` (`STU001`) | `teacher` (`teacher01`) |
| **C2: Target Endpoint** | Any protected route | `/student/view/STU001` | `/student/view/STU002` | `/teacher/*` | `/teacher/*` |
| **A1: HTTP Response** | `302 Redirect` $\rightarrow$ `/login` | `200 OK` | `403 Forbidden` | `403 Forbidden` | `200 OK` |
