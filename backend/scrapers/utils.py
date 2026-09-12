"""Shared scraper utilities.

- Rate limiting decorator
- User-agent rotation
- Sector taxonomy normalisation
- Indian date parsing
"""

from __future__ import annotations

import datetime
import random
import re
import time
from functools import wraps
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)

# ---------------------------------------------------------------------------
# User-agent pool
# ---------------------------------------------------------------------------

_USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
        "Gecko/20100101 Firefox/122.0"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
]


def random_user_agent() -> str:
    """Return a realistic browser user-agent from a small pool."""
    return random.choice(_USER_AGENTS)


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def throttle(min_delay: float = 1.5):
    """Decorator: ensure at least *min_delay* seconds between calls."""

    def decorator(func: F) -> F:
        last_called: list[float] = [0.0]  # mutable closure

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Sector normalisation
# ---------------------------------------------------------------------------

SECTOR_TAXONOMY: set[str] = {
    "education",
    "health",
    "livelihood",
    "rural_development",
    "women_empowerment",
    "disability",
    "social_welfare",
    "agriculture",
    "environment",
    "technology",
    "skill_development",
    "water_sanitation",
    "arts_culture",
    "governance",
    "minority_welfare",
    "disaster_relief",
    "capacity_building",
}

# Free-text phrases → canonical sector.  Add entries as new sources surface
# unexpected wordings.
_SECTOR_ALIASES: dict[str, str] = {
    "healthcare": "health",
    "medical": "health",
    "sanitation": "water_sanitation",
    "water": "water_sanitation",
    "drinking water": "water_sanitation",
    "wash": "water_sanitation",
    "rural": "rural_development",
    "tribal": "social_welfare",
    "sc/st": "social_welfare",
    "scheduled caste": "social_welfare",
    "scheduled tribe": "social_welfare",
    "women": "women_empowerment",
    "girl child": "women_empowerment",
    "gender": "women_empowerment",
    "pwd": "disability",
    "disabled": "disability",
    "persons with disabilities": "disability",
    "divyang": "disability",
    "elderly": "social_welfare",
    "senior citizen": "social_welfare",
    "drug": "health",
    "deaddiction": "health",
    "nutrition": "health",
    "farming": "agriculture",
    "fisheries": "agriculture",
    "animal husbandry": "agriculture",
    "watershed": "environment",
    "ecology": "environment",
    "climate": "environment",
    "conservation": "environment",
    "forest": "environment",
    "science": "technology",
    "innovation": "technology",
    "digital": "technology",
    "ict": "technology",
    "vocational": "skill_development",
    "skilling": "skill_development",
    "training": "skill_development",
    "employment": "skill_development",
    "livelihood": "livelihood",
    "fpo": "agriculture",
    "farmer producer": "agriculture",
    "self help group": "livelihood",
    "shg": "livelihood",
    "art": "arts_culture",
    "culture": "arts_culture",
    "heritage": "arts_culture",
    "disaster": "disaster_relief",
    "flood": "disaster_relief",
    "relief": "disaster_relief",
    "panchayat": "governance",
    "governance": "governance",
    "minority": "minority_welfare",
    "muslim": "minority_welfare",
    "christian": "minority_welfare",
    "madrasa": "minority_welfare",
}


def normalize_sectors(raw_sectors: list[str]) -> list[str]:
    """Map free-text sector labels to the project's canonical taxonomy.

    Returns a de-duplicated list preserving insertion order.
    """
    normalised: list[str] = []

    for raw in raw_sectors:
        raw_lower = raw.strip().lower()

        # 1. Direct match against canonical set.
        if raw_lower.replace(" ", "_") in SECTOR_TAXONOMY:
            _add_unique(normalised, raw_lower.replace(" ", "_"))
            continue

        # 2. Substring match against aliases.
        for phrase, sector in _SECTOR_ALIASES.items():
            if phrase in raw_lower:
                _add_unique(normalised, sector)

        # 3. Substring match against canonical names.
        for sector in SECTOR_TAXONOMY:
            if sector.replace("_", " ") in raw_lower:
                _add_unique(normalised, sector)

    return normalised


def _add_unique(lst: list[str], val: str) -> None:
    if val not in lst:
        lst.append(val)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_ORDINAL_RE = re.compile(r"(\d+)(st|nd|rd|th)\b", re.IGNORECASE)

_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y-%m-%d",
    "%d %b, %Y",
    "%d %B, %Y",
]


def parse_indian_date(text: str) -> datetime.date | None:
    """Parse common Indian date formats into a ``datetime.date``.

    Handles ordinal suffixes (``1st``, ``2nd``, ``3rd``, ``4th``).
    Returns ``None`` on failure rather than raising.
    """
    if not text:
        return None

    cleaned = _ORDINAL_RE.sub(r"\1", text.strip())

    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    return None
