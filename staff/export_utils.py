import openpyxl
from pathlib import Path
from django.conf import settings
from django.utils.timezone import now
from .models import StaffMember, ExportLog, ExportedZipFile
import os
import io
import zipfile
from django.http import HttpResponse
from django.utils import timezone
from openpyxl.styles import Font, Alignment

def save_zip_to_media(zip_bytes, prefix="Plog"):
    """Save ZIP bytes to MEDIA_ROOT/exports/ and return filename."""
    export_dir = Path(settings.MEDIA_ROOT) / "exports"
    export_dir.mkdir(exist_ok=True)

    filename = f"{prefix}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
    filepath = export_dir / filename

    with open(filepath, "wb") as f:
        f.write(zip_bytes)

    ExportedZipFile.objects.create(filename=filename)
    return filename

def safe(value):
    return value if value else ""


def export_staff_data(user):

    # Load the template (must contain header + instruction rows only)
    template_path = Path(settings.BASE_DIR) / "templates/export/template.xlsx"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at: {template_path}")

    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    queryset = StaffMember.objects.filter(status__status_id="1") \
        .select_related(
            "function_code",
            "gender",
            "nationality",
            "document_type",
            "country_issuing_document",
            "country_of_birth",
            "place_or_city_of_birth"
        ).prefetch_related("venue").filter(supplier__code=user.supplier.code).order_by("pk")

    if not queryset.exists():
        return None, "NO_RECORDS"

    row = 4  # DATA ALWAYS STARTS HERE

    for s in queryset:

        # COLUMN-BY-COLUMN EXPORT
        ws.cell(row=row, column=1).value = "Yes" if s.olympic_request else "No"
        ws.cell(row=row, column=2).value = "Yes" if s.paralympic_request else "No"

        # Organisation (comes from model default)
        ws.cell(row=row, column=3).value = s.organisation

        # Registration Group (from model default)
        ws.cell(row=row, column=4).value = s.registration_group

        # Function Code
        ws.cell(row=row, column=5).value = safe(getattr(s.function_code, "code", ""))

        # Venues → comma-separated → NO SPACES
        venues = ",".join([v.code for v in s.venue.all()])  if s.venue.exists() else ""
        ws.cell(row=row, column=6).value = venues

        # Discipline (default empty)
        ws.cell(row=row, column=7).value = s.discipline

        # Organisation Reference Number
        ws.cell(row=row, column=8).value = s.organisation_reference_number

        # Given Name
        ws.cell(row=row, column=9).value = s.document_given_name

        # Unknown Given Name ("NO" – from model)
        ws.cell(row=row, column=10).value = s.unknown_given_name

        # Middle Name
        ws.cell(row=row, column=11).value = s.document_middle_name

        # Family Name
        ws.cell(row=row, column=12).value = s.document_family_name

        # Unknown Family Name ("NO")
        ws.cell(row=row, column=13).value = s.unknown_family_name

        # Preferred Given Name (model auto-fills)
        ws.cell(row=row, column=14).value = s.preferred_given_name

        # Preferred Family Name (model auto-fills)
        ws.cell(row=row, column=15).value = s.preferred_family_name

        # Date of Birth (DD.MM.YYYY)
        ws.cell(row=row, column=16).value = s.date_of_birth.strftime("%d.%m.%Y")

        # Unknown Date of Birth ("Date of birth is correct")
        ws.cell(row=row, column=17).value = s.unknown_date_of_birth

        # Gender label
        ws.cell(row=row, column=18).value = safe(getattr(s.gender, "code", ""))

        # Nationality Code (REG expects code)
        ws.cell(row=row, column=19).value = safe(getattr(s.nationality, "code", ""))

        # Document Type (exact REG name)
        ws.cell(row=row, column=20).value = s.document_type.type_name if s.document_type else ""

        # Document Number
        ws.cell(row=row, column=21).value = s.document_number

        # Document Expiry Date (DD.MM.YYYY)
        ws.cell(row=row, column=22).value = s.document_expiry.strftime("%d.%m.%Y") if s.document_expiry else ""

        # Country Issuing Document (code)
        ws.cell(row=row, column=23).value = safe(getattr(s.country_issuing_document, "code", ""))

        # Country of Birth (code)
        ws.cell(row=row, column=24).value = safe(getattr(s.country_of_birth, "code", ""))

        # Place of Birth (ONLY if Italy)
        if getattr(s.country_of_birth, "code", "") == "ITA":
            ws.cell(row=row, column=25).value = safe(getattr(s.place_or_city_of_birth, "city_name", ""))
        else:
            ws.cell(row=row, column=25).value = ""

        # Email
        ws.cell(row=row, column=26).value = s.email_address

        # Photograph → only filename
        ws.cell(row=row, column=27).value = (
            s.photograph.name.split("/")[-1] if s.photograph else ""
        )

        # Wheelchair User ("NO")
        ws.cell(row=row, column=28).value = s.wheelchair_user

        # Transferable Wheelchair User ("NO")
        ws.cell(row=row, column=29).value = s.transferable_wheelchair_user

        row += 1

    # SAVE EXPORT FILE
    export_dir = Path(settings.MEDIA_ROOT) / "exports"
    export_dir.mkdir(exist_ok=True)

    timestamp = now().strftime("%Y%m%d_%H%M")
    filename = f"Plog_{timestamp}.xlsx"
    output_path = export_dir / filename

    wb.save(output_path)

    ExportLog.objects.create(
        file_name=filename,
        exported_by=user,
        record_count=queryset.count()
    )

    return filename, "OK"

