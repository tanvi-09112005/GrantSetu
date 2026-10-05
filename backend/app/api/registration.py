"""NGO registration (Task 1): one multipart call that stores the whole wizard.

The React wizard first creates the Supabase Auth user (email + password), then
calls ``POST /ngo/register`` with the session JWT, the form fields and the
certificate PDFs. Validation is repeated here on purpose: the browser check is
for convenience, this one is the authoritative one.

Verification (fixed):
  * the Darpan certificate is READ and checked BEFORE anything is written -
    a wrong / blank / mismatching certificate is rejected with a 422 and no
    profile or document rows are created;
  * scanned or graphic certificates are read with Gemini Vision;
  * if anything fails after the profile row exists, it is rolled back;
  * ``POST /ngo/{ngo_id}/verify`` lets an unverified NGO re-upload its proof.
"""

from __future__ import annotations

import logging
import re
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import current_user
from app.db import pool
from app.services.darpan_verify import verify_darpan_certificate
from app.services.verification_gate import VERIFIED_STATUSES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ngo", tags=["ngo-registration"])

# NGO Darpan unique ID: 2-letter state code / 4-digit year / 7 digits.
DARPAN_RE = re.compile(r"^[A-Z]{2}/\d{4}/\d{7}$")
PHONE_RE = re.compile(r"^(?:\+91[\s-]?)?[6-9]\d{9}$")
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB per file


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _read_pdf(upload: UploadFile, label: str) -> bytes:
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=422, detail=f"{label}: file is empty")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=422, detail=f"{label}: file is larger than 10 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail=f"{label}: must be a real PDF file")
    return data


def _store_document(ngo_id: str, doc_type: str, filename: str, data: bytes) -> dict:
    """Insert an ngo_documents row and run the existing ingestion pipeline."""
    row = pool.fetch_one(
        """
        insert into ngo_documents (ngo_id, doc_type, ingest_status, file_url)
        values (%s, %s, 'pending', %s) returning id
        """,
        (ngo_id, doc_type, filename),
    )
    document_id = str(row["id"])
    try:
        from app.services.ingestion import ingest_document

        ingest_document(document_id, file_bytes=data)
    except Exception:  # noqa: BLE001 - a failed ingest must not undo registration
        logger.exception("ingestion failed for %s", document_id)
    return pool.fetch_one(
        "select id, raw_text, ingest_status from ngo_documents where id = %s", (document_id,)
    )


