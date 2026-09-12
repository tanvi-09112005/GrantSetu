"""Shared state for the GrantSetu LangGraph (Implementation Plan section 4).

One state object flows through every node. The revision loop means a node can
be entered more than once, so anything a node writes must be safe to overwrite
on a second pass -- keep accumulating fields (like `revision_count`) explicit.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

Status = Literal[
    "started",
    "discovered",
    "eligible",
    "ineligible",
    "drafted",
    "claims_extracted",
    "verified",
    "needs_revision",
    "human_review",
    "failed",
]


class CandidateGrant(TypedDict, total=False):
    grant_id: str
    title: str
    funder_name: str
    description: str
    deadline: str | None
    score: float  # fused RRF score
    bm25_rank: int | None
    vector_rank: int | None
    match_reason: str  # why this grant surfaced, for the UI


class EligibilityResult(TypedDict, total=False):
    grant_id: str
    eligible: bool
    missing_criteria: list[str]
    satisfied_criteria: list[str]
    notes: str


class Claim(TypedDict, total=False):
    claim_id: str
    section_key: str
    claim_text: str
    claim_type: Literal["numeric", "qualitative"]


class VerificationResult(TypedDict, total=False):
    claim_id: str
    claim_text: str
    verdict: Literal["supported", "unsupported", "partially_supported"]
    evidence_chunk_id: str | None
    evidence_span: str | None
    confidence: float
    model_used: str


class GrantSetuState(TypedDict, total=False):
    # --- inputs -------------------------------------------------------------
    ngo_id: str
    ngo_profile: dict[str, Any]

    # --- discovery / eligibility -------------------------------------------
    candidate_grants: list[CandidateGrant]
    selected_grant_id: str
    eligibility_result: EligibilityResult

    # --- drafting -----------------------------------------------------------
    draft_sections: dict[str, str]
    sections_to_revise: list[str]

    # --- verification -------------------------------------------------------
    claims: list[Claim]
    verification_results: list[VerificationResult]
    fabrication_rate: float

    # --- loop control -------------------------------------------------------
    revision_count: int
    status: Status
    errors: list[str]


def initial_state(ngo_id: str, selected_grant_id: str | None = None) -> GrantSetuState:
    """A fresh state with every loop-control field seeded.

    Nodes may assume `revision_count`, `errors` and `status` are always present.
    """
    state: GrantSetuState = {
        "ngo_id": ngo_id,
        "ngo_profile": {},
        "candidate_grants": [],
        "draft_sections": {},
        "sections_to_revise": [],
        "claims": [],
        "verification_results": [],
        "fabrication_rate": 0.0,
        "revision_count": 0,
        "status": "started",
        "errors": [],
    }
    if selected_grant_id:
        state["selected_grant_id"] = selected_grant_id
    return state
