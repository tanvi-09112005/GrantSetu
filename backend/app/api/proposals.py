"""Proposal generation, revision and export routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import current_user, owned_ngo
from app.models.schemas import GenerateProposalRequest, ProposalResponse, ReviseRequest

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.post("/generate", response_model=ProposalResponse)
def generate(
    payload: GenerateProposalRequest, user: dict = Depends(current_user)
) -> ProposalResponse:
    """Run the full LangGraph and return the draft plus its verification report."""
    owned_ngo(payload.ngo_id, user)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="proposal generation lands in Phase 3",
    )


@router.post("/{proposal_id}/revise", response_model=ProposalResponse)
def revise(
    proposal_id: str, payload: ReviseRequest, _user: dict = Depends(current_user)
) -> ProposalResponse:
    """Apply human edits, or re-trigger the revision agent."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="revision lands in Phase 4",
    )


@router.get("/{proposal_id}/export")
def export(
    proposal_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    _user: dict = Depends(current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="export lands in Phase 5",
    )
