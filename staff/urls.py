from django.urls import path
from .views import StaffListView, StaffCreateView, StaffUpdateView, export_reg_excel, export_staff, check_document_rules, check_document_rules_all, admin_document_type_filter, download_all_photos, admin_export_flagged

urlpatterns = [
    path("", StaffListView.as_view(), name="landing"),
    path("create/", StaffCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", StaffUpdateView.as_view(), name="edit"),
    path("export/reg/", export_reg_excel, name="export_reg_excel"),
    path("export/", export_staff, name="export"),
    path("check-document-rules/<int:nationality_id>/", check_document_rules, name="check_document_rules"),
    path("check-document-rules/all/", check_document_rules_all, name="check_document_rules_all"),
    path("document-type-filter/", admin_document_type_filter, name="admin_document_type_filter"),
    path("download/photos/", download_all_photos, name="download_all_photos"),
    path("export/flag/<str:status>/<str:mode>/", admin_export_flagged, name="admin_export_flagged"),
]


# urlpatterns = [
#     path("portal/", StaffListView.as_view(), name="staff_portal"),
#     path("create/", StaffCreateView.as_view(), name="staff_create"),
#     path("edit/<int:pk>/", StaffUpdateView.as_view(), name="staff_edit"),
# ]
