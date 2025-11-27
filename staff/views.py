from django.views.generic import ListView, CreateView, UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from .models import StaffMember, Status, ExportLog, Document, DocumentTypeRestriction, DocumentExpiryRule, ExportTracker

# from accounts.models import Supplier
from .forms import StaffMemberForm
import pandas as pd
from django.http import HttpResponse
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required

from .export_utils import export_staff_data
from django.http import FileResponse, JsonResponse
from django.contrib import messages
from pathlib import Path
from django.conf import settings
import os
from django.core.files.storage import default_storage

import openpyxl
from openpyxl.utils import get_column_letter

import io
import zipfile
from django.conf import settings


VALID_STATUS = ["completed", "not_completed", "all"]
VALID_MODE = ["new", "all"]

def get_tracker(key):
    obj, created = ExportTracker.objects.get_or_create(key=key)
    return obj


@staff_member_required
def admin_export_flagged(request, status, mode):
    """Export based on flag selection in admin."""

    if status not in VALID_STATUS or mode not in VALID_MODE:
        return HttpResponse("Invalid export filter.", status=400)

    # Map status → queryset filter
    if status == "completed":
        base_qs = StaffMember.objects.filter(status__status_id="1")
    elif status == "not_completed":
        base_qs = StaffMember.objects.exclude(status__status_id="1")
    else:
        base_qs = StaffMember.objects.all()

    tracker = get_tracker(status)

    # MODE: new (only records > last_exported_pk)
    if mode == "new":
        qs = base_qs.filter(pk__gt=tracker.last_exported_pk)
    else:
        qs = base_qs

    # No records?
    if not qs.exists():
        return HttpResponse("No matching records for export.", status=404)

    # Do your export
    # Replace this with your template export function
    response = export_reg_excel_generate(qs)  # ← we create this below

    # Update tracker only if mode=new
    if mode == "new":
        max_pk = qs.order_by("-pk").first().pk
        tracker.last_exported_pk = max_pk
        tracker.save()

    return response


@staff_member_required
def download_all_photos(request):
    """Download all files inside MEDIA_ROOT/photos/ as a single ZIP."""

    photos_dir = os.path.join(settings.MEDIA_ROOT, "photos")

    if not os.path.isdir(photos_dir):
        return HttpResponse("❌ photos directory does not exist.", status=404)

    buffer = io.BytesIO()

    # Create ZIP in memory
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_name in os.listdir(photos_dir):
            file_path = os.path.join(photos_dir, file_name)

            if os.path.isfile(file_path):
                # add photo to ZIP with filename only (not full path)
                zipf.write(file_path, arcname=file_name)

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/zip"
    )
    response["Content-Disposition"] = 'attachment; filename="all_photos.zip"'

    return response


def admin_document_type_filter(request):
    group = request.GET.get("group")

    if group == "NON_EU":
        options = [{"id": "passport", "name": "Passport"}]
    else:
        options = [
            {"id": "id_card", "name": "Identity Card"},
            {"id": "passport", "name": "Passport"},
        ]

    return JsonResponse({"options": options})

def check_document_rules_all(request):
    docs = Document.objects.all()
    return JsonResponse({
        "options": [{"id": d.id, "name": d.type_name} for d in docs],
        "passport_only": False
    })

def check_document_rules(request, nationality_id):
    docs = Document.objects.all()

    restriction = DocumentTypeRestriction.objects.filter(
        nationality_id=nationality_id
    ).first()

    passport_only = False

    if not restriction or not restriction.allow_identity_card:
        docs = docs.filter(type_name__icontains="passport")
        passport_only = True

    return JsonResponse({
        "options": [{"id": d.id, "name": d.type_name} for d in docs],
        "passport_only": passport_only
    })

def export_staff(request):
    
    supplier = getattr(request.user, "supplier", None)

    # BLOCK EXPORT unless supplier has permission turned on
    if not supplier or not supplier.allow_frontend_export:
        messages.error(request, "Export disabled by Administrator.")
        return redirect("staff:landing")

    filename, status = export_staff_data(request.user)

    if status == "NO_RECORDS":
        messages.warning(request, "No records with Status = 1 to export.")
        return redirect("staff:landing")

    export_path = Path(settings.MEDIA_ROOT) / "exports" / filename
    return FileResponse(open(export_path, "rb"), as_attachment=True, filename=filename)


