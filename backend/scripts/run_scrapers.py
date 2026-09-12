"""Run GrantSetu scrapers.

    python -m scripts.run_scrapers                          # all scrapers
    python -m scripts.run_scrapers --source dst_cfp         # just DST
    python -m scripts.run_scrapers --source myscheme --dry-run
    python -m scripts.run_scrapers --source all --no-embed  # fast, no GPU
"""

from __future__ import annotations

import argparse
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(name)s  %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run GrantSetu grant scrapers")
    ap.add_argument(
        "--source",
        choices=["data_gov_in", "myscheme", "dst_cfp", "grants_gov", "all"],
        default="all",
        help="Which scraper to run (default: all)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print normalised rows as JSON; do not write to the database",
    )
    ap.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip embedding generation (faster for testing)",
    )
    args = ap.parse_args()

    # Lazy imports so the embedding model isn't loaded when running --dry-run.
    scrapers = []
    if args.source in ("all", "data_gov_in"):
        from scrapers.data_gov_in import DataGovInScraper

        scrapers.append(DataGovInScraper())
    if args.source in ("all", "myscheme"):
        from scrapers.myscheme_gov_in import MySchemeScraper

        scrapers.append(MySchemeScraper())
    if args.source in ("all", "dst_cfp"):
        from scrapers.dst_cfp import DstCfpScraper

        scrapers.append(DstCfpScraper())
    if args.source in ("all", "grants_gov"):
        from scrapers.grants_gov import GrantsGovScraper

        scrapers.append(GrantsGovScraper())

    for scraper in scrapers:
        name = scraper.__class__.__name__
        logger.info("--- %s ---", name)
        try:
            rows, stats = scraper.run(
                dry_run=args.dry_run, embed=not args.no_embed
            )

            if args.dry_run:
                print(json.dumps(rows, indent=2, default=str))
            else:
                logger.info("%s  %s", name, stats)

        except Exception:
            logger.exception("scraper %s failed", name)

    # Summary (only meaningful when not dry-running).
    if not args.dry_run:
        from app.db import pool

        total = pool.fetch_one("select count(*) as n from grants")
        print(f"\ngrants table now holds {total['n']} rows")


if __name__ == "__main__":
    main()
