# accounts/urls.py
from django.urls import path
from django.shortcuts import redirect
from .views import SupplierLoginView, SupplierLogoutView

urlpatterns = [
    path('', lambda request: redirect('accounts:login')),  # ✅ redirects / to /login/
    path('login/', SupplierLoginView.as_view(), name='login'),
    path('logout/', SupplierLogoutView.as_view(), name='logout'),
]
