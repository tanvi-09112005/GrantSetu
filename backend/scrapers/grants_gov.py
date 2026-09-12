"""International and Foreign Grants scraper for FCRA-registered Indian NGOs.

Fetches real international/foreign grants awarded to Indian entities by foreign
governments and foundations using the open, keyless USASpending/Grants API.

Foreign funding legally requires FCRA registration under Indian law.
This scraper tags each result with:
    funder_type = 'international'
    eligibility_json = {'requires_fcra': True, 'requires_12a': True, 'min_years_registered': 3}
    geography = ['India', 'International']
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseScraper
from .utils import normalize_sectors, parse_indian_date

logger = logging.getLogger(__name__)

# Keyless public REST endpoint for foreign awards to Indian entities
_INTERNATIONAL_GRANTS_API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


class GrantsGovScraper(BaseScraper):
    """Scraper for foreign and international grants to Indian non-profits."""

    def __init__(self, *, limit: int = 50, min_delay: float = 1.5) -> None:
        super().__init__(min_delay=min_delay)
        self.limit = limit

    def scrape(self) -> list[dict]:
        """Query open international grants API for Indian recipient organizations."""
        payload = {
            "fields": [
                "Award ID",
                "Recipient Name",
                "Awarding Agency",
                "Description",
                "Award Amount",
                "Start Date",
                "End Date",
            ],
            "filters": {
                "award_type_codes": ["02", "03", "04", "05"],  # Grants
                "recipient_locations": [{"country": "IND"}],   # Indian NGOs & Institutions
            },
            "limit": min(self.limit, 100),
            "page": 1,
        }

        try:
            self._throttle()
            logger.info("fetching international grants for Indian organizations...")
            resp = self.session.post(
                _INTERNATIONAL_GRANTS_API,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                logger.info("received %d international grants", len(results))
                return results
            else:
                logger.warning("international grants API error %d: %s", resp.status_code, resp.text[:200])
        except Exception:
            logger.exception("international grants scraper request failed")

        return []

    def to_grants_rows(self, raw_data: list[dict]) -> list[dict]:
        rows: list[dict] = []
        seen: set[tuple[str, str]] = set()

        for item in raw_data:
            agency = (item.get("Awarding Agency") or "International Funding Agency").strip()
            desc = (item.get("Description") or "").strip()
            recipient = (item.get("Recipient Name") or "").strip()
            award_id = item.get("Award ID") or ""

            # Use meaningful title based on description or recipient project
            title = desc.split(".")[0].strip() if desc else f"International Grant to {recipient}"
            if len(title) > 150:
                title = title[:147] + "..."
            title = title.title()

            if not title:
                continue

            key = (agency, title)
            if key in seen:
                continue
            seen.add(key)

            # Deadline / End Date
            deadline = None
            end_date_str = item.get("End Date")
            if end_date_str:
                deadline = parse_indian_date(str(end_date_str))

            sectors = normalize_sectors([title, desc])
            if not sectors:
                sectors = ["health", "technology", "social_welfare"]

            rows.append({
                "title": title,
                "funder_name": agency,
                "funder_type": "international",
                "description": desc[:2000] if desc else f"International grant awarded by {agency}.",
                "eligibility_json": {
                    "requires_fcra": True,
                    "requires_12a": True,
                    "requires_80g": False,
                    "min_years_registered": 3,
                },
                "sectors": sectors,
                "geography": ["India", "International"],
                "deadline": deadline.isoformat() if deadline else None,
                "source_url": f"https://www.usaspending.gov/award/{award_id}" if award_id else "https://www.grants.gov",
                "source": "grants_gov_scraper",
            })

        return rows
