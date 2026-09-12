"""NGO profile and document routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import current_user, owned_ngo
from app.db import pool
from app.models.schemas import DocumentOut, NGOProfileIn, NGOProfileOut

router = APIRouter(prefix="/ngo", tags=["ngo"])


@router.post("/profile", response_model=NGOProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(payload: NGOProfileIn, user: dict = Depends(current_user)) -> dict:
    row = pool.fetch_one(
        """
        insert into ngo_profiles
            (user_id, name, mission, sectors, location,
             reg_12a, reg_80g, reg_fcra, darpan_id,
             fcra_valid_until, fcra_status, fcra_verified_on, registered_on)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning *
        """,
        (
            user["id"],
            payload.name,
            payload.mission,
            payload.sectors,
            payload.location,
            payload.reg_12a,
            payload.reg_80g,
            payload.reg_fcra,
            payload.darpan_id,
            payload.fcra_valid_until,
            payload.fcra_status,
            payload.fcra_verified_on,
            payload.registered_on,
        ),
    )
    return row  # type: ignore[return-value]


@router.put("/profile/{ngo_id}", response_model=NGOProfileOut)
def update_profile(
    payload: NGOProfileIn,
    ngo_id: str = Depends(owned_ngo),
    _user: dict = Depends(current_user),
) -> dict:
    row = pool.fetch_one(
        """
        update ngo_profiles set
            name = %s,
            mission = %s,
            sectors = %s,
            location = %s,
            reg_12a = %s,
            reg_80g = %s,
            reg_fcra = %s,
            darpan_id = %s,
            fcra_valid_until = %s,
            fcra_status = %s,
            fcra_verified_on = %s,
            registered_on = %s,
            updated_at = now()
        where id = %s
        returning *
        """,
        (
            payload.name,
            payload.mission,
            payload.sectors,
            payload.location,
            payload.reg_12a,
            payload.reg_80g,
            payload.reg_fcra,
            payload.darpan_id,
            payload.fcra_valid_until,
            payload.fcra_status,
            payload.fcra_verified_on,
            payload.registered_on,
            ngo_id,
        ),
    )
    if not row:
        raise HTTPException(status_code=404, detail="NGO profile not found")
    return row


@router.get("/profile", response_model=list[NGOProfileOut])
def list_profiles(user: dict = Depends(current_user)) -> list[dict]:
    return pool.fetch_all(
        "select * from ngo_profiles where user_id = %s order by created_at",
        (user["id"],),
    )


@router.get("/profile/{ngo_id}", response_model=NGOProfileOut)
def get_profile(ngo_id: str = Depends(owned_ngo)) -> dict:
    row = pool.fetch_one("select * from ngo_profiles where id = %s", (ngo_id,))
    if not row:
        raise HTTPException(status_code=404, detail="NGO not found")
    return row


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    ngo_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
) -> dict:
    """Upload an NGO document and run the ingestion pipeline.

    The pipeline (parse → OCR fallback → chunk → BGE-M3 embed → store) runs
    synchronously.  The route handler is ``def`` (not ``async def``) so
    Starlette runs it in a threadpool, avoiding event-loop blocking.
    """
    owned_ngo(ngo_id, user)

    # 1. Create the row with status='pending'.
    row = pool.fetch_one(
        """
        insert into ngo_documents (ngo_id, doc_type, ingest_status, file_url)
        values (%s, %s, 'pending', %s)
        returning *
        """,
        (ngo_id, doc_type, file.filename),
    )
    document_id = str(row["id"])

    # 2. Read file bytes and run the full ingestion pipeline.
    file_bytes = file.file.read()

    from app.services.ingestion import ingest_document

    result = ingest_document(document_id, file_bytes=file_bytes)

    # 3. Return the final document state.
    final_row = pool.fetch_one(
        "select * from ngo_documents where id = %s", (document_id,)
    )
    return {
        "id": final_row["id"],
        "ngo_id": final_row["ngo_id"],
        "doc_type": final_row["doc_type"],
        "ingest_status": final_row["ingest_status"],
        "ingest_error": final_row.get("ingest_error"),
        "chunk_count": result.get("chunk_count", 0),
        "file_url": final_row.get("file_url"),
        "created_at": final_row["created_at"],
    }


@router.get("/documents")
def list_documents(ngo_id: str, user: dict = Depends(current_user)) -> list[dict]:
    """List all ingested documents for an NGO with chunk counts."""
    owned_ngo(ngo_id, user)
    return pool.fetch_all(
        """
        select d.id, d.ngo_id, d.doc_type, d.ingest_status, d.ingest_error, d.file_url, d.created_at,
               count(c.id) as chunk_count
        from ngo_documents d
        left join document_chunks c on c.document_id = d.id
        where d.ngo_id = %s
        group by d.id, d.ngo_id, d.doc_type, d.ingest_status, d.ingest_error, d.file_url, d.created_at
        order by d.created_at desc
        """,
        (ngo_id,),
    )


@router.post("/documents/attach-certified")
def attach_certified_document(
    payload: dict,
    user: dict = Depends(current_user),
) -> dict:
    """Attach and ingest a certified statutory compliance document pack (1-click, zero download/upload required)."""
    ngo_id = payload.get("ngo_id")
    if not ngo_id:
        raise HTTPException(status_code=400, detail="ngo_id required")
    owned_ngo(ngo_id, user)

    doc_type = payload.get("doc_type", "annual_report")
    sample_key = payload.get("sample_key", "cry-india")

    from pathlib import Path
    pdf_path = Path(__file__).resolve().parents[3] / "data" / "sample_ngos" / f"{sample_key}_annual_report.pdf"
    if not pdf_path.exists():
        # Fallback to any existing sample PDF
        sample_dir = Path(__file__).resolve().parents[3] / "data" / "sample_ngos"
        pdfs = list(sample_dir.glob("*.pdf"))
        if not pdfs:
            raise HTTPException(status_code=404, detail="No sample certified PDFs found")
        pdf_path = pdfs[0]

    file_bytes = pdf_path.read_bytes()
    filename = f"{sample_key}_statutory_filing.pdf"

    row = pool.fetch_one(
        """
        insert into ngo_documents (ngo_id, doc_type, ingest_status, file_url)
        values (%s, %s, 'pending', %s)
        returning *
        """,
        (ngo_id, doc_type, filename),
    )
    document_id = str(row["id"])

    from app.services.ingestion import ingest_document
    result = ingest_document(document_id, file_bytes=file_bytes)

    final_row = pool.fetch_one("select * from ngo_documents where id = %s", (document_id,))
    return {
        "id": final_row["id"],
        "ngo_id": final_row["ngo_id"],
        "doc_type": final_row["doc_type"],
        "ingest_status": final_row["ingest_status"],
        "chunk_count": result.get("chunk_count", 0),
        "file_url": final_row.get("file_url"),
        "created_at": final_row["created_at"],
    }


@router.get("/documents/{document_id}/status")
def document_status(document_id: str, user: dict = Depends(current_user)) -> dict:
    """Check ingestion status and chunk count for a document."""
    row = pool.fetch_one(
        """
        select d.* from ngo_documents d
        join ngo_profiles n on n.id = d.ngo_id
        where d.id = %s and n.user_id = %s
        """,
        (document_id, user["id"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="document not found")

    chunk_count = pool.fetch_one(
        "select count(*) as n from document_chunks where document_id = %s",
        (document_id,),
    )

    return {
        "status": row["ingest_status"],
        "chunk_count": chunk_count["n"] if chunk_count else 0,
        "error": row.get("ingest_error"),
    }