def _rollback_ngo(ngo_id: str) -> None:
    """Best-effort removal of a half-created NGO (children first)."""
    for sql in (
        "delete from document_chunks where ngo_id = %s",
        "delete from ngo_documents where ngo_id = %s",
        "delete from ngo_assets where ngo_id = %s",
        "delete from ngo_profiles where id = %s",
    ):
        try:
            pool.execute(sql, (ngo_id,))
        except Exception:  # noqa: BLE001
            logger.exception("rollback step failed: %s", sql)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_ngo(
    # Step 1 - admin & identity (email/password live in Supabase Auth, not here)
    admin_name: str = Form(...),
    admin_designation: str = Form(...),
    admin_phone: str = Form(...),
    # Step 2 - statutory details
    ngo_name: str = Form(...),
    incorporation_year: int = Form(...),
    state: str = Form(...),
    district: str = Form(...),
    darpan_id: str = Form(...),
    has_12a: bool = Form(False),
    has_80g: bool = Form(False),
    has_fcra: bool = Form(False),
    # Step 3 - proof
    darpan_certificate: UploadFile = File(...),
    cert_12a: UploadFile | None = File(None),
    cert_80g: UploadFile | None = File(None),
    user: dict = Depends(current_user),
) -> dict:
    # ---- validate -----------------------------------------------------------
    darpan = _clean(darpan_id).upper()
    if not DARPAN_RE.match(darpan):
        raise HTTPException(422, "Darpan ID must look like MH/2021/0123456")
    if not PHONE_RE.match(_clean(admin_phone).replace(" ", "")):
        raise HTTPException(422, "Enter a valid 10-digit Indian mobile number")
    this_year = date.today().year
    if not (1800 <= incorporation_year <= this_year):
        raise HTTPException(422, f"Year of incorporation must be between 1800 and {this_year}")
    if not _clean(ngo_name) or not _clean(state) or not _clean(district):
        raise HTTPException(422, "NGO name, state and district are required")

    if pool.fetch_one("select 1 from ngo_profiles where user_id = %s", (user["id"],)):
        raise HTTPException(409, "This account already has an NGO registered")
    if pool.fetch_one(
        "select 1 from ngo_profiles where upper(darpan_id) = %s", (darpan,)
    ):
        raise HTTPException(409, "This Darpan ID is already registered on GrantSetu")

    darpan_bytes = _read_pdf(darpan_certificate, "Darpan certificate")
    bytes_12a = _read_pdf(cert_12a, "12A certificate") if cert_12a and cert_12a.filename else None
    bytes_80g = _read_pdf(cert_80g, "80G certificate") if cert_80g and cert_80g.filename else None

    # ---- verify BEFORE writing anything -------------------------------------
    check = verify_darpan_certificate(darpan_bytes, darpan, _clean(ngo_name))
    if not check.ok:
        logger.info("registration rejected for %s: %s", user.get("email"), check.reason)
        raise HTTPException(status_code=422, detail=check.message)

    # ---- create the profile -------------------------------------------------
    # The existing eligibility engine reads reg_12a / reg_80g / reg_fcra (a
    # number when held, NULL when not) and fcra_status, so we fill those too.
    ngo = pool.fetch_one(
        """
        insert into ngo_profiles
            (user_id, name, location, registered_on, darpan_id,
             reg_12a, reg_80g, reg_fcra, fcra_status,
             admin_name, admin_designation, admin_phone, admin_email,
             state, district, incorporation_year,
             has_12a, has_80g, has_fcra, verification_status)
        values (%s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, 'pending_review')
        returning id
        """,
        (
            user["id"], _clean(ngo_name), f"{_clean(district)}, {_clean(state)}",
            date(incorporation_year, 1, 1), darpan,
            "DECLARED" if has_12a else None,
            "DECLARED" if has_80g else None,
            "DECLARED" if has_fcra else None,
            "active" if has_fcra else "never_held",
            _clean(admin_name), _clean(admin_designation), _clean(admin_phone),
            user.get("email"), _clean(state), _clean(district), incorporation_year,
            has_12a, has_80g, has_fcra,
        ),
    )
    ngo_id = str(ngo["id"])

    # ---- store proofs; any failure rolls the whole NGO back -----------------
    try:
        _store_document(ngo_id, "darpan_certificate", darpan_certificate.filename, darpan_bytes)
        if bytes_12a:
            _store_document(ngo_id, "cert_12a", cert_12a.filename, bytes_12a)
        if bytes_80g:
            _store_document(ngo_id, "cert_80g", cert_80g.filename, bytes_80g)
        pool.execute(
            "update ngo_profiles set verification_status = 'document_matched', "
            "verified_at = now() where id = %s",
            (ngo_id,),
        )
    except Exception:  # noqa: BLE001
        logger.exception("registration failed after profile insert; rolling back %s", ngo_id)
        _rollback_ngo(ngo_id)
        raise HTTPException(
            status_code=500,
            detail="Registration could not be completed and nothing was saved. Please try again.",
        )

    return {
        "ngo_id": ngo_id,
        "verification_status": "document_matched",
        "darpan_id": darpan,
        "darpan_id_found_in_certificate": True,
        "verification_method": check.method,  # text | vision
        "certificate_name": check.found_name,
    }


@router.post("/{ngo_id}/verify")
def reverify_ngo(
    ngo_id: str,
    darpan_certificate: UploadFile = File(...),
    user: dict = Depends(current_user),
) -> dict:
    """Retry verification for an NGO that is not (or no longer) document-matched.

    Uses the Darpan ID and name the NGO registered with, so the ID can't be swapped.
    """
    ngo = pool.fetch_one(
        "select id, user_id, name, darpan_id, verification_status "
        "from ngo_profiles where id = %s and user_id = %s",
        (ngo_id, user["id"]),
    )
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found")
    if ngo["verification_status"] in VERIFIED_STATUSES:
        return {"ngo_id": ngo_id, "verification_status": ngo["verification_status"], "already_verified": True}

    data = _read_pdf(darpan_certificate, "Darpan certificate")
    check = verify_darpan_certificate(data, ngo["darpan_id"], ngo["name"])
    if not check.ok:
        raise HTTPException(status_code=422, detail=check.message)

    _store_document(ngo_id, "darpan_certificate", darpan_certificate.filename, data)
    pool.execute(
        "update ngo_profiles set verification_status = 'document_matched', "
        "verified_at = now() where id = %s",
        (ngo_id,),
    )
    return {
        "ngo_id": ngo_id,
        "verification_status": "document_matched",
        "verification_method": check.method,
    }
