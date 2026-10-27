from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from find_bananas.editions import edition_date_at, ensure_edition, redraw_edition


class Command(BaseCommand):
    help = (
        "Create the live edition and the next ones if they do not exist yet. "
        "Idempotent: run it from a scheduler (e.g. every hour)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--ahead", type=int, default=2, help="Number of future editions to prepare (default 2).")
        parser.add_argument("--market", default="global")
        parser.add_argument(
            "--redraw",
            action="store_true",
            help="Local only (DJANGO_DEBUG=1): redraw the images of these editions, keeping their counts.",
        )

    def handle(self, *args, ahead, market, redraw, **options):
        if redraw and not settings.DEBUG:
            raise CommandError("--redraw is for local testing only (DJANGO_DEBUG=1).")
        today = edition_date_at(timezone.now())
        for offset in range(ahead + 1):
            edition = ensure_edition(today + timedelta(days=offset), market)
            if redraw:
                redraw_edition(edition)
            self.stdout.write(f"{edition} — live from {edition.starts_at.isoformat()}")
