"""Game flow, enforced on the server.

1. The player starts a play (one per edition, per account or per guest).
2. For each round, the browser asks for the image. The server records when it
   served it. The image can be fetched again only for a few seconds (to
   survive a network hiccup), then never again.
3. The browser sends the guess. Only then does the server reveal the real
   count. Answers are final and resubmitting is harmless (idempotent).
4. After the last round the server computes the score and decides whether
   the play counts in the comparison with other players ("ranked").

The browser never knows a count before answering and never sends a score.
"""

from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import scoring
from .editions import ROUND_SPECS
from .models import Edition, EditionRound, Play
from .players import find_play, get_guest_key, ip_hash

IMAGE_REFETCH_SECONDS = 15  # how long a round image can be re-downloaded after first serve
ANSWER_WINDOW_SECONDS = 120  # slower answers still count for the player, not for the comparison
MAX_RANKED_PLAYS_PER_IP = 5  # per edition; limits cookie-clearing replays from one connection
MAX_GUESS = 9999


class GameError(Exception):
    """A request that breaks the rules. `code` is stable and sent to the browser."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def _now() -> datetime:
    return timezone.now()


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def round_total(edition: Edition) -> int:
    return edition.rounds.count()


def start_play(request, edition: Edition) -> Play:
    """Return this visitor's play for the edition, creating it if needed."""
    play = find_play(request, edition)
    if play:
        return play
    user = request.user if request.user.is_authenticated else None
    try:
        with transaction.atomic():
            return Play.objects.create(
                edition=edition,
                user=user,
                guest_key=get_guest_key(request),
                ip_hash=ip_hash(request, f"edition:{edition.pk}"),
            )
    except IntegrityError:
        # Double click / two tabs: the other request created it.
        play = find_play(request, edition)
        if play is None:
            # The session's guest key already played as another account.
            raise GameError("already_played", status=409)
        return play


def serve_round(play: Play, index: int) -> EditionRound:
    """Give the image of round `index`, recording when it was first served."""
    with transaction.atomic():
        play = Play.objects.select_for_update().get(pk=play.pk)
        if play.is_completed:
            raise GameError("play_completed", status=409)
        rounds = play.rounds
        now = _now()
        if index == len(rounds) + 1:
            # Next round: allowed once the previous one is answered.
            if rounds and rounds[-1].get("guess") is None:
                raise GameError("previous_round_unanswered", status=409)
            if index > round_total(play.edition):
                raise GameError("no_such_round", status=404)
            rounds.append({"served_at": now.isoformat(), "answered_at": None, "guess": None, "count": None})
            play.save(update_fields=["rounds"])
        elif index == len(rounds) and rounds[-1].get("guess") is None:
            # Re-download of the current round, only right after the first serve.
            served_at = _parse(rounds[-1]["served_at"])
            if now - served_at > timedelta(seconds=IMAGE_REFETCH_SECONDS):
                raise GameError("image_expired", status=410)
        else:
            raise GameError("round_not_available", status=409)
    return EditionRound.objects.get(edition_id=play.edition_id, index=index)


def answer_round(play: Play, index: int, guess) -> tuple[Play, dict]:
    """Record a guess and reveal the count. Submitting the same round again
    returns the stored answer unchanged."""
    try:
        guess = int(guess)
    except (TypeError, ValueError):
        raise GameError("invalid_guess")
    if not 0 <= guess <= MAX_GUESS:
        raise GameError("invalid_guess")

    with transaction.atomic():
        play = Play.objects.select_for_update().get(pk=play.pk)
        rounds = play.rounds
        if not 1 <= index <= len(rounds):
            raise GameError("round_not_started", status=409)
        current = rounds[index - 1]
        if current.get("guess") is None:
            if index != len(rounds):
                raise GameError("round_not_available", status=409)
            count = EditionRound.objects.values_list("count", flat=True).get(
                edition_id=play.edition_id, index=index
            )
            current.update(guess=guess, count=count, answered_at=_now().isoformat())
            if index == round_total(play.edition):
                _complete(play)
            play.save()
    return play, public_round(index, current)


def _complete(play: Play) -> None:
    """Score the play and decide whether it is fair to compare. Called with
    the play row locked."""
    play.status = Play.Status.COMPLETED
    play.completed_at = _now()
    play.score = scoring.total_score(play.rounds)
    on_time = all(
        _parse(r["answered_at"]) - _parse(r["served_at"]) <= timedelta(seconds=ANSWER_WINDOW_SECONDS)
        for r in play.rounds
    )
    same_connection = Play.objects.filter(
        edition_id=play.edition_id, ip_hash=play.ip_hash, ranked=True
    ).exclude(pk=play.pk)
    play.ranked = on_time and (not play.ip_hash or same_connection.count() < MAX_RANKED_PLAYS_PER_IP)


def public_round(index: int, data: dict) -> dict:
    """What the browser may know about a round: nothing before it is answered."""
    out = {"index": index, "answered": data.get("guess") is not None}
    if out["answered"]:
        out.update(
            guess=data["guess"], count=data["count"], gap=data["guess"] - data["count"],
        )
    return out


def play_state(play: Play | None, edition: Edition) -> dict:
    """Everything the page needs to resume or display a play."""
    total = round_total(edition)
    state = {
        "edition": {
            "number": edition.number,
            "date": edition.date.isoformat(),
            "rounds": total,
            "ranges": [[spec.min_count, spec.max_count] for spec in ROUND_SPECS[:total]],
            "tiers": [list(spec.tiers) for spec in ROUND_SPECS[:total]],
            "ends_at": edition.ends_at.isoformat(),
        },
        "status": "not_started",
        "rounds": [],
        "next_round": 1,
        "score": None,
        "ranking": None,
    }
    if play is None:
        return state
    state["rounds"] = [public_round(i, r) for i, r in enumerate(play.rounds, start=1)]
    if play.is_completed:
        state.update(status="completed", next_round=None, score=play.score, ranking=scoring.ranking_for(play))
        return state
    state["status"] = "in_progress"
    answered = sum(1 for r in state["rounds"] if r["answered"])
    state["next_round"] = answered + 1
    # A round that was shown but never answered (page reloaded during the 5
    # seconds) is waiting for its answer: the image is not shown again.
    state["awaiting_answer"] = len(play.rounds) > answered
    return state
