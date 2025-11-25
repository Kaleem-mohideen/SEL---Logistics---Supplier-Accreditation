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
    console.log(here in nation);
    let nationalityId = $(this).val();

    if (!nationalityId) return;

    $.ajax({
      url: "/staff/check-document-rules/" + nationalityId + "/",
      method: "GET",
      success: function (data) {
        let documentSelect = $("#id_document_type");

        // Clear and rebuild document type options
        documentSelect.empty();

        data.options.forEach(opt => {
          documentSelect.append(
            `<option value="${opt.id}">${opt.name}</option>`
          );
        });

        // Passport only case
        $("#doc-warning").remove();
        if (data.passport_only) {
          documentSelect.after(
            '<small id="doc-warning" class="text-danger">⚠️ Solo il Passaporto è accettato per questa nazionalità.</small>'
          );
        }
      },
      error: function () {
        console.error("Document type rule AJAX failed.");
      }
    });
  }).trigger("change");

  // Trigger once on page load (useful for edit mode)
  // $("#id_nationality").trigger("change");

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

