"""Ingest one real sample PDF for an existing ngo_profiles row, using the
real ingestion pipeline (app.services.ingestion.ingest_document) end to end.

This WRITES to the DB: inserts one row into ngo_documents, then lets
ingest_document populate raw_text, ingest_status, and document_chunks for it.

Matches the sample PDF to the NGO by name/acronym (same logic as
test_draft_offline.py) rather than assuming file order.

Usage:
    python -m scripts.ingest_sample_document              # first NGO found
    python -m scripts.ingest_sample_document --ngo-name CRY
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from app.db import pool
from app.services.ingestion import ingest_document

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_NGO_DIR = REPO_ROOT / "data" / "sample_ngos"


def _slug(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _find_matching_pdf(ngo_name: str) -> Path:
    pdfs = sorted(SAMPLE_NGO_DIR.glob("*.pdf"))
    acronym = None
    if "(" in ngo_name and ")" in ngo_name:
        acronym = ngo_name[ngo_name.index("(") + 1 : ngo_name.index(")")].strip()
    candidates = [acronym] if acronym else []
    candidates += [w for w in ngo_name.replace("(", " ").replace(")", " ").split() if len(w) > 3]

    for pdf in pdfs:
        pdf_slug = _slug(pdf.stem)
        for cand in candidates:
            if cand and _slug(cand) in pdf_slug:
                return pdf
    raise ValueError(f"No sample PDF matched NGO name '{ngo_name}'. Available: {[p.name for p in pdfs]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ngo-name", default=None, help="Substring to match against ngo_profiles.name")
    args = parser.parse_args()

    if args.ngo_name:
        ngo = pool.fetch_one(
            "select id, name from ngo_profiles where name ilike %s limit 1",
            (f"%{args.ngo_name}%",),
        )
    else:
        ngo = pool.fetch_one("select id, name from ngo_profiles order by created_at limit 1")

    if not ngo:
        print("No matching NGO profile found.")
        return 1

    ngo_id = str(ngo["id"])
    print(f"NGO: {ngo['name']} ({ngo_id})")

    pdf_path = _find_matching_pdf(ngo["name"])
    print(f"Matched document: {pdf_path.name}")

    document_id = str(uuid.uuid4())
    pool.execute(
        """
        insert into ngo_documents (id, ngo_id, doc_type, file_url, ingest_status)
        values (%s, %s, %s, %s, %s)
        """,
        (document_id, ngo_id, "annual_report", pdf_path.name, "pending"),
    )
    print(f"Created ngo_documents row: {document_id}")

    print("Running ingest_document (parse -> chunk -> embed -> store)...")
    result = ingest_document(document_id, file_bytes=pdf_path.read_bytes())
    print(f"Result: {result}")

    return 0 if result.get("status") == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())