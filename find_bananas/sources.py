"""Where players come from.

The first time a visitor arrives, the source is kept in their session:
- `?ref=<name>` in the link (the share button adds `?ref=share`; use
  `?ref=tiktok`, `?ref=instagram`… in profiles and posts), else
- the site that sent them (the Referer header: reddit, google, x…), else
- nothing: the play is then counted as "direct" (typed address, WhatsApp
  and most apps, which send no Referer).

A link with `?ref=` is redirected to the same address without it, so that a
visitor who copies the address bar does not pass their own source on.
Each play records the session's source; a player's source is the one of
their first play.
"""

import re
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.http import HttpResponseRedirect

SESSION_KEY = "src"
DIRECT = "direct"
REF_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
BOT_HINTS = ("bot", "crawl", "spider", "preview", "facebookexternalhit", "whatsapp", "slack", "telegram", "embedly")

# Referer hosts grouped under one readable name.
KNOWN_HOSTS = {
    "t.co": "x",
    "x.com": "x",
    "twitter.com": "x",
    "tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "l.instagram.com": "instagram",
    "facebook.com": "facebook",
    "l.facebook.com": "facebook",
    "lm.facebook.com": "facebook",
    "m.facebook.com": "facebook",
    "reddit.com": "reddit",
    "old.reddit.com": "reddit",
    "out.reddit.com": "reddit",
    "linkedin.com": "linkedin",
    "lnkd.in": "linkedin",
    "discord.com": "discord",
    "threads.net": "threads",
    "bsky.app": "bluesky",
    "youtube.com": "youtube",
    "duckduckgo.com": "duckduckgo",
    "bing.com": "bing",
}


def source_from_referer(referer: str, own_hosts: set[str]) -> str | None:
    host = (urlsplit(referer).hostname or "").lower()
    if not host or host in own_hosts:
        return None
    if host.startswith("www."):
        host = host[4:]
    if host in own_hosts:
        return None
    if host in KNOWN_HOSTS:
        return KNOWN_HOSTS[host]
    if host.startswith("google.") or ".google." in host:
        return "google"
    return host[:32]


def _own_hosts(request) -> set[str]:
    hosts = {request.get_host().split(":")[0].lower()}
    site = urlsplit(settings.SITE_URL).hostname
    if site:
        hosts |= {site.lower(), f"www.{site.lower()}"}
    return hosts


def _is_bot(request) -> bool:
    agent = request.META.get("HTTP_USER_AGENT", "").lower()
    return not agent or any(hint in agent for hint in BOT_HINTS)


class TrafficSourceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and not request.path.startswith(("/api/", "/static/", "/admin/")):
            response = self._capture(request)
            if response is not None:
                return response
        return self.get_response(request)

    def _capture(self, request):
        ref = request.GET.get("ref")
        if not _is_bot(request) and SESSION_KEY not in request.session:
            source = None
            if ref is not None:
                ref = ref.strip().lower()
                source = ref if REF_PATTERN.match(ref) else None
            if source is None:
                source = source_from_referer(request.META.get("HTTP_REFERER", ""), _own_hosts(request))
            if source:
                request.session[SESSION_KEY] = source
        if ref is not None:
            # Clean address bar; link-preview bots follow the redirect too.
            rest = [(k, v) for k, v in request.GET.lists() if k != "ref"]
            query = urlencode([(k, v) for k, values in rest for v in values])
            return HttpResponseRedirect(request.path + (f"?{query}" if query else ""))
        return None


def session_source(request) -> str:
    return request.session.get(SESSION_KEY) or DIRECT
