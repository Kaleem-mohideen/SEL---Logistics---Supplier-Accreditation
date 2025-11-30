# staff/models.py
from django.db import models, transaction
from django.conf import settings
from accounts.models import Supplier
from pathlib import Path

# from .models_lookup import (
#     FunctionCode, Venue, Gender, Nationality, Document,
#     CountryIssuingDocument, CountryOfBirth, PlaceOrCityOfBirth, Status
# )

class FunctionCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.description}"


class Venue(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Gender(models.Model):
    code = models.CharField(max_length=1, unique=True)
    label = models.CharField(max_length=50)

    def __str__(self):
        return self.code


class Nationality(models.Model):
    code = models.CharField(max_length=10, unique=True)
    country_name = models.CharField(max_length=255)

    def __str__(self):
        return self.country_name

class DocumentTypeRestriction(models.Model):
    nationality = models.ForeignKey(
        Nationality,
        on_delete=models.CASCADE,
        related_name="document_restrictions"
    )
    allow_identity_card = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nationality.country_name} — ID Allowed: {self.allow_identity_card}"


class Document(models.Model):
    type_name = models.CharField(max_length=100)

    def __str__(self):
        return self.type_name


class CountryIssuingDocument(models.Model):
    code = models.CharField(max_length=10, unique=True)
    country_name = models.CharField(max_length=255)

    def __str__(self):
        return self.country_name


class CountryOfBirth(models.Model):
    code = models.CharField(max_length=10, unique=True)
    country_name = models.CharField(max_length=255)

    def __str__(self):
        return self.country_name


class PlaceOrCityOfBirth(models.Model):
    city_name = models.CharField(max_length=255)
    category = models.ForeignKey(CountryOfBirth, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'country_name': 'Italy'})
    
    def save(self, *args, **kwargs):
        # if self.category is None:  # Assign only if empty
        from .models import CountryOfBirth
        self.category = CountryOfBirth.objects.filter(country_name="Italy").first()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.city_name


class Status(models.Model):
    status_id = models.CharField(max_length=5, unique=True)
    label = models.CharField(max_length=100)

    def __str__(self):
        return self.label



