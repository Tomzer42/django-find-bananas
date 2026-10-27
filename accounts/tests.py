from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase

from find_bananas.models import Play
from find_bananas.tests.helpers import GameClientMixin, make_edition

from .models import User

PASSWORD = "banana-split-42"


class AccountTests(GameClientMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.edition = make_edition(counts=(30, 75, 150))

    def signup(self, email="tom@example.com", client=None):
        client = client or self.client
        return client.post(
            "/account/signup/", {"email": email, "password1": PASSWORD, "password2": PASSWORD, "next": "/"}
        )

    def test_guest_can_play_without_account(self):
        state = self.play_full_game(self.edition, [30, 75, 150])["state"]
        self.assertEqual(state["status"], "completed")
        self.assertIsNone(Play.objects.get().user)

    def test_signup_after_game_attaches_the_guest_play(self):
        self.play_full_game(self.edition, [31, 75, 150])
        response = self.signup()
        self.assertRedirects(response, "/")
        user = User.objects.get(email="tom@example.com")
        self.assertEqual(Play.objects.get().user, user)
        history = self.client.get("/history/")
        self.assertContains(history, "#1")

    def test_email_is_case_insensitive_and_unique(self):
        self.signup("Tom@Example.com")
        self.client.post("/account/logout/")
        response = self.signup("tom@example.COM")
        self.assertContains(response, "already exists")
        self.assertTrue(self.client.login(username="tom@example.com", password=PASSWORD))

    def test_login_from_another_device_keeps_one_play_per_edition(self):
        self.signup()
        self.play_full_game(self.edition, [30, 75, 150])
        self.client.post("/account/logout/")

        other = Client()
        self.play_full_game(self.edition, [10, 10, 10], client=other)  # as a guest on another device
        other.post("/account/login/", {"username": "tom@example.com", "password": PASSWORD})
        user = User.objects.get()
        self.assertEqual(Play.objects.filter(user=user).count(), 1)
        self.assertEqual(Play.objects.get(user=user).score, 0)
        # The device now shows the account's game.
        self.assertContains(other.get("/"), '"score": 0')

    def test_history_is_private(self):
        self.signup("a@example.com")
        self.play_full_game(self.edition, [30, 75, 150])
        self.client.post("/account/logout/")
        self.assertRedirects(self.client.get("/history/"), "/account/login/?next=/history/")

        intruder = Client()
        self.signup("b@example.com", client=intruder)
        page = intruder.get("/history/").content.decode()
        self.assertNotIn("a@example.com", page)
        self.assertIn("No results yet", page)

    def test_logout_requires_post(self):
        self.signup()
        self.assertEqual(self.client.get("/account/logout/").status_code, 405)

    def test_password_reset_sends_an_email(self):
        self.signup()
        self.client.post("/account/logout/")
        self.client.post("/account/password-reset/", {"email": "tom@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/account/password-reset/", mail.outbox[0].body)

    def test_delete_account_removes_its_results(self):
        self.signup()
        self.play_full_game(self.edition, [30, 75, 150])
        response = self.client.post("/account/delete/", {"password": "wrong"})
        self.assertContains(response, "Wrong password")
        self.client.post("/account/delete/", {"password": PASSWORD})
        self.assertFalse(User.objects.exists())
        self.assertFalse(Play.objects.exists())

    def test_login_is_rate_limited(self):
        codes = [
            self.client.post("/account/login/", {"username": "x@example.com", "password": "nope"}).status_code
            for _ in range(11)
        ]
        self.assertEqual(codes[-1], 429)

    def test_open_redirect_is_blocked(self):
        response = self.client.post(
            "/account/signup/",
            {"email": "t@example.com", "password1": PASSWORD, "password2": PASSWORD, "next": "https://evil.example"},
        )
        self.assertRedirects(response, "/")
