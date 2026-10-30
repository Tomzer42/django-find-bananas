import json

from django.test import TestCase

from .helpers import make_edition


class LanguageTests(TestCase):
    def setUp(self):
        self.edition = make_edition()

    def strings(self, response):
        html = response.content.decode()
        start = html.index('<script id="i18n" type="application/json">') + len('<script id="i18n" type="application/json">')
        return json.loads(html[start:html.index("</script>", start)])

    def test_french_browser_gets_french(self):
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="fr-FR,fr;q=0.9,en;q=0.8")
        self.assertContains(response, '<html lang="fr">')
        self.assertContains(response, "Combien de bananes")
        self.assertEqual(self.strings(response)["nextRound"], "Round suivant")

    def test_other_languages_fall_back_to_english(self):
        for header in ["it-IT,it;q=0.9", "zh-CN", ""]:
            response = self.client.get("/", HTTP_ACCEPT_LANGUAGE=header)
            self.assertContains(response, '<html lang="en">')
            self.assertContains(response, "How many bananas?")

    def test_visitor_choice_overrides_the_browser(self):
        self.client.post("/i18n/setlang/", {"language": "en", "next": "/"}, HTTP_ACCEPT_LANGUAGE="fr")
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="fr")
        self.assertContains(response, '<html lang="en">')

    def test_share_text_and_numbers_in_french(self):
        strings = self.strings(self.client.get("/", HTTP_ACCEPT_LANGUAGE="fr"))
        self.assertEqual(strings["shareTitle"], "Find Bananas n°{number}")
        self.assertIn("{p}", strings["topPercent"])
        self.assertIn("{players}", strings["topPercent"])

    def test_django_messages_are_translated_too(self):
        response = self.client.post(
            "/account/signup/",
            {"email": "a@example.com", "username": "Lea", "password1": "short", "password2": "short"},
            HTTP_ACCEPT_LANGUAGE="fr",
        )
        self.assertContains(response, "Ce mot de passe est trop court")
