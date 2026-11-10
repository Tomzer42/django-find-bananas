"""Give an existing account access to /stats/ and /admin/.

    python manage.py make_staff you@example.com

Works for Google accounts too (no password needed: being signed in on the
site is enough). --remove takes the access back.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Give an account staff access (statistics page and admin)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--remove", action="store_true", help="Remove the access instead.")

    def handle(self, email, remove=False, **options):
        user = get_user_model().objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise CommandError(f"No account with the email {email}.")
        user.is_staff = user.is_superuser = not remove
        user.save(update_fields=["is_staff", "is_superuser"])
        state = "removed from" if remove else "given"
        self.stdout.write(self.style.SUCCESS(f"{user.email}: staff access {state}."))
