# staff/views.py
from django.views.generic import ListView, CreateView, UpdateView
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from .models import StaffMember, Status, ExportLog, Document, DocumentTypeRestriction, DocumentExpiryRule, ExportTracker

from accounts.models import Supplier
from .forms import StaffMemberForm
import pandas as pd
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required

from .export_utils import export_staff_data
from django.contrib import messages
from pathlib import Path
from django.conf import settings
import os
from django.core.files.storage import default_storage

import openpyxl
from openpyxl.utils import get_column_letter

import io
import zipfile
from django.db.models import Q, Max
from .export_utils import generate_workbook_from_qs, workbook_to_http_response, make_export_zip_with_photos, log_export
from django.utils import timezone

@staff_member_required
def admin_supplier_list(request):
    suppliers = Supplier.objects.all().values("code", "name")
    return JsonResponse(list(suppliers), safe=False)

# ----- helper to build queryset by category and supplier key -----
def build_base_qs(status_key, supplier_code=None):
    if status_key == "completed":
        qs = StaffMember.objects.filter(status__status_id="1")
    elif status_key == "not_completed":
        qs = StaffMember.objects.exclude(status__status_id="1")
    else:
        qs = StaffMember.objects.all()

    if supplier_code:
        qs = qs.filter(supplier__code=supplier_code)
    return qs.order_by("pk")

# ----- counts view used by admin dropdown (AJAX) -----
@staff_member_required
def export_counts_view(request):
    completed = StaffMember.objects.filter(status__status_id="1")
    not_completed = StaffMember.objects.exclude(status__status_id="1")
    all_qs = StaffMember.objects.all()

    def get_tracker(key):
        t, _ = ExportTracker.objects.get_or_create(key=key)
        return t

    trackers = {
        "completed": get_tracker("completed"),
        "not_completed": get_tracker("not_completed"),
        "all": get_tracker("all"),
    }

    data = {
        "completed_total": completed.count(),
        "completed_new": completed.filter(pk__gt=trackers["completed"].last_exported_pk).count(),
        "not_completed_total": not_completed.count(),
        "not_completed_new": not_completed.filter(pk__gt=trackers["not_completed"].last_exported_pk).count(),
        "all_total": all_qs.count(),
        "all_new": all_qs.filter(pk__gt=trackers["all"].last_exported_pk).count(),
    }
    return JsonResponse(data)

# ----- main admin export endpoint (flagged) -----
@staff_member_required
def admin_export_flagged(request, status=None, mode=None, supplier_code=None, include_photos=True, async_task=False):
    """
    status: completed | not_completed | all
    mode: new | all
    supplier_code: optional supplier code string
    include_photos: bool
    async_task: if True, delegate to Celery
    """
    # Case 1 — supplier export (URL: supplier/<code>/<mode>/)
    if supplier_code and not status:
        status = "all"  # default for supplier exports

    if status not in ("completed", "not_completed", "all"):
        return HttpResponse("Invalid status", status=400)
    if mode not in ("new", "all"):
        return HttpResponse("Invalid mode", status=400)

    base_qs = build_base_qs(status, supplier_code=supplier_code)

    # Apply 'new' logic via tracker
    tracker_key = status if not supplier_code else f"{status}_supplier_{supplier_code}"
    tracker_obj, _ = ExportTracker.objects.get_or_create(key=tracker_key)

    if mode == "new":
        qs = base_qs.filter(pk__gt=tracker_obj.last_exported_pk)
    else:
        qs = base_qs

    if not qs.exists():
        return JsonResponse({"error": "No records to export"}, status=400)
        # return HttpResponse("No records to export", status=404)

    # Optional: If big and async requested → enqueue
    if async_task:
        # We'll call Celery task below; return a simple page
        from .tasks import celery_export_task
        job = celery_export_task.delay(list(qs.values_list("pk", flat=True)), request.user.id, include_photos)
        return render(request, "admin/staff/async_export_started.html", {"job_id": job.id})

    # Validate data before exporting
    # Build list of invalid records (simple checks example)
    invalid = []
    for s in qs:
        if not s.document_given_name or not s.document_family_name or not s.date_of_birth or not s.gender:
            invalid.append({
                "pk": s.pk,
                "plog": s.plog_unique_id,
                "reason": "Missing required fields (given/family/email)"
            })

    if invalid:
        # render validation page with option to force-export
        return render(request, "admin/staff/export_validation.html", {
            "invalid": invalid,
            "count_ok": qs.count() - len(invalid),
            "status": status, "mode": mode, "supplier_code": supplier_code,
        })

    # Build workbook
    wb, count = generate_workbook_from_qs(qs)
    # If include_photos → ZIP
    if include_photos:
        resp, saved_filename = make_export_zip_with_photos(wb, qs, include_photos=True)
        # update tracker if mode==new
        if mode == "new":
            tracker_obj.last_exported_pk = qs.order_by("-pk").first().pk
            tracker_obj.save()
        # log export
        log_export(request.user, resp.get("Content-Disposition", ""), count, suppliers_str=(supplier_code or ""))
        return resp

    # normal excel
    resp, filename = workbook_to_http_response(wb)
    # update tracker if mode==new
    if mode == "new":
        tracker_obj.last_exported_pk = qs.order_by("-pk").first().pk
        tracker_obj.save()
    # log export
    log_export(request.user, filename, count, suppliers_str=(supplier_code or ""))
    return resp


