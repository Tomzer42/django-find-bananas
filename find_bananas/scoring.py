"""Scoring and comparison with other players.

Score (unchanged from the original game): the sum, over the three rounds, of
the distance between the guess and the real count. 0 is perfect; lower is
better. Every player of an edition sees the same images, so comparing raw
scores within one edition is fair.

Comparison: among the *ranked* plays of the same edition (completed in time,
see game.py), a player's position is reported as "top X %", where
X = ceil(100 * (number of strictly better players + 1) / number of players).
Ties share the best position. Below RANKING_MIN_PLAYERS ranked plays, no
percentile is shown: the number of players so far is shown instead.

Scores are small integers, so the distribution of an edition is kept as a
histogram {score: players}, built with one GROUP BY query and cached for a
short time. Computing a percentile is then a sum over that histogram,
whatever the number of players.
"""

import math

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count

from .models import Play

HISTOGRAM_CACHE_SECONDS = 30


def round_gap(guess: int, count: int) -> int:
    return abs(guess - count)


def total_score(rounds: list[dict]) -> int:
    return sum(round_gap(r["guess"], r["count"]) for r in rounds)


def _histogram_cache_key(edition_id: int) -> str:
    return f"score-histogram:{edition_id}"


def score_histogram(edition_id: int, use_cache: bool = True) -> dict[int, int]:
    key = _histogram_cache_key(edition_id)
    if use_cache:
        cached = cache.get(key)
        if cached is not None:
            return cached
    rows = (
        Play.objects.filter(edition_id=edition_id, ranked=True, score__isnull=False)
        .values("score")
        .annotate(n=Count("id"))
    )
    histogram = {row["score"]: row["n"] for row in rows}
    cache.set(key, histogram, HISTOGRAM_CACHE_SECONDS)
    return histogram


def ranking_for(play: Play) -> dict:
    """Comparison data for a completed play, ready to send to the page."""
    histogram = score_histogram(play.edition_id, use_cache=True)
    # A play that has just finished may not be in the cached histogram yet.
    if play.ranked and histogram.get(play.score, 0) == 0:
        histogram = dict(histogram)
        histogram[play.score] = 1
    players = sum(histogram.values())
    data = {
        "players": players,
        "min_players": settings.RANKING_MIN_PLAYERS,
        "ranked": play.ranked,
        "top_percent": None,
        "beaten_percent": None,
    }
    if not play.ranked or players < settings.RANKING_MIN_PLAYERS:
        return data
    better = sum(n for score, n in histogram.items() if score < play.score)
    worse = sum(n for score, n in histogram.items() if score > play.score)
    data["top_percent"] = max(1, min(100, math.ceil(100 * (better + 1) / players)))
    data["beaten_percent"] = math.floor(100 * worse / players)
    return data
