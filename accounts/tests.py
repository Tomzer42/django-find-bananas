import uuid

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

    def signup(self, email="tom@example.com", client=None, username=None):
        client = client or self.client
        username = username or email.split("@")[0].replace(".", "_") + "_fan"
        return client.post(
            "/account/signup/",
            {"email": email, "username": username, "password1": PASSWORD, "password2": PASSWORD, "next": "/"},
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
        profile = self.client.get("/profile/")
        self.assertContains(profile, "#1")

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
        self.assertRedirects(self.client.get("/profile/"), "/account/login/?next=/profile/")

        intruder = Client()
        self.signup("b@example.com", client=intruder)
        page = intruder.get("/profile/").content.decode()
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
            {"email": "t@example.com", "username": "Tom", "password1": PASSWORD, "password2": PASSWORD,
             "next": "https://evil.example"},
        )
        self.assertRedirects(response, "/")

    def test_profile_shows_overall_and_per_round_averages(self):
        self.signup()
        self.play_full_game(self.edition, [32, 75, 140])  # gaps 2, 0, 10 -> score 12
        second = make_edition(counts=(20, 60, 100), number=2, live=False)
        Play.objects.create(
            edition=second, user=User.objects.get(), guest_key=uuid.uuid4(), status=Play.Status.COMPLETED,
            score=8, ranked=True,
            rounds=[{"guess": 24, "count": 20}, {"guess": 60, "count": 60}, {"guess": 96, "count": 100}],
        )
        summary = self.client.get("/profile/").context["summary"]
        self.assertEqual(summary["games"], 2)
        self.assertEqual(summary["best"], 8)
        self.assertEqual(summary["average"], 10.0)
        self.assertEqual(
            summary["rounds"],
            [{"index": 1, "average": 3.0}, {"index": 2, "average": 0.0}, {"index": 3, "average": 7.0}],
        )


class UsernameTests(TestCase):
    def setUp(self):
        cache.clear()

    def signup(self, username, email="u@example.com", client=None):
        return (client or self.client).post(
            "/account/signup/",
            {"email": email, "username": username, "password1": PASSWORD, "password2": PASSWORD},
        )

    def test_signup_requires_a_username(self):
        response = self.signup("")
        self.assertContains(response, "errorlist")
        self.assertFalse(User.objects.exists())
        self.signup("Banana_King")
        self.assertEqual(User.objects.get().username, "Banana_King")

    def test_username_is_unique_regardless_of_case(self):
        self.signup("Tom", email="a@example.com")
        response = self.signup("tOM", email="b@example.com", client=Client())
        self.assertContains(response, "already taken")
        self.assertEqual(User.objects.count(), 1)

    def test_format_reserved_and_vulgar_names_are_refused(self):
        for bad in ["ab", "x" * 21, "Léa", "tom!", "admin", "Find_Bananas", "connard", "F_u_c_k", "sh1t", "Tom_con"]:
            response = self.signup(bad, email=f"{abs(hash(bad))}@example.com", client=Client())
            self.assertContains(response, "errorlist", msg_prefix=bad)
        self.assertFalse(User.objects.exists())

    def test_innocent_names_are_accepted(self):
        for i, name in enumerate(["Constance", "Computer", "Scunthorpe", "Nazim", "Hitchcock", "Pascal"]):
            self.signup(name, email=f"ok{i}@example.com", client=Client())
        self.assertEqual(User.objects.count(), 6)

    def test_account_without_username_must_choose_one_but_game_api_still_works(self):
        user = User.objects.create_user("old@example.com", PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(
            self.client.get("/profile/"), "/account/username/?next=/profile/", fetch_redirect_response=False
        )
        edition = make_edition()
        self.assertEqual(self.client.post(f"/api/editions/{edition.number}/start").status_code, 200)
        self.client.post("/account/username/", {"username": "OldTimer", "next": "/profile/"})
        user.refresh_from_db()
        self.assertEqual(user.username, "OldTimer")
        self.assertEqual(self.client.get("/profile/").status_code, 200)

    def test_change_username_from_profile_and_profile_title(self):
        self.signup("FirstName")
        self.assertContains(self.client.get("/profile/"), '<h1 class="profile-name">FirstName</h1>')
        self.client.post("/account/username/", {"username": "Second_Name"})
        self.assertContains(self.client.get("/profile/"), '<h1 class="profile-name">Second_Name</h1>')
        # Keeping your own name with another case is allowed.
        self.client.post("/account/username/", {"username": "second_name"})
        self.assertEqual(User.objects.get().username, "second_name")

    def test_spaces_become_underscores(self):
        self.signup("  Banana   King ")
        self.assertEqual(User.objects.get().username, "Banana_King")
        # ...and the result is checked for uniqueness like any other name.
        response = self.signup("Banana King", email="other@example.com", client=Client())
        self.assertContains(response, "already taken")

    def test_empty_usernames_do_not_collide(self):
        User.objects.create_user("a@example.com", PASSWORD, username="")
        User.objects.create_user("b@example.com", PASSWORD)
        self.assertEqual(User.objects.filter(username__isnull=True).count(), 2)

