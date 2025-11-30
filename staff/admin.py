from django.contrib import admin
from .models import (
    FunctionCode,
    Venue,
    Gender,
    Nationality,
    DocumentTypeRestriction,
    Document,
    CountryIssuingDocument,
    CountryOfBirth,
    PlaceOrCityOfBirth,
    Status,
    StaffMember,
    ExportLog,
    DocumentExpiryRule,
    ExportTracker,
)
from django.utils.html import format_html
from django.urls import reverse
from django import forms

from django.http import JsonResponse, FileResponse, Http404
from django.urls import path
from accounts.models import Supplier
from .forms import DocumentTypeRestrictionAdminForm, DocumentExpiryRuleForm
from .views import admin_export_flagged, export_counts_view, admin_supplier_list
# from django.db.models import Max
from django.shortcuts import redirect
from django.conf import settings
from pathlib import Path
from .models import ExportedZipFile

@admin.register(ExportedZipFile)
class ExportedZipFileAdmin(admin.ModelAdmin):
    list_display = ("filename", "created_at", "size_mb", "file_actions")
    readonly_fields = ("filename", "created_at")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("download/<str:filename>/", self.admin_site.admin_view(self.download_file), name="exportedzipfile_download"),
            path("delete/<str:filename>/", self.admin_site.admin_view(self.delete_file), name="exportedzipfile_delete"),
        ]
        return custom + urls

    @admin.display(description="Actions")
    def file_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Download</a>&nbsp;'
            '<a class="button" style="background:#d9534f;color:white;" href="{}">Delete</a>',
            reverse("admin:exportedzipfile_download", args=[obj.filename]),
            reverse("admin:exportedzipfile_delete", args=[obj.filename]),
        )

    def download_file(self, request, filename):
        filepath = Path(settings.MEDIA_ROOT) / "exports" / filename
        if not filepath.exists():
            raise Http404("File missing")

        return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)

    def delete_file(self, request, filename):
        ExportedZipFile.objects.filter(filename=filename).delete()
        filepath = Path(settings.MEDIA_ROOT) / "exports" / filename
        if filepath.exists():
            filepath.unlink()
        self.message_user(request, f"Deleted {filename}")
        return redirect("admin:staff_exportedzipfile_changelist")

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


@admin.register(DocumentExpiryRule)
class DocumentExpiryRuleAdmin(admin.ModelAdmin):
    form = DocumentExpiryRuleForm
    list_display = ("country_group", "event_type", "document_type", "min_expiry_date")
    list_filter = ("country_group", "event_type", "document_type")
    search_fields = ("country_group", "event_type", "document_type")
    ordering = ("country_group", "event_type", "document_type")

    class Media:
        js = ("js/admin_document_rule_filter.js",)   # file path inside static/

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

@admin.register(DocumentTypeRestriction)
class DocumentTypeRestrictionAdmin(admin.ModelAdmin):
    form = DocumentTypeRestrictionAdminForm
    list_display = ("nationality", "allow_identity_card")
    list_filter = ("allow_identity_card",)
    search_fields = ("nationality__country_name", "nationality__code")


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

        # # Prevent Django from loading DateTimeShortcuts
        # for field_name in ['date_of_birth', 'document_expiry']:
        #     print("self.fields", self.fields)
        #     if field_name in self.fields:
        #         self.fields[field_name].widget.is_admin_related = False
        #         self.fields[field_name].widget.attrs['class'] = 'vDateField flatpickr-input'


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
        # Load Flatpickr library and your custom JS scripts
        js = [
            "https://cdn.jsdelivr.net/npm/flatpickr",  # Flatpickr core
            "js/staff_autofill.js",                   # your existing JS
            "js/staff_datepicker.js",                 # new date picker enhancements
        ]
        css = {
            "all": [
                "https://cdn.jsdelivr.net/npm/flatpickr/dist/themes/material_blue.css",
            ]
        }

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)

        # ✅ Guard 1: Skip fields without form widgets
        if not formfield:
            return formfield

        # ✅ Check if widget is a date widget
        if isinstance(getattr(formfield, "widget", None), admin.widgets.AdminDateWidget):
            # ✅ Create a subclass of the widget with no media
            class CleanDateWidget(formfield.widget.__class__):
                @property
                def media(self):
                    # Return empty media to prevent loading admin's calendar.js
                    return forms.Media(js=[], css={})

            # Replace the widget with our clean one
            formfield.widget = CleanDateWidget()

        return formfield

    # ✅ Add custom admin URL for AJAX calls
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("get_function_code/<str:supplier_code>/", self.admin_site.admin_view(get_function_code)),
            path("export/flag/<str:status>/<str:mode>/", admin_export_flagged, name="admin_export_flagged"),
            path("export/flag/supplier/<str:supplier_code>/<str:mode>/", admin_export_flagged, name="admin_export_flagged_supplier"),
            path("export/counts/", export_counts_view, name="admin_export_counts"),
            path("admin/suppliers/list/", admin_supplier_list, name="staff_supplier_list"),
        ]
        return custom_urls + urls

@admin.register(ExportTracker)
class ExportTrackerAdmin(admin.ModelAdmin):
    list_display = ("key", "last_exported_pk", "updated_at")
    actions = ["reset_tracker"]

    def reset_tracker(self, request, queryset):
        queryset.update(last_exported_pk=0)
        self.message_user(request, "Selected trackers reset.")
    reset_tracker.short_description = "Reset selected trackers to 0"


@admin.register(ExportLog)
class ExportLogAdmin(admin.ModelAdmin):
    list_display = ("file_name", "record_count", "exported_at", "exported_by")
    readonly_fields = ("file_name", "record_count", "exported_at", "exported_by")