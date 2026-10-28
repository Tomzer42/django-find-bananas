"""Daily streaks: how many challenges in a row a player has finished.

A streak is counted in editions (one per day), for an account or, without an
account, for the guest identifier kept in the browser. Guest plays are
attached to the account at signup, so a streak survives creating an account.

The current streak stays alive until the end of the day after the last
game: someone who played yesterday but not yet today still has their streak.
"""

from datetime import date, timedelta

from django.utils import timezone

from .editions import edition_date_at
from .models import Play


def _completed_dates(plays) -> set[date]:
    return set(plays.filter(status=Play.Status.COMPLETED).values_list("edition__date", flat=True))


def plays_of(play: Play):
    """All plays of the same player as `play` (account or guest)."""
    if play.user_id:
        return Play.objects.filter(user_id=play.user_id)
    return Play.objects.filter(guest_key=play.guest_key, user__isnull=True)


def compute(dates: set[date], today: date) -> dict:
    """Current and best streak from the set of edition dates played."""
    anchor = today if today in dates else today - timedelta(days=1)
    current = 0
    while anchor - timedelta(days=current) in dates:
        current += 1
    best = run = 0
    previous = None
    for day in sorted(dates):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return {"current": current, "best": best, "played_today": today in dates}


def for_play(play: Play) -> dict:
    return compute(_completed_dates(plays_of(play)), edition_date_at(timezone.now()))


def for_user(user) -> dict:
    return compute(_completed_dates(Play.objects.filter(user=user)), edition_date_at(timezone.now()))