def export_reg_excel_generate(qs):
    """
    Generates Excel using template.xlsx and places records starting from row 4,
    following EXACT FORMAT of Download File Structure – FORM 5.
    """

    template_path = settings.BASE_DIR / "templates/export/template.xlsx"
    if not template_path.exists():
        raise FileNotFoundError("template.xlsx missing in templates/export/")

    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    row = 4  # Data always starts at row 4 in FORM 5

    for s in qs:
        row_data = [
            "Yes" if s.olympic_request else "No",
            "Yes" if s.paralympic_request else "No",
            s.organisation,
            s.registration_group,
            s.function_code.code if s.function_code else "",
            ",".join(v.code for v in s.venue.all()) if s.venue.exists() else "",
            "",  # Discipline(s) always empty
            s.organisation_reference_number or "",
            s.document_given_name,
            s.unknown_given_name,
            s.document_middle_name or "",
            s.document_family_name,
            s.unknown_family_name,
            s.preferred_given_name,
            s.preferred_family_name,
            s.date_of_birth.strftime("%d.%m.%Y") if s.date_of_birth else "",
            s.unknown_date_of_birth,
            s.gender.code if s.gender else "",
            s.nationality.code if s.nationality else "",
            s.document_type.type_name if s.document_type else "",
            s.document_number,
            s.document_expiry.strftime("%d.%m.%Y") if s.document_expiry else "",
            s.country_issuing_document.code if s.country_issuing_document else "",
            s.country_of_birth.code if s.country_of_birth else "",
            s.place_or_city_of_birth.city_name if s.place_or_city_of_birth else "",
            s.email_address,
            s.photograph.name.split("/")[-1] if s.photograph else "",
            s.wheelchair_user,
            s.transferable_wheelchair_user,
        ]

        for col_index, value in enumerate(row_data, start=1):
            ws.cell(row=row, column=col_index).value = value

        row += 1

    # Create downloadable output response
    output = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    timestamp = now().strftime("%Y%m%d_%H%M")
    filename = f"Plog_{timestamp}.xlsx"
    output["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(output)

    return output


@staff_member_required
def export_reg_excel(request):
    """Exports REG Excel using template.xlsx and exact FORM 5 ordering."""

    staff = StaffMember.objects.filter(status__status_id="1").select_related(
        "supplier",
        "function_code",
        "gender",
        "nationality",
        "document_type",
        "country_issuing_document",
        "country_of_birth",
        "place_or_city_of_birth",
    ).prefetch_related("venue")

    if not staff.exists():
        messages.warning(request, "No completed (status=1) records available for export.")
        return redirect("admin:staff_staffmember_changelist")

    # --- Load Excel Template ---
    # template_path = BASE_DIR / "templates" / "export" / "template.xlsx"
    template_path = settings.BASE_DIR / "templates/export/template.xlsx"

    if not template_path.exists():
        return HttpResponse("❌ template.xlsx missing in /templates/export/", status=500)

    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    # --- Define EXACT COLUMN ORDER per FORM 5 Row 4 ---
    COLUMNS = [
        "Request for Olympic Winter Games Accreditation",
        "Request for Paralympic Winter Games Accreditation",
        "Organisation",
        "Registration Group",
        "Function code",
        "Venue(s)",
        "Discipline(s)",
        "Organisation reference number",
        "Given name",
        "Unknown Given name",
        "Document Middle name",
        "Document Family name",
        "Unknown Family name",
        "Preferred Given name",
        "Preferred Family name",
        "Date of birth",
        "Unknown Date of birth",
        "Gender",
        "Nationality",
        "Document type",
        "Document Number",
        "Document Expiry Date",
        "Country issuing document",
        "Country or Territory of birth",
        "Place or City of birth",
        "Email address",
        "Photograph",
        "Wheelchair user",
        "Transferable wheelchair user",
    ]

    # Start writing data after header row
    row = 4

    for s in staff:
        row_data = [
            "Yes" if s.olympic_request else "No",
            "Yes" if s.paralympic_request else "No",
            s.organisation,
            s.registration_group,
            s.function_code.code if s.function_code else "",
            ",".join(v.code for v in s.venue.all()) or "",
            "",  # discipline always empty
            s.organisation_reference_number or "",
            s.document_given_name,
            s.unknown_given_name,  # ALWAYS "NO"
            s.document_middle_name or "",
            s.document_family_name,
            s.unknown_family_name,  # ALWAYS "NO"
            s.preferred_given_name,
            s.preferred_family_name,
            s.date_of_birth.strftime("%d.%m.%Y"),
            s.unknown_date_of_birth,  # ALWAYS “Date of birth is correct”
            s.gender.code if s.gender else "",
            s.nationality.code if s.nationality else "",
            s.document_type.type_name if s.document_type else "",
            s.document_number,
            s.document_expiry.strftime("%d.%m.%Y") if s.document_expiry else "",
            s.country_issuing_document.code if s.country_issuing_document else "",
            s.country_of_birth.code if s.country_of_birth else "",
            s.place_or_city_of_birth.city_name if s.place_or_city_of_birth else "",
            s.email_address,
            s.photograph.name.split("/")[-1] if s.photograph else "",
            s.wheelchair_user,
            s.transferable_wheelchair_user,
        ]

        # Insert row values in correct order
        for col_index, value in enumerate(row_data, start=1):
            ws.cell(row=row, column=col_index).value = value

        row += 1

    # Prepare response
    timestamp = now().strftime("%Y%m%d_%H%M")
    filename = f"Plog_{timestamp}.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)

    # Log export
    ExportLog.objects.create(
        exported_by=request.user,
        file_name=filename,
        record_count=staff.count(),
    )

    return response

class SupplierSecureMixin(LoginRequiredMixin):
    """Ensures user has a supplier before accessing staff"""
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "supplier"):
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)

    @property
    def supplier(self):
        return getattr(self.request.user, "supplier")

