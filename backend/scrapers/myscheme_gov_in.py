"""myscheme.gov.in scraper — Next.js ``__NEXT_DATA__`` parser.

The portal is built on Next.js with Server-Side Rendering.  Every scheme page
embeds a ``<script id="__NEXT_DATA__">`` tag containing fully structured JSON
metadata.  This scraper:

1. Fetches the sitemap to discover all ``/schemes/*`` slugs.
2. For each slug, HTTP-GETs the page and parses the embedded JSON — **no
   headless browser required**.
3. Filters for NGO-relevant schemes (keyword matching against the full JSON).
4. Normalises the result to the grants table schema.

~95 % of schemes on myScheme are citizen-facing.  The keyword filter keeps
only those mentioning NGOs, voluntary organisations, implementing agencies,
or grant-in-aid language.

Rate limit: 1 req / 2 s to stay below Cloudflare thresholds.
"""

from __future__ import annotations

import json
import logging

from bs4 import BeautifulSoup

from .base import BaseScraper
from .utils import normalize_sectors

logger = logging.getLogger(__name__)

# Keywords that suggest a scheme involves NGO implementation or funding.
_NGO_KEYWORDS = [
    "ngo",
    "voluntary organisation",
    "voluntary organization",
    "implementing agency",
    "non-profit",
    "non profit",
    "registered society",
    "registered trust",
    "section 8",
    "grant-in-aid",
    "grant in aid",
    "civil society",
    "community based organisation",
    "community based organization",
]


class MySchemeScraper(BaseScraper):
    """Parser for myscheme.gov.in scheme pages."""

    def __init__(self, *, max_schemes: int = 500, min_delay: float = 2.0) -> None:
        super().__init__(min_delay=min_delay)
        self.max_schemes = max_schemes

    # ------------------------------------------------------------------
    # Sitemap discovery
    # ------------------------------------------------------------------

    def get_scheme_urls(self) -> list[str]:
        """Parse the sitemap for ``/schemes/*`` URLs."""
        resp = self.get("https://www.myscheme.gov.in/sitemap.xml")
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml-xml")
        urls: list[str] = []
        for loc in soup.find_all("loc"):
            url = loc.text.strip()
            if "/schemes/" in url:
                urls.append(url)

        logger.info("sitemap contains %d scheme URLs", len(urls))
        return urls

    # ------------------------------------------------------------------
    # Scrape
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        urls = self.get_scheme_urls()
        raw_data: list[dict] = []

        for url in urls[: self.max_schemes]:
            try:
                resp = self.get(url)
                if resp.status_code != 200:
                    logger.warning("HTTP %d for %s", resp.status_code, url)
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                script_tag = soup.find("script", id="__NEXT_DATA__")
                if not script_tag or not script_tag.string:
                    continue

                next_data = json.loads(script_tag.string)
                page_props = next_data.get("props", {}).get("pageProps", {})
                scheme = page_props.get("scheme") or page_props.get("data", {})
                if not scheme:
                    continue

                # Keyword filter: check the full JSON blob for NGO relevance.
                scheme_blob = json.dumps(scheme).lower()
                if not any(kw in scheme_blob for kw in _NGO_KEYWORDS):
                    continue

                scheme["_source_url"] = url
                raw_data.append(scheme)
                logger.debug("kept NGO-relevant scheme from %s", url)

            except Exception:
                logger.exception("failed to parse %s", url)

        logger.info(
            "filtered %d NGO-relevant schemes from %d checked",
            len(raw_data),
            min(len(urls), self.max_schemes),
        )
        return raw_data

    # ------------------------------------------------------------------
    # Normalise
    # ------------------------------------------------------------------

    def to_grants_rows(self, raw_data: list[dict]) -> list[dict]:
        rows: list[dict] = []

        for item in raw_data:
            # myScheme JSON structure varies; try common shapes.
            basic = item.get("basicDetails", item)
            title = (
                basic.get("schemeName")
                or basic.get("name")
                or item.get("title", "")
            ).strip()
            if not title:
                continue

            ministry_obj = item.get("ministry", {})
            ministry = (
                ministry_obj.get("name")
                if isinstance(ministry_obj, dict)
                else str(ministry_obj)
            ) or "Government of India"

            description = (
                basic.get("briefDescription")
                or basic.get("description")
                or basic.get("shortDescription")
                or ""
            )

            # Tags / sectors
            tags = item.get("tags", [])
            if isinstance(tags, list):
                sectors = normalize_sectors(tags)
            else:
                sectors = []

            # Eligibility
            eligibility: dict = {}
            criteria = item.get("eligibilityCriteria") or item.get("eligibility")
            if criteria:
                eligibility["criteria"] = criteria

            rows.append({
                "title": title,
                "funder_name": ministry,
                "funder_type": "govt",
                "description": description[:2000],  # cap at 2 KB
                "eligibility_json": eligibility,
                "sectors": sectors,
                "geography": [],  # myScheme doesn't always specify geography
                "deadline": None,  # most are "ongoing / year-round"
                "source_url": item.get("_source_url", ""),
                "source": "myscheme_scraper",
            })

        return rows
