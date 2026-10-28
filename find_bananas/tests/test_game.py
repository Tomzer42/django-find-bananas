from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from find_bananas import game
from find_bananas.models import Play

from .helpers import GameClientMixin, make_edition


class GameFlowTests(GameClientMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.edition = make_edition(counts=(30, 75, 150))

    def test_home_never_contains_the_counts(self):
        html = self.client.get("/").content.decode()
        for count in (30, 75, 150):
            self.assertNotIn(f'"count": {count}', html)
            self.assertNotIn(f"({count}", html)

    def test_full_game_is_scored_by_the_server(self):
        state = self.play_full_game(self.edition, [33, 75, 140])["state"]
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["score"], 3 + 0 + 10)
        self.assertEqual([r["gap"] for r in state["rounds"]], [3, 0, -10])
        play = Play.objects.get()
        self.assertTrue(play.ranked)
        self.assertEqual(play.score, 13)

    def test_count_only_revealed_after_answer(self):
        self.api(self.edition, "/start")
        self.api(self.edition, "/rounds/1/image")
        state = self.api(self.edition, "/state").json()
        self.assertEqual(state["rounds"], [{"index": 1, "answered": False}])
        self.assertTrue(state["awaiting_answer"])

    def test_client_cannot_submit_a_score(self):
        self.api(self.edition, "/start")
        self.api(self.edition, "/rounds/1/image")
        response = self.api(self.edition, "/rounds/1/answer", {"guess": 30, "score": 0, "count": 30})
        self.assertEqual(response.json()["round"]["gap"], 0)
        self.assertIsNone(Play.objects.get().score)  # not completed yet

    def test_rounds_cannot_be_skipped_or_answered_before_the_image(self):
        self.api(self.edition, "/start")
        self.assertEqual(self.api(self.edition, "/rounds/1/answer", {"guess": 3}).status_code, 409)
        self.assertEqual(self.api(self.edition, "/rounds/2/image").status_code, 409)
        self.api(self.edition, "/rounds/1/image")
        self.assertEqual(self.api(self.edition, "/rounds/2/image").status_code, 409)

    def test_image_cannot_be_viewed_again_later(self):
        self.api(self.edition, "/start")
        self.assertEqual(self.api(self.edition, "/rounds/1/image").status_code, 200)
        # A quick retry (network hiccup) is fine.
        self.assertEqual(self.api(self.edition, "/rounds/1/image").status_code, 200)
        later = timezone.now() + timedelta(seconds=game.IMAGE_REFETCH_SECONDS + 1)
        with mock.patch("find_bananas.game._now", return_value=later):
            self.assertEqual(self.api(self.edition, "/rounds/1/image").status_code, 410)
        # After answering, the round is closed for good.
        self.api(self.edition, "/rounds/1/answer", {"guess": 30})
        self.assertEqual(self.api(self.edition, "/rounds/1/image").status_code, 409)

    def test_answers_are_final_and_resubmission_is_harmless(self):
        self.api(self.edition, "/start")
        self.api(self.edition, "/rounds/1/image")
        first = self.api(self.edition, "/rounds/1/answer", {"guess": 25}).json()
        second = self.api(self.edition, "/rounds/1/answer", {"guess": 30}).json()
        self.assertEqual(first["round"], second["round"])
        self.assertEqual(Play.objects.get().rounds[0]["guess"], 25)

    def test_invalid_guesses_are_rejected(self):
        self.api(self.edition, "/start")
        self.api(self.edition, "/rounds/1/image")
        for bad in ["abc", -1, 10000, None, 1.5e6]:
            response = self.api(self.edition, "/rounds/1/answer", {"guess": bad})
            self.assertEqual(response.status_code, 400, bad)
        response = self.client.post(
            f"/api/editions/{self.edition.number}/rounds/1/answer", data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_one_play_per_visitor_per_edition(self):
        self.play_full_game(self.edition, [30, 75, 150])
        self.api(self.edition, "/start")
        self.assertEqual(Play.objects.count(), 1)
        self.assertEqual(self.api(self.edition, "/rounds/1/image").status_code, 409)

    def test_home_resumes_a_finished_game(self):
        self.play_full_game(self.edition, [30, 75, 150])
        html = self.client.get("/").content.decode()
        self.assertIn('"status": "completed"', html)

    def test_slow_answers_are_not_ranked(self):
        self.api(self.edition, "/start")
        self.api(self.edition, "/rounds/1/image")
        later = timezone.now() + timedelta(seconds=game.ANSWER_WINDOW_SECONDS + 5)
        with mock.patch("find_bananas.game._now", return_value=later):
            self.api(self.edition, "/rounds/1/answer", {"guess": 30})
        self.play_round(self.edition, 2, 75)
        state = self.play_round(self.edition, 3, 150).json()["state"]
        self.assertFalse(Play.objects.get().ranked)
        self.assertFalse(state["ranking"]["ranked"])

    def test_cookie_clearing_replays_from_one_connection_stop_counting(self):
        for _ in range(game.MAX_RANKED_PLAYS_PER_IP + 2):
            self.client.cookies.clear()
            self.play_full_game(self.edition, [30, 75, 150])
        self.assertEqual(Play.objects.filter(ranked=True).count(), game.MAX_RANKED_PLAYS_PER_IP)

    def test_raw_ip_is_never_stored(self):
        self.play_full_game(self.edition, [30, 75, 150])
        play = Play.objects.get()
        self.assertNotIn("127.0.0.1", play.ip_hash)
        self.assertEqual(len(play.ip_hash), 32)

    def test_finished_edition_cannot_be_started(self):
        old = make_edition(number=7, live=False)
        self.assertEqual(self.api(old, "/start").status_code, 410)

    def test_unknown_edition(self):
        response = self.client.post("/api/editions/999/start", content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_api_requires_csrf(self):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        response = strict.post(f"/api/editions/{self.edition.number}/start", content_type="application/json")
        self.assertEqual(response.status_code, 403)


class RateLimitTests(GameClientMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.edition = make_edition()

    def test_start_is_rate_limited(self):
        codes = [self.api(self.edition, "/start").status_code for _ in range(32)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[-1], 429)


@override_settings(RANKING_MIN_PLAYERS=5)
class RankingTests(GameClientMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.edition = make_edition(counts=(30, 75, 150))

    def _seed(self, scores):
        import uuid

        for i, score in enumerate(scores):
            Play.objects.create(
                edition=self.edition,
                guest_key=uuid.uuid4(),
                ip_hash=f"seed{i}",
                status=Play.Status.COMPLETED,
                score=score,
                ranked=True,
                completed_at=timezone.now(),
            )

    def test_no_percentile_with_too_few_players(self):
        self._seed([10, 20])
        ranking = self.play_full_game(self.edition, [30, 75, 150])["state"]["ranking"]
        self.assertIsNone(ranking["top_percent"])
        self.assertEqual(ranking["players"], 3)

    def test_percentile_with_enough_players(self):
        self._seed([1, 5, 8, 12, 20, 30, 40, 50, 60])  # 9 others
        ranking = self.play_full_game(self.edition, [32, 76, 150])["state"]["ranking"]  # score 3
        self.assertEqual(ranking["players"], 10)
        self.assertEqual(ranking["top_percent"], 20)  # 1 better -> rank 2 of 10
        self.assertEqual(ranking["beaten_percent"], 80)

    def test_ties_share_the_best_position(self):
        self._seed([0, 0, 0, 0, 9])
        ranking = self.play_full_game(self.edition, [30, 75, 150])["state"]["ranking"]  # perfect
        self.assertEqual(ranking["top_percent"], 17)  # rank 1 of 6
        self.assertEqual(ranking["beaten_percent"], 16)

    def test_unranked_plays_are_left_out_of_the_population(self):
        self._seed([1, 2, 3, 4, 5])
        Play.objects.filter(score=1).update(ranked=False)
        ranking = self.play_full_game(self.edition, [30, 75, 150])["state"]["ranking"]
        self.assertEqual(ranking["players"], 5)


class TierTests(GameClientMixin, TestCase):
    def test_tier_limits(self):
        from find_bananas.editions import ROUND_SPECS
        from find_bananas.scoring import tier

        r1, r2, r3 = (spec.tiers for spec in ROUND_SPECS)
        self.assertEqual([tier(g, r1) for g in (0, 4, 5, 6, 7, 8, 9)],
                         ["green", "green", "yellow", "yellow", "orange", "orange", "red"])
        self.assertEqual([tier(g, r2) for g in (-8, 9, 11, 12, 15, 16)],
                         ["green", "yellow", "yellow", "orange", "orange", "red"])
        self.assertEqual([tier(g, r3) for g in (15, 16, 23, 24, 30, 31)],
                         ["green", "yellow", "yellow", "orange", "orange", "red"])
        total = [sum(x) for x in zip(r1, r2, r3)]
        self.assertEqual(total, [27, 40, 53])

    def test_state_sends_tiers(self):
        edition = make_edition()
        state = self.api(edition, "/state").json()
        self.assertEqual(state["edition"]["tiers"], [[4, 6, 8], [8, 11, 15], [15, 23, 30]])
