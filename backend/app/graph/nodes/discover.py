"""discover_grants — hybrid RAG over the grants catalogue.

Hybrid retrieval: BM25 (grants.tsv) + pgvector cosine similarity (grants.embedding),
fused with Reciprocal Rank Fusion (k=60), then reranked with Gemini 3.6 Flash.
Produces CandidateGrant records with fused scores and explainable match reasons.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.db import pool
from app.graph.state import CandidateGrant, GrantSetuState
from app.services.embeddings import embed_query
from app.services.llm import get_llm, parse_json_response

logger = logging.getLogger(__name__)


def run_hybrid_discovery(
    ngo_profile: dict[str, Any],
    top_k: int = 5,
    custom_query: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Execute hybrid BM25 + pgvector + RRF + Gemini Flash reranking."""
    # 1. Build search query text
    ngo_id = ngo_profile.get("id")
    name = ngo_profile.get("name", "")
    mission = ngo_profile.get("mission", "")
    sectors = " ".join(ngo_profile.get("sectors") or [])

    # Enrich with ingested document chunks if present
    chunk_text = ""
    if ngo_id:
        import uuid
        try:
            uuid.UUID(str(ngo_id))
            chunks = pool.fetch_all(
                """
                select chunk_text from document_chunks
                where ngo_id = %s
                order by chunk_index
                limit 3
                """,
                (ngo_id,),
            )
            if chunks:
                chunk_text = " ".join(c["chunk_text"][:200] for c in chunks)
        except (ValueError, TypeError):
            pass

    if custom_query and custom_query.strip():
        query_text = custom_query.strip()
    else:
        parts = [p for p in [sectors, mission, chunk_text] if p]
        query_text = " ".join(parts) if parts else name or "social welfare education health development"

    # 2. Dense Vector Embedding
    try:
        vector = embed_query(query_text)
    except Exception as e:
        logger.warning("Embedding query failed (%s); proceeding with zero vector fallback", e)
        vector = [0.0] * 1024

    # 3. Sparse BM25 Search
    bm25_rows = pool.fetch_all(
        """
        select id, title, funder_name, funder_type, description,
               sectors, geography, deadline, source_url, is_foreign_contribution,
               eligibility_text, eligibility_json,
               ts_rank(tsv, plainto_tsquery('english', %s)) as bm25_score
        from grants
        where is_active and tsv @@ plainto_tsquery('english', %s)
        order by bm25_score desc
        limit 30
        """,
        (query_text, query_text),
    )

    # If narrow query yielded no rows, try with sectors
    if not bm25_rows and sectors:
        bm25_rows = pool.fetch_all(
            """
            select id, title, funder_name, funder_type, description,
                   sectors, geography, deadline, source_url, is_foreign_contribution,
                   eligibility_text, eligibility_json,
                   ts_rank(tsv, plainto_tsquery('english', %s)) as bm25_score
            from grants
            where is_active and tsv @@ plainto_tsquery('english', %s)
            order by bm25_score desc
            limit 30
            """,
            (sectors, sectors),
        )

    # 4. Dense pgvector Search
    vector_rows = pool.fetch_all(
        """
        select id, title, funder_name, funder_type, description,
               sectors, geography, deadline, source_url, is_foreign_contribution,
               eligibility_text, eligibility_json,
               (1 - (embedding <=> %s::vector)) as vector_score
        from grants
        where is_active and embedding is not null
        order by embedding <=> %s::vector
        limit 30
        """,
        (vector, vector),
    )

    # 5. Reciprocal Rank Fusion (RRF, k=60)
    k = 60
    candidates: dict[str, dict[str, Any]] = {}

    for rank, row in enumerate(bm25_rows, start=1):
        gid = str(row["id"])
        candidates[gid] = {
            "row": row,
            "bm25_rank": rank,
            "vector_rank": None,
            "rrf_score": 1.0 / (k + rank),
        }

    for rank, row in enumerate(vector_rows, start=1):
        gid = str(row["id"])
        if gid not in candidates:
            candidates[gid] = {
                "row": row,
                "bm25_rank": None,
                "vector_rank": rank,
                "rrf_score": 1.0 / (k + rank),
            }
        else:
            candidates[gid]["vector_rank"] = rank
            candidates[gid]["row"] = row
            candidates[gid]["rrf_score"] += 1.0 / (k + rank)

    # If both searches yielded few results, fallback to active catalogue rows
    if not candidates:
        fallback_rows = pool.fetch_all(
            """
            select id, title, funder_name, funder_type, description,
                   sectors, geography, deadline, source_url, is_foreign_contribution,
                   eligibility_text, eligibility_json
            from grants
            where is_active
            order by deadline nulls last, created_at desc
            limit 15
            """
        )
        for rank, r in enumerate(fallback_rows, start=1):
            gid = str(r["id"])
            candidates[gid] = {
                "row": r,
                "bm25_rank": None,
                "vector_rank": None,
                "rrf_score": 1.0 / (k + rank),
            }

    ranked_list = sorted(candidates.values(), key=lambda x: x["rrf_score"], reverse=True)[:15]

    # 6. Gemini 3.6 Flash Reranker & Match Reason
    results = _rerank_with_gemini(ngo_profile, ranked_list, top_k=top_k)
    return results, query_text


