from django.urls import path
from .views import StaffListView, StaffCreateView, StaffUpdateView, export_reg_excel, export_staff

urlpatterns = [
    path("", StaffListView.as_view(), name="landing"),
    path("create/", StaffCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", StaffUpdateView.as_view(), name="edit"),
    path("export/reg/", export_reg_excel, name="export_reg_excel"),
    path("export/", export_staff, name="export"),
]
# urlpatterns = [
#     path("portal/", StaffListView.as_view(), name="staff_portal"),
#     path("create/", StaffCreateView.as_view(), name="staff_create"),
#     path("edit/<int:pk>/", StaffUpdateView.as_view(), name="staff_edit"),
# ]
