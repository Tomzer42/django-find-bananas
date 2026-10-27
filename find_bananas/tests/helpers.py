import json
from datetime import timedelta

from django.utils import timezone

from find_bananas.editions import edition_date_at
from find_bananas.models import Edition, EditionRound

TINY_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8L\r\x00\x00\x00/\x00\x00\x00\x10\x07\x10\x11\x11\x88\x88\xfe\x07\x00"


def make_edition(counts=(30, 75, 150), number=1, live=True):
    """A live edition with fake (tiny) images, without running Pillow."""
    now = timezone.now()
    edition = Edition.objects.create(
        date=edition_date_at(now) if live else edition_date_at(now) - timedelta(days=number),
        number=number,
        starts_at=now - timedelta(hours=1) if live else now - timedelta(days=3),
        ends_at=now + timedelta(hours=23) if live else now - timedelta(days=2),
    )
    for i, count in enumerate(counts, start=1):
        EditionRound.objects.create(
            edition=edition, index=i, count=count, image=TINY_WEBP, width=1, height=1
        )
    return edition


class GameClientMixin:
    """Drive the JSON API like the browser does."""

    def api(self, edition, path, body=None, client=None):
        client = client or self.client
        url = f"/api/editions/{edition.number}{path}"
        if body is None and path.endswith("state"):
            return client.get(url)
        return client.post(url, data=json.dumps(body or {}), content_type="application/json")

    def play_round(self, edition, index, guess, client=None):
        self.assertEqual(self.api(edition, f"/rounds/{index}/image", client=client).status_code, 200)
        return self.api(edition, f"/rounds/{index}/answer", {"guess": guess}, client=client)

    def play_full_game(self, edition, guesses, client=None):
        self.assertEqual(self.api(edition, "/start", client=client).status_code, 200)
        response = None
        for index, guess in enumerate(guesses, start=1):
            response = self.play_round(edition, index, guess, client=client)
            self.assertEqual(response.status_code, 200, response.content)
        return response.json()
