from pathlib import Path
from app.db import pool
from app.services.ingestion import ingest_document

def main():
    eoto = pool.fetch_one("select id from ngo_profiles where name like '%Each One Teach One%' limit 1")
    if not eoto:
        print("EOTO profile not found in database")
        return

    doc_path = Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / "eoto_vile_parle_proposal.txt"
    if not doc_path.exists():
        print(f"File not found: {doc_path}")
        return

    raw_bytes = doc_path.read_bytes()

    # Check if document already ingested
    existing_doc = pool.fetch_one(
        "select id from ngo_documents where ngo_id = %s and file_url = 'eoto_vile_parle_proposal.txt'",
        (eoto["id"],),
    )
    if existing_doc:
        doc_id = str(existing_doc["id"])
        print(f"Document already exists: {doc_id}")
    else:
        doc_row = pool.fetch_one(
            """
            insert into ngo_documents (ngo_id, doc_type, ingest_status, file_url)
            values (%s, 'program_report', 'pending', 'eoto_vile_parle_proposal.txt')
            returning id
            """,
            (eoto["id"],),
        )
        doc_id = str(doc_row["id"])
        print(f"Created document record: {doc_id}")

    res = ingest_document(doc_id, file_bytes=raw_bytes)
    print("Ingestion result:", res)

    # Count chunks
    chunks = pool.fetch_one("select count(*) as n from document_chunks where document_id = %s", (doc_id,))
    print(f"Total chunks in database: {chunks['n']}")

if __name__ == "__main__":
    main()
