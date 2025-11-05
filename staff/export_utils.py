import openpyxl
from openpyxl.styles import Font, Alignment
from django.utils import timezone
from pathlib import Path
from django.conf import settings
from .models import StaffMember, ExportLog


def safe_get(obj, field, default=""):
    """
    Safely resolve related fields.
    Example: safe_get(s, "nationality.name")
    """
    try:
        for part in field.split("."):
            obj = getattr(obj, part)
            if obj is None:
                return default
        return obj or default
    except Exception:
        return default


def export_staff_data(user):
    """Exports to Excel only those staff members having Status = 1 (Approved/Submitted)."""

    queryset = StaffMember.objects.filter(status__status_id="1").select_related(
        "function_code",
        "nationality",
        "gender",
        "document_type",
        "country_issuing_document",
        "country_of_birth",
        "place_or_city_of_birth",
        "supplier",
    ).prefetch_related("venue")

    if not queryset.exists():
        return None, "NO_RECORDS"

    export_dir = Path(settings.MEDIA_ROOT) / "exports"
    export_dir.mkdir(exist_ok=True)

    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"Plog_{timestamp}.xlsx"
    file_path = export_dir / filename

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Export"

    headers = [
        "Request Olympic*", "Request Paralympic*", "Organisation*",
        "Registration Group*", "Function Code*", "Venue(s)",
        "Discipline(s)", "Organisation Reference Number",
        "Given Name*", "Unknown Given Name*", "Document Middle Name",
        "Family Name*", "Unknown Family Name*",
        "Preferred Given Name*", "Preferred Family Name*",
        "Date of Birth*", "Unknown Date of Birth*",
        "Gender*", "Nationality*", "Document Type*",
        "Document Number*", "Document Expiry*",
        "Country Issuing Document*", "Country of Birth*",
        "Place / City of Birth*", "Email Address*",
        "Photograph", "Wheelchair User*", "Transferable Wheelchair User*",
    ]

    ws.append(headers)

    bold = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold
        cell.alignment = Alignment(horizontal="center")

    for s in queryset:
        row = [
            "Yes" if s.olympic_request else "No",
            "Yes" if s.paralympic_request else "No",
            safe_get(s, "supplier.name"),
            "OCOG - STAFF",  # fixed value per requirement
            safe_get(s, "function_code.code"),
            ", ".join([v.name for v in s.venue.all()]) if s.venue.exists() else "",
            "",  # Discipline* (not used yet)
            getattr(s, "reference_number", ""),
            s.document_given_name,
            "Yes" if getattr(s, "unknown_given_name", False) else "No",
            s.document_middle_name,
            s.document_family_name,
            "Yes" if getattr(s, "unknown_family_name", False) else "No",
            getattr(s, "preferred_given_name", ""),
            getattr(s, "preferred_family_name", ""),
            s.date_of_birth.strftime("%d.%m.%Y") if s.date_of_birth else "",
            "Date of birth is correct",
            safe_get(s, "gender.label"),
            safe_get(s, "nationality.name"),
            safe_get(s, "document_type.type_name"),
            s.document_number,
            s.document_expiry.strftime("%d.%m.%Y") if s.document_expiry else "",
            safe_get(s, "country_issuing_document.country_name"),
            safe_get(s, "country_of_birth.country_name"),
            safe_get(s, "place_or_city_of_birth.city_name"),
            s.email_address,
            s.photograph.name if s.photograph else "",
            "Yes" if getattr(s, "wheelchair_user", False) else "No",
            "Yes" if getattr(s, "transferable_wheelchair_user", False) else "No",
        ]

        ws.append(row)

    wb.save(file_path)

    # log export
    ExportLog.objects.create(
        file_name=filename,
        record_count=queryset.count(),
        exported_by=user,
    )

    return filename, "OK"
