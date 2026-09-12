"""data.gov.in REST API scraper.

Uses the official OGD (Open Government Data) REST API with a free API key.
Targets ministry grant disbursement datasets to extract unique scheme names
and their metadata. Since data.gov.in is mostly historical disbursements
(not active grant calls), this scraper focuses on building a baseline of
*which schemes exist and who funds them*.

    API URL format:
    https://api.data.gov.in/resource/{resource_id}?api-key={key}&format=json

License: Government Open Data License - India (GODL). Permits worldwide,
royalty-free, perpetual reuse with attribution.
"""

from __future__ import annotations

import logging

from app.core.config import settings

from .base import BaseScraper
from .utils import normalize_sectors

logger = logging.getLogger(__name__)

# Known resource IDs for ministry grant datasets.  Add new IDs as they are
# discovered on data.gov.in — each is a separate table of records.
DEFAULT_RESOURCE_IDS: list[str] = [
    # Placeholder — replace with real resource IDs after team registers for
    # an API key and searches the OGD catalogue.
    # e.g. "9115b836-0aae-4272-8bad-68cd7fcfe4df" (MoSJE disbursements)
]


class DataGovInScraper(BaseScraper):
    """Client for the data.gov.in REST API."""

    def __init__(
        self, resource_ids: list[str] | None = None, *, min_delay: float = 1.5
    ) -> None:
        super().__init__(min_delay=min_delay)
        self.api_key = settings.data_gov_in_api_key
        self.base_url = "https://api.data.gov.in/resource/"
        self.resource_ids = resource_ids or DEFAULT_RESOURCE_IDS

    def fetch_page(self, resource_id: str, offset: int = 0) -> dict:
        """Fetch one page of records from the API."""
        if not self.api_key:
            logger.warning("DATA_GOV_IN_API_KEY not set — skipping API call")
            return {}

        resp = self.get(
            f"{self.base_url}{resource_id}",
            params={
                "api-key": self.api_key,
                "format": "json",
                "offset": offset,
                "limit": 100,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def scrape(self) -> list[dict]:
        if not self.api_key:
            logger.warning(
                "DATA_GOV_IN_API_KEY not configured. "
                "Register at https://data.gov.in and set the env var."
            )
            return []

        if not self.resource_ids:
            logger.warning(
                "No resource IDs configured. Add IDs to DEFAULT_RESOURCE_IDS "
                "or pass them to the constructor."
            )
            return []

        all_records: list[dict] = []
        for rid in self.resource_ids:
            logger.info("fetching resource %s", rid)
            offset = 0
            while True:
                data = self.fetch_page(rid, offset)
                records = data.get("records", [])
                if not records:
                    break
                all_records.extend(records)
                total = data.get("total", 0)
                offset += 100
                if offset >= total:
                    break
            logger.info("resource %s: %d total records", rid, len(all_records))

        return all_records

    def to_grants_rows(self, raw_data: list[dict]) -> list[dict]:
        rows: list[dict] = []
        seen: set[tuple[str, str]] = set()

        for record in raw_data:
            funder_name = (
                record.get("ministry_department")
                or record.get("ministry")
                or record.get("department")
                or "Government of India"
            )
            title = (
                record.get("scheme_name")
                or record.get("title")
                or record.get("scheme")
                or ""
            ).strip()
            if not title:
                continue

            key = (funder_name, title)
            if key in seen:
                continue
            seen.add(key)

            raw_sector = record.get("sector", record.get("field_of_work", ""))
            sectors = normalize_sectors([raw_sector]) if raw_sector else []

            raw_state = record.get("state", record.get("state_ut", ""))
            geography = [raw_state] if raw_state and raw_state != "All India" else ["India"]

            rows.append({
                "title": title,
                "funder_name": funder_name,
                "funder_type": "govt",
                "description": record.get("description", record.get("purpose", "")),
                "eligibility_json": {},
                "sectors": sectors,
                "geography": geography,
                "deadline": None,
                "source_url": "https://data.gov.in",
                "source": "data_gov_in_scraper",
            })

        return rows
