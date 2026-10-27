"""Daily editions: which one is live, and how their images are generated."""

import io
import logging
import secrets
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image

from .models import Edition, EditionRound

logger = logging.getLogger(__name__)

ASSET_DIR = Path(__file__).resolve().parent / "assets"
CANVAS_SIZE = (1080, 1080)  # square: fits portrait phones and landscape screens alike
BACKGROUND = (255, 255, 255)


@dataclass(frozen=True)
class RoundSpec:
    """Difficulty of a round. The ranges are the original game's."""

    min_count: int
    max_count: int
    object_length: int  # px on the 1080px canvas; fixed per round so size never hints at the count


ROUND_SPECS = [
    RoundSpec(20, 50, 165),
    RoundSpec(50, 100, 118),
    RoundSpec(100, 200, 84),
]

_random = secrets.SystemRandom()


# --- Which edition is live -------------------------------------------------


def _edition_tz():
    return ZoneInfo(settings.EDITION_TIMEZONE)


def edition_bounds(edition_date: date):
    """Start and end of an edition, as UTC instants.

    Converted to UTC on purpose: Python compares and subtracts two datetimes
    sharing the same ZoneInfo by wall-clock time, which is wrong across a
    daylight-saving change."""
    tz = _edition_tz()
    start = datetime.combine(edition_date, time(settings.EDITION_HOUR), tzinfo=tz)
    end = datetime.combine(edition_date + timedelta(days=1), time(settings.EDITION_HOUR), tzinfo=tz)
    return start.astimezone(dt_timezone.utc), end.astimezone(dt_timezone.utc)


def edition_date_at(moment: datetime) -> date:
    """Date of the edition that is live at `moment`."""
    local = moment.astimezone(_edition_tz())
    if local.hour < settings.EDITION_HOUR:
        return local.date() - timedelta(days=1)
    return local.date()


def get_live_edition(market: str = "global", now: datetime | None = None) -> Edition:
    """The edition live right now, generated on the fly if the scheduled job
    has not created it (a safety net: normally `generate_editions` runs ahead
    of time)."""
    edition_date = edition_date_at(now or timezone.now())
    edition = Edition.objects.filter(market=market, date=edition_date).first()
    if edition is None:
        logger.warning("No pre-generated edition for %s/%s, generating now.", market, edition_date)
        edition = ensure_edition(edition_date, market)
    return edition


def ensure_edition(edition_date: date, market: str = "global") -> Edition:
    """Return the edition for this day, creating it if needed. Safe to call
    from several processes at once: the unique constraint picks one winner."""
    existing = Edition.objects.filter(market=market, date=edition_date).first()
    if existing:
        return existing

    # Render outside the transaction: it is the slow part.
    rendered = [render_round(spec) for spec in ROUND_SPECS]
    start, end = edition_bounds(edition_date)
    try:
        with transaction.atomic():
            edition = Edition.objects.create(
                date=edition_date,
                market=market,
                number=_edition_number(edition_date, market),
                starts_at=start,
                ends_at=end,
            )
            EditionRound.objects.bulk_create(
                EditionRound(
                    edition=edition,
                    index=i,
                    count=r.count,
                    image=r.image,
                    image_type="image/webp",
                    width=r.width,
                    height=r.height,
                )
                for i, r in enumerate(rendered, start=1)
            )
    except IntegrityError:
        # Another process created it first.
        return Edition.objects.get(market=market, date=edition_date)
    logger.info("Created edition %s (counts %s)", edition, [r.count for r in rendered])
    return edition


def _edition_number(edition_date: date, market: str) -> int:
    first = Edition.objects.filter(market=market).order_by("date").values_list("date", flat=True).first()
    if first is None or edition_date < first:
        return 1
    return (edition_date - first).days + 1


# --- Image generation ------------------------------------------------------


@dataclass
class RenderedRound:
    count: int
    image: bytes
    width: int
    height: int


@lru_cache(maxsize=8)
def _object_sprite(length: int) -> Image.Image:
    source = Image.open(ASSET_DIR / "banana_large.png").convert("RGBA")
    ratio = length / source.width
    return source.resize((length, max(1, round(source.height * ratio))), Image.LANCZOS)


def _place_centers(count: int, length: int, width: int, height: int) -> list[tuple[float, float]]:
    """Random centers kept at least `min_dist` apart, so objects may overlap
    but none is hidden entirely under another. The distance is relaxed
    progressively if the canvas gets crowded."""
    margin = length * 0.5
    min_dist = length * 0.55
    centers: list[tuple[float, float]] = []
    attempts = 0
    while len(centers) < count:
        x = _random.uniform(margin, width - margin)
        y = _random.uniform(margin, height - margin)
        if all((x - cx) ** 2 + (y - cy) ** 2 >= min_dist**2 for cx, cy in centers):
            centers.append((x, y))
            attempts = 0
            continue
        attempts += 1
        if attempts > 400:
            min_dist *= 0.95
            attempts = 0
    return centers


def render_round(spec: RoundSpec, count: int | None = None) -> RenderedRound:
    count = count if count is not None else _random.randint(spec.min_count, spec.max_count)
    width, height = CANVAS_SIZE
    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND)
    for cx, cy in _place_centers(count, spec.object_length, width, height):
        scale = _random.uniform(0.88, 1.12)
        length = max(8, round(spec.object_length * scale))
        sprite = _object_sprite(length).rotate(_random.uniform(0, 360), resample=Image.BICUBIC, expand=True)
        canvas.paste(sprite, (round(cx - sprite.width / 2), round(cy - sprite.height / 2)), sprite)
    buffer = io.BytesIO()
    canvas.save(buffer, format="WEBP", quality=80, method=4)
    return RenderedRound(count=count, image=buffer.getvalue(), width=width, height=height)


def object_density_ok(spec: RoundSpec) -> bool:
    """Sanity check used by tests: the busiest round still leaves room."""
    w, h = CANVAS_SIZE
    sprite = _object_sprite(spec.object_length)
    return spec.max_count * sprite.width * sprite.height < 0.9 * w * h
