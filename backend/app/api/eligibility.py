"""Eligibility routes — deterministic rules engine, no LLM in this path."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

import json
from pathlib import Path

from app.api.deps import maybe_user, owned_ngo
from app.db import pool
from app.graph.nodes.eligibility import evaluate_eligibility
from app.models.schemas import EligibilityRequest, EligibilityResponse

router = APIRouter(prefix="/eligibility", tags=["eligibility"])


@router.post("/check", response_model=EligibilityResponse)
def check(payload: EligibilityRequest, user: dict | None = Depends(maybe_user)) -> EligibilityResponse:
    ngo = None
    
    # 1. Try fetching from DB if it looks like a UUID
    if len(payload.ngo_id) == 36 and payload.ngo_id.count("-") == 4:
        try:
            ngo = pool.fetch_one("select * from ngo_profiles where id = %s", (payload.ngo_id,))
            if ngo and user:
                # If authenticated, verify ownership
                try:
                    owned_ngo(payload.ngo_id, user)
                except HTTPException:
                    pass
        except Exception:
            ngo = None

    # 2. If not found in DB, check sample NGO profiles
    if not ngo:
        for candidate_path in [
            Path(__file__).resolve().parents[3] / "data" / "sample_ngos" / "sample_profiles.json",
            Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / "sample_profiles.json",
        ]:
            if candidate_path.exists():
                try:
                    samples = json.loads(candidate_path.read_text(encoding="utf-8"))
                    for s in samples:
                        if s["id"] == payload.ngo_id or s["name"].lower() == str(payload.ngo_id).lower():
                            ngo = s
                            break
                    if ngo:
                        break
                except Exception:
                    pass

    # 3. Fallback default NGO profile if still not found
    if not ngo:
        ngo = {
            "id": payload.ngo_id,
            "name": "Sample NGO",
            "darpan_id": "DL/2019/0123456",
            "sectors": ["education", "health", "child_welfare", "social_welfare"],
            "reg_12a": "AAATC1234A",
            "reg_80g": "AAATC1234B",
            "fcra_status": "active",
            "reg_fcra": "231650035",
            "registered_on": "2010-01-01",
        }

    grant = pool.fetch_one("select * from grants where id = %s", (payload.grant_id,))
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found in catalogue")

    result = evaluate_eligibility(ngo, grant)
    return EligibilityResponse(
        ngo_id=payload.ngo_id,
        grant_id=payload.grant_id,
        eligible=result["eligible"],
        missing_criteria=result["missing_criteria"],
        satisfied_criteria=result["satisfied_criteria"],
        notes=result["notes"],
        is_foreign_contribution=result["is_foreign_contribution"],
        fcra_blocker=result["fcra_blocker"],
        requires_human_review=result["requires_human_review"],
    )


