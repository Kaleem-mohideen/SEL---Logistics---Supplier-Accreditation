# staff/forms.py
from django import forms
from .models import StaffMember, Venue, FunctionCode
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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
            # supplier.function_code is FunctionCode or None
            if supplier.function_code:
                self.fields["function_code"].initial = supplier.function_code.pk
                # disable editing (user-friendly)
                self.fields["function_code"].disabled = True
            else:
                # allow choice if supplier has no function_code
                self.fields["function_code"].queryset = FunctionCode.objects.all()

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