def generate_workbook_from_qs(qs, template_relative="templates/export/template.xlsx"):
    """
    Build an openpyxl workbook using the template and the queryset.
    Returns (wb, record_count).
    """
    template_path = settings.BASE_DIR / template_relative
    if not template_path.exists():
        raise FileNotFoundError(f"Missing template at {template_path}")

    wb = openpyxl.load_workbook(template_path)
    ws = wb.active
    start_row = 4

    for s in qs:
        row_data = [
            "Yes" if getattr(s, "olympic_request", False) else "No",
            "Yes" if getattr(s, "paralympic_request", False) else "No",
            s.organisation,
            s.registration_group,
            s.function_code.code if s.function_code else "",
            ",".join([v.code for v in s.venue.all()]) if s.venue.exists() else "",
            s.discipline,  # Discipline (empty)
            s.organisation_reference_number or "",
            s.document_given_name or "",
            s.unknown_given_name or "No",
            s.document_middle_name or "",
            s.document_family_name or "",
            s.unknown_family_name or "No",
            s.preferred_given_name or "",
            s.preferred_family_name or "",
            s.date_of_birth.strftime("%d.%m.%Y") if getattr(s, "date_of_birth", None) else "",
            s.unknown_date_of_birth,
            s.gender.code if s.gender else "",
            s.nationality.code if s.nationality else "",
            s.document_type.type_name if s.document_type else "",
            s.document_number or "",
            s.document_expiry.strftime("%d.%m.%Y") if getattr(s, "document_expiry", None) else "",
            s.country_issuing_document.code if s.country_issuing_document else "",
            s.country_of_birth.code if s.country_of_birth else "",
            s.place_or_city_of_birth.city_name if getattr(s.country_of_birth, "code", "") == "ITA" and s.place_or_city_of_birth else "",
            s.email_address or "",
            s.photograph.name.split("/")[-1] if getattr(s, "photograph", None) else "",
            s.wheelchair_user or "No",
            s.transferable_wheelchair_user or "No",
        ]
        for col_index, val in enumerate(row_data, start=1):
            ws.cell(row=start_row, column=col_index).value = val
        start_row += 1
        
    return wb, qs.count()

def workbook_to_http_response(wb, filename_prefix="Plog"):
    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"{filename_prefix}_{timestamp}.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response, filename

def make_export_zip_with_photos(wb, qs, include_photos=True, filename_prefix="Plog"):
    """
    Creates ZIP with Excel + photos.
    - Saves ZIP to MEDIA_ROOT/exports/
    - Returns HttpResponse for download
    - Also returns saved filename for logging
    """
    # 1) Convert Excel workbook to bytes
    excel_bytes = io.BytesIO()
    wb.save(excel_bytes)
    excel_bytes.seek(0)

    # 2) Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        # Excel name inside ZIP
        excel_name = f"{filename_prefix}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        zf.writestr(excel_name, excel_bytes.read())

        # Photos
        if include_photos:
            photos_dir = Path(settings.MEDIA_ROOT) / "photos"
            if photos_dir.exists():
                for s in qs:
                    if s.photograph:
                        fname = Path(s.photograph.name).name
                        file_path = photos_dir / fname
                        if file_path.exists():
                            zf.write(file_path, arcname=f"photos/{fname}")

    # Prepare ZIP bytes
    zip_buffer.seek(0)
    zip_bytes = zip_buffer.getvalue()

    # 3) SAVE ZIP TO MEDIA_ROOT/exports/
    saved_filename = save_zip_to_media(zip_bytes, prefix=filename_prefix)

    # 4) Also return as HttpResponse for browser download
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{saved_filename}"'
    

    return response, saved_filename


def log_export(user, filename, record_count, suppliers_str="", notes=""):
    ExportLog.objects.create(
        exported_by=user,
        file_name=filename,
        record_count=record_count,
        suppliers=suppliers_str,
        notes=notes,
    )
