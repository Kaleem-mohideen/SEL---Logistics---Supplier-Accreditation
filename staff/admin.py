from django.contrib import admin
from .models import (
    FunctionCode,
    Venue,
    Gender,
    Nationality,
    Document,
    CountryIssuingDocument,
    CountryOfBirth,
    PlaceOrCityOfBirth,
    Status,
    StaffMember,
    ExportLog,
)
from django.utils.html import format_html
from django.urls import reverse
from django import forms

from django.http import JsonResponse
from django.urls import path
from accounts.models import Supplier

def get_function_code(request, supplier_code):
    """Return supplier's assigned function_code for admin auto-fill"""
    try:
        supplier = Supplier.objects.get(code=supplier_code)
        if supplier.function_code:
            return JsonResponse({"function_code_id": supplier.function_code.id})
        else:
            return JsonResponse({"function_code_id": None})
    except Supplier.DoesNotExist:
        return JsonResponse({"error": "Supplier not found"}, status=404)

# ✅ Add custom CSS to admin without overriding AdminSite
admin.site.site_header = "Django administration"

class CustomAdminMedia:
    class Media:
        css = {
            "all": ("css/admin_custom.css",)
        }

# ✅ Apply to all ModelAdmins dynamically
for model, model_admin in admin.site._registry.items():
    model_admin.__class__.__bases__ += (CustomAdminMedia,)

@admin.register(FunctionCode)
class FunctionCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")
    ordering = ("code",)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(Gender)
class GenderAdmin(admin.ModelAdmin):
    list_display = ("code", "label")
    search_fields = ("code", "label")
    ordering = ("code",)


@admin.register(Nationality)
class NationalityAdmin(admin.ModelAdmin):
    list_display = ("code", "country_name")
    search_fields = ("code", "country_name")
    ordering = ("country_name",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("type_name",)
    search_fields = ("type_name",)
    ordering = ("type_name",)


@admin.register(CountryIssuingDocument)
class CountryIssuingDocumentAdmin(admin.ModelAdmin):
    list_display = ("code", "country_name")
    search_fields = ("code", "country_name")
    ordering = ("country_name",)


@admin.register(CountryOfBirth)
class CountryOfBirthAdmin(admin.ModelAdmin):
    list_display = ('pk', "code", "country_name")
    search_fields = ("code", "country_name")
    ordering = ("country_name",)


@admin.register(PlaceOrCityOfBirth)
class PlaceOrCityOfBirthAdmin(admin.ModelAdmin):
    list_display = ("city_name", "category")
    search_fields = ("city_name",)
    ordering = ("city_name",)
    autocomplete_fields = ("category",)

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("status_id", "label")
    search_fields = ("status_id", "label")
    ordering = ("status_id",)

class StaffMemberAdminForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make specific fields optional in admin
        optional_fields = [
            "function_code",
            "nationality",
            "document_type",
            "country_issuing_document",
            "country_of_birth",
            "place_or_city_of_birth",
            "document_number",
            "document_expiry",
            "email_address",
            "photograph",
            # "worker_unique_id",
        ]
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False

        # ✅ Auto-fill Function Code if Supplier already chosen
        supplier = getattr(self.instance, "supplier", None)
        if supplier and supplier.function_code:
            self.fields["function_code"].initial = supplier.function_code.pk

        # ✅ If editing an existing record (supplier locked), keep function_code editable
        # but re-populate queryset safely
        self.fields["function_code"].queryset = FunctionCode.objects.all()

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    form = StaffMemberAdminForm
    list_display = (
        "plog_unique_id",
        "document_family_name",
        "document_given_name",
        "function_code",
        "colored_status",        
        "supplier",
        "registered_by", 
        "created_at",
        # "export_button",
    )

    list_filter = (
        "status",
        "function_code",
        "nationality",
        "gender",
        "supplier",
    )

    search_fields = (
        "plog_unique_id",
        "document_family_name",
        "document_given_name",
        "document_number",
        "email_address",
    )

    readonly_fields = (
        "plog_unique_id",
        "created_at",
    )

    filter_horizontal = ("venue",)   # Better UI for ManyToMany fields

    ordering = ("-created_at",)

    change_list_template = "admin/staff/staffmember/change_list.html"

    # def export_button(self, obj):
    #     url = reverse("staff:export_reg_excel")
    #     return format_html(f'<a class="button" href="{url}">⬇ Export Status #1</a>')
    # export_button.short_description = "Export"

    def get_readonly_fields(self, request, obj=None):
        """Disable editing of user (registered_by) once set."""
        readonly = list(self.readonly_fields)
        if obj and obj.user:  # existing record and user already assigned
            readonly.append("user")
        return readonly

    @admin.display(description="Status")
    def colored_status(self, obj):
        color = obj.status_color()
        return format_html(
            '<span style="color: var(--bs-{0}); font-weight:bold;">{1}</span>',
            color,
            obj.status.label,
        )
        
    @admin.display(description="Registered By")
    def registered_by(self, obj):
        return obj.user.username if obj.user else "—"

    class Media:
        js = ("js/staff_autofill.js",)

    # ✅ Add custom admin URL for AJAX calls
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("get_function_code/<str:supplier_code>/", self.admin_site.admin_view(get_function_code)),
        ]
        return custom_urls + urls

@admin.register(ExportLog)
class ExportLogAdmin(admin.ModelAdmin):
    list_display = ("file_name", "record_count", "exported_at", "exported_by")
    readonly_fields = ("file_name", "record_count", "exported_at", "exported_by")