# Software Requirements Specification (SRS) — Student Result Management System (SRMS)

## 1. Project Introduction
The **Student Result Management System (SRMS)** is a locally hosted web application designed for managing, calculating, analyzing, and publishing Class 10 Secondary Board Examination results. Built as an academic Software Testing and Quality Assurance (STQA) reference system, SRMS pairs a clean, modular Flask architecture with a comprehensive automated testing suite covering Unit, Black-Box, White-Box, Functional, Integration, and End-to-End (Selenium WebDriver) verification.

## 2. Problem Statement
Manual compilation of secondary school examination marks is error-prone, particularly when enforcing multi-rule grading schemes where:
1. Individual subject grades follow an 8-tier grading matrix (`O` down to `F`).
2. Overall classification depends on both aggregate percentage and a strict mandatory pass criterion across all six subjects (scoring `< 35` in even a single subject must override a high aggregate percentage and result in an overall `FAIL`).
3. Section-wise class analytics must be computed accurately without cross-contaminating student cohorts across Sections A, B, and C.

## 3. Objectives
- Automate calculation of total marks (out of 600), percentages (rounded to two decimal places), subject-wise grades, and overall result classification.
- Enforce role-based access control separating **Teacher** administrative operations from **Student** result viewing.
- Persist all student records and marks reliably in local JSON files using atomic file-write patterns without requiring external databases or cloud services.
- Provide verifiable, repeatable automated test suites demonstrating formal STQA methodologies.

## 4. Scope
- **In Scope:**
  - Preassigned local authentication for Teacher and Student roles.
  - Full Student CRUD (Create, Read, Search, Filter by Section, Update, Delete) by Teachers.
  - Subject marks entry and validation across six Class 10 subjects (`Physics`, `Chemistry`, `Mathematics`, `Computer Science`, `Kannada`, `English`).
  - Automatic calculation engine and critical single-subject fail override rule.
  - One-time per-session celebratory popup on the Student Dashboard for passing students.
  - Independent section-wise analytics (`Section A`, `Section B`, `Section C`) with visual bar charts.
- **Out of Scope:**
  - External relational/NoSQL databases, Docker containers, cloud deployment, user self-registration, and password reset workflows.

## 5. Functional Requirements

| Req ID | Requirement Title | Description |
|---|---|---|
| **FR-01** | Role-Based Login | Authenticate teachers and students using predefined credentials (`teachers.json`, `students.json`) and redirect to role-specific dashboards. |
| **FR-02** | Access Control & Isolation | Prevent unauthenticated access to protected routes (`302` redirect to login), prevent students from accessing teacher routes (`403 Forbidden`), and prevent students from viewing other students' records (`403 Forbidden`). |
| **FR-03** | Student CRUD Operations | Allow teachers to create, view, search (by name/ID), filter (by section A/B/C), update, and delete student records with immediate JSON persistence. |
| **FR-04** | Marks Validation | Validate each of the 6 subject marks as an integer in `[0, 100]`. Reject negative numbers, marks `> 100`, decimals, booleans, non-numeric strings, and empty inputs. |
| **FR-05** | Marks Calculation Engine | Automatically compute `Total Marks = sum(6 subjects)` out of `600` and `Percentage = round((Total / 600) * 100, 2)`. |
| **FR-06** | Individual Subject Grading | Assign subject grades: `O` (90–100), `A+` (85–89), `A` (80–84), `B+` (70–79), `B` (60–69), `C+` (50–59), `C` (35–49), `F` (0–34). |
| **FR-07** | Overall Classification & Critical Rule | Assign `Distinction` (≥75%), `First Class` (60–74.99%), `Second Class` (50–59.99%), `Pass` (35–49.99%), or `Fail` (<35%). If any single subject has `< 35` marks, overall status MUST be `FAIL` and classification MUST be `Fail`. |
| **FR-08** | Result Announcement Popup | Display a celebratory popup on the Student Dashboard only if the student passes all 6 subjects, and only once per login session. |
| **FR-09** | Section-Wise Class Analytics | Calculate student count, average total, average percentage, subject-wise averages, pass/fail counts, and distinction counts strictly for the selected section (`A`, `B`, or `C`). |

## 6. Non-Functional Requirements
- **NFR-01 (Data Integrity):** JSON writes must use temporary files and atomic `os.replace()` with `os.fsync()` so interrupted operations never corrupt `students.json`.
- **NFR-02 (Testability):** Business logic must be decoupled into pure service modules (`marks_service.py`, `grading.py`, `result_service.py`, `student_service.py`, `analytics_service.py`) testable independently of HTTP or browser layers.
- **NFR-03 (Performance):** Marks calculation and JSON persistence must complete in `< 50 ms` for typical classroom datasets.
- **NFR-04 (Usability & Accessibility):** Responsive layout with high-contrast status badges, password visibility toggle, and confirmation prompts before record deletion.

## 7. User Roles
1. **Teacher (`teacher01`):** Full access to Dashboard Overview, Student Management (CRUD), Marks Management, individual Student Result Cards, and Class Analytics.
2. **Student (`student01`, `student02`, `student03`, etc.):** Read-only access strictly restricted to their own Dashboard, Result Card, and Official Grading Matrix.

## 8. Technical Constraints
- Runs strictly on `127.0.0.1` (localhost) using Python 3.11+ and Flask.
- Zero external databases (no SQLite, PostgreSQL, MySQL, MongoDB, Firebase, or Supabase).
- Zero containerization or cloud dependencies (no Docker, Cloudflare, or external OAuth).

## 9. Assumptions
- Each Class 10 student is enrolled in Section `A`, `B`, or `C` and takes all six mandatory subjects.
- Preassigned credentials are distributed by the school examination coordinator.
