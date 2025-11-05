from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Supplier, LoginAttempt
from itertools import count

# from .forms import UserCreationForm, UserChangeForm  # optional if you have them

User = get_user_model()


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('row_number', 'code', 'name', 'function_code')
    search_fields = ('code', 'name')
    ordering = ('code',)

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