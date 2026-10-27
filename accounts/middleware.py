from django.shortcuts import redirect
from django.urls import reverse

# Paths an account without a username may still use.
ALLOWED_PREFIXES = ("/account/", "/i18n/", "/static/", "/admin/", "/api/", "/privacy/")


class RequireUsernameMiddleware:
    """Send signed-in players without a username to the page where they
    choose one (accounts created before usernames existed, and Google
    sign-ins later). The game API is left alone so a game in progress is
    never interrupted."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not user.username
            and request.method == "GET"
            and not request.path.startswith(ALLOWED_PREFIXES)
        ):
            return redirect(f"{reverse('choose_username')}?next={request.get_full_path()}")
        return self.get_response(request)
