// main.js
// Common front-end behaviors for Supplier Accreditation System

document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ main.js loaded successfully");

    // 1️⃣ Auto-hide Bootstrap alerts after a delay
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 4000); // 4 seconds
    });

    // 2️⃣ Add a loading spinner when submitting any form
    const forms = document.querySelectorAll("form");
    forms.forEach(form => {
        form.addEventListener("submit", function (e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const spinner = document.createElement("span");
                spinner.classList.add("spinner-border", "spinner-border-sm", "ms-2");
                spinner.setAttribute("role", "status");
                spinner.setAttribute("aria-hidden", "true");
                submitBtn.appendChild(spinner);
            }
        });
    });

    // 3️⃣ Toggle password visibility (if applicable)
    const togglePasswordButtons = document.querySelectorAll(".toggle-password");
    togglePasswordButtons.forEach(btn => {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (input) {
                input.type = input.type === "password" ? "text" : "password";
                this.classList.toggle("text-primary");
            }
        });
    });

    // 4️⃣ Simple logging helper
    window.logEvent = function (eventName, details = {}) {
        console.log(`[Event] ${eventName}`, details);
    };

    // 5️⃣ Optional file input validator (useful in registration phase)
    const fileInputs = document.querySelectorAll("input[type='file']");
    fileInputs.forEach(input => {
        input.addEventListener("change", function () {
            const file = this.files[0];
            if (!file) return;

            const maxSize = 600 * 1024 * 1024; // 600 MB limit
            if (file.size > maxSize) {
                alert("❌ File size exceeds 600MB limit!");
                this.value = "";
                return;
            }

            const allowedTypes = ["image/jpeg", "image/png"];
            if (!allowedTypes.includes(file.type)) {
                alert("❌ Invalid file type! Only JPG or PNG allowed.");
                this.value = "";
            }
        });
    });
});