@staff_member_required
def download_all_photos(request):
    """Download all files inside MEDIA_ROOT/photos/ as a single ZIP."""

    photos_dir = os.path.join(settings.MEDIA_ROOT, "photos")

    if not os.path.isdir(photos_dir):
        return HttpResponse("❌ photos directory does not exist.", status=404)

    buffer = io.BytesIO()

    # Create ZIP in memory
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_name in os.listdir(photos_dir):
            file_path = os.path.join(photos_dir, file_name)

            if os.path.isfile(file_path):
                # add photo to ZIP with filename only (not full path)
                zipf.write(file_path, arcname=file_name)

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/zip"
    )
    response["Content-Disposition"] = 'attachment; filename="all_photos.zip"'

    return response


def admin_document_type_filter(request):
    group = request.GET.get("group")

    if group == "NON_EU":
        options = [{"id": "passport", "name": "Passport"}]
    else:
        options = [
            {"id": "id_card", "name": "Identity Card"},
            {"id": "passport", "name": "Passport"},
        ]

    return JsonResponse({"options": options})

def check_document_rules_all(request):
    docs = Document.objects.all()
    return JsonResponse({
        "options": [{"id": d.id, "name": d.type_name} for d in docs],
        "passport_only": False
    })

def check_document_rules(request, nationality_id):
    docs = Document.objects.all()

    restriction = DocumentTypeRestriction.objects.filter(
        nationality_id=nationality_id
    ).first()

    passport_only = False

    if not restriction or not restriction.allow_identity_card:
        docs = docs.filter(type_name__icontains="passport")
        passport_only = True

    return JsonResponse({
        "options": [{"id": d.id, "name": d.type_name} for d in docs],
        "passport_only": passport_only
    })

def export_staff(request):
    
    supplier = getattr(request.user, "supplier", None)

    # BLOCK EXPORT unless supplier has permission turned on
    if not supplier or not supplier.allow_frontend_export:
        messages.error(request, "Export disabled by Administrator.")
        return redirect("staff:landing")

    filename, status = export_staff_data(request.user)

    if status == "NO_RECORDS":
        messages.warning(request, "No records with Status = 1 to export.")
        return redirect("staff:landing")

    export_path = Path(settings.MEDIA_ROOT) / "exports" / filename
    return FileResponse(open(export_path, "rb"), as_attachment=True, filename=filename)


class SupplierSecureMixin(LoginRequiredMixin):
    """Ensures user has a supplier before accessing staff"""
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "supplier"):
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)

    @property
    def supplier(self):
        return getattr(self.request.user, "supplier")

class StaffListView(SupplierSecureMixin, ListView):
    model = StaffMember
    template_name = "staff/landing.html"
    context_object_name = "staff_list"
    paginate_by = 20

    def get_queryset(self):
        return StaffMember.objects.filter(supplier=self.supplier).order_by("-created_at")

