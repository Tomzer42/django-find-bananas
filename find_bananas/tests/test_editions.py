from datetime import date, datetime
from io import BytesIO, StringIO
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from find_bananas.editions import (
    ROUND_SPECS,
    edition_bounds,
    edition_date_at,
    ensure_edition,
    redraw_edition,
    render_round,
)
from find_bananas.models import Edition

PARIS = ZoneInfo("Europe/Paris")


@override_settings(EDITION_TIMEZONE="Europe/Paris", EDITION_HOUR=12)
class EditionScheduleTests(TestCase):
    def test_switches_at_noon_paris(self):
        self.assertEqual(edition_date_at(datetime(2026, 10, 27, 11, 59, tzinfo=PARIS)), date(2026, 10, 26))
        self.assertEqual(edition_date_at(datetime(2026, 10, 27, 12, 0, tzinfo=PARIS)), date(2026, 10, 27))

    def test_same_edition_everywhere(self):
        tokyo = datetime(2026, 10, 28, 19, 59, tzinfo=ZoneInfo("Asia/Tokyo"))  # 11:59 in Paris
        new_york = datetime(2026, 10, 27, 7, 0, tzinfo=ZoneInfo("America/New_York"))  # 12:00 in Paris
        self.assertEqual(edition_date_at(tokyo), date(2026, 10, 27))
        self.assertEqual(edition_date_at(new_york), date(2026, 10, 27))

    def test_bounds_follow_daylight_saving(self):
        # Clocks go back on 2026-10-25: that edition lasts 25 hours.
        start, end = edition_bounds(date(2026, 10, 24))
        self.assertEqual((end - start).total_seconds(), 25 * 3600)
        self.assertEqual(start.astimezone(PARIS).hour, 12)
        self.assertEqual(end.astimezone(PARIS).hour, 12)


class EditionGenerationTests(TestCase):
    def test_render_round_matches_spec(self):
        for spec in ROUND_SPECS:
            rendered = render_round(spec)
            self.assertGreaterEqual(rendered.count, spec.min_count)
            self.assertLessEqual(rendered.count, spec.max_count)
            image = Image.open(BytesIO(rendered.image))
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (rendered.width, rendered.height))
            self.assertLess(len(rendered.image), 300 * 1024)

    def test_ensure_edition_is_idempotent_and_numbered(self):
        first = ensure_edition(date(2026, 11, 1))
        again = ensure_edition(date(2026, 11, 1))
        third = ensure_edition(date(2026, 11, 3))
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(first.number, 1)
        self.assertEqual(third.number, 3)
        self.assertEqual(first.rounds.count(), 3)
        self.assertEqual(Edition.objects.count(), 2)

    def test_command_prepares_editions_ahead(self):
        call_command("generate_editions", "--ahead", "1", stdout=StringIO())
        self.assertEqual(Edition.objects.count(), 2)
        call_command("generate_editions", "--ahead", "1", stdout=StringIO())
        self.assertEqual(Edition.objects.count(), 2)

    @override_settings(DEBUG=True)
    def test_redraw_keeps_counts(self):
        edition = ensure_edition(date(2026, 11, 1))
        before = list(edition.rounds.values_list("count", "image"))
        call_command("generate_editions", "--ahead", "0", "--redraw", stdout=StringIO())
        redraw_edition(edition)
        after = list(edition.rounds.values_list("count", "image"))
        self.assertEqual([c for c, _ in before], [c for c, _ in after])
        self.assertNotEqual([bytes(i) for _, i in before], [bytes(i) for _, i in after])

    def test_redraw_refused_in_production(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("generate_editions", "--redraw", stdout=StringIO())

