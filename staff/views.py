from django.views.generic import ListView, CreateView, UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from .models import StaffMember, Status, ExportLog

# from accounts.models import Supplier
from .forms import StaffMemberForm
import pandas as pd
from django.http import HttpResponse
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required

from .export_utils import export_staff_data
from django.http import FileResponse
from django.contrib import messages
from pathlib import Path
from django.conf import settings
import os


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
        instance.worker_unique_id = f"{supplier.code}-{next_num:03d}"

        # 🔹 Default to "01 Non Completo"
        status_non_completo, _ = Status.objects.get_or_create(status_id="0", defaults={"label": "Non Completo"})
        instance.status = status_non_completo

        # 🔹 Save initially
        response = super().form_valid(form)
        instance.refresh_from_db()

        # 🔹 Rename photograph file (after pk generated)
        if instance.photograph:
            ext = os.path.splitext(instance.photograph.name)[1].lower()
            new_name = f"{instance.document_family_name}_{instance.document_given_name}_{instance.plog_unique_id}{ext}"
            instance.photograph.name = f"photos/{new_name}"
            instance.save(update_fields=["photograph"])

        # ✅ Minimal and Extended Mandatory Field Checks
        minimal_fields = [
            instance.document_given_name,
            instance.document_family_name,
            instance.date_of_birth,
            instance.gender_id,
        ]
        extended_fields = [
            instance.nationality_id,
            instance.document_type_id,
            instance.document_number,
            instance.document_expiry,
            instance.country_issuing_document_id,
            instance.country_of_birth_id,
            instance.email_address,
            instance.worker_unique_id,
        ]

        # ✅ Conditional rule: if country_of_birth is Italy, then city is required
        italy_check = False
        if instance.country_of_birth and instance.country_of_birth.country_name.lower() == "italy":
            italy_check = bool(instance.place_or_city_of_birth_id)
        else:
            italy_check = True  # skip check if not Italy

        # Step 1 → Partial (01 Non Completo)
        if all(minimal_fields):
            instance.status = status_non_completo  # stays 01 until fully completed

        # Step 2 → Automatic upgrade to 02 Completato
        if all(minimal_fields) and all(extended_fields) and italy_check:
            status_completato, _ = Status.objects.get_or_create(status_id="1", defaults={"label": "Completato"})
            instance.status = status_completato

        instance.save()

        # User feedback
        if instance.status.status_id == "1":
            messages.success(self.request, "✅ Staff record saved and marked as COMPLETATO.")
        else:
            messages.info(self.request, "🕓 Partial save successful (Non Completo). You can complete it later.")

        return response

# class StaffCreateView1(SupplierSecureMixin, CreateView):
#     model = StaffMember
#     form_class = StaffMemberForm
#     template_name = "staff/staff_form.html"
#     success_url = reverse_lazy("staff:landing")

#     def get_form_kwargs(self):
#         """Pass supplier to form so function code auto-fills"""
#         kwargs = super().get_form_kwargs()
#         kwargs["supplier"] = self.supplier
#         return kwargs

#     @transaction.atomic
#     def form_valid(self, form):
#         """Final backend verification"""
#         supplier = self.supplier
#         form.instance.supplier = supplier

#         # ensure function_code assigned server-side (even though form disabled)
#         if supplier and supplier.function_code:
#             # Force function code based on Supplier (ignores hacked values)
#             form.instance.function_code = supplier.function_code

#         # Generate unique PLOG ID and worker ID
#         # progressive PLOG ID generation: SupplierCode + next progressive (02 digits)
#         next_num = StaffMember.objects.filter(supplier=supplier).count() + 1
#         form.instance.plog_unique_id = f"{supplier.code}{next_num:02d}"

#         # worker_unique_id (internal) example
#         form.instance.worker_unique_id = f"{supplier.code}-{next_num:03d}"

#         # default status '0' (Non Completo) — ensure Status exists
#         try:
#             form.instance.status = Status.objects.get(status_id="0")
#         except Status.DoesNotExist:
#             form.instance.status = None

#         return super().form_valid(form)

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
            return redirect(self.success_url)
        # ensure supplier matches
        if obj.supplier != self.supplier:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Prevent changing function_code via REST call"""
        form.instance.function_code = self.supplier.function_code
        return super().form_valid(form)        