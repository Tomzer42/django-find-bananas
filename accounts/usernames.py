"""Usernames (pseudos): format, reserved names and a basic vulgarity filter.

Usernames are public, so they are checked when chosen or changed:
- 3 to 20 characters: letters without accents, digits, "_" and "-";
- unique regardless of case ("Tom" and "tom" cannot both exist);
- not a reserved name, not vulgar or hateful.

The filter is deliberately simple and will never be perfect: staff can rename
any player from /admin/. To block a new word, add it to one of the lists
below (lowercase, without accents).

Two lists, to avoid blocking innocent names (the "Scunthorpe problem"):
- BLOCKED_ANYWHERE: long, unambiguous words, refused even inside a name.
- BLOCKED_WORDS: short words that also appear inside innocent names
  ("con" in "Constance", "pute" in "computer"), refused only as a whole
  word of the name (name split on "_", "-" and digits, or the whole name).
"""

import re
import unicodedata

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MIN_LENGTH = 3
MAX_LENGTH = 20
FORMAT = re.compile(r"^[A-Za-z0-9_-]+$")

RESERVED = {
    "admin", "administrator", "administrateur", "root", "staff", "support", "moderator",
    "moderateur", "modo", "system", "systeme", "official", "officiel", "findbananas",
    "find_bananas", "find-bananas", "bananas", "anonymous", "anonyme", "guest", "invite",
    "null", "none", "undefined", "me", "moi", "claude", "anthropic",
}

BLOCKED_ANYWHERE = {
    # English
    "fuck", "shit", "bitch", "asshole", "dickhead", "motherf", "whore", "slut",
    "bastard", "wanker", "nigger", "nigga", "faggot", "pedophil", "paedophil",
    # French
    "connard", "connasse", "salope", "salaud", "encule", "enculer", "putain", "batard",
    "fdp", "ntm", "nique ta", "niquetamere", "bougnoul", "youpin",
    "tafiole", "tapette", "gouine", "branleur", "pouffiasse", "petasse", "trouduc",
    # Hate
    "hitler", "heilhitler", "siegheil", "kkk", "daesh",
}

BLOCKED_WORDS = {
    # English
    "ass", "dick", "cock", "pussy", "fag", "sex", "porn", "anal", "rape", "tits", "boobs", "cum",
    "cunt", "retard", "rapist", "nazi", "negro",
    # French
    "con", "conne", "cul", "pute", "putes", "bite", "chatte", "couille", "couilles", "merde",
    "nique", "niquer", "pd", "pede", "tg", "fion", "zob", "teub", "pedale", "nazis", "negre",
}

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "@": "a", "$": "s"})


def _strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def is_vulgar(name: str) -> bool:
    lowered = _strip_accents(name).lower()
    # Whole words as typed: "Tom_con" -> ["tom", "con"].
    words = [w for w in re.split(r"[_\-0-9]+", lowered) if w]
    # Squashed and de-leeted: "F_u_c_k", "sh1t" -> "fuck", "shit".
    squashed = re.sub(r"[_\-]+", "", lowered).translate(_LEET)
    letters_only = re.sub(r"[^a-z]+", "", squashed)
    for blocked in BLOCKED_ANYWHERE:
        compact = blocked.replace(" ", "")
        if compact in squashed or compact in letters_only:
            return True
    candidates = set(words) | {squashed, letters_only}
    return any(c in BLOCKED_WORDS for c in candidates)


def validate_username(value: str) -> str:
    """Return the cleaned username or raise ValidationError."""
    name = (value or "").strip()
    if not MIN_LENGTH <= len(name) <= MAX_LENGTH:
        raise ValidationError(
            _("Your username must be %(min)s to %(max)s characters long."),
            params={"min": MIN_LENGTH, "max": MAX_LENGTH},
            code="length",
        )
    if not FORMAT.match(name):
        raise ValidationError(
            _("Use only letters without accents, digits, “_” and “-”."), code="format"
        )
    lowered = name.lower()
    if lowered in RESERVED or lowered.replace("-", "").replace("_", "") in RESERVED:
        raise ValidationError(_("This username is reserved. Choose another one."), code="reserved")
    if is_vulgar(name):
        raise ValidationError(
            _("This username is not allowed. Choose one that everyone can see."), code="vulgar"
        )
    return name