def _rerank_with_gemini(
    ngo_profile: dict[str, Any],
    candidates: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Use Gemini Flash to score relevance and formulate human-friendly match reasons."""
    if not candidates:
        return []

    ngo_name = ngo_profile.get("name", "NGO")
    ngo_mission = ngo_profile.get("mission", "")
    ngo_sectors = ", ".join(ngo_profile.get("sectors") or [])
    # Only send top candidates to LLM to keep response fast (1-2s)
    top_candidates = candidates[: max(top_k, 5)]
    items_payload = []
    for c in top_candidates:
        r = c["row"]
        items_payload.append(
            {
                "id": str(r["id"]),
                "title": r.get("title"),
                "funder_name": r.get("funder_name"),
                "sectors": r.get("sectors"),
                "description": (r.get("description") or "")[:150],
            }
        )

    prompt = f"""You are an expert grant advisor for Indian NGOs.
NGO Name: {ngo_name}
Mission: {ngo_mission}
Sectors: {ngo_sectors}

Evaluate the following candidate grants. For each grant, determine relevance to this NGO on a scale of 0.0 to 1.0 and write a concise 1-sentence match explanation highlighting specific alignment.

Grants:
{json.dumps(items_payload, indent=2)}

Return ONLY a JSON array of objects with the following keys:
[
  {{
    "id": "<grant_id>",
    "relevance_score": 0.95,
    "match_reason": "<1-sentence specific alignment explanation>"
  }}
]
"""

    rerank_map: dict[str, dict[str, Any]] = {}
    try:
        import concurrent.futures

        def _call_llm():
            llm = get_llm(tier="flash", temperature=0.1)
            resp = llm.invoke(prompt)
            text_content = resp.content
            if isinstance(text_content, list):
                text_content = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in text_content
                )
            return parse_json_response(str(text_content))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_llm)
            parsed = future.result(timeout=6.0)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "id" in item:
                        rerank_map[item["id"]] = item
    except Exception as e:
        logger.warning("Gemini reranker timed out or failed (%s); defaulting to RRF scores", e)

    output = []
    for c in candidates:

        row = c["row"]
        gid = str(row["id"])
        gemini_info = rerank_map.get(gid, {})

        fused_score = gemini_info.get("relevance_score")
        if fused_score is None:
            # Normalized score from RRF
            fused_score = min(1.0, round(c["rrf_score"] * 30.0, 3))

        match_reason = gemini_info.get("match_reason")
        if not match_reason:
            common = set(row.get("sectors") or []).intersection(set(ngo_profile.get("sectors") or []))
            if common:
                match_reason = f"Aligned with your focus area in {', '.join(common)}."
            else:
                match_reason = f"Offered by {row.get('funder_name')} in {', '.join(row.get('sectors') or ['development'])}."

        grant_dict = dict(row)
        grant_dict["score"] = float(fused_score)
        grant_dict["bm25_rank"] = c.get("bm25_rank")
        grant_dict["vector_rank"] = c.get("vector_rank")
        grant_dict["match_reason"] = match_reason
        output.append(grant_dict)

    # Sort by final score descending and slice top_k
    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]


def discover_grants(state: GrantSetuState) -> GrantSetuState:
    """LangGraph node: runs hybrid discovery for state['ngo_id']."""
    ngo_id = state.get("ngo_id")
    if ngo_id == "00000000-0000-0000-0000-000000000000":
        return {
            "candidate_grants": [],
            "status": "discovered",
        }

    ngo_profile = state.get("ngo_profile") or {}
    if not ngo_profile and ngo_id:
        ngo_profile = pool.fetch_one("select * from ngo_profiles where id = %s", (ngo_id,)) or {}

    results, _ = run_hybrid_discovery(ngo_profile, top_k=5)

    candidate_grants: list[CandidateGrant] = []
    for r in results:
        candidate_grants.append(
            {
                "grant_id": str(r["id"]),
                "title": r.get("title", ""),
                "funder_name": r.get("funder_name", ""),
                "description": r.get("description", ""),
                "deadline": str(r["deadline"]) if r.get("deadline") else None,
                "score": r.get("score", 0.0),
                "bm25_rank": r.get("bm25_rank"),
                "vector_rank": r.get("vector_rank"),
                "match_reason": r.get("match_reason", ""),
            }
        )

    out: dict[str, Any] = {
        "candidate_grants": candidate_grants,
        "status": "discovered",
    }
    if candidate_grants and not state.get("selected_grant_id"):
        out["selected_grant_id"] = candidate_grants[0]["grant_id"]
    return out

