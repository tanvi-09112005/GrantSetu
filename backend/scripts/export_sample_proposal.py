"""Export a proposal to PDF, using real discovery + real draft_proposal output.

Runs discover_grants (real hybrid RAG matching) to pick a relevant grant for
the NGO -- not an arbitrary DB row -- then drafts and exports to PDF, saved
directly to your OS Downloads folder.

Usage:
    python -m scripts.export_sample_proposal
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import settings
from app.db import pool
from app.graph.nodes.discover import discover_grants
from app.graph.nodes.draft import draft_proposal
from app.graph.state import initial_state
from app.services.export import generate_proposal_pdf


def _downloads_folder() -> Path:
    home = Path.home()
    downloads = home / "Downloads"
    return downloads if downloads.exists() else home


def main() -> int:
    missing = settings.missing_required()
    if missing:
        print(f"Missing required settings: {missing}")
        return 1

    ngo_row = pool.fetch_one("select * from ngo_profiles order by created_at limit 1")
    if not ngo_row:
        print("No NGO profiles found. Run scripts.download_sample_ngos first.")
        return 1
    ngo_profile = dict(ngo_row)
    print(f"NGO: {ngo_profile.get('name')}\n")

    state = initial_state(ngo_id=str(ngo_profile["id"]))
    state["ngo_profile"] = ngo_profile

    print("Running discover_grants (real hybrid RAG matching)...")
    discovery = discover_grants(state)
    candidates = discovery.get("candidate_grants", [])
    if not candidates:
        print("No candidate grants found. Run scripts.seed_grants and scripts.backfill_grant_embeddings first.")
        return 1

    print(f"Top {min(3, len(candidates))} matches:")
    for c in candidates[:3]:
        print(f"  - {c['title']} ({c['funder_name']}) — score {c.get('score', 0):.2f} — {c.get('match_reason', '')}")

    selected_grant_id = discovery.get("selected_grant_id") or candidates[0]["grant_id"]
    chosen = next((c for c in candidates if c["grant_id"] == selected_grant_id), candidates[0])
    print(f"\nSelected: {chosen['title']} ({chosen['funder_name']})\n")

    state.update(discovery)
    state["selected_grant_id"] = selected_grant_id

    print("Running draft_proposal (real Gemini calls)...")
    result = draft_proposal(state)

    if result["errors"]:
        print(f"{len(result['errors'])} issue(s) — exporting whatever drafted successfully:")
        for e in result["errors"]:
            print(f"  - {e}")

    non_empty = {k: v for k, v in result["draft_sections"].items() if v}
    budget_table = result.get("budget_table") or {}
    if not non_empty and not budget_table.get("line_items"):
        print("Nothing drafted successfully — nothing to export.")
        return 1

    grant_full = pool.fetch_one("select * from grants where id = %s", (selected_grant_id,))

    downloads = _downloads_folder()
    ngo_slug = "".join(c if c.isalnum() else "_" for c in ngo_profile.get("name", "ngo"))
    output_path = downloads / f"GrantSetu_Proposal_{ngo_slug}.pdf"

    generate_proposal_pdf(
        ngo_profile, dict(grant_full), non_empty, output_path,
        budget_table=budget_table,
    )
    print(f"\nSaved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())