# accounts/signals.py
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import LoginAttempt

User = get_user_model()

@receiver(user_logged_in)
def log_success(sender, request, user, **kwargs):
    """Logs successful logins"""
    ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    LoginAttempt.objects.create(
        username=getattr(user, 'username', None),  # use username safely
        user=user,
        ip_address=ip,
        success=True
    )

@receiver(user_login_failed)
def log_failed(sender, credentials, request, **kwargs):
    """Logs failed login attempts"""
    ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    LoginAttempt.objects.create(
        username=credentials.get('username', None),  # correct field name
        ip_address=ip,
        success=False
    )