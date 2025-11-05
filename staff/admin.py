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

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
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
        "worker_unique_id",
        "created_at",
    )

    filter_horizontal = ("venue",)   # Better UI for ManyToMany fields

    ordering = ("-created_at",)

    change_list_template = "admin/staff/staffmember/change_list.html"

    # def export_button(self, obj):
    #     url = reverse("staff:export_reg_excel")
    #     return format_html(f'<a class="button" href="{url}">⬇ Export Status #1</a>')
    # export_button.short_description = "Export"

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

@admin.register(ExportLog)
class ExportLogAdmin(admin.ModelAdmin):
    list_display = ("file_name", "record_count", "exported_at", "exported_by")
    readonly_fields = ("file_name", "record_count", "exported_at", "exported_by")