from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from find_bananas.ratelimit import ratelimit

from .forms import DeleteAccountForm, LoginForm, SignupForm, UsernameForm


def _safe_next(request, fallback="home"):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return target
    return fallback


@ratelimit("signup", limit=10, window_seconds=3600, json=False)
def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        # login() fires user_logged_in, which attaches this device's guest plays.
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, _("Welcome! Your results are now saved to your account."))
        return redirect(_safe_next(request))
    return render(request, "registration/signup.html", {"form": form, "next": _safe_next(request, "")})


@method_decorator(ratelimit("login", limit=10, window_seconds=900, json=False), name="dispatch")
class LoginView(auth_views.LoginView):
    form_class = LoginForm
    redirect_authenticated_user = True


@method_decorator(ratelimit("password-reset", limit=5, window_seconds=3600, json=False), name="dispatch")
class PasswordResetView(auth_views.PasswordResetView):
    pass


@login_required
@ratelimit("username", limit=10, window_seconds=3600, json=False)
def choose_username(request):
    """Shown to accounts without a username; also used to change it."""
    form = UsernameForm(request.user, request.POST or None)
    first_time = not request.user.username
    if request.method == "POST" and form.is_valid():
        form.save()
        if not first_time:
            messages.success(request, _("Your username has been changed."))
        return redirect(_safe_next(request, "profile" if not first_time else "home"))
    return render(
        request,
        "registration/choose_username.html",
        {"form": form, "first_time": first_time, "next": _safe_next(request, "")},
    )


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()  # cascades to the account's plays
        messages.info(request, _("Your account and its history have been deleted."))
        return redirect("home")
    return render(request, "registration/delete_account.html", {"form": form})
