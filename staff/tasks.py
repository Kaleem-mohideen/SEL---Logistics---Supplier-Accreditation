# staff/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import ExportLog, StaffMember, ExportTracker
from .export_utils import generate_workbook_from_qs, make_export_zip_with_photos, log_export
import io

@shared_task
def test_task(name):
    print(f"Celery is running: {name}")
    return f"Hello {name}"
    
User = get_user_model()

@shared_task(bind=True)
def celery_export_task(self, pks, user_id, include_photos=False):
    """
    pks: list of StaffMember pks to export
    """
    user = User.objects.filter(pk=user_id).first()
    qs = StaffMember.objects.filter(pk__in=pks).order_by("pk")
    if not qs.exists():
        return {"status": "no_records"}

    wb, count = generate_workbook_from_qs(qs)
    # create zip if photos included
    if include_photos:
        resp, saved_filename = make_export_zip_with_photos(wb, qs, include_photos=True)
        # since this runs inside celery, we should save the zip to disk and store path in ExportLog
        export_dir = Path(settings.MEDIA_ROOT) / "exports"
        export_dir.mkdir(exist_ok=True)
        filename = f"Plog_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with open(export_dir / filename, "wb") as f:
            f.write(resp.content)
        ExportLog.objects.create(exported_by=user, file_name=filename, record_count=count, notes="async zip")
        # send email to user with download link (or admin)
        if user and user.email:
            send_mail("Your export is ready", f"Download: {settings.MEDIA_URL}exports/{filename}", settings.DEFAULT_FROM_EMAIL, [user.email])
        return {"status": "ok", "file": filename}
    else:
        # save excel to file and store
        export_dir = Path(settings.MEDIA_ROOT) / "exports"
        export_dir.mkdir(exist_ok=True)
        filename = f"Plog_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with open(export_dir / filename, "wb") as f:
            wb.save(f)
        ExportLog.objects.create(exported_by=user, file_name=filename, record_count=count, notes="async excel")
        if user and user.email:
            send_mail("Your export is ready", f"Download: {settings.MEDIA_URL}exports/{filename}", settings.DEFAULT_FROM_EMAIL, [user.email])
        return {"status": "ok", "file": filename}
