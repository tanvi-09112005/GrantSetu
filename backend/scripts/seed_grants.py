"""Load the hand-curated grants CSV into the grants table, with embeddings.

This is the seed/fallback layer that sits *underneath* the scheduled scraper
(Addendum section 2) -- not instead of it. Re-running is safe: rows are upserted
on (funder_name, title).

    python -m scripts.seed_grants                    # embed and load
    python -m scripts.seed_grants --no-embed         # load without embeddings
    python -m scripts.seed_grants --file ../data/grants_seed.csv

Every seed row carries verified=no until a human has checked it against its
source URL. The loader reports the unverified count loudly, because an
eligibility rule built on a guessed 12A requirement is worse than no rule.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.db import pool

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "grants_seed.csv"


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split("|") if v.strip()]


def _bool(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "1", "y"}


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    parsed = []
    for row in rows:
        eligibility = {
            "requires_12a": _bool(row.get("requires_12a", "")),
            "requires_80g": _bool(row.get("requires_80g", "")),
            "requires_fcra": _bool(row.get("requires_fcra", "")),
            "min_years_registered": int(row["min_years_registered"])
            if row.get("min_years_registered", "").strip()
            else None,
            "sectors": _split(row.get("sectors", "")),
            "geography": _split(row.get("geography", "")),
        }
        parsed.append(
            {
                "title": row["title"].strip(),
                "funder_name": row["funder_name"].strip(),
                "funder_type": row["funder_type"].strip() or None,
                "description": row.get("description", "").strip(),
                "eligibility_json": json.dumps(eligibility),
                "sectors": _split(row.get("sectors", "")),
                "geography": _split(row.get("geography", "")),
                "deadline": row.get("deadline", "").strip() or None,
                "source_url": row.get("source_url", "").strip() or None,
                "verified": _bool(row.get("verified", "")),
            }
        )
    return parsed


def embedding_text(row: dict) -> str:
    """What gets embedded. Must match the query side in the discovery node."""
    sectors = ", ".join(row["sectors"])
    return (
        f"{row['title']}. {row['funder_name']}. "
        f"{row['description']} Sectors: {sectors}."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--no-embed", action="store_true", help="skip embedding generation")
    args = ap.parse_args()

    rows = load_rows(args.file)
    print(f"parsed {len(rows)} rows from {args.file}")

    vectors: list[list[float] | None] = [None] * len(rows)
    if not args.no_embed:
        from app.services.embeddings import embed_texts

        print("embedding...")
        vectors = embed_texts([embedding_text(r) for r in rows])  # type: ignore[assignment]

    for row, vector in zip(rows, vectors, strict=True):
        pool.execute(
            """
            insert into grants
                (title, funder_name, funder_type, description, eligibility_json,
                 sectors, geography, deadline, source_url, source, embedding)
            values (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, 'seed_csv', %s)
            on conflict (funder_name, title) do update set
                funder_type      = excluded.funder_type,
                source_url       = excluded.source_url,
                description      = excluded.description,
                eligibility_json = excluded.eligibility_json,
                sectors          = excluded.sectors,
                geography        = excluded.geography,
                deadline         = excluded.deadline,
                embedding        = coalesce(excluded.embedding, grants.embedding),
                last_seen_at     = now(),
                is_active        = true
            """,
            (
                row["title"],
                row["funder_name"],
                row["funder_type"],
                row["description"],
                row["eligibility_json"],
                row["sectors"],
                row["geography"],
                row["deadline"],
                row["source_url"],
                vector,
            ),
        )

    total = pool.fetch_one("select count(*) as n from grants")
    unverified = sum(1 for r in rows if not r["verified"])
    print(f"grants table now holds {total['n']} rows")
    if unverified:
        print(
            f"\n{unverified} of {len(rows)} seed rows are marked verified=no.\n"
            "Open each source_url, confirm the eligibility flags and the current\n"
            "application window, then flip the column. Eligibility rules built on\n"
            "unverified flags will produce confidently wrong verdicts."
        )


if __name__ == "__main__":
    main()
