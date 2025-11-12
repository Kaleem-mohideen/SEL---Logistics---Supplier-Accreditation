document.addEventListener('DOMContentLoaded', function () {
    if (typeof flatpickr === 'undefined') {
        console.error('❌ Flatpickr not loaded!');
        return;
    }

    // Helper: Initialize a datepicker safely
    function initFlatpickr(selector, options) {
        const elements = document.querySelectorAll(selector);
        if (elements.length === 0) return;
        elements.forEach(el => {
            flatpickr(el, Object.assign({
                dateFormat: "Y-m-d",
                altInput: true,
                altFormat: "d-m-Y",
                allowInput: true,
                monthSelectorType: "dropdown",
                yearSelectorType: "dropdown",
            }, options));
        });
    }

    // 🎯 Date of Birth — Past only
    initFlatpickr("input[name='date_of_birth'], input#id_date_of_birth", {
        maxDate: "today",
    });

    // // 🎯 Document Expiry — Future only
    // initFlatpickr("input[name='document_expiry'], input#id_document_expiry", {
    //     minDate: "today",
    // });

    // 🎯 Other Date Fields — No restriction
    const excludedNames = ["date_of_birth"];
    document.querySelectorAll("input.vDateField").forEach(input => {
        if (!excludedNames.includes(input.name)) {
            initFlatpickr(`input[name='${input.name}']`);
        }
    });
});
