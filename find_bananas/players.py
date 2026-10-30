"""Who is playing: account holders and guests."""

import hashlib
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction

from .models import Play

SESSION_GUEST_KEY = "guest_key"


def get_guest_key(request) -> uuid.UUID:
    """A random identifier kept in the server-side session. Survives login
    (Django keeps session data when it rotates the key) so guest plays can be
    attached to the new account."""
    value = request.session.get(SESSION_GUEST_KEY)
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        key = uuid.uuid4()
        request.session[SESSION_GUEST_KEY] = str(key)
        return key


def find_play(request, edition) -> Play | None:
    """This visitor's play for an edition, if any."""
    if request.user.is_authenticated:
        play = Play.objects.filter(edition=edition, user=request.user).first()
        if play:
            return play
    return Play.objects.filter(edition=edition, guest_key=get_guest_key(request), user__isnull=True).first()


def claim_guest_plays(user, guest_key: uuid.UUID) -> int:
    """Attach unclaimed guest plays to `user`, skipping editions the account
    already played. Returns the number of plays attached."""
    played = set(Play.objects.filter(user=user).values_list("edition_id", flat=True))
    attached = 0
    for play in Play.objects.filter(guest_key=guest_key, user__isnull=True):
        if play.edition_id in played:
            continue
        try:
            with transaction.atomic():
                Play.objects.filter(pk=play.pk, user__isnull=True).update(user=user)
        except IntegrityError:
            continue
        played.add(play.edition_id)
        attached += 1
    return attached


def client_ip(request) -> str:
    """Client IP, honouring X-Forwarded-For only for the number of proxies we
    actually sit behind (DJANGO_TRUSTED_PROXY_COUNT), so it cannot be spoofed."""
    proxies = settings.TRUSTED_PROXY_COUNT
    if proxies > 0:
        forwarded = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if len(forwarded) >= proxies:
            return forwarded[-proxies]
    return request.META.get("REMOTE_ADDR", "")


def ip_hash(request, scope: str) -> str:
    """Pseudonymous IP fingerprint, salted per scope (e.g. per edition) so it
    cannot be linked across days. The raw IP is never stored."""
    raw = f"{settings.SECRET_KEY}|{scope}|{client_ip(request)}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]
