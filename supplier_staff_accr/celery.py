import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "supplier_staff_accr.settings")

app = Celery("supplier_staff_accr")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
