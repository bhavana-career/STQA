(function () {
    const openBtn = document.getElementById("btn-open-change-password");
    const backdrop = document.getElementById("change-password-backdrop");
    const modal = document.getElementById("change-password-modal");
    const closeBtn = document.getElementById("change-password-close-btn");
    const cancelBtn = document.getElementById("btn-cancel-change-password");
    const form = document.getElementById("form-change-password");
    const submitBtn = document.getElementById("btn-submit-change-password");
    const errorAlert = document.getElementById("change-password-error");
    const successAlert = document.getElementById("change-password-success");

    let lastActiveElement = null;

    function openModal() {
        lastActiveElement = document.activeElement;
        if (errorAlert) {
            errorAlert.style.display = "none";
            errorAlert.textContent = "";
        }
        if (successAlert) {
            successAlert.style.display = "none";
            successAlert.textContent = "";
        }
        if (form) form.reset();
        backdrop.classList.add("is-active");
        backdrop.setAttribute("aria-hidden", "false");
        const currentInput = document.getElementById("input-current-password");
        if (currentInput) currentInput.focus();
    }

    function closeModal() {
        backdrop.classList.remove("is-active");
        backdrop.setAttribute("aria-hidden", "true");
        if (lastActiveElement) lastActiveElement.focus();
    }

    if (openBtn) openBtn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

    document.addEventListener("keydown", function (e) {
        if (!backdrop || !backdrop.classList.contains("is-active")) return;
        if (e.key === "Escape") {
            closeModal();
        }
    });

    if (backdrop) {
        backdrop.addEventListener("click", function (e) {
            if (e.target === backdrop) closeModal();
        });
    }

    if (form) {
        form.addEventListener("submit", async function (e) {
            e.preventDefault();
            if (errorAlert) {
                errorAlert.style.display = "none";
                errorAlert.textContent = "";
            }
            if (successAlert) {
                successAlert.style.display = "none";
                successAlert.textContent = "";
            }

            const currentPassword = document.getElementById("input-current-password").value;
            const newPassword = document.getElementById("input-new-password").value;
            const confirmPassword = document.getElementById("input-confirm-password").value;

            if (!currentPassword || !newPassword || !confirmPassword) {
                showError("Please fill out all password fields.");
                return;
            }

            if (newPassword !== confirmPassword) {
                showError("New password and confirmation do not match.");
                return;
            }

            if (newPassword.length < 12) {
                showError("Password must be at least 12 characters long.");
                return;
            }

            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

            submitBtn.disabled = true;
            submitBtn.textContent = "Updating...";

            try {
                const response = await fetch("/change-password", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    showError(data?.error?.message || "Failed to update password. Please check your credentials.");
                } else {
                    if (successAlert) {
                        successAlert.style.display = "block";
                        successAlert.textContent = data.message || "Password updated successfully!";
                    }
                    form.reset();
                    setTimeout(closeModal, 2000);
                }
            } catch (err) {
                showError("Network error. Please try again.");
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = "Change Password";
            }
        });
    }

    function showError(msg) {
        if (errorAlert) {
            errorAlert.style.display = "block";
            errorAlert.textContent = msg;
        }
    }
})();
