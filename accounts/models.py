from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


def check_username(value):
    # Imported here to keep the model importable without the word lists.
    from .usernames import validate_username

    validate_username(value)


class User(AbstractBaseUser, PermissionsMixin):
    """A player account: an email, a password and a public username."""

    email = models.EmailField(_("email address"), unique=True)
    # Public. Empty only for accounts created before usernames existed (and,
    # later, right after a Google sign-in): those are asked to choose one.
    username = models.CharField(
        _("username"), max_length=20, null=True, blank=True, validators=[check_username]
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("username"), name="unique_username_ignoring_case"),
        ]

    def __str__(self):
        return self.username or self.email

    def save(self, *args, **kwargs):
        # An empty username is stored as NULL so the uniqueness rule ignores it.
        if not self.username:
            self.username = None
        super().save(*args, **kwargs)
