from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from storefront.forms import PhoneAuthenticationForm, RegisterForm


class StorefrontLoginView(LoginView):
    template_name = "storefront/auth/login.html"
    authentication_form = PhoneAuthenticationForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("storefront:home")
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect("storefront:home")
    else:
        form = RegisterForm()
    return render(request, "storefront/auth/register.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("storefront:home")
