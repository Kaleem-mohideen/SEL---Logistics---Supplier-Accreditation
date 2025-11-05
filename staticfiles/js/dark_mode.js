document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;
    const toggle = document.getElementById("darkModeToggle");

    // Load saved mode
    if (localStorage.getItem("darkMode") === "enabled") {
        body.classList.add("dark-mode");
        toggle.innerText = "☀️ Light Mode";
    }

    toggle.addEventListener("click", () => {
        body.classList.toggle("dark-mode");

        if (body.classList.contains("dark-mode")) {
            localStorage.setItem("darkMode", "enabled");
            toggle.innerText = "☀️ Light Mode";
        } else {
            localStorage.removeItem("darkMode");
            toggle.innerText = "🌙 Dark Mode";
        }
    });
});
