# staff/forms.py
from django import forms
from .models import StaffMember, Venue, FunctionCode, DocumentTypeRestriction, Document, Nationality
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from accounts.models import DisabledVenueSupplier


class DocumentTypeRestrictionAdminForm(forms.ModelForm):
    class Meta:
        model = DocumentTypeRestriction
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        used_nationalities = DocumentTypeRestriction.objects.values_list(
            "nationality_id", flat=True
        )

        # If editing an existing entry — lock nationality field
        if self.instance.pk:
            # Disable editing nationality
            self.fields["nationality"].widget.attrs["disabled"] = True

            # Preload the existing selected value only
            self.fields["nationality"].queryset = Nationality.objects.filter(
                id=self.instance.nationality_id
            )

        else:
            # Creating new restriction → exclude used nationalities
            self.fields["nationality"].queryset = Nationality.objects.exclude(
                id__in=used_nationalities
            )

    def clean_nationality(self):
        """
        When field is disabled, HTML will not submit its value.
        So we must return the existing nationality instance manually.
        """
        if self.instance.pk:  # editing → keep old value
            return self.instance.nationality
        
        # creating new → return the chosen nationality
        return self.cleaned_data.get("nationality")

class StaffMemberForm(forms.ModelForm):

    class Meta:
        model = StaffMember
        exclude = ("supplier", "plog_unique_id", "created_at", "organisation", "registration_group", "unknown_given_name", "unknown_family_name", "unknown_date_of_birth", "wheelchair_user", "transferable_wheelchair_user")

        widgets = {
            "olympic_request": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "paralympic_request": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "function_code": forms.Select(attrs={"class": "form-select", "readonly": "readonly"}),
            # ✅ Modern Multi-select UI (Searchable + Tags)
            "venue": forms.SelectMultiple(attrs={
                "class": "form-select venue-select",   # class used for JS enhancement
                # "size": 5,  # allow multiple selections with visible area
                "data-placeholder": "Select up to 7 venues"
            }),

            "document_given_name": forms.TextInput(attrs={"class": "form-control"}),
            "document_middle_name": forms.TextInput(attrs={"class": "form-control"}),
            "document_family_name": forms.TextInput(attrs={"class": "form-control"}),

            "date_of_birth": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),

            "gender": forms.Select(attrs={"class": "form-select"}),
            "nationality": forms.Select(attrs={"class": "form-select"}),

            "document_type": forms.Select(attrs={"class": "form-select"}),
            "document_number": forms.TextInput(attrs={"class": "form-control"}),
            "document_expiry": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),

            "country_issuing_document": forms.Select(attrs={"class": "form-select"}),
            "country_of_birth": forms.Select(attrs={"class": "form-select", "id": "id_country_of_birth"}),
            "place_or_city_of_birth": forms.Select(attrs={"class": "form-select", "id": "id_place_or_city_of_birth"}),

            "email_address": forms.EmailInput(attrs={"class": "form-control"}),

            "photograph": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/jpeg,image/png"}),

            "worker_unique_id": forms.TextInput(attrs={"class": "form-control"}),
            # "forniture_id": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        supplier = kwargs.pop("supplier", None)
        super().__init__(*args, **kwargs)

        for f in ["olympic_request", "paralympic_request"]:
            self.fields[f].widget.attrs.update({"class": "form-check-input"})
        # Mark all fields optional initially
        for field in self.fields.values():
            field.required = False

        # Explicitly mark minimal fields as required
        minimal_required = [
            "document_given_name",
            "document_family_name",
            "date_of_birth",
            "gender",
        ]
        # Step 3: Mark minimal fields as required and add red asterisk
        for f in minimal_required:
            if f in self.fields:
                self.fields[f].required = True
                self.fields[f].widget.attrs["required"] = "required"
                label = self.fields[f].label or f.replace("_", " ").title()
                self.fields[f].label = f"{label} <span class='text-danger fw-bold'>*</span>"
                
        # Venue queryset (all venues) - kept full but Select2 will help search
        self.fields["venue"].queryset = Venue.objects.all().order_by("name")

        # If a supplier instance provided, auto-assign and lock function_code
        if supplier is not None:
            # If supplier is known, check if in DisabledVenueSupplier table
            if DisabledVenueSupplier.objects.filter(supplier=supplier).exists():
                self.fields["venue"].disabled = True
                self.fields["venue"].help_text = (
                    "⚠️ Venue selection disabled for this supplier (controlled externally)."
                )            
            # supplier.function_code is FunctionCode or None
            if supplier.function_code:
                self.fields["function_code"].initial = supplier.function_code.pk
                # disable editing (user-friendly)
                self.fields["function_code"].disabled = True
            else:
                # allow choice if supplier has no function_code
                self.fields["function_code"].queryset = FunctionCode.objects.all()

        all_docs = Document.objects.all()

        # Detect nationality on:
        # - Edit form (instance has nationality)
        # - POST submission
        # - GET initial load
        nationality_id = None
        print("self.instance.nationality_id", self.instance.nationality_id)
        if self.instance and self.instance.pk and self.instance.nationality_id:
            nationality_id = self.instance.nationality_id
        elif "nationality" in self.data:
            nationality_id = self.data.get("nationality")
        elif "nationality" in self.initial:
            nationality_id = self.initial.get("nationality")

        if nationality_id:
            self.apply_doc_rules(nationality_id, all_docs)

    def apply_doc_rules(self, nationality_id, all_docs):
        """Apply passport-only restriction based on nationality rules."""
        restriction = DocumentTypeRestriction.objects.filter(
            nationality_id=nationality_id
        ).first()

        # Passport-only case:
        if not restriction or not restriction.allow_identity_card:
            self.fields["document_type"].queryset = all_docs.filter(
                type_name__icontains="passport"
            )
            self.fields["document_type"].widget.attrs.update({"data-passport-only": "1"})
            return

        # Identity card allowed:
        self.fields["document_type"].queryset = all_docs
        self.fields["document_type"].widget.attrs.update({"data-passport-only": "0"})

    def clean_photograph(self):
        file = self.cleaned_data.get("photograph")
        # if not file:
        #     raise ValidationError(_("Photograph is required."))
        # size limit 600MB
        limit = 600 * 1024 * 1024
        if file and file.size > limit:
            raise ValidationError(_("File too large ( > 600MB )."))
        # content type
        # Only validate content_type if this is an uploaded file
        if file and hasattr(file, 'content_type'):
            content_type = file.content_type
            if content_type not in ("image/jpeg", "image/png"):
                raise ValidationError(_("Unsupported file type. Use JPG or PNG."))
        return file

    def clean_venue(self):
        data = self.cleaned_data.get("venue")
        if data and len(data) > 7:
            raise ValidationError(_("You can select a maximum of 7 venues."))
        return data
    
    def clean_worker_unique_id(self):
        worker_id = self.cleaned_data.get("worker_unique_id")
        if worker_id:
            qs = StaffMember.objects.filter(worker_unique_id__iexact=worker_id)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)  # allow same object on update
            if qs.exists():
                raise ValidationError("❌ This Worker Unique ID already exists. Please use a different one.")
        return worker_id