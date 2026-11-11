"""Numbers for the staff statistics page (/stats/).

A *player* is an account when the play belongs to one, otherwise the guest
identifier of the device. Guest plays are attached to the account at signup,
so someone who plays a few days and then signs up stays one player.

Per edition day:
- players: who started that day's challenge; completed: who finished it.
- new: players whose first play ever is that day; returning: the others.
- J+1 / J+7: among that day's new players, the share who played again exactly
  1 / 7 days later. Shown once that day has started; marked as running while
  that day's challenge is still live.
- accounts: accounts created that day (edition day, noon to noon).
- sources: where new players came from (the source of their first play).

Everything is computed from the plays in Python: a few thousand rows a month,
well within a request's time. If it ever gets slow, cache `build()`.
"""

from collections import Counter, defaultdict
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .editions import edition_date_at
from .models import Play
from .sources import DIRECT

UNKNOWN = "inconnu"


def _player(user_id, guest_key) -> str:
    return f"u{user_id}" if user_id else f"g{guest_key}"


def _rate(part: int, whole: int) -> int | None:
    return round(100 * part / whole) if whole else None


def build(days: int = 30, today: date | None = None) -> dict:
    today = today or edition_date_at(timezone.now())
    rows = Play.objects.filter(edition__market="global").values_list(
        "edition__date", "edition__number", "user_id", "guest_key", "status", "source", "created_at"
    )

    played: dict[str, set[date]] = defaultdict(set)
    first: dict[str, tuple] = {}  # player -> (created_at, date, source)
    by_day_players: dict[date, set[str]] = defaultdict(set)
    by_day_completed: dict[date, set[str]] = defaultdict(set)
    numbers: dict[date, int] = {}
    for day, number, user_id, guest_key, status, source, created_at in rows:
        player = _player(user_id, guest_key)
        played[player].add(day)
        by_day_players[day].add(player)
        numbers[day] = number
        if status == Play.Status.COMPLETED:
            by_day_completed[day].add(player)
        if player not in first or created_at < first[player][0]:
            first[player] = (created_at, day, source or UNKNOWN)

    new_by_day: dict[date, list[str]] = defaultdict(list)
    for player, (_, day, _source) in first.items():
        new_by_day[day].append(player)

    def returned(cohort: list[str], day: date, offset: int):
        target = day + timedelta(days=offset)
        if not cohort or target > today:
            return None
        return {
            "rate": _rate(sum(1 for p in cohort if target in played[p]), len(cohort)),
            "running": target == today,
        }

    accounts_by_day = Counter(
        edition_date_at(joined) for joined in get_user_model().objects.values_list("date_joined", flat=True)
    )

    daily = []
    for offset in range(days):
        day = today - timedelta(days=offset)
        cohort = new_by_day.get(day, [])
        players = len(by_day_players.get(day, ()))
        daily.append(
            {
                "date": day,
                "number": numbers.get(day),
                "players": players,
                "completed": len(by_day_completed.get(day, ())),
                "new": len(cohort),
                "returning": players - len(cohort),
                "from_share": sum(1 for p in cohort if first[p][2] == "share"),
                "d1": returned(cohort, day, 1),
                "d7": returned(cohort, day, 7),
                "accounts": accounts_by_day.get(day, 0),
            }
        )

    # Days before the first edition carry no information.
    daily = [d for d in daily if d["number"] is not None or d["players"]]

    peak = max((d["players"] for d in daily), default=0)
    for d in daily:
        d["bar"] = round(100 * d["players"] / peak) if peak else 0

    finished = [d for d in daily if d["date"] < today][:7]
    week_avg = round(sum(d["players"] for d in finished) / len(finished), 1) if finished else None

    def sources_since(since: date) -> list[dict]:
        counts = Counter(src for _, day, src in first.values() if since <= day <= today)
        total = sum(counts.values())
        return [
            {"name": name, "players": n, "share": _rate(n, total)}
            for name, n in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

    return {
        "today": today,
        "summary": {
            "players_today": len(by_day_players.get(today, ())),
            "week_avg": week_avg,
            "players_total": len(first),
            "accounts_total": sum(accounts_by_day.values()),
        },
        "daily": daily,
        "sources_7": sources_since(today - timedelta(days=6)),
        "sources_30": sources_since(today - timedelta(days=29)),
        "direct": DIRECT,
    }
