import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts import google
from accounts.models import User

CLIENT = "client-123.apps.googleusercontent.com"


def claims(nonce, **extra):
    data = {
        "aud": CLIENT,
        "iss": "https://accounts.google.com",
        "exp": int(time.time()) + 300,
        "nonce": nonce,
        "sub": "google-42",
        "email": "Player@Example.com",
        "email_verified": True,
    }
    data.update(extra)
    return data


@override_settings(GOOGLE_CLIENT_ID=CLIENT, GOOGLE_CLIENT_SECRET="secret")
class GoogleLoginTests(TestCase):
    def begin(self, next_url=None):
        url = reverse("google_login") + (f"?next={next_url}" if next_url else "")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(query["client_id"], [CLIENT])
        self.assertTrue(query["redirect_uri"][0].endswith("/account/google/callback/"))
        return query["state"][0], query["nonce"][0]

    def finish(self, state, returned_claims):
        with mock.patch.object(google, "exchange_code", return_value=returned_claims):
            return self.client.get(reverse("google_callback"), {"state": state, "code": "abc"})

    def test_new_player_is_created_and_asked_for_a_username(self):
        state, nonce = self.begin()
        response = self.finish(state, claims(nonce))
        user = User.objects.get()
        self.assertEqual(user.email, "player@example.com")
        self.assertEqual(user.google_sub, "google-42")
        self.assertFalse(user.has_usable_password())
        self.assertIsNone(user.username)
        # Home redirects to the username page.
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/"), reverse("choose_username") + "?next=/", fetch_redirect_response=False)

    def test_existing_email_account_is_linked(self):
        existing = User.objects.create_user(email="player@example.com", password="pw-12345678", username="banana_fan")
        state, nonce = self.begin(next_url="/account/profile/")
        response = self.finish(state, claims(nonce))
        self.assertRedirects(response, "/account/profile/", fetch_redirect_response=False)
        existing.refresh_from_db()
        self.assertEqual(existing.google_sub, "google-42")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(int(self.client.session["_auth_user_id"]), existing.pk)

    def test_returning_player_found_by_google_id_even_if_email_changed(self):
        User.objects.create_user(email="old@example.com", username="banana_fan", google_sub="google-42")
        state, nonce = self.begin()
        self.finish(state, claims(nonce, email="new@example.com"))
        self.assertEqual(User.objects.count(), 1)

    def test_wrong_state_nonce_audience_or_unverified_email_are_refused(self):
        for bad in ("state", "nonce", "aud", "email_verified", "exp"):
            with self.subTest(bad=bad):
                state, nonce = self.begin()
                data = claims(nonce)
                if bad == "state":
                    state = "forged"
                elif bad == "nonce":
                    data["nonce"] = "other"
                elif bad == "aud":
                    data["aud"] = "someone-else"
                elif bad == "email_verified":
                    data["email_verified"] = False
                elif bad == "exp":
                    data["exp"] = int(time.time()) - 10
                response = self.finish(state, data)
                self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
                self.assertFalse(User.objects.exists())
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_state_cannot_be_replayed(self):
        state, nonce = self.begin()
        self.finish(state, claims(nonce))
        self.client.logout()
        response = self.finish(state, claims(nonce))
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unsafe_next_is_ignored(self):
        state, nonce = self.begin(next_url="https://evil.example/")
        response = self.finish(state, claims(nonce))
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_button_shown_on_login_page(self):
        self.assertContains(self.client.get(reverse("login")), reverse("google_login"))

    def test_google_account_deletes_by_typing_username(self):
        user = User.objects.create_user(email="g@example.com", username="banana_fan", google_sub="g-1")
        self.client.force_login(user)
        self.client.post(reverse("delete_account"), {"password": "wrong"})
        self.assertTrue(User.objects.exists())
        self.client.post(reverse("delete_account"), {"password": "Banana_Fan"})
        self.assertFalse(User.objects.exists())


class GoogleDisabledTests(TestCase):
    @override_settings(GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET="")
    def test_hidden_and_404_without_credentials(self):
        self.assertNotContains(self.client.get(reverse("login")), "/account/google/")
        self.assertEqual(self.client.get(reverse("google_login")).status_code, 404)
