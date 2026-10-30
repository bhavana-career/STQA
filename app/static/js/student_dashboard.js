(function () {
    const viewBtn = document.getElementById("btn-view-result");
    const backdrop = document.getElementById("result-modal-backdrop");
    const modal = document.getElementById("result-modal");
    const closeBtn = document.getElementById("modal-close-btn");
    const footerCloseBtn = document.getElementById("btn-modal-close-footer");

    const loadingDiv = document.getElementById("modal-loading");
    const errorDiv = document.getElementById("modal-error");
    const contentDiv = document.getElementById("modal-result-content");

    let lastActiveElement = null;

    function getFocusableElements() {
        if (!modal) return [];
        return modal.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
    }

    function openModal() {
        lastActiveElement = document.activeElement;
        backdrop.classList.add("is-active");
        backdrop.setAttribute("aria-hidden", "false");
        modal.focus();
        loadResult();
    }

    function closeModal() {
        backdrop.classList.remove("is-active");
        backdrop.setAttribute("aria-hidden", "true");
        if (lastActiveElement) {
            lastActiveElement.focus();
        }
    }

    if (viewBtn) {
        viewBtn.addEventListener("click", openModal);
    }
    if (closeBtn) {
        closeBtn.addEventListener("click", closeModal);
    }
    if (footerCloseBtn) {
        footerCloseBtn.addEventListener("click", closeModal);
    }

    // Accessibility: Trap focus within modal and handle Escape
    document.addEventListener("keydown", function (e) {
        if (!backdrop || !backdrop.classList.contains("is-active")) return;

        if (e.key === "Escape") {
            closeModal();
            return;
        }

        if (e.key === "Tab") {
            const focusable = getFocusableElements();
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

    // Close on clicking backdrop outside modal
    if (backdrop) {
        backdrop.addEventListener("click", function (e) {
            if (e.target === backdrop) {
                closeModal();
            }
        });
    }

    async function loadResult() {
        if (!loadingDiv || !errorDiv || !contentDiv) return;
        loadingDiv.style.display = "block";
        errorDiv.style.display = "none";
        contentDiv.style.display = "none";

        try {
            const response = await fetch("/api/student/result", {
                headers: { "Accept": "application/json" }
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error?.message || "Failed to load examination result.");
            }

            const data = await response.json();
            renderResult(data);
        } catch (err) {
            loadingDiv.style.display = "none";
            errorDiv.textContent = err.message;
            errorDiv.style.display = "block";
        }
    }

    function renderResult(data) {
        loadingDiv.style.display = "none";
        contentDiv.style.display = "block";

        document.getElementById("exam-header-info").textContent =
            `Exam: ${data.exam.name} (${data.exam.academic_year})`;

        const sum = data.summary;
        document.getElementById("res-total").textContent =
            sum.total_obtained !== null ? `${sum.total_obtained} / ${sum.total_max}` : `— / ${sum.total_max}`;
        document.getElementById("res-percentage").textContent =
            sum.percentage !== null ? `${sum.percentage}%` : "—";
        document.getElementById("res-grade").textContent = sum.grade || "—";

        const statusEl = document.getElementById("res-status");
        statusEl.textContent = sum.status;
        statusEl.className = "value";
        if (sum.status === "PASS") {
            statusEl.innerHTML = `<span class="badge badge-pass">PASS</span>`;
        } else if (sum.status === "FAIL") {
            statusEl.innerHTML = `<span class="badge badge-fail">FAIL</span>`;
        } else {
            statusEl.innerHTML = `<span class="badge badge-incomplete">INCOMPLETE</span>`;
        }

        const tbody = document.getElementById("subjects-table-body");
        tbody.innerHTML = "";

        data.subjects.forEach(sub => {
            const tr = document.createElement("tr");

            let passBadge = "";
            if (sub.passed === true) {
                passBadge = `<span class="badge badge-pass">PASS</span>`;
            } else if (sub.passed === false) {
                passBadge = `<span class="badge badge-fail">FAIL</span>`;
            } else {
                passBadge = `<span class="badge badge-incomplete">PENDING</span>`;
            }

            tr.innerHTML = `
                <td><strong>${sub.name}</strong> <span class="badge-pill">${sub.code}</span></td>
                <td>${sub.max_marks}</td>
                <td>${sub.pass_marks}</td>
                <td><strong>${sub.marks_obtained !== null ? sub.marks_obtained : "—"}</strong></td>
                <td>${sub.percentage !== null ? `${sub.percentage}%` : "—"}</td>
                <td>${sub.grade || "—"}</td>
                <td>${passBadge}</td>
            `;
            tbody.appendChild(tr);
        });
    }
})();
