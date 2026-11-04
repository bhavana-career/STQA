/**
 * Client-side interactions for SRMS:
 * - Password visibility toggle on login and forms
 * - Delete confirmation dialog
 * - Success popup modal dismissal
 * - Teacher dashboard quick table search & section filter
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Password visibility toggle
  const toggleBtn = document.getElementById("togglePasswordBtn");
  const passwordInput = document.getElementById("password");

  if (toggleBtn && passwordInput) {
    toggleBtn.addEventListener("click", function () {
      const isPassword = passwordInput.getAttribute("type") === "password";
      passwordInput.setAttribute("type", isPassword ? "text" : "password");
      toggleBtn.textContent = isPassword ? "Hide" : "Show";
      toggleBtn.setAttribute("aria-pressed", isPassword ? "true" : "false");
    });
  }

  // 2. Delete confirmation forms
  const deleteForms = document.querySelectorAll(".delete-student-form");
  deleteForms.forEach(function (form) {
    form.addEventListener("submit", function (event) {
      const studentName = form.getAttribute("data-student-name") || "this student";
      const confirmed = window.confirm(
        "Are you sure you want to permanently delete the record for " + studentName + "?"
      );
      if (!confirmed) {
        event.preventDefault();
      }
    });
  });

  // 3. Success popup modal close button
  const closePopupBtn = document.getElementById("closeSuccessPopupBtn");
  const popupOverlay = document.getElementById("resultSuccessPopup");

  if (closePopupBtn && popupOverlay) {
    closePopupBtn.addEventListener("click", function () {
      popupOverlay.classList.add("hidden");
    });
  }

  // 4. Teacher Dashboard quick search & section filter
  const quickSearch = document.getElementById("dashboardQuickSearch");
  const quickSection = document.getElementById("dashboardQuickSection");
  const dashboardTable = document.getElementById("dashboardStudentsTable");

  if (dashboardTable && (quickSearch || quickSection)) {
    const filterDashboardRows = function () {
      const query = (quickSearch ? quickSearch.value : "").trim().toLowerCase();
      const sec = (quickSection ? quickSection.value : "").trim().toUpperCase();
      const rows = dashboardTable.querySelectorAll("tbody tr");

      rows.forEach(function (row) {
        const text = row.textContent.toLowerCase();
        const rowSec = (row.getAttribute("data-section") || "").toUpperCase();
        const matchesQuery = !query || text.indexOf(query) !== -1;
        const matchesSec = !sec || rowSec === sec;
        row.style.display = matchesQuery && matchesSec ? "" : "none";
      });
    };

    if (quickSearch) {
      quickSearch.addEventListener("input", filterDashboardRows);
    }
    if (quickSection) {
      quickSection.addEventListener("change", filterDashboardRows);
    }
  }
});