class StaffListView(SupplierSecureMixin, ListView):
    model = StaffMember
    template_name = "staff/landing.html"
    context_object_name = "staff_list"
    paginate_by = 20

    def get_queryset(self):
        return StaffMember.objects.filter(supplier=self.supplier).order_by("-created_at")

class StaffCreateView(SupplierSecureMixin, CreateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = "staff/staff_form.html"
    success_url = reverse_lazy("staff:landing")

    def get_form_kwargs(self):
        """Pass supplier context for function code pre-fill"""
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        supplier = self.supplier
        instance = form.save(commit=False)
        instance.supplier = supplier

        # Save the logged-in user performing registration
        instance.user = self.request.user
        # 🔹 Assign function_code from supplier securely
        if supplier and supplier.function_code:
            instance.function_code = supplier.function_code

        # 🔹 Generate unique IDs
        next_num = StaffMember.objects.filter(supplier=supplier).count() + 1
        instance.plog_unique_id = f"{supplier.code}{next_num:02d}"
        # instance.worker_unique_id = f"{supplier.code}-{next_num:03d}"

        # instance.refresh_from_db()
        # Save instance so photograph gets a file path
        instance.save()
        # instance.venue.set(form.cleaned_data.get("venue", []))
        # Evaluate completion status
        instance.evaluate_completion_status()
        instance.save()
        
        # ---- Renaming the photograph ON DISK ----
        # 🔹 Rename photograph file (after pk generated)
        if instance.photograph:
            old_path = instance.photograph.path
            ext = os.path.splitext(old_path)[1].lower()
            new_filename = f"{instance.document_family_name}_{instance.document_given_name}_{instance.plog_unique_id}{ext}"
            new_relative_path = os.path.join("photos", new_filename)
            new_full_path = os.path.join(settings.MEDIA_ROOT, new_relative_path)

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

            # Move/rename actual file
            if os.path.exists(old_path):
                # If old file exists → remove it first
                if os.path.exists(new_full_path):
                    os.remove(new_full_path)
                os.rename(old_path, new_full_path)

            # Update model field
            instance.photograph.name = new_relative_path
            instance.save(update_fields=["photograph"])

        # User feedback
        if instance.status.status_id == "1":
            messages.success(self.request, "✅ Staff record saved and marked as COMPLETATO.")
        else:
            messages.info(self.request, "🕓 Partial save successful (Non Completo). You can complete it later.")

        return super().form_valid(form)


class StaffUpdateView(SupplierSecureMixin, UpdateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = "staff/staff_form.html"
    success_url = reverse_lazy("staff:landing")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        """Block editing if:
        - record does not belong to logged-in supplier
        - status is completed (01)
        """
        obj = self.get_object()
        # prevent edits if status is completed (status_id == '1')
        if obj.status and getattr(obj.status, "status_id", None) == "1":
            messages.info(request, "✅ This record is already marked as COMPLETATO and cannot be edited.")
            return redirect(self.success_url)
        # ensure supplier matches
        if obj.supplier != self.supplier:
            messages.warning(request, "You cannot edit staff from another supplier.")
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.supplier = self.supplier
        instance.user = self.request.user  # track who made the update
        instance.function_code = self.supplier.function_code  # lock to supplier’s function

        old_photo_path = None
        if instance.pk and instance.photograph:
            try:
                old_photo_path = instance.photograph.path
            except Exception:
                old_photo_path = None

        # Save first to get PK if not yet saved
        instance.save()

        # Update many-to-many venue field
        # instance.venue.set(form.cleaned_data.get("venue", []))

        # 🔹 Recalculate completion status (partial → complete)
        instance.evaluate_completion_status()
        instance.save()

        # ---- Renaming logic only if a NEW file was uploaded ----
        new_file = form.cleaned_data.get("photograph")

        if new_file and hasattr(new_file, "name"):
            # a NEW file uploaded → rename it
            try:
                new_uploaded_path = instance.photograph.path
            except Exception:
                new_uploaded_path = None

            if new_uploaded_path and os.path.exists(new_uploaded_path):
                ext = os.path.splitext(new_uploaded_path)[1].lower()
                new_filename = f"{instance.document_family_name}_{instance.document_given_name}_{instance.plog_unique_id}{ext}"
                new_relative_path = os.path.join("photos", new_filename)
                new_full_path = os.path.join(settings.MEDIA_ROOT, new_relative_path)

                # Ensure directory exists
                os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

                # 🔥 FIX: If target file already exists, delete it before rename
                if os.path.exists(new_full_path):
                    os.remove(new_full_path)

                os.rename(new_uploaded_path, new_full_path)
                instance.photograph.name = new_relative_path
                instance.save(update_fields=["photograph"])

        # 🔹 Set messages based on status
        if instance.status and instance.status.status_id == "1":
            messages.success(self.request, "✅ Staff record updated and now marked as COMPLETATO.")
        else:
            messages.info(self.request, "🕓 Staff record updated (still Non Completo). Fill remaining fields to complete it.")

        return super().form_valid(form)
  