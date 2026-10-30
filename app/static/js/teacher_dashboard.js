(function () {
    const csrfTokenEl = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenEl ? csrfTokenEl.getAttribute("content") : "";
    const backdrop = document.getElementById("marks-modal-backdrop");
    const modal = document.getElementById("marks-modal");
    const closeBtn = document.getElementById("marks-modal-close-btn");
    const cancelBtn = document.getElementById("btn-marks-cancel");
    const saveBtn = document.getElementById("btn-save-marks");

    const loadingDiv = document.getElementById("students-loading");
    const errorDiv = document.getElementById("students-error");
    const tableContainer = document.getElementById("students-table-container");
    const tbody = document.getElementById("students-table-body");

    let currentStudentId = null;
    let currentExamId = null;
    let lastFocusedElement = null;
    let initialMarksValues = {};

    function getModalFocusableElements() {
        if (!modal) return [];
        return modal.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
    }

    // Fetch students on page load
    loadStudents();

    async function loadStudents() {
        if (!loadingDiv || !tableContainer) return;
        loadingDiv.style.display = "block";
        errorDiv.style.display = "none";
        tableContainer.style.display = "none";

        try {
            const response = await fetch("/api/teacher/students", {
                headers: { "Accept": "application/json" }
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error?.message || "Failed to load students.");
            }

            const data = await response.json();
            currentExamId = data.exam.id;
            renderStudents(data.students);
        } catch (err) {
            loadingDiv.style.display = "none";
            errorDiv.textContent = err.message;
            errorDiv.style.display = "block";
        }
    }

    function renderStudents(students) {
        loadingDiv.style.display = "none";
        tableContainer.style.display = "block";
        tbody.innerHTML = "";

        if (students.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--muted-color); padding: 2.5rem;">
                <div class="empty-state">
                    <h3>No Assigned Students</h3>
                    <p>You currently do not have any students assigned for subject marks entry.</p>
                </div>
            </td></tr>`;
            return;
        }

        students.forEach(s => {
            const tr = document.createElement("tr");

            let statusBadge = "";
            if (s.result_status === "PASS") {
                statusBadge = `<span class="badge badge-pass">PASS</span>`;
            } else if (s.result_status === "FAIL") {
                statusBadge = `<span class="badge badge-fail">FAIL</span>`;
            } else {
                statusBadge = `<span class="badge badge-incomplete">INCOMPLETE</span>`;
            }

            const subjectPills = s.assigned_subjects.map(c => `<span class="badge-pill">${c}</span>`).join(" ");

            tr.innerHTML = `
                <td><strong>${s.student_code}</strong></td>
                <td>${s.full_name}</td>
                <td>${s.section}</td>
                <td>${s.roll_number}</td>
                <td>${subjectPills}</td>
                <td>${statusBadge}</td>
                <td>
                    <button type="button" class="btn btn-primary btn-sm btn-edit-student" data-id="${s.id}" data-name="${s.full_name}" data-code="${s.student_code}" aria-haspopup="dialog">
                        Enter Marks
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll(".btn-edit-student").forEach(btn => {
            btn.addEventListener("click", function () {
                const id = parseInt(this.getAttribute("data-id"));
                openMarksModal(id, this);
            });
        });
    }

    async function openMarksModal(studentId, triggerEl) {
        currentStudentId = studentId;
        lastFocusedElement = triggerEl || document.activeElement;

        backdrop.classList.add("is-active");
        backdrop.setAttribute("aria-hidden", "false");
        modal.focus();

        document.getElementById("marks-modal-loading").style.display = "block";
        document.getElementById("marks-modal-error").style.display = "none";
        document.getElementById("marks-modal-success").style.display = "none";
        document.getElementById("marks-modal-content").style.display = "none";

        try {
            const response = await fetch(`/api/teacher/students/${studentId}/marks?exam_id=${currentExamId}`, {
                headers: { "Accept": "application/json" }
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error?.message || "Failed to load marks.");
            }

            const data = await response.json();
            renderMarksModal(data);
        } catch (err) {
            document.getElementById("marks-modal-loading").style.display = "none";
            const errDiv = document.getElementById("marks-modal-error");
            errDiv.textContent = err.message;
            errDiv.style.display = "block";
        }
    }

    function renderMarksModal(data) {
        document.getElementById("marks-modal-loading").style.display = "none";
        document.getElementById("marks-modal-content").style.display = "block";

        document.getElementById("marks-modal-subtitle").textContent =
            `Student: ${data.student.full_name} (${data.student.student_code}) — Exam: ${data.exam.name}`;

        updateSummaryDisplay(data.summary);

        const mBody = document.getElementById("marks-table-body");
        mBody.innerHTML = "";
        initialMarksValues = {};

        data.subjects.forEach(sub => {
            const tr = document.createElement("tr");
            const editable = sub.editable;
            const currentVal = sub.marks_obtained !== null ? sub.marks_obtained : '';
            if (editable) {
                initialMarksValues[sub.subject_id] = currentVal;
            }

            const inputHtml = editable
                ? `<input type="text" class="input-mark" id="input-sub-${sub.subject_id}" data-sub-id="${sub.subject_id}" data-sub-code="${sub.code}" value="${currentVal}" placeholder="0 - ${sub.max_marks}" aria-label="${sub.name} marks obtained" aria-describedby="error-sub-${sub.subject_id}">
                   <span class="field-error-msg" id="error-sub-${sub.subject_id}" role="alert"></span>`
                : `<input type="text" class="input-mark" value="${currentVal}" disabled title="Not assigned to you" aria-label="${sub.name} marks obtained (read-only)">`;

            const permLabel = editable
                ? `<span style="color: var(--success-color); font-weight: 700; font-size: 0.8rem;">Assigned (Editable)</span>`
                : `<span style="color: var(--muted-color); font-size: 0.8rem;">Read-only</span>`;

            tr.innerHTML = `
                <td><strong>${sub.name}</strong> <span class="badge-pill">${sub.code}</span></td>
                <td>${sub.max_marks}</td>
                <td>${sub.pass_marks}</td>
                <td>${inputHtml}</td>
                <td>${permLabel}</td>
            `;
            mBody.appendChild(tr);
        });
    }

    function updateSummaryDisplay(summary) {
        document.getElementById("modal-res-total").textContent =
            summary.total_obtained !== null ? `${summary.total_obtained} / ${summary.total_max}` : `— / ${summary.total_max}`;
        document.getElementById("modal-res-percentage").textContent =
            summary.percentage !== null ? `${summary.percentage}%` : "—";
        document.getElementById("modal-res-grade").textContent = summary.grade || "—";

        const statusEl = document.getElementById("modal-res-status");
        statusEl.textContent = summary.status;
        if (summary.status === "PASS") {
            statusEl.innerHTML = `<span class="badge badge-pass">PASS</span>`;
        } else if (summary.status === "FAIL") {
            statusEl.innerHTML = `<span class="badge badge-fail">FAIL</span>`;
        } else {
            statusEl.innerHTML = `<span class="badge badge-incomplete">INCOMPLETE</span>`;
        }
    }

    function closeMarksModal() {
        if (!backdrop) return;
        backdrop.classList.remove("is-active");
        backdrop.setAttribute("aria-hidden", "true");
        if (lastFocusedElement) {
            lastFocusedElement.focus();
        }
    }

    if (closeBtn) closeBtn.addEventListener("click", closeMarksModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeMarksModal);

    // Accessibility: Trap focus within modal and handle Escape
    document.addEventListener("keydown", function (e) {
        if (!backdrop || !backdrop.classList.contains("is-active")) return;

        if (e.key === "Escape") {
            closeMarksModal();
            return;
        }

        if (e.key === "Tab") {
            const focusable = getModalFocusableElements();
            if (focusable.length === 0) {
                e.preventDefault();
                return;
            }
            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === first || document.activeElement === modal) {
                    last.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === last) {
                    first.focus();
                    e.preventDefault();
                }
            }
        }
    });

    if (backdrop) {
        backdrop.addEventListener("click", function (e) {
            if (e.target === backdrop) {
                closeMarksModal();
            }
        });
    }

    // Save Marks submission
    if (saveBtn) {
        saveBtn.addEventListener("click", async function () {
            document.getElementById("marks-modal-error").style.display = "none";
            document.getElementById("marks-modal-success").style.display = "none";
            document.querySelectorAll(".field-error-msg").forEach(el => el.textContent = "");

            const inputs = document.querySelectorAll(".input-mark:not(:disabled)");
            const marksPayload = [];
            let clearingDetected = false;

            inputs.forEach(input => {
                const subId = parseInt(input.getAttribute("data-sub-id"));
                const rawVal = input.value.trim();
                const wasNotEmpty = initialMarksValues[subId] && initialMarksValues[subId].trim() !== "";
                if (wasNotEmpty && rawVal === "") {
                    clearingDetected = true;
                }
                marksPayload.push({
                    subject_id: subId,
                    marks_obtained: rawVal === "" ? null : rawVal
                });
            });

            // Confirmation if clearing previously saved marks
            if (clearingDetected) {
                const confirmed = window.confirm("You are clearing previously entered marks for one or more subjects. This will mark the student's result as INCOMPLETE. Do you wish to proceed?");
                if (!confirmed) {
                    return;
                }
            }

            saveBtn.disabled = true;
            const originalBtnText = saveBtn.textContent;
            saveBtn.textContent = "Saving...";

            try {
                const response = await fetch(`/api/teacher/students/${currentStudentId}/marks`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                    body: JSON.stringify({
                        exam_id: currentExamId,
                        marks: marksPayload
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    if (response.status === 422 && data.error?.details?.fields) {
                        const fields = data.error.details.fields;
                        inputs.forEach(input => {
                            const code = input.getAttribute("data-sub-code");
                            const subId = input.getAttribute("data-sub-id");
                            if (fields[code]) {
                                document.getElementById(`error-sub-${subId}`).textContent = fields[code];
                            }
                        });
                        throw new Error("Please correct the highlighted validation errors.");
                    }
                    throw new Error(data.error?.message || "Failed to save marks.");
                }

                // Success
                const successDiv = document.getElementById("marks-modal-success");
                successDiv.textContent = `Marks saved successfully! (${data.saved} subject(s) recorded with audit log).`;
                successDiv.style.display = "block";

                // Update initial values
                inputs.forEach(input => {
                    const subId = parseInt(input.getAttribute("data-sub-id"));
                    initialMarksValues[subId] = input.value.trim();
                });

                // Update summary in modal
                if (data.summary) {
                    updateSummaryDisplay(data.summary);
                }

                // Refresh main students list
                loadStudents();
            } catch (err) {
                const errDiv = document.getElementById("marks-modal-error");
                errDiv.textContent = err.message;
                errDiv.style.display = "block";
            } finally {
                saveBtn.disabled = false;
                saveBtn.textContent = originalBtnText;
            }
        });
    }
})();
