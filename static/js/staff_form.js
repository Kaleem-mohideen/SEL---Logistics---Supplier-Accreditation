// static/js/staff_form.js
document.addEventListener("DOMContentLoaded", function () {
  /* ---------------------------------------------------
      1) Venue Select2 + limit 7
  --------------------------------------------------- */
  // Initialize Select2 on venue-select
  if (typeof $ !== "undefined" && $(".venue-select").length) {
    $(".venue-select").select2({
      placeholder: "Select up to 7 venues",
      width: "100%",
      allowClear: true,
      tags: false,
      // Bootstrap look: we rely on CSS to style
    });

    // Limit selections to 7
    $(".venue-select").on("change", function () {
      const max = 7;
      const selected = $(this).val() || [];
      if (selected.length > max) {
        // remove last selected
        selected.splice(max);
        $(this).val(selected).trigger("change.select2");
        alert("You can select up to 7 venues only.");
      }
      // update helper text to show count
      $("#venue-help").text(`${selected.length} selected (max 7).`);
    });
  }

  /* ---------------------------------------------------
      2) Disable Place of Birth unless Italy
  --------------------------------------------------- */
  
    // Disable Place of Birth when not Italy
  $("#id_country_of_birth").on("change", function () {
    const selected = $("#id_country_of_birth option:selected").text().trim().toLowerCase();
    console.log(selected);
    const placeField = $("#id_place_or_city_of_birth");
    if (selected === "italy" || selected === "italia") {
      placeField.prop("disabled", false);
    } else {
      placeField.val("").trigger("change").prop("disabled", true);
    }
  }).trigger("change");

    /* ---------------------------------------------------
      3) AJAX: Document Type Rules based on Nationality
  --------------------------------------------------- */
  $("#id_nationality").on("change", function () {

        let nationalityId = $(this).val();
        let documentSelect = $("#id_document_type");

        // CASE 1: Nationality is empty ("---------")
        if (!nationalityId) {
            $("#doc-warning").remove();

            // Restore all document types (full list)
            $.ajax({
                url: "/staff/check-document-rules/all/",
                method: "GET",
                success: function (data) {
                    documentSelect.empty();

                    // Always re-add blank option
                    documentSelect.append('<option value="">---------</option>');

                    // Add all available document types
                    data.options.forEach(opt => {
                        documentSelect.append(
                            `<option value="${opt.id}">${opt.name}</option>`
                        );
                    });

                    // Reset selection to blank
                    documentSelect.val("");
                }
            });

            return; // stop here for blank nationality
        }

        // CASE 2: Normal AJAX processing for valid nationality
        $.ajax({
            url: "/staff/check-document-rules/" + nationalityId + "/",
            method: "GET",
            success: function (data) {
                let previousValue = documentSelect.val();  // keep selection

                documentSelect.empty();

                // add placeholder
                documentSelect.append('<option value="">---------</option>');

                // add options
                data.options.forEach(opt => {
                    documentSelect.append(
                        `<option value="${opt.id}">${opt.name}</option>`
                    );
                });

                // restore previous selection if still valid
                if (data.options.some(opt => opt.id == previousValue)) {
                    documentSelect.val(previousValue);
                } else {
                    documentSelect.val("");
                }

                // warning
                $("#doc-warning").remove();
                if (data.passport_only) {
                    documentSelect.after(
                        '<small id="doc-warning" class="text-danger">⚠️ Solo il Passaporto è accettato per questa nazionalità.</small>'
                    );
                }
            }
        });

    });

  // Trigger once on page load (useful for edit mode)
  $("#id_nationality").trigger("change");

  /* ---------------------------------------------------
      4) Photo file validation + preview
  --------------------------------------------------- */
  // Photo preview + size/type validation
  const photoInput = document.getElementById("id_photograph");
  if (photoInput) {
    photoInput.addEventListener("change", function (e) {
      const f = e.target.files[0];
      const preview = document.getElementById("photo-preview");
      preview.innerHTML = "";
      if (!f) return;

      // type check
      if (!["image/jpeg", "image/png"].includes(f.type)) {
        alert("Invalid file type. Please upload JPG or PNG.");
        e.target.value = "";
        return;
      }

      // size check 3MB
      const max = 3 * 1024 * 1024;
      if (f.size > max) {
        alert("File exceeds 3MB limit.");
        e.target.value = "";
        return;
      }

      // show preview
      const img = document.createElement("img");
      img.style.maxWidth = "160px";
      img.style.maxHeight = "160px";
      img.classList.add("img-thumbnail");
      const reader = new FileReader();
      reader.onload = function (ev) {
        img.src = ev.target.result;
        preview.appendChild(img);
      };
      reader.readAsDataURL(f);
    });
  }

    /* ---------------------------------------------------
      5) Prevent double submit
  --------------------------------------------------- */

  // Prevent accidental form double-submit and show spinner
  const form = document.getElementById("staff-form");
  if (form) {
    form.addEventListener("submit", function () {
      const btn = form.querySelector("button[type='submit']");
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = "Saving... <span class='spinner-border spinner-border-sm' role='status' aria-hidden='true'></span>";
      }
    });
  }
});

