"""Sign in with Google (OAuth 2.0 / OpenID Connect, authorization-code flow).

Written with the standard library only, to avoid a large dependency for one
provider. The flow:

1. /account/google/ stores a random `state` and `nonce` in the session and
   sends the visitor to Google.
2. Google sends them back to /account/google/callback/?code=...&state=...
3. The code is exchanged for tokens by a direct HTTPS call to Google's token
   endpoint, authenticated with the client secret. The ID token received this
   way comes straight from Google over TLS, so (as Google's documentation
   allows) its signature is not re-checked; its audience, issuer, expiry,
   nonce and email verification are.
4. The account is found by Google's stable user id ("sub"), else by verified
   email (an existing email/password account is linked), else created
   without a password and without a username: RequireUsernameMiddleware then
   asks the player to choose one.

Settings: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET. Without them the button is
hidden and these URLs return 404.
"""

import base64
import json
import secrets
import time
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from find_bananas.ratelimit import ratelimit

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
SESSION_KEY = "google_oauth"
BACKEND = "django.contrib.auth.backends.ModelBackend"


class GoogleError(Exception):
    pass


def enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _redirect_uri(request) -> str:
    return request.build_absolute_uri(reverse("google_callback"))


@require_GET
@ratelimit("google-start", limit=30, window_seconds=600, methods=("GET",), json=False)
def start(request):
    if not enabled():
        raise Http404
    from .views import _safe_next

    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    request.session[SESSION_KEY] = {"state": state, "nonce": nonce, "next": _safe_next(request, "")}
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
    }
    return redirect(f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}")


def exchange_code(code: str, redirect_uri: str) -> dict:
    """POST the code to Google's token endpoint; return the decoded ID token
    claims. Isolated so tests can replace it."""
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            tokens = json.load(response)
    except (OSError, ValueError) as exc:
        raise GoogleError("token_exchange_failed") from exc
    id_token = tokens.get("id_token")
    if not id_token or id_token.count(".") != 2:
        raise GoogleError("no_id_token")
    payload = id_token.split(".")[1]
    try:
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError as exc:
        raise GoogleError("bad_id_token") from exc


def check_claims(claims: dict, nonce: str) -> tuple[str, str]:
    if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise GoogleError("wrong_audience")
    if claims.get("iss") not in ISSUERS:
        raise GoogleError("wrong_issuer")
    if int(claims.get("exp", 0)) < time.time():
        raise GoogleError("expired")
    if not nonce or claims.get("nonce") != nonce:
        raise GoogleError("wrong_nonce")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleError("email_not_verified")
    sub, email = str(claims.get("sub") or ""), (claims.get("email") or "").strip().lower()
    if not sub or not email:
        raise GoogleError("missing_identity")
    return sub, email


def account_for(sub: str, email: str):
    User = get_user_model()
    user = User.objects.filter(google_sub=sub).first()
    if user is None:
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and not user.google_sub:
            user.google_sub = sub
            user.save(update_fields=["google_sub"])
    if user is None:
        user = User.objects.create_user(email=email, password=None, google_sub=sub)
    return user


@require_GET
@ratelimit("google-callback", limit=30, window_seconds=600, methods=("GET",), json=False)
def callback(request):
    if not enabled():
        raise Http404
    pending = request.session.pop(SESSION_KEY, None) or {}
    failed = _("Google sign-in did not work. Please try again.")
    if request.GET.get("error"):
        # The player closed or refused Google's consent screen.
        return redirect("login")
    state = request.GET.get("state", "")
    if not pending or not secrets.compare_digest(state, pending.get("state", "")) or not request.GET.get("code"):
        messages.error(request, failed)
        return redirect("login")
    try:
        claims = exchange_code(request.GET["code"], _redirect_uri(request))
        sub, email = check_claims(claims, pending.get("nonce", ""))
    except GoogleError:
        messages.error(request, failed)
        return redirect("login")
    user = account_for(sub, email)
    if not user.is_active:
        messages.error(request, failed)
        return redirect("login")
    # login() fires user_logged_in, which attaches this device's guest plays.
    login(request, user, backend=BACKEND)
    return redirect(pending.get("next") or "home")
