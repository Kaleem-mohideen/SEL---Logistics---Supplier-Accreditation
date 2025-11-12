// staff/static/js/staff_datepicker.js

document.addEventListener('DOMContentLoaded', function () {
    // Attach Flatpickr to Django admin date fields
    if (typeof flatpickr !== "undefined") {
        flatpickr(".vDateField", {
            dateFormat: "Y-m-d",
            altInput: true,
            altFormat: "d-m-Y",
            allowInput: true,
            monthSelectorType: "dropdown",  // ✅ month dropdown
            yearSelectorType: "dropdown",   // ✅ year dropdown
            maxDate: "today",               // optional: prevent future dates for DOB
        });
    } else {
        console.warn("Flatpickr not loaded. Check admin Media configuration.");
    }
});
