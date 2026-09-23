"""Quick inventory of what's actually in the DB right now.

Doesn't insert or modify anything -- pure SELECT counts/summaries, so it's
safe to run anytime. Use this before trusting any "real data" test run.

Usage:
    python -m scripts.check_db_state
"""

from __future__ import annotations

from app.core.config import settings
from app.db import pool


def main() -> int:
    missing = settings.missing_required()
    if missing:
        print(f"Missing required settings: {missing}")
        return 1

    print("=== ngo_profiles ===")
    rows = pool.fetch_all("select id, name from ngo_profiles order by created_at")
    print(f"{len(rows)} row(s)")
    for r in rows:
        print(f"  - {r['name']}  ({r['id']})")

    print("\n=== ngo_documents (by ingest_status) ===")
    rows = pool.fetch_all(
        """
        select d.ingest_status, count(*) as n
        from ngo_documents d
        group by d.ingest_status
        order by d.ingest_status
        """
    )
    if not rows:
        print("0 rows — no documents uploaded/ingested at all yet")
    for r in rows:
        print(f"  {r['ingest_status']}: {r['n']}")

    print("\n=== ngo_documents detail (per NGO) ===")
    rows = pool.fetch_all(
        """
        select p.name as ngo_name, d.id as doc_id, d.doc_type, d.ingest_status, d.ingest_error
        from ngo_documents d
        join ngo_profiles p on p.id = d.ngo_id
        order by p.name
        """
    )
    for r in rows:
        err = f"  ERROR: {r['ingest_error']}" if r.get("ingest_error") else ""
        print(f"  {r['ngo_name']} | {r['doc_type']} | {r['ingest_status']}{err}")

    print("\n=== document_chunks (by NGO) ===")
    rows = pool.fetch_all(
        """
        select p.name as ngo_name, count(c.id) as n_chunks
        from ngo_profiles p
        left join document_chunks c on c.ngo_id = p.id
        group by p.name
        order by p.name
        """
    )
    for r in rows:
        flag = "" if r["n_chunks"] > 0 else "  <- NO CHUNKS, discovery/drafting will have no grounding for this NGO"
        print(f"  {r['ngo_name']}: {r['n_chunks']} chunks{flag}")

    print("\n=== grants ===")
    total = pool.fetch_one("select count(*) as n from grants")
    active = pool.fetch_one("select count(*) as n from grants where is_active")
    embedded = pool.fetch_one("select count(*) as n from grants where embedding is not null")
    print(f"  total: {total['n']}, active: {active['n']}, with embeddings: {embedded['n']}")
    if embedded["n"] < active["n"]:
        print(
            f"  <- {active['n'] - embedded['n']} active grant(s) have no embedding — "
            "run scripts.backfill_grant_embeddings"
        )

    print("\n=== grants by funder_type (sanity check on seed data) ===")
    rows = pool.fetch_all(
        "select funder_type, count(*) as n from grants group by funder_type order by funder_type"
    )
    for r in rows:
        print(f"  {r['funder_type']}: {r['n']}")

    return 0


if __name__ == "__main__":
    exit(main())