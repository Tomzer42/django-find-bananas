from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from find_bananas.players import claim_guest_plays, get_guest_key


@receiver(user_logged_in)
def attach_guest_plays(sender, request, user, **kwargs):
    """A guest who signs up or logs in keeps the games played on this device."""
    if request is not None:
        claim_guest_plays(user, get_guest_key(request))
