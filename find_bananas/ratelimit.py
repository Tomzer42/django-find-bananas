"""Minimal fixed-window rate limiting on top of the Django cache.

With the default per-process memory cache the limits apply per app process;
set CACHE_URL to a Redis instance to share them once several instances run.
"""

from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render

from .players import client_ip


def is_limited(scope: str, ident: str, limit: int, window_seconds: int) -> bool:
    """Count one hit and say whether the limit is now exceeded."""
    key = f"rl:{scope}:{ident}"
    if cache.add(key, 1, window_seconds):
        return False
    try:
        hits = cache.incr(key)
    except ValueError:  # expired between add() and incr()
        cache.add(key, 1, window_seconds)
        return False
    return hits > limit


def ratelimit(scope: str, limit: int, window_seconds: int, methods=("POST",), json=True):
    """View decorator limiting requests per client IP."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method in methods and is_limited(scope, client_ip(request), limit, window_seconds):
                if json:
                    return JsonResponse({"error": "too_many_requests"}, status=429)
                return render(request, "find_bananas/429.html", status=429)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
