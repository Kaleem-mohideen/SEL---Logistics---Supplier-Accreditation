# accounts/views.py
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect

class SupplierLoginView(LoginView):
    template_name = 'accounts/login.html'

    def dispatch(self, request, *args, **kwargs):
        # ✅ If user is already logged in, redirect to landing page
        if request.user.is_authenticated:
            return redirect(self.get_success_url())  # <--- staff portal landing page
        
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user

        # ✅ If REG team or Admin — go to Django Admin page
        if getattr(user, "role", None) == "reg" or user.is_staff or user.is_superuser:
            return reverse_lazy("admin:index")
        # ✅ Default for supplier users — go to staff landing page
        return reverse_lazy("staff:landing")

class SupplierLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')
