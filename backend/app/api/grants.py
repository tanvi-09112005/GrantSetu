"""Grant catalogue and discovery routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import current_user, owned_ngo
from app.db import pool
from app.models.schemas import DiscoveredGrant, DiscoverResponse, GrantOut

router = APIRouter(prefix="/grants", tags=["grants"])


@router.get("", response_model=list[GrantOut])
def list_grants(
    limit: int = Query(50, le=200),
    offset: int = 0,
    _user: dict = Depends(current_user),
) -> list[dict]:
    """Plain catalogue listing — no matching, just what is in the DB."""
    return pool.fetch_all(
        """
        select id, title, funder_name, funder_type, description,
               sectors, geography, deadline, source_url
        from grants
        where is_active
        order by deadline nulls last, created_at desc
        limit %s offset %s
        """,
        (limit, offset),
    )


@router.get("/discover", response_model=DiscoverResponse)
def discover(
    ngo_id: str | None = Query(None),
    top_k: int = Query(6, le=25),
    q: str | None = Query(None, description="Optional custom search query"),
    sectors: str | None = Query(None, description="Comma-separated sectors"),
    name: str | None = Query(None, description="NGO name"),
    mission: str | None = Query(None, description="NGO mission"),
) -> DiscoverResponse:
    """Run the discovery agent for an NGO.

    Phase 2: hybrid RAG — BM25 over grants.tsv + cosine over grants.embedding,
    fused with Reciprocal Rank Fusion, reranked with Gemini 3.6 Flash.
    """
    ngo = None
    if ngo_id:
        import uuid
        try:
            uuid.UUID(str(ngo_id))
            ngo = pool.fetch_one("select * from ngo_profiles where id = %s", (ngo_id,))
        except (ValueError, TypeError):
            pass

        if not ngo:
            from pathlib import Path
            import json
            meta_path = Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / "sample_profiles.json"
            if meta_path.exists():
                try:
                    samples = json.loads(meta_path.read_text(encoding="utf-8"))
                    for s in samples:
                        if s["id"] == ngo_id or s["name"].lower() == str(ngo_id).lower():
                            ngo = s
                            break
                except Exception:
                    pass

    if not ngo:
        sector_list = [s.strip() for s in sectors.split(",")] if sectors else ["education", "health", "child_welfare", "social_welfare"]
        ngo = {
            "id": ngo_id or "cry-india",
            "name": name or "Child Rights and You (CRY)",
            "mission": mission or "To enable individuals and organizations to collaborate and build an India where all children enjoy their rights to happy, healthy and creative childhoods.",
            "sectors": sector_list,
        }

    from app.graph.nodes.discover import run_hybrid_discovery

    results, query_used = run_hybrid_discovery(ngo, top_k=top_k, custom_query=q)

    # Format into DiscoveredGrant models
    discovered: list[DiscoveredGrant] = []
    for r in results:
        discovered.append(
            DiscoveredGrant(
                id=str(r["id"]),
                title=r["title"],
                funder_name=r["funder_name"],
                funder_type=r.get("funder_type"),
                description=r.get("description"),
                sectors=r.get("sectors") or [],
                geography=r.get("geography") or [],
                deadline=r.get("deadline"),
                source_url=r.get("source_url"),
                is_foreign_contribution=bool(r.get("is_foreign_contribution", False)),
                eligibility_text=r.get("eligibility_text"),
                score=r.get("score", 0.0),
                bm25_rank=r.get("bm25_rank"),
                vector_rank=r.get("vector_rank"),
                match_reason=r.get("match_reason"),
            )
        )

    return DiscoverResponse(
        ngo_id=str(ngo.get("id", ngo_id or "demo")),
        query=query_used,
        results=discovered,
    )


@router.get("/{grant_id}", response_model=GrantOut)
def get_grant(grant_id: str, _user: dict = Depends(current_user)) -> dict:
    row = pool.fetch_one(
        """
        select id, title, funder_name, funder_type, description,
               sectors, geography, deadline, source_url
        from grants where id = %s
        """,
        (grant_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="grant not found")
    return row
