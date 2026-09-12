"""DST Call-for-Proposals scraper.

The Department of Science & Technology (dst.gov.in) maintains the most
standardised, machine-readable, and deadline-oriented portal among all
central ministries.  Active calls are listed in clean semantic HTML tables.

This is the **highest-value scraping target** for live grant deadlines.
"""

from __future__ import annotations

import logging
import urllib3

from bs4 import BeautifulSoup

from .base import BaseScraper
from .utils import normalize_sectors, parse_indian_date

# DST sometimes has an expired/self-signed cert on sub-pages.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Pages to scrape — onlinedst.gov.in hosts the live active calls with deadlines.
_CFP_URLS = [
    "https://onlinedst.gov.in/",
    "https://dst.gov.in/call-for-proposals",
    "https://dst.gov.in/archive-call-for-proposals",
]


class DstCfpScraper(BaseScraper):
    """Scraper for DST Call-for-Proposals HTML tables."""

    def __init__(self, *, min_delay: float = 1.5) -> None:
        super().__init__(min_delay=min_delay)

    def scrape(self) -> list[dict]:
        raw_data: list[dict] = []

        for url in _CFP_URLS:
            try:
                resp = self.get(url, verify=False)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Find all tables on the page — DST may have multiple.
                tables = soup.find_all("table")
                if not tables:
                    logger.warning("no tables found on %s", url)
                    continue

                for table in tables:
                    tbody = table.find("tbody") or table
                    for tr in tbody.find_all("tr"):
                        tds = tr.find_all("td")
                        if not tds or len(tds) < 3:
                            continue

                        cell_texts = [td.get_text(strip=True) for td in tds]
                        links = [
                            a["href"]
                            for td in tds
                            for a in td.find_all("a", href=True)
                        ]

                        raw_data.append({
                            "cells": cell_texts,
                            "links": links,
                            "page_url": url,
                        })

            except Exception:
                logger.exception("failed to scrape %s", url)

        logger.info("scraped %d raw CFP rows", len(raw_data))
        return raw_data

    def to_grants_rows(self, raw_data: list[dict]) -> list[dict]:
        rows: list[dict] = []

        for item in raw_data:
            cells = item["cells"]
            if len(cells) < 3:
                continue

            # Common DST table layouts:
            #   [Programme, Division, Status, Start, End, Link]
            #   [Programme, Division, Deadline, Link]
            title = cells[0].strip()
            if not title or title.lower() in ("programme", "scheme", "s.no", "sr no"):
                continue  # skip header rows

            division = cells[1].strip() if len(cells) > 1 else ""

            # Try to find a deadline in the later cells.
            deadline = None
            for cell in cells[2:]:
                parsed = parse_indian_date(cell)
                if parsed:
                    deadline = parsed
                    break  # take the last date (usually the end date)

            # Build source URL from first link, or fall back to page URL.
            links = item["links"]
            source_url = links[0] if links else item["page_url"]
            if source_url.startswith("/"):
                source_url = "https://dst.gov.in" + source_url

            funder_name = (
                f"DST — {division}"
                if division and division.lower() not in ("", "dst", "department")
                else "Department of Science and Technology"
            )

            rows.append({
                "title": title,
                "funder_name": funder_name,
                "funder_type": "govt",
                "description": (
                    f"Call for proposals under {division}. "
                    "See linked document for full guidelines and eligibility."
                ),
                "eligibility_json": {},
                "sectors": normalize_sectors(["science", "technology", "research"]),
                "geography": ["India"],
                "deadline": deadline.isoformat() if deadline else None,
                "source_url": source_url,
                "source": "dst_cfp_scraper",
            })

        return rows
