"""Base scraper functionality.

All scrapers inherit from BaseScraper, which provides session management, rate
limiting (via urllib3 retry), structured logging, and upsert logic against the
grants table.  The abstract contract: implement ``scrape`` (fetch raw data) and
``to_grants_rows`` (normalise it to the grants schema).

The upsert conflict key is ``(funder_name, title)`` — matching the unique index
in ``0001_init.sql``.
"""

from __future__ import annotations

import json
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.db import pool

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all GrantSetu scrapers."""

    def __init__(self, min_delay: float = 1.5) -> None:
        self.min_delay = min_delay
        self._last_request_at: float = 0.0

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
        })

        # Exponential backoff retry with jitter for transient failures.
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            backoff_jitter=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        """Sleep if necessary to keep requests at least ``min_delay`` apart."""
        elapsed = time.time() - self._last_request_at
        if elapsed < self.min_delay:
            jitter = random.uniform(0, 0.3)
            time.sleep(self.min_delay - elapsed + jitter)
        self._last_request_at = time.time()

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Rate-limited GET."""
        self._throttle()
        logger.debug("GET %s", url)
        return self.session.get(url, timeout=30, **kwargs)

    # ------------------------------------------------------------------
    # Abstract contract
    # ------------------------------------------------------------------

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Fetch raw data from the source. Returns un-normalised dicts."""

    @abstractmethod
    def to_grants_rows(self, raw_data: list[dict]) -> list[dict]:
        """Normalise raw scraped data to the grants table schema.

        Each dict must contain at minimum ``title`` and ``funder_name``.
        """

    # ------------------------------------------------------------------
    # Database persistence
    # ------------------------------------------------------------------

    def upsert_to_db(self, rows: list[dict]) -> dict[str, int]:
        """Upsert normalised rows into the ``grants`` table.

        Returns ``{"upserted": n, "errors": m}``.
        """
        stats: dict[str, int] = {"upserted": 0, "errors": 0}

        for row in rows:
            eligibility_json = json.dumps(row.get("eligibility_json", {}))
            try:
                pool.execute(
                    """
                    insert into grants
                        (title, funder_name, funder_type, description,
                         eligibility_json, sectors, geography, deadline,
                         source_url, source, embedding)
                    values (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s)
                    on conflict (funder_name, title) do update set
                        funder_type      = excluded.funder_type,
                        source_url       = excluded.source_url,
                        description      = excluded.description,
                        eligibility_json = excluded.eligibility_json,
                        sectors          = excluded.sectors,
                        geography        = excluded.geography,
                        deadline         = excluded.deadline,
                        embedding        = coalesce(excluded.embedding,
                                                    grants.embedding),
                        last_seen_at     = now(),
                        is_active        = true
                    """,
                    (
                        row["title"],
                        row["funder_name"],
                        row.get("funder_type"),
                        row.get("description", ""),
                        eligibility_json,
                        row.get("sectors", []),
                        row.get("geography", []),
                        row.get("deadline"),
                        row.get("source_url"),
                        row.get("source", "scraper"),
                        row.get("embedding"),
                    ),
                )
                stats["upserted"] += 1
            except Exception:
                logger.exception("upsert failed for %r", row.get("title"))
                stats["errors"] += 1

        return stats

    def embed_and_upsert(self, rows: list[dict]) -> dict[str, int]:
        """Generate embeddings for *rows*, then upsert.

        Embedding text is built the same way as ``seed_grants.py`` so that
        seed rows and scraped rows land in the same vector space.
        """
        from app.services.embeddings import embed_texts

        texts = []
        for row in rows:
            sectors_str = ", ".join(row.get("sectors", []))
            texts.append(
                f"{row.get('title', '')}. {row.get('funder_name', '')}. "
                f"{row.get('description', '')} Sectors: {sectors_str}."
            )

        if texts:
            logger.info("embedding %d rows...", len(texts))
            vectors = embed_texts(texts)
            for row, vector in zip(rows, vectors, strict=True):
                row["embedding"] = vector

        return self.upsert_to_db(rows)

    # ------------------------------------------------------------------
    # Convenience: full pipeline
    # ------------------------------------------------------------------

    def run(
        self, *, dry_run: bool = False, embed: bool = True
    ) -> tuple[list[dict], dict[str, int]]:
        """Scrape → normalise → (embed →) upsert. Returns (rows, stats)."""
        raw = self.scrape()
        logger.info("scraped %d raw items", len(raw))

        rows = self.to_grants_rows(raw)
        logger.info("normalised to %d grants rows", len(rows))

        if dry_run:
            return rows, {"dry_run": len(rows)}

        if embed:
            stats = self.embed_and_upsert(rows)
        else:
            stats = self.upsert_to_db(rows)

        return rows, stats
