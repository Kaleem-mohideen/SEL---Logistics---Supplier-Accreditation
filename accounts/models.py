# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, user_id, user_email, password=None, **extra_fields):
        if not user_id:
            raise ValueError("The user_id field must be set")
        if not user_email:
            raise ValueError("The user_email field must be set")

        email = self.normalize_email(user_email)
        user = self.model(user_id=user_id, user_email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, user_email, password=None, **extra_fields):
        from accounts.models import Supplier  # local import to avoid circular import
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'reg')  # optional: REG Team role for admin

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Assign default supplier if not provided
        if 'supplier' not in extra_fields or not extra_fields['supplier']:
            supplier, _ = Supplier.objects.get_or_create(code='ADMIN', defaults={'name': 'Admin Supplier'})
            extra_fields['supplier'] = supplier

        return self.create_user(user_id, user_email, password, **extra_fields)

class Supplier(models.Model):
    code = models.CharField(max_length=10, primary_key=True)  # e.g. SA02
    name = models.CharField(max_length=255)

    # NEW FIELD
    allow_frontend_export = models.BooleanField(default=False)
    
    # ✅ Add FunctionCode FK here
    function_code = models.ForeignKey(
        "staff.FunctionCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suppliers"
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

class DisabledVenueSupplier(models.Model):
    supplier = models.OneToOneField(
        'accounts.Supplier',
        on_delete=models.CASCADE,
        related_name='venue_disabled_rule'
    )
    reason = models.CharField(max_length=255, blank=True, help_text="Optional note for why venue is disabled")

    def __str__(self):
        return f"{self.supplier.code} - Venue Disabled"

class User(AbstractUser):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='users')
    user_code = models.CharField(max_length=2)  # 01–99
    user_id = models.CharField(max_length=20, unique=True)  # SA0201
    user_name = models.CharField(max_length=255)
    user_email = models.EmailField(unique=True)

    ROLE_CHOICES = (
        ('supplier_user', 'Supplier User'),
        ('reg', 'REG Team'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='supplier_user')

    # remove default name fields
    first_name = None
    last_name = None
    email = None
    objects = CustomUserManager()

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['user_email', 'user_name']


    def save(self, *args, **kwargs):
        if not self.user_id and self.supplier and self.user_code:
            self.user_id = f"{self.supplier.code}{self.user_code}"

        # Keep AbstractUser happy — ensure username is populated uniquely
        self.username = self.user_name  

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.user_id} ({self.user_name})"

class LoginAttempt(models.Model):
    username = models.CharField(max_length=150, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} - {'OK' if self.success else 'FAIL'} @ {self.timestamp:%Y-%m-%d %H:%M}"
