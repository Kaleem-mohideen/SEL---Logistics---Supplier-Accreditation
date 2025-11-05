# accounts/urls.py
from django.urls import path
from .views import SupplierLoginView, SupplierLogoutView

urlpatterns = [
    path('login/', SupplierLoginView.as_view(), name='login'),
    path('logout/', SupplierLogoutView.as_view(), name='logout'),
]
