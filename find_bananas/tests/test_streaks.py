import uuid
from datetime import date, timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from find_bananas import streaks
from find_bananas.editions import edition_date_at
from find_bananas.models import Edition, Play

from .helpers import GameClientMixin, make_edition

D = date(2026, 11, 10)


class ComputeTests(TestCase):
    def test_empty(self):
        self.assertEqual(streaks.compute(set(), D), {"current": 0, "best": 0, "played_today": False})

    def test_played_today_and_before(self):
        dates = {D, D - timedelta(1), D - timedelta(2), D - timedelta(5)}
        self.assertEqual(streaks.compute(dates, D), {"current": 3, "best": 3, "played_today": True})

    def test_still_alive_when_today_not_played_yet(self):
        dates = {D - timedelta(1), D - timedelta(2)}
        self.assertEqual(streaks.compute(dates, D)["current"], 2)

    def test_broken_after_a_missed_day(self):
        dates = {D - timedelta(2), D - timedelta(3)}
        result = streaks.compute(dates, D)
        self.assertEqual(result["current"], 0)
        self.assertEqual(result["best"], 2)

    def test_best_is_the_longest_run(self):
        dates = {D - timedelta(d) for d in (0, 1, 4, 5, 6, 7, 10)}
        self.assertEqual(streaks.compute(dates, D), {"current": 2, "best": 4, "played_today": True})


class StreakInGameTests(GameClientMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.today = make_edition(counts=(30, 75, 150))

    def _past_play(self, days_ago, **who):
        day = edition_date_at(timezone.now()) - timedelta(days=days_ago)
        edition = Edition.objects.create(
            date=day, number=100 + days_ago, starts_at=timezone.now() - timedelta(days=days_ago + 1),
            ends_at=timezone.now() - timedelta(days=days_ago),
        )
        Play.objects.create(edition=edition, status=Play.Status.COMPLETED, score=10, rounds=[], **who)

    def test_guest_streak_in_result_state(self):
        self.client.get("/")
        guest_key = uuid.UUID(self.client.session["guest_key"])
        self._past_play(1, guest_key=guest_key)
        self._past_play(2, guest_key=guest_key)
        self._past_play(4, guest_key=guest_key)
        state = self.play_full_game(self.today, [30, 75, 150])["state"]
        self.assertEqual(state["streak"], {"current": 3, "best": 3, "played_today": True})

    def test_other_players_do_not_count(self):
        self._past_play(1, guest_key=uuid.uuid4())
        state = self.play_full_game(self.today, [30, 75, 150])["state"]
        self.assertEqual(state["streak"]["current"], 1)

    def test_streak_survives_signup_and_shows_in_profile(self):
        self.client.get("/")
        guest_key = uuid.UUID(self.client.session["guest_key"])
        self._past_play(1, guest_key=guest_key)
        self.play_full_game(self.today, [30, 75, 150])
        self.client.post("/account/signup/", {
            "email": "s@example.com", "username": "Streaker", "password1": "banana-split-42",
            "password2": "banana-split-42",
        })
        summary = self.client.get("/profile/").context["summary"]
        self.assertEqual(summary["streak"]["current"], 2)
        state = self.api(self.today, "/state").json()
        self.assertEqual(state["streak"]["current"], 2)
