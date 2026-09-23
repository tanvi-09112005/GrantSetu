"""Phase 3 verification: run draft_proposal against real seeded data.

Does NOT insert any data itself -- it only SELECTs. If the prerequisites
below aren't there yet, it tells you exactly which existing script to run
first, rather than guessing at insert schemas this script hasn't seen.

Prerequisites (run once, in order, if not already done):
    python -m scripts.seed_grants          # populates `grants`
    python -m scripts.download_sample_ngos # populates `ngo_profiles` +
                                            # ingests at least one document
                                            # into `ngo_documents` / `document_chunks`

Usage:
    python -m scripts.verify_phase3_draft
"""

from __future__ import annotations

import sys
import textwrap

from app.core.config import settings
from app.db import pool
from app.graph.nodes.draft import draft_proposal
from app.graph.state import initial_state


def _wrap(text: str, width: int = 100, max_chars: int = 400) -> str:
    shown = text[:max_chars] + ("..." if len(text) > max_chars else "")
    return textwrap.indent(textwrap.fill(shown, width=width), "    ")


def main() -> int:
    missing = settings.missing_required()
    if missing:
        print(f"Missing required settings: {missing}. Check your .env before continuing.")
        return 1

    ngo_row = pool.fetch_one(
        "select id, name from ngo_profiles order by created_at limit 1"
    )
    if not ngo_row:
        print(
            "No rows in ngo_profiles.\n"
            "Run:  python -m scripts.download_sample_ngos\n"
            "...then re-run this script."
        )
        return 1

    ngo_id = str(ngo_row["id"])
    print(f"Using NGO: {ngo_row['name']} ({ngo_id})")

    doc_row = pool.fetch_one(
        "select id from ngo_documents where ngo_id = %s and ingest_status = 'ready' limit 1",
        (ngo_id,),
    )
    if not doc_row:
        print(
            f"NGO {ngo_row['name']} has no ready (ingested) document.\n"
            "Either run:  python -m scripts.download_sample_ngos\n"
            "or check that ingestion actually completed for this NGO "
            "(query ngo_documents.ingest_status / ingest_error for details)."
        )
        return 1

    chunk_count = pool.fetch_one(
        "select count(*) as n from document_chunks where ngo_id = %s", (ngo_id,)
    )
    print(f"Found {chunk_count['n']} document chunks for this NGO — drafting will be grounded.")

    grant_row = pool.fetch_one(
        "select id, title, funder_name from grants where is_active limit 1"
    )
    if not grant_row:
        print(
            "No rows in grants.\n"
            "Run:  python -m scripts.seed_grants\n"
            "...then re-run this script."
        )
        return 1

    grant_id = str(grant_row["id"])
    print(f"Using grant: {grant_row['title']} ({grant_row['funder_name']}) [{grant_id}]\n")

    state = initial_state(ngo_id=ngo_id, selected_grant_id=grant_id)
    # Leave ngo_profile empty deliberately -- exercises the DB-fallback path
    # in draft.py's _get_ngo_profile, same code path the real graph will use.

    print("Running draft_proposal ... (this makes real Gemini calls, one per section)\n")
    result = draft_proposal(state)

    print(f"status: {result['status']}")
    if result["errors"]:
        print(f"\n{len(result['errors'])} section(s) failed:")
        for err in result["errors"]:
            print(f"  - {err}")

    print("\n--- Draft sections ---\n")
    for section, text in result["draft_sections"].items():
        print(f"[{section}]")
        print(_wrap(text) if text else "    (empty — see errors above)")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())