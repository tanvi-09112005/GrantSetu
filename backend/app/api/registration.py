"""NGO registration (Task 1): one multipart call that stores the whole wizard.

The React wizard first creates the Supabase Auth user (email + password), then
calls ``POST /ngo/register`` with the session JWT, the form fields and the
certificate PDFs. Validation is repeated here on purpose: the browser check is
for convenience, this one is the authoritative one.
"""

from __future__ import annotations

import logging
import re
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import current_user
from app.db import pool

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

    # ---- store proofs + a real (cheap) content check ------------------------
    darpan_doc = _store_document(ngo_id, "darpan_certificate", darpan_certificate.filename, darpan_bytes)
    if bytes_12a:
        _store_document(ngo_id, "cert_12a", cert_12a.filename, bytes_12a)
    if bytes_80g:
        _store_document(ngo_id, "cert_80g", cert_80g.filename, bytes_80g)

    # Does the uploaded PDF actually mention the ID the user typed?
    text = (darpan_doc.get("raw_text") or "").upper().replace(" ", "")
    id_found_in_pdf = darpan.replace(" ", "") in text

    new_status = "document_matched" if id_found_in_pdf else "format_verified"
    pool.execute(
        "update ngo_profiles set verification_status = %s, verified_at = now() where id = %s",
        (new_status, ngo_id),
    )
    return {
        "ngo_id": ngo_id,
        "verification_status": new_status,
        "darpan_id": darpan,
        "darpan_id_found_in_certificate": id_found_in_pdf,
    }
