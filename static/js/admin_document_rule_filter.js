// Runs inside Django Admin (jQuery already included)
(function($) {
    $(document).ready(function() {

        function loadDocumentTypes(group) {
            $.ajax({
                url: "/staff/admin/document-type-filter/",
                method: "GET",
                data: { group: group },
                success: function(data) {
                    var select = $("#id_document_type");
                    select.empty();

                    data.options.forEach(function(opt) {
                        select.append(`<option value="${opt.id}">${opt.name}</option>`);
                    });
                }
            });
        }

        // Trigger when the admin changes the country group
        $("#id_country_group").on("change", function() {
            let group = $(this).val();
            loadDocumentTypes(group);
        });

        // Auto-load when editing an existing record
        let initialGroup = $("#id_country_group").val();
        if (initialGroup) {
            loadDocumentTypes(initialGroup);
        }
    });
})(django.jQuery);
