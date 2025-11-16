from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Supplier, LoginAttempt, DisabledVenueSupplier
from itertools import count

# from .forms import UserCreationForm, UserChangeForm  # optional if you have them

User = get_user_model()

@admin.register(DisabledVenueSupplier)
class DisabledVenueSupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier", "reason")
    search_fields = ("supplier__code", "supplier__name")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "supplier":
            # Exclude suppliers already in the disabled table
            disabled = DisabledVenueSupplier.objects.values_list("supplier_id", flat=True)
            kwargs["queryset"] = Supplier.objects.exclude(code__in=disabled)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)    

@admin.action(description="Disable venue selection for selected suppliers")
def disable_venue_selection(modeladmin, request, queryset):
    for supplier in queryset:
        DisabledVenueSupplier.objects.get_or_create(supplier=supplier)

@admin.action(description="Enable venue selection (remove restriction)")
def enable_venue_selection(modeladmin, request, queryset):
    DisabledVenueSupplier.objects.filter(supplier__in=queryset).delete()

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('row_number', 'code', 'name', 'function_code')
    search_fields = ('code', 'name')
    ordering = ('code',)
    actions = [disable_venue_selection, enable_venue_selection]

    _counter = count()

    def row_number(self, obj):
        return next(self._counter)

    def get_queryset(self, request):
        self._counter = count()  # reset numbering when page is refreshed
        return super().get_queryset(request)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for the custom User model."""
    model = User

    # Fields shown in the list view
    list_display = (
        'user_id', 'user_name', 'user_email', 'supplier',
        'role', 'is_staff', 'is_active'
    )
    list_filter = ('is_staff', 'is_active', 'role', 'supplier')

    # Fields to search by
    search_fields = ('user_id', 'user_name', 'user_email', 'supplier__name')

    ordering = ('user_id',)

    # Customize fieldsets for editing users
    fieldsets = (
        (None, {'fields': ('user_id', 'password')}),
        (_('Personal info'), {'fields': ('user_name', 'user_email', 'supplier', 'user_code', 'role')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Fields shown when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('user_id', 'user_name', 'user_email', 'supplier', 'user_code', 'role', 'password1', 'password2'),
        }),
    )

    # Optional: attach your custom forms if you have them
    # add_form = UserCreationForm
    # form = UserChangeForm


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("username", "user", "ip_address", "success", "timestamp")
    list_filter = ("success", "timestamp")
    search_fields = ("username", "user__username", "ip_address")
    ordering = ("-timestamp",)
    readonly_fields = ("username", "user", "ip_address", "success", "timestamp")

    def has_add_permission(self, request):
        """Prevent manual creation of login attempts."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of login attempt log entries."""
        return False