class StaffMember(models.Model):
    # Supplier relation
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)

    # Fixed fields (always the same value)
    organisation = models.CharField(max_length=50, default="Poste Italiane")
    registration_group = models.CharField(max_length=50, default="OCOG - NATIONAL PARTNER OPERATIONS STAFF (1PP)")
    discipline = models.CharField(max_length=50, default="", blank=True)
    organisation_reference_number = models.CharField(max_length=70, default="", blank=True)
    unknown_given_name = models.CharField(max_length=25, default="No")
    unknown_family_name = models.CharField(max_length=25, default="No")
    preferred_given_name = models.CharField(max_length=25, blank=True)
    preferred_family_name = models.CharField(max_length=25, blank=True)
    unknown_date_of_birth = models.CharField(max_length=50, default="Date of birth is correct")
    wheelchair_user = models.CharField(max_length=10, default="No")
    transferable_wheelchair_user = models.CharField(max_length=10, default="No")

    # Checkbox fields
    olympic_request = models.BooleanField(default=False)
    paralympic_request = models.BooleanField(default=False)

    # Foreign key/value list fields
    function_code = models.ForeignKey(FunctionCode, on_delete=models.SET_NULL, null=True)
    venue = models.ManyToManyField(Venue, blank=True)  # up to 7
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True)
    nationality = models.ForeignKey(Nationality, on_delete=models.SET_NULL, null=True)
    document_type = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True)
    country_issuing_document = models.ForeignKey(CountryIssuingDocument, on_delete=models.SET_NULL, null=True)
    country_of_birth = models.ForeignKey(CountryOfBirth, on_delete=models.SET_NULL, null=True)
    place_or_city_of_birth = models.ForeignKey(PlaceOrCityOfBirth, on_delete=models.SET_NULL, null=True)

    # Free-text / date fields
    document_given_name = models.CharField(max_length=25)
    document_middle_name = models.CharField(max_length=25, blank=True)
    document_family_name = models.CharField(max_length=25)
    date_of_birth = models.DateField()
    document_number = models.CharField(max_length=20)
    document_expiry = models.DateField(null=True, blank=True)
    email_address = models.EmailField(max_length=70)
    photograph = models.ImageField(upload_to="photos/")

    # System-generated identifiers
    plog_unique_id = models.CharField(max_length=80, editable=False, unique=True)
    # elearning_id = models.CharField(max_length=8, blank=True, null=True)
    worker_unique_id = models.CharField(max_length=80, unique=True, blank=True, null=True)
    # reg_id = models.CharField(max_length=20, blank=True, null=True)
    # accred_id = models.CharField(max_length=20, blank=True, null=True)


    # Registration metadata
    created_at = models.DateTimeField(auto_now_add=True)
    registration_date = models.DateField(auto_now_add=True)
    registration_time = models.TimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    # Status from reference table
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, default=1)

    def status_color(self):
        """Return a bootstrap badge color depending on status label."""
        label = self.status.label.lower() if self.status else ""
        if label in ["approved", "validated", "completed", "completato"]:
            return "success"
        return "danger"

    def evaluate_completion_status(self):
        """Evaluate if record should be marked as Completato based on filled fields."""
        minimal_fields = [
            self.document_given_name,
            self.document_family_name,
            self.date_of_birth,
            self.gender_id,
        ]

        extended_fields = [
            self.olympic_request,
            self.paralympic_request,
            self.nationality_id,
            self.document_type_id,
            self.document_number,
            self.document_expiry,
            self.country_issuing_document_id,
            self.country_of_birth_id,
            self.email_address,
            self.worker_unique_id,
            # self.venue.exists(),  # must have at least one venue
        ]

        # Conditional rule: if Italy, place of birth is mandatory
        italy_ok = True
        if self.country_of_birth and self.country_of_birth.country_name.lower() == "italy":
            italy_ok = bool(self.place_or_city_of_birth_id)

        if all(minimal_fields) and all(extended_fields) and italy_ok:
            status_obj, _ = Status.objects.get_or_create(status_id="1", defaults={"label": "Completato"})
        else:
            status_obj, _ = Status.objects.get_or_create(status_id="0", defaults={"label": "Non Completo"})

        self.status = status_obj
        return self.status

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Assign PLOG UNIQUE ID = SupplierCode + progressive count
        if not self.plog_unique_id:
            last = (
                StaffMember.objects.filter(supplier=self.supplier)
                .order_by("-plog_unique_id")
                .first()
            )

            if last:
                try:
                    last_num = int(last.plog_unique_id.replace(self.supplier.code, ""))
                except:
                    last_num = 0
            else:
                last_num = 0

            new_num = last_num + 1
            self.plog_unique_id = f"{self.supplier.code}{new_num:02d}"

            # count = StaffMember.objects.filter(supplier=self.supplier).count() + 1
            # user_code = f"{count:02}"
            # self.plog_unique_id = f"{self.supplier.code}{user_code}"
            
        # Auto-fill fixed fields based on the rules
        if not self.preferred_given_name:
            self.preferred_given_name = self.document_given_name
        if not self.preferred_family_name:
            self.preferred_family_name = self.document_family_name

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document_family_name} {self.document_given_name} ({self.plog_unique_id})"


class DocumentExpiryRule(models.Model):
    COUNTRY_GROUP_CHOICES = [
        ("EU", "EU Nationality"),
        ("NON_EU", "Non-EU Nationality"),
    ]

    EVENT_CHOICES = [
        ("OLY", "Olympics"),
        ("PAR", "Paralympics"),
    ]

    DOC_TYPE_CHOICES = [
        ("passport", "Passport"),
        ("id_card", "Identity Card"),
    ]

    country_group = models.CharField(max_length=10, choices=COUNTRY_GROUP_CHOICES)
    event_type = models.CharField(max_length=5, choices=EVENT_CHOICES)
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    min_expiry_date = models.DateField()

    class Meta:
        unique_together = ("country_group", "event_type", "document_type")

    def __str__(self):
        return f"{self.country_group} - {self.event_type} - {self.document_type}"

class ExportTracker(models.Model):
    """
    Track last exported PK per category and per supplier.
    Key examples:
      - completed                (global)
      - completed_supplier_{id}  (per supplier)
      - not_completed
      - all
      - all_supplier_{id}
    """
    key = models.CharField(max_length=100, unique=True)
    last_exported_pk = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key} -> {self.last_exported_pk}"


class ExportLog(models.Model):
    exported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    file_name = models.CharField(max_length=255)
    record_count = models.PositiveIntegerField(default=0)
    suppliers = models.TextField(blank=True)  # comma separated supplier codes (optional)
    exported_at = models.DateTimeField(auto_now_add=True)
    done = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.file_name} ({self.record_count} records)  - {self.exported_at.strftime('%Y-%m-%d %H:%M:%S')}"        



class ExportedZipFile(models.Model):
    """
    Tracks all generated ZIP or XLSX files saved in MEDIA_ROOT/exports/.
    """
    filename = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def path(self):
        return Path(settings.MEDIA_ROOT) / "exports" / self.filename

    @property
    def size_mb(self):
        try:
            return round(self.path.stat().st_size / (1024*1024), 2)
        except FileNotFoundError:
            return 0

    def __str__(self):
        return self.filename
