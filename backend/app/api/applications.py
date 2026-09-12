"""Application history / status tracker."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import owned_ngo
from app.db import pool
from app.models.schemas import ApplicationOut

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(ngo_id: str = Depends(owned_ngo)) -> list[dict]:
    return pool.fetch_all(
        """
        select a.id, a.ngo_id, a.grant_id, g.title as grant_title,
               a.status, a.created_at, a.updated_at
        from applications a
        join grants g on g.id = a.grant_id
        where a.ngo_id = %s
        order by a.updated_at desc
        """,
        (ngo_id,),
    )
