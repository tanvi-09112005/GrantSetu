"""Request/response models for the FastAPI layer (plan section 5)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from uuid import UUID

FunderType = Literal["govt", "csr", "foundation", "international"]
FcraStatus = Literal["active", "expired", "cancelled", "suspended", "never_held", "unknown"]
DocType = Literal[
    "registration", "annual_report", "program_report", "financial_statement", "other",
    "12a_80g", "fcra",
    "darpan_certificate", "cert_12a", "cert_80g", "cert_fcra", "csr1",
    "audited_balance_sheet", "itr7", "annual_budget", "past_proposal", "project_plan",
]


# --- NGO ---------------------------------------------------------------------
class NGOProfileIn(BaseModel):
    name: str
    mission: str | None = None
    sectors: list[str] = Field(default_factory=list)
    location: str | None = None
    reg_12a: str | None = None
    reg_80g: str | None = None
    reg_fcra: str | None = None
    # NITI Aayog NGO Darpan unique registration ID (e.g. MH/2021/0123456)
    # Required for all Central Government grants-in-aid.
    darpan_id: str | None = None
    # FCRA is binary admission for foreign contribution, and it expires and is
    # revoked -- so it is a dated state, not just a number. See
    # docs/data-sources-foreign.md.
    fcra_valid_until: date | None = None
    fcra_status: FcraStatus = "unknown"
    fcra_verified_on: date | None = None
    registered_on: date | None = None

    @field_validator("darpan_id")
    @classmethod
    def validate_darpan_id(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip().upper()
        import re
        if not re.match(r"^[A-Z]{2}/\d{4}/\d{7}$", v):
            raise ValueError(
                "Invalid NGO Darpan ID format. Must match official NITI Aayog format: "
                "XX/YYYY/0123456 (e.g. MH/2018/0192837)"
            )
        return v


class NGOProfileOut(NGOProfileIn):
       id: str | UUID
       user_id: str | UUID
       created_at: datetime
       # Added by the registration wizard (Task 1)
       admin_name: str | None = None
       admin_designation: str | None = None
       admin_phone: str | None = None
       admin_email: str | None = None
       state: str | None = None
       district: str | None = None
       incorporation_year: int | None = None
       has_12a: bool = False
       has_80g: bool = False
       has_fcra: bool = False
       verification_status: str = "pending_review"
       verified_at: datetime | None = None

       @field_validator("id", "user_id", mode="before")
       @classmethod
       def coerce_id(cls, v: Any) -> str:
           return str(v) if v is not None else ""


class DocumentOut(BaseModel):
    id: str | UUID
    ngo_id: str | UUID
    doc_type: DocType
    file_url: str | None = None
    ingest_status: str
    ingest_error: str | None = None
    created_at: datetime

    @field_validator("id", "ngo_id", mode="before")
    @classmethod
    def coerce_id(cls, v: Any) -> str:
        return str(v) if v is not None else ""


# --- Grants / discovery ------------------------------------------------------
class GrantOut(BaseModel):
    id: str | UUID
    title: str
    funder_name: str
    funder_type: FunderType | None = None
    description: str | None = None
    sectors: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    deadline: date | None = None
    source_url: str | None = None
    is_foreign_contribution: bool = False
    # Quoted verbatim from the source and shown to the user. Never turned into
    # an automatic eligibility verdict for foreign opportunities.
    eligibility_text: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v: Any) -> str:
        return str(v) if v is not None else ""


class DiscoveredGrant(GrantOut):
    score: float
    bm25_rank: int | None = None
    vector_rank: int | None = None
    match_reason: str | None = None


class DiscoverResponse(BaseModel):
    ngo_id: str | UUID
    query: str
    results: list[DiscoveredGrant]

    @field_validator("ngo_id", mode="before")
    @classmethod
    def coerce_id(cls, v: Any) -> str:
        return str(v) if v is not None else ""


# --- Eligibility -------------------------------------------------------------
class EligibilityRequest(BaseModel):
    ngo_id: str
    grant_id: str


class EligibilityResponse(BaseModel):
    ngo_id: str | UUID
    grant_id: str | UUID
    eligible: bool
    missing_criteria: list[str] = Field(default_factory=list)
    satisfied_criteria: list[str] = Field(default_factory=list)
    notes: str | None = None
    is_foreign_contribution: bool = False
    fcra_blocker: str | None = None
    requires_human_review: bool = False

    @field_validator("ngo_id", "grant_id", mode="before")
    @classmethod
    def coerce_id(cls, v: Any) -> str:
        return str(v) if v is not None else ""



# --- Proposals ---------------------------------------------------------------
class GenerateProposalRequest(BaseModel):
    ngo_id: str
    grant_id: str
    template_type: Literal["standard", "csr", "govt"] = "standard"
    force_regenerate: bool = False


class BatchGenerateRequest(BaseModel):
    ngo_id: str
    grant_ids: list[str] = Field(..., min_length=1, max_length=5)
    template_type: Literal["standard", "csr", "govt"] = "standard"
    force_regenerate: bool = False


class ClaimVerdict(BaseModel):
    id: str | None = None
    section_key: str | None = None
    claim_text: str
    verdict: Literal["supported", "unsupported", "partially_supported"]
    evidence_span: str | None = None
    evidence_chunk_id: str | None = None
    confidence: float | None = None
    document_name: str | None = None
    document_id: str | None = None
    doc_type: str | None = None
    chunk_section: str | None = None
    chunk_text: str | None = None


class ProposalResponse(BaseModel):
    proposal_id: str | None = None
    application_id: str | None = None
    grant_id: str | None = None
    ngo_id: str | None = None
    template_type: str = "standard"
    sections: dict[str, str] = Field(default_factory=dict)
    verification_results: list[ClaimVerdict] = Field(default_factory=list)
    fabrication_rate: float = 0.0
    revision_count: int = 0
    status: str


class ReviseRequest(BaseModel):
    """Either apply human edits, or re-trigger the revision agent."""

    edits: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, str] = Field(default_factory=dict)
    rerun_verification: bool = True


class RefineSectionRequest(BaseModel):
    """Targeted single-section refinement with custom instruction."""

    section_key: str
    instruction: str
    current_content: str | None = None
    temperature: float = 0.2
    preview_only: bool = False


class RefineSectionResponse(BaseModel):
    """Candidate refinement text for visual diff before user acceptance."""

    proposal_id: str | None = None
    section_key: str
    original_text: str
    refined_text: str
    instruction: str
    proposal: ProposalResponse | None = None


class ApplySectionRevisionRequest(BaseModel):
    """Accept and apply a reviewed section revision with targeted verification."""

    section_key: str
    refined_text: str
    rerun_verification: bool = True


class EditClaimRequest(BaseModel):
    """Manually update an unsupported claim sentence in the proposal."""

    section_key: str
    old_text: str
    new_text: str


class DropClaimRequest(BaseModel):
    """Remove a hallucinated/unsupported claim sentence from the proposal."""

    section_key: str
    claim_text: str


# --- Applications ------------------------------------------------------------
class ApplicationOut(BaseModel):
    id: str
    ngo_id: str
    grant_id: str
    grant_title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


# --- Evaluation --------------------------------------------------------------
class EvalRunRequest(BaseModel):
    run_type: Literal["ragas", "deepeval", "fabrication_rate"]
    sample_size: int | None = None
    notes: str | None = None


class EvalRunOut(BaseModel):
    id: str
    run_type: str
    metrics_json: dict[str, Any]
    sample_size: int | None
    notes: str | None
    created_at: datetime