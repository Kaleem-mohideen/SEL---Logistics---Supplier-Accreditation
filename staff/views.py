from django.views.generic import ListView, CreateView, UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from .models import StaffMember, Status, ExportLog, Document, DocumentTypeRestriction

# from accounts.models import Supplier
from .forms import StaffMemberForm
import pandas as pd
from django.http import HttpResponse
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required

from .export_utils import export_staff_data
from django.http import FileResponse, JsonResponse
from django.contrib import messages
from pathlib import Path
from django.conf import settings
import os


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
    filename, status = export_staff_data(request.user)

    if status == "NO_RECORDS":
        messages.warning(request, "No records with Status = 1 to export.")
        return redirect("staff:landing")

    export_path = Path(settings.MEDIA_ROOT) / "exports" / filename
    return FileResponse(open(export_path, "rb"), as_attachment=True, filename=filename)

@staff_member_required
def export_reg_excel(request):
    staff = StaffMember.objects.filter(status__status_id=1)

    # Convert to Excel column order EXACTLY as provided
    df = pd.DataFrame([{
        "Request for Olympic Winter Games Accreditation": "Yes" if s.olympic_request else "No",
        "Request for Paralympic Winter Games Accreditation": "Yes" if s.paralympic_request else "No",
        "Organisation": s.supplier.name,
        "Registration Group": "OCOG - STAFF",
        "Function code": s.function_code.code,
        "Venue(s)": ", ".join([v.name for v in s.venue.all()]),
        "Discipline(s)": ", ".join([d.name for d in s.disciplines.all()]) if hasattr(s, 'disciplines') else "",
        "Organisation reference number": getattr(s, "reference_number", "") or "",
        "Given name": s.document_given_name,
        "Unknown Given name": "Yes" if getattr(s, "unknown_given_name", False) else "No",
        "Document Middle name": s.document_middle_name or "",
        "Document Family name": s.document_family_name,
        "Unknown Family name": "Yes" if getattr(s, "unknown_family_name", False) else "No",
        "Preferred Given name": getattr(s, "preferred_given_name", "") or "",
        "Preferred Family name": getattr(s, "preferred_family_name", "") or "",
        "Date of birth": s.date_of_birth.strftime("%d.%m.%Y"),
        "Unknown Date of birth": "Date of birth is correct",
        "Gender": s.gender,
        "Nationality": getattr(getattr(s, "nationality", None), "name", "") or "",
        "Document type": s.document_type,
        "Document Number": s.document_number,
        "Document Expiry Date": s.document_expiry.strftime("%d.%m.%Y"),
        "Country issuing document": getattr(getattr(s, "country_issuing_document", None), "name", "") or "",
        "Country or Territory of birth": getattr(getattr(s, "country_of_birth", None), "name", "") or "",
        "Place or City of birth": getattr(s, "place_or_city_of_birth", "") or "",
        "Email address": s.email_address,
        "Photograph": s.photograph.name.split("/")[-1] if s.photograph else "",
        "Wheelchair user": "Yes" if getattr(s, "wheelchair_user", False) else "No",
        "Transferable wheelchair user": "Yes" if getattr(s, "transferable_wheelchair_user", False) else "No",
    } for s in staff])

    timestamp = now().strftime("%Y%m%d_%H%M")
    filename = f"Plog_{timestamp}.xlsx"

    # Save Excel in memory (no temp file on disk)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    df.to_excel(response, index=False)

    # Store export log
    ExportLog.objects.create(exported_by=request.user, file_name=filename)

    return response

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
        instance.save()
        # instance.venue.set(form.cleaned_data.get("venue", []))
        instance.evaluate_completion_status()
        instance.save()
        
        # 🔹 Save initially
        response = super().form_valid(form)

        # 🔹 Rename photograph file (after pk generated)
        if instance.photograph:
            ext = os.path.splitext(instance.photograph.name)[1].lower()
            new_name = f"{instance.document_family_name}_{instance.document_given_name}_{instance.plog_unique_id}{ext}"
            full_path = os.path.join("photos", new_name)

            # Avoid overwriting existing file
            if default_storage.exists(full_path):
                default_storage.delete(full_path)

            instance.photograph.name = full_path
            instance.save(update_fields=["photograph"])

        # User feedback
        if instance.status.status_id == "1":
            messages.success(self.request, "✅ Staff record saved and marked as COMPLETATO.")
        else:
            messages.info(self.request, "🕓 Partial save successful (Non Completo). You can complete it later.")

        return response


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

        # Save first to get PK if not yet saved
        instance.save()

        # Update many-to-many venue field
        # instance.venue.set(form.cleaned_data.get("venue", []))

        # 🔹 Recalculate completion status (partial → complete)
        instance.evaluate_completion_status()
        instance.save()

        # 🔹 Rename photograph if uploaded again
        if instance.photograph and not instance.photograph.name.endswith(f"{instance.plog_unique_id}.jpg"):
            ext = os.path.splitext(instance.photograph.name)[1].lower()
            new_name = f"{instance.document_family_name}_{instance.document_given_name}_{instance.plog_unique_id}{ext}"
            full_path = os.path.join("photos", new_name)

            # Avoid overwriting existing file
            if default_storage.exists(full_path):
                default_storage.delete(full_path)

            instance.photograph.name = full_path
            instance.save(update_fields=["photograph"])

        # 🔹 Set messages based on status
        if instance.status and instance.status.status_id == "1":
            messages.success(self.request, "✅ Staff record updated and now marked as COMPLETATO.")
        else:
            messages.info(self.request, "🕓 Staff record updated (still Non Completo). Fill remaining fields to complete it.")

        return super().form_valid(form)
  