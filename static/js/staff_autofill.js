document.addEventListener("DOMContentLoaded", function () {
    const supplierSelect = document.querySelector("#id_supplier");
    const functionCodeSelect = document.querySelector("#id_function_code");

    if (!supplierSelect || !functionCodeSelect) return;

    supplierSelect.addEventListener("change", function () {
        const supplierId = this.value;
        if (!supplierId) return;

        // ✅ Updated to match admin route
        fetch(`/admin/staff/staffmember/get_function_code/${supplierId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.function_code_id) {
                    functionCodeSelect.value = data.function_code_id;
                } else {
                    functionCodeSelect.value = "";
                }
            })
            .catch(err => console.error("Error fetching function code:", err));
    });
});