class StaffCreateView(SupplierSecureMixin, CreateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = "staff/staff_form.html"
    success_url = reverse_lazy("staff:landing")

    def get_form_kwargs(self):
        """Pass supplier context for function code pre-fill"""
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        supplier = self.supplier
        instance = form.save(commit=False)
        instance.supplier = supplier

        # Save the logged-in user performing registration
        instance.user = self.request.user
        # 🔹 Assign function_code from supplier securely
        if supplier and supplier.function_code:
            instance.function_code = supplier.function_code

        # 🔹 Generate unique IDs
        next_num = StaffMember.objects.filter(supplier=supplier).count() + 1
        instance.plog_unique_id = f"{supplier.code}{next_num:02d}"
        # instance.worker_unique_id = f"{supplier.code}-{next_num:03d}"

        # instance.refresh_from_db()
        # Save instance so photograph gets a file path
        instance.save()
        # instance.venue.set(form.cleaned_data.get("venue", []))
        # Evaluate completion status
        instance.evaluate_completion_status()
        instance.save()
        
        # ---- Renaming the photograph ON DISK ----
        # 🔹 Rename photograph file (after pk generated)
        if instance.photograph:
            old_path = instance.photograph.path
            ext = os.path.splitext(old_path)[1].lower()
            new_filename = f"{instance.document_family_name}_{instance.document_given_name}_{instance.plog_unique_id}{ext}"
            new_relative_path = os.path.join("photos", new_filename)
            new_full_path = os.path.join(settings.MEDIA_ROOT, new_relative_path)

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

            # Move/rename actual file
            if os.path.exists(old_path):
                # If old file exists → remove it first
                if os.path.exists(new_full_path):
                    os.remove(new_full_path)
                os.rename(old_path, new_full_path)

            # Update model field
            instance.photograph.name = new_relative_path
            instance.save(update_fields=["photograph"])

        # User feedback
        if instance.status.status_id == "1":
            messages.success(self.request, "✅ Staff record saved and marked as COMPLETATO.")
        else:
            messages.info(self.request, "🕓 Partial save successful (Non Completo). You can complete it later.")

        return super().form_valid(form)


class StaffUpdateView(SupplierSecureMixin, UpdateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = "staff/staff_form.html"
    success_url = reverse_lazy("staff:landing")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        """Block editing if:
        - record does not belong to logged-in supplier
        - status is completed (01)
        """
        obj = self.get_object()
        # prevent edits if status is completed (status_id == '1')
        if obj.status and getattr(obj.status, "status_id", None) == "1":
            messages.info(request, "✅ This record is already marked as COMPLETATO and cannot be edited.")
            return redirect(self.success_url)
        # ensure supplier matches
        if obj.supplier != self.supplier:
            messages.warning(request, "You cannot edit staff from another supplier.")
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.supplier = self.supplier
        instance.user = self.request.user  # track who made the update
        instance.function_code = self.supplier.function_code  # lock to supplier’s function

        old_photo_path = None
        if instance.pk and instance.photograph:
            try:
                old_photo_path = instance.photograph.path
            except Exception:
                old_photo_path = None

        # Save first to get PK if not yet saved
        instance.save()

        # Update many-to-many venue field
        # instance.venue.set(form.cleaned_data.get("venue", []))

        # 🔹 Recalculate completion status (partial → complete)
        instance.evaluate_completion_status()
        instance.save()

        # ---- Renaming logic only if a NEW file was uploaded ----
        new_file = form.cleaned_data.get("photograph")

        if new_file and hasattr(new_file, "name"):
            # a NEW file uploaded → rename it
            try:
                new_uploaded_path = instance.photograph.path
            except Exception:
                new_uploaded_path = None

            if new_uploaded_path and os.path.exists(new_uploaded_path):
                ext = os.path.splitext(new_uploaded_path)[1].lower()
                new_filename = f"{instance.document_family_name}_{instance.document_given_name}_{instance.plog_unique_id}{ext}"
                new_relative_path = os.path.join("photos", new_filename)
                new_full_path = os.path.join(settings.MEDIA_ROOT, new_relative_path)

                # Ensure directory exists
                os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

                # 🔥 FIX: If target file already exists, delete it before rename
                if os.path.exists(new_full_path):
                    os.remove(new_full_path)

                os.rename(new_uploaded_path, new_full_path)
                instance.photograph.name = new_relative_path
                instance.save(update_fields=["photograph"])

        # 🔹 Set messages based on status
        if instance.status and instance.status.status_id == "1":
            messages.success(self.request, "✅ Staff record updated and now marked as COMPLETATO.")
        else:
            messages.info(self.request, "🕓 Staff record updated (still Non Completo). Fill remaining fields to complete it.")

        return super().form_valid(form)
  