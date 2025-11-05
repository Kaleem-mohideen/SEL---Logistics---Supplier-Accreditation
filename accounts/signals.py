# accounts/signals.py
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import LoginAttempt

@receiver(user_logged_in)
def log_success(sender, user, request, **kwargs):
    LoginAttempt.objects.create(
        username=user.user_id,
        user=user,
        ip_address=request.META.get('REMOTE_ADDR'),
        success=True
    )

@receiver(user_login_failed)
def log_failed(sender, credentials, request, **kwargs):
    LoginAttempt.objects.create(
        username=credentials.get('user_id'),
        ip_address=request.META.get('REMOTE_ADDR'),
        success=False
    )
