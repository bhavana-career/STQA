(function () {
    const form = document.getElementById("login-form");
    const submitBtn = document.getElementById("btn-submit-login");
    if (form && submitBtn) {
        form.addEventListener("submit", function () {
            // Prevent accidental duplicate clicks while submitting
            setTimeout(() => {
                submitBtn.disabled = true;
                submitBtn.textContent = "Signing In...";
            }, 0);
        });
    }
})();
