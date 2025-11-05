from django.db import models
from django.conf import settings
from accounts.models import Supplier

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
    unknown_given_name = models.CharField(max_length=25, default="NO")
    unknown_family_name = models.CharField(max_length=25, default="NO")
    preferred_given_name = models.CharField(max_length=25, blank=True)
    preferred_family_name = models.CharField(max_length=25, blank=True)
    unknown_date_of_birth = models.CharField(max_length=50, default="Date of birth is correct")
    wheelchair_user = models.CharField(max_length=10, default="NO")
    transferable_wheelchair_user = models.CharField(max_length=10, default="NO")

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
    document_expiry = models.DateField()
    email_address = models.EmailField(max_length=70)
    photograph = models.ImageField(upload_to="photos/")

    # System-generated identifiers
    plog_unique_id = models.CharField(max_length=80, editable=False)
    # elearning_id = models.CharField(max_length=8, blank=True, null=True)
    worker_unique_id = models.CharField(max_length=80)
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

    def save(self, *args, **kwargs):
        # Assign PLOG UNIQUE ID = SupplierCode + progressive count
        if not self.plog_unique_id:
            count = StaffMember.objects.filter(supplier=self.supplier).count() + 1
            user_code = f"{count:02}"
            print("****",f"{self.supplier.code}{user_code}")
            self.plog_unique_id = f"{self.supplier.code}{user_code}"
        # Auto-fill fixed fields based on the rules
        if not self.preferred_given_name:
            self.preferred_given_name = self.document_given_name
        if not self.preferred_family_name:
            self.preferred_family_name = self.document_family_name

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document_family_name} {self.document_given_name} ({self.plog_unique_id})"

class ExportLog(models.Model):
    file_name = models.CharField(max_length=255)
    exported_at = models.DateTimeField(auto_now_add=True)
    record_count = models.PositiveIntegerField(default=0)
    exported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.file_name} ({self.record_count} records)  - {self.exported_at.strftime('%Y-%m-%d %H:%M:%S')}"
