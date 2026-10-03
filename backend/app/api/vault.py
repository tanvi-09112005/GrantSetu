"""Document Vault extras (Task 3): branding assets + deleting documents.

Uploading / listing documents already lives in ``app.api.ngo``. This module adds
what the categorized vault needs on top:

* ``/ngo/assets``       list / upload / delete the logo, stamp and signature PNGs
* ``DELETE /ngo/documents/{id}``  remove a document (its chunks cascade)

Images are small (<= 1 MB), so they are stored in Postgres (``ngo_assets``) and
returned as base64 data-URLs. That lets the browser show a preview in a plain
``<img>`` tag without having to send an auth header for the image request.
"""

from __future__ import annotations

import base64
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import current_user, owned_ngo
from app.db import pool

router = APIRouter(prefix="/ngo", tags=["vault"])

ASSET_TYPES = ("logo", "stamp", "signature")
MAX_ASSET_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_ASSET_PIXELS = 4000  # per side
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _validate_png(data: bytes) -> None:
    """Reject anything that is not a real, reasonably sized PNG."""
    if not data:
        raise HTTPException(422, "The file is empty")
    if len(data) > MAX_ASSET_BYTES:
        raise HTTPException(422, "Image is larger than 1 MB")
    if not data.startswith(PNG_MAGIC):
        raise HTTPException(422, "Only PNG images are accepted (transparent PNG recommended)")
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, "This file is not a valid PNG image") from exc
    if max(width, height) > MAX_ASSET_PIXELS:
        raise HTTPException(422, f"Image is larger than {MAX_ASSET_PIXELS}px on one side")


def _check_type(asset_type: str) -> str:
    if asset_type not in ASSET_TYPES:
        raise HTTPException(404, f"Unknown asset type. Use one of: {', '.join(ASSET_TYPES)}")
    return asset_type


@router.get("/assets")
def list_assets(ngo_id: str, user: dict = Depends(current_user)) -> list[dict]:
    """Branding images for an NGO, each with an inline ``data_url`` preview."""
    owned_ngo(ngo_id, user)
    rows = pool.fetch_all(
        """
        select asset_type, filename, content_type, size_bytes, updated_at, data
        from ngo_assets where ngo_id = %s order by asset_type
        """,
        (ngo_id,),
    )
    out = []
    for row in rows:
        raw = bytes(row["data"])
        out.append(
            {
                "asset_type": row["asset_type"],
                "filename": row["filename"],
                "size_bytes": row["size_bytes"],
                "updated_at": row["updated_at"],
                "data_url": f"data:{row['content_type']};base64,{base64.b64encode(raw).decode()}",
            }
        )
    return out


@router.put("/assets/{asset_type}")
def upload_asset(
    asset_type: str,
    ngo_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
) -> dict:
    """Create or replace one branding image (one slot per type per NGO)."""
    _check_type(asset_type)
    owned_ngo(ngo_id, user)
    data = file.file.read()
    _validate_png(data)
    pool.execute(
        """
        insert into ngo_assets (ngo_id, asset_type, filename, content_type, size_bytes, data)
        values (%s, %s, %s, 'image/png', %s, %s)
        on conflict (ngo_id, asset_type) do update set
            filename = excluded.filename,
            size_bytes = excluded.size_bytes,
            data = excluded.data,
            updated_at = now()
        """,
        (ngo_id, asset_type, file.filename, len(data), data),
    )
    return {"asset_type": asset_type, "filename": file.filename, "size_bytes": len(data)}


@router.delete("/assets/{asset_type}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_type: str, ngo_id: str, user: dict = Depends(current_user)) -> None:
    _check_type(asset_type)
    owned_ngo(ngo_id, user)
    pool.execute("delete from ngo_assets where ngo_id = %s and asset_type = %s", (ngo_id, asset_type))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user: dict = Depends(current_user)) -> None:
    """Delete a document the caller owns. Its embedded chunks are removed by cascade."""
    row = pool.fetch_one(
        """
        select d.id from ngo_documents d
        join ngo_profiles n on n.id = d.ngo_id
        where d.id = %s and n.user_id = %s
        """,
        (document_id, user["id"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="document not found")
    pool.execute("delete from ngo_documents where id = %s", (document_id,))
