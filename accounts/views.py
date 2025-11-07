# accounts/views.py
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect

class SupplierLoginView(LoginView):
    template_name = 'accounts/login.html'

    def dispatch(self, request, *args, **kwargs):
        # ✅ If user is already logged in, redirect to landing page
        if request.user.is_authenticated:
            return redirect("staff:landing")  # <--- staff portal landing page
        
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        if self.request.user.role == 'reg':
            return reverse_lazy('admin:index')
        return reverse_lazy("staff:landing")

class SupplierLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')
