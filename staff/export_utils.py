import openpyxl
from pathlib import Path
from django.conf import settings
from django.utils.timezone import now
from .models import StaffMember, ExportLog


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
        ).prefetch_related("venue")

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
        venues = ",".join([v.code for v in s.venue.all()])
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
        ws.cell(row=row, column=18).value = safe(getattr(s.gender, "label", ""))

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
        if getattr(s.country_of_birth, "country_code", "") == "ITA":
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
