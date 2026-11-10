import uuid
from datetime import date, timedelta
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from find_bananas import stats
from find_bananas.models import Edition, Play
from find_bananas.sources import source_from_referer

from .helpers import GameClientMixin, make_edition

TODAY = date(2026, 11, 20)
BROWSER = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)"


def edition_on(day: date) -> Edition:
    number = (day - date(2026, 11, 1)).days + 1
    now = timezone.now()
    return Edition.objects.create(date=day, number=number, starts_at=now, ends_at=now)


def play(edition, player, source="direct", completed=True, user=None):
    return Play.objects.create(
        edition=edition,
        guest_key=player,
        user=user,
        source=source,
        status=Play.Status.COMPLETED if completed else Play.Status.IN_PROGRESS,
    )


class BuildTests(TestCase):
    def test_new_returning_retention_and_sources(self):
        days = {offset: edition_on(TODAY - timedelta(days=offset)) for offset in range(9)}
        a, b, c, d = (uuid.uuid4() for _ in range(4))
        # Eight days ago: a (via share) and b start. a comes back the next day
        # and seven days later; b never comes back.
        play(days[8], a, source="share")
        play(days[8], b)
        play(days[7], a)
        play(days[1], a)
        # Yesterday: c is new and plays again today; d is new today, unfinished.
        play(days[1], c, source="tiktok")
        play(days[0], c)
        play(days[0], d, completed=False)

        result = stats.build(days=9, today=TODAY)
        by_date = {row["date"]: row for row in result["daily"]}

        eight = by_date[TODAY - timedelta(days=8)]
        self.assertEqual((eight["players"], eight["new"], eight["from_share"]), (2, 2, 1))
        self.assertEqual(eight["d1"], {"rate": 50, "running": False})
        self.assertEqual(eight["d7"], {"rate": 50, "running": False})

        yesterday = by_date[TODAY - timedelta(days=1)]
        self.assertEqual((yesterday["players"], yesterday["new"], yesterday["returning"]), (2, 1, 1))
        self.assertEqual(yesterday["d1"], {"rate": 100, "running": True})
        self.assertIsNone(yesterday["d7"])

        today = by_date[TODAY]
        self.assertEqual((today["players"], today["completed"], today["new"]), (2, 1, 1))
        self.assertIsNone(today["d1"])

        self.assertEqual(result["summary"]["players_today"], 2)
        self.assertEqual(result["summary"]["players_total"], 4)
        sources = {s["name"]: s["players"] for s in result["sources_30"]}
        self.assertEqual(sources, {"share": 1, "direct": 2, "tiktok": 1})
        self.assertEqual({s["name"] for s in result["sources_7"]}, {"tiktok", "direct"})

    def test_guest_who_signs_up_stays_one_player(self):
        first, second = edition_on(TODAY - timedelta(days=1)), edition_on(TODAY)
        user = User.objects.create_user(email="p@example.com", username="banana_fan")
        device = uuid.uuid4()
        play(first, device, user=user)  # claimed at signup
        play(second, uuid.uuid4(), user=user)  # another device, signed in
        result = stats.build(days=2, today=TODAY)
        self.assertEqual(result["summary"]["players_total"], 1)
        self.assertEqual(result["daily"][0]["returning"], 1)


class SourceCaptureTests(GameClientMixin, TestCase):
    def setUp(self):
        cache.clear()  # rate limits are kept in the cache

    def test_ref_link_is_recorded_and_the_address_cleaned(self):
        edition = make_edition()
        response = self.client.get("/?ref=Share", HTTP_USER_AGENT=BROWSER)
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.client.get("/?ref=tiktok", HTTP_USER_AGENT=BROWSER)  # first source wins
        self.client.defaults["HTTP_USER_AGENT"] = BROWSER
        self.play_full_game(edition, [30, 75, 150])
        self.assertEqual(Play.objects.get().source, "share")

    def test_referer_and_direct(self):
        edition = make_edition()
        self.client.get("/", HTTP_USER_AGENT=BROWSER, HTTP_REFERER="https://www.reddit.com/r/WebGames/")
        self.play_full_game(edition, [30, 75, 150])
        self.assertEqual(Play.objects.get().source, "reddit")

        other = self.client_class()
        other.get("/", HTTP_USER_AGENT=BROWSER)
        self.play_full_game(edition, [30, 75, 150], client=other)
        self.assertEqual(Play.objects.exclude(source="reddit").get().source, "direct")

    def test_link_preview_bots_are_not_counted(self):
        self.client.get("/?ref=share", HTTP_USER_AGENT="WhatsApp/2.23")
        self.assertNotIn("src", self.client.session)

    def test_referer_names(self):
        own = {"find-bananas.com", "www.find-bananas.com"}
        self.assertEqual(source_from_referer("https://t.co/abc", own), "x")
        self.assertEqual(source_from_referer("https://www.google.fr/", own), "google")
        self.assertEqual(source_from_referer("https://find-bananas.com/profile/", own), None)
        self.assertEqual(source_from_referer("https://blog.example.org/post", own), "blog.example.org")
        self.assertEqual(source_from_referer("", own), None)

    def test_share_text_uses_the_tracked_link(self):
        with open("find_bananas/static/find_bananas/game.js", encoding="utf-8") as f:
            self.assertIn('"/?ref=share"', f.read())


class StatsPageTests(TestCase):
    def test_staff_only(self):
        make_edition()
        self.assertEqual(self.client.get("/stats/").status_code, 302)
        user = User.objects.create_user(email="p@example.com", username="banana_fan")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/stats/").status_code, 302)
        call_command("make_staff", "P@example.com", stdout=StringIO())
        response = self.client.get("/stats/")
        self.assertContains(response, "Joueurs aujourd")
        self.assertContains(response, "?ref=tiktok")
        self.assertContains(self.client.get("/profile/"), "/stats/")
