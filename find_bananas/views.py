import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Min
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from . import game, scoring
from .editions import get_live_edition
from .models import Edition, Play
from .players import find_play
from .ratelimit import ratelimit
from .strings import game_strings

# A play started just before the daily switch can still be finished.
FINISH_GRACE = timedelta(minutes=15)


# --- Pages -----------------------------------------------------------------


@never_cache
@require_GET
def home(request):
    edition = get_live_edition()
    play = find_play(request, edition)
    return render(
        request,
        "find_bananas/home.html",
        {"edition": edition, "state": game.play_state(play, edition), "strings": game_strings()},
    )


@login_required
@require_GET
def history(request):
    plays = (
        Play.objects.filter(user=request.user, status=Play.Status.COMPLETED)
        .select_related("edition")
        .order_by("-edition__date")
    )
    page = Paginator(plays, 30).get_page(request.GET.get("page"))
    rows = [{"play": p, "ranking": scoring.ranking_for(p)} for p in page]
    recent = list(plays.values_list("score", flat=True)[:10])
    summary = {
        "games": page.paginator.count,
        "best": plays.aggregate(best=Min("score"))["best"],
        "average_recent": round(sum(recent) / len(recent), 1) if recent else None,
        "recent_count": len(recent),
    }
    return render(request, "find_bananas/history.html", {"page": page, "rows": rows, "summary": summary})


@require_GET
def privacy(request):
    return render(request, "find_bananas/privacy.html")


# --- Game API (JSON) -------------------------------------------------------


def _error(exc: game.GameError) -> JsonResponse:
    return JsonResponse({"error": exc.code}, status=exc.status)


def _playable_edition(number: int, allow_grace: bool) -> Edition:
    edition = Edition.objects.filter(market="global", number=number).first()
    now = timezone.now()
    if edition is None or now < edition.starts_at:
        raise game.GameError("edition_not_found", status=404)
    deadline = edition.ends_at + (FINISH_GRACE if allow_grace else timedelta(0))
    if now >= deadline:
        raise game.GameError("edition_over", status=410)
    return edition


def _current_play(request, number: int):
    edition = _playable_edition(number, allow_grace=True)
    play = find_play(request, edition)
    if play is None:
        raise game.GameError("play_not_started", status=409)
    return edition, play


@never_cache
@require_POST
@ratelimit("play-start", limit=30, window_seconds=600)
def api_start(request, number):
    try:
        edition = _playable_edition(number, allow_grace=False)
        play = game.start_play(request, edition)
    except game.GameError as exc:
        return _error(exc)
    return JsonResponse(game.play_state(play, edition))


@never_cache
@require_POST
@ratelimit("play-image", limit=60, window_seconds=600)
def api_round_image(request, number, index):
    try:
        _, play = _current_play(request, number)
        round_ = game.serve_round(play, index)
    except game.GameError as exc:
        return _error(exc)
    response = HttpResponse(bytes(round_.image), content_type=round_.image_type)
    response["Cache-Control"] = "no-store, private"
    return response


@never_cache
@require_POST
@ratelimit("play-answer", limit=60, window_seconds=600)
def api_answer(request, number, index):
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)
    try:
        edition, play = _current_play(request, number)
        play, round_data = game.answer_round(play, index, payload.get("guess"))
    except game.GameError as exc:
        return _error(exc)
    return JsonResponse({"round": round_data, "state": game.play_state(play, edition)})


@never_cache
@require_GET
def api_state(request, number):
    try:
        edition = _playable_edition(number, allow_grace=True)
    except game.GameError as exc:
        return _error(exc)
    return JsonResponse(game.play_state(find_play(request, edition), edition))
