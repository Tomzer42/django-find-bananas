from django.conf import settings
from django.db import models
from django.db.models import Q


class Edition(models.Model):
    """The daily challenge: the same rounds for every player of a market.

    `market` and `theme` are not used for anything yet beyond their defaults.
    They exist so that country-specific or sponsored editions ("cans in Italy
    this Monday") can be added later as new rows, without a schema change.
    """

    date = models.DateField(help_text="Day the edition goes live (at EDITION_HOUR, EDITION_TIMEZONE).")
    market = models.CharField(max_length=32, default="global")
    theme = models.CharField(max_length=32, default="banana", help_text="Object shown in the images.")
    number = models.PositiveIntegerField(help_text="Public edition number, shown in share messages.")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["market", "date"], name="unique_edition_per_market_day")]
        indexes = [models.Index(fields=["market", "starts_at"])]

    def __str__(self):
        return f"#{self.number} {self.date} ({self.market})"


class EditionRound(models.Model):
    """One image of an edition. The correct count never leaves the server
    before the player has answered."""

    edition = models.ForeignKey(Edition, on_delete=models.CASCADE, related_name="rounds")
    index = models.PositiveSmallIntegerField(help_text="1-based round number.")
    count = models.PositiveIntegerField()
    image = models.BinaryField()
    image_type = models.CharField(max_length=32, default="image/webp")
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()

    class Meta:
        ordering = ["edition", "index"]
        constraints = [models.UniqueConstraint(fields=["edition", "index"], name="unique_round_per_edition")]

    def __str__(self):
        return f"{self.edition} round {self.index}"


class Play(models.Model):
    """One player's attempt at one edition.

    Guests are identified by `guest_key`, a random value stored in their
    server-side session. When a guest signs up or logs in, their plays are
    attached to the account.

    `rounds` holds one entry per round:
    {"served_at": iso, "answered_at": iso|None, "guess": int|None, "count": int|None}.
    `count` is copied in once the round is answered, so a finished play is
    self-contained. Storing rounds as JSON keeps the schema stable if the
    number of rounds or the per-round data changes.
    """

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"

    edition = models.ForeignKey(Edition, on_delete=models.PROTECT, related_name="plays")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="plays"
    )
    guest_key = models.UUIDField(db_index=True)
    ip_hash = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS)
    rounds = models.JSONField(default=list)
    score = models.PositiveIntegerField(null=True, blank=True, help_text="Sum of the gaps; lower is better.")
    ranked = models.BooleanField(default=False, help_text="Counts in the comparison with other players.")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["edition", "user"], condition=Q(user__isnull=False), name="one_play_per_user_per_edition"
            ),
            models.UniqueConstraint(fields=["edition", "guest_key"], name="one_play_per_guest_per_edition"),
        ]
        indexes = [models.Index(fields=["edition", "ranked", "score"], name="play_ranking_idx")]

    def __str__(self):
        who = self.user or f"guest {str(self.guest_key)[:8]}"
        return f"{self.edition} — {who} — {self.status}"

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED
