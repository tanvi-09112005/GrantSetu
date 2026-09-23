"""Offline test of draft_proposal using real sample data — no live Supabase
connection required. A workaround for the DATABASE_URL credentials issue.

Uses a real sample NGO annual report + a real row from the seeded grants CSV,
but does retrieval in-memory (cosine similarity in Python) instead of hitting
pgvector, and monkeypatches only app.graph.nodes.draft.pool -- the node
function itself runs completely unmodified.

This still makes REAL Gemini API calls for embeddings and drafting. Only the
Postgres layer is bypassed.

Usage:
    python -m scripts.test_draft_offline
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

from app.graph.nodes.draft import draft_proposal
from app.graph.state import initial_state
from app.services.embeddings import embed_texts
from app.services.ingestion import _chunk_text, _extract_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]  # backend/scripts/.. -> backend -> repo root
SAMPLE_NGO_DIR = REPO_ROOT / "data" / "sample_ngos"
GRANTS_CSV = REPO_ROOT / "data" / "grants_seed.csv"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _load_all_profiles() -> list[dict]:
    profiles_path = SAMPLE_NGO_DIR / "sample_profiles.json"
    data = json.loads(profiles_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "profiles" in data:
        return data["profiles"]
    if isinstance(data, dict):
        return list(data.values())
    raise ValueError(f"Unrecognised sample_profiles.json structure: {type(data)}")


def _slug(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _match_profile_to_pdf(profiles: list[dict], pdfs: list[Path]) -> tuple[dict, Path]:
    """Pair a profile with the PDF that's actually about the same NGO.

    Sample profile order and PDF filename order aren't guaranteed to line up
    (confirmed: they don't, as-is) -- match by name/acronym instead of index.
    """
    for profile in profiles:
        name = profile.get("name", "")
        # acronym in parens, e.g. "Child Rights and You (CRY)" -> "cry"
        acronym = None
        if "(" in name and ")" in name:
            acronym = name[name.index("(") + 1 : name.index(")")].strip().lower()
        candidates = [acronym] if acronym else []
        candidates += [w for w in name.replace("(", " ").replace(")", " ").split() if len(w) > 3]

        for pdf in pdfs:
            pdf_slug = _slug(pdf.stem)
            for cand in candidates:
                if cand and _slug(cand) in pdf_slug:
                    return profile, pdf

    raise ValueError(
        "Could not match any sample profile to any sample PDF by name/acronym. "
        f"Profiles: {[p.get('name') for p in profiles]}  PDFs: {[p.name for p in pdfs]}"
    )


def _load_sample_pair() -> tuple[dict, str]:
    profiles = _load_all_profiles()
    pdfs = sorted(SAMPLE_NGO_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No sample PDFs found in {SAMPLE_NGO_DIR}")

    profile, pdf = _match_profile_to_pdf(profiles, pdfs)
    print(f"Matched profile '{profile.get('name')}' -> document '{pdf.name}'")
    text = _extract_pdf(pdf.read_bytes())
    return profile, text


def _load_sample_grant() -> dict:
    with GRANTS_CSV.open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    return {
        "id": "sample-grant",
        "title": row.get("title", ""),
        "funder_name": row.get("funder_name") or row.get("funder", ""),
        "description": row.get("description", ""),
    }


def main() -> int:
    ngo_profile, text = _load_sample_pair()

    chunks = _chunk_text(text)
    print(f"Extracted {len(chunks)} chunks from the sample document")
    if not chunks:
        print("No chunks extracted — the PDF may need OCR, or _chunk_text needs a look.")
        return 1

    chunk_texts = [c["text"] for c in chunks]
    print("Embedding chunks (real Gemini call)...")
    chunk_vectors = embed_texts(chunk_texts)

    grant = _load_sample_grant()
    print(f"Grant: {grant['title']} ({grant['funder_name']})\n")

    def fake_fetch_one(query, params=None):
        if "ngo_profiles" in query:
            return ngo_profile
        if "grants" in query:
            return grant
        return None

    def fake_fetch_all(query, params=None):
        if "document_chunks" not in query:
            return []
        query_vec = params[1] if params and len(params) > 1 else None
        if query_vec is None:
            return [{"chunk_text": t} for t in chunk_texts[:5]]
        scored = sorted(
            zip(chunk_texts, chunk_vectors),
            key=lambda cv: _cosine(cv[1], query_vec),
            reverse=True,
        )
        return [{"chunk_text": t} for t, _ in scored[:5]]

    with patch("app.graph.nodes.draft.pool") as mock_pool:
        mock_pool.fetch_one.side_effect = fake_fetch_one
        mock_pool.fetch_all.side_effect = fake_fetch_all

        state = initial_state(ngo_id="sample-ngo", selected_grant_id="sample-grant")
        state["ngo_profile"] = ngo_profile

        print("Drafting all sections (real Gemini calls — this takes a bit)...\n")
        result = draft_proposal(state)

    print(f"status: {result['status']}")
    if result["errors"]:
        print("Errors:")
        for e in result["errors"]:
            print(f"  - {e}")

    print("\n--- Draft sections ---\n")
    for section, text_out in result["draft_sections"].items():
        print(f"[{section}]")
        print(text_out[:500] if text_out else "(empty)")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())