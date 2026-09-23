"""Proposal generation, revision and export routes (Phase 3 & 4)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import maybe_user, owned_ngo
from app.db import pool
from app.graph.nodes.draft import TEMPLATES, draft_proposal
from app.graph.nodes.extract_claims import extract_claims
from app.graph.nodes.verify import verify_claims
from app.models.schemas import (
    BatchGenerateRequest,
    ClaimVerdict,
    GenerateProposalRequest,
    ProposalResponse,
    ReviseRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proposals", tags=["proposals"])


def _resolve_ngo_profile(ngo_id_input: str) -> tuple[str, dict]:
    """Resolve ngo_id (UUID or sample slug) to (valid_uuid, ngo_profile_dict)."""
    # 1. Try direct UUID lookup
    if len(ngo_id_input) == 36 and ngo_id_input.count("-") == 4:
        row = pool.fetch_one("select * from ngo_profiles where id = %s", (ngo_id_input,))
        if row:
            return str(row["id"]), row

    # 2. Try lookup by slug or name in ngo_profiles
    name_map = {
        "eoto-india": "Each One Teach One",
        "cry-india": "Child Rights and You",
        "pratham-education": "Pratham",
        "goonj": "Goonj",
        "akshaya-patra": "Akshaya Patra",
    }
    search_term = name_map.get(ngo_id_input, ngo_id_input)
    row = pool.fetch_one("select * from ngo_profiles where name ilike %s limit 1", (f"%{search_term}%",))
    if row:
        return str(row["id"]), row

    # 3. Check sample_profiles.json
    for path in [
        Path(__file__).resolve().parents[3] / "data" / "sample_ngos" / "sample_profiles.json",
        Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / "sample_profiles.json",
    ]:
        if path.exists():
            try:
                samples = json.loads(path.read_text(encoding="utf-8"))
                for s in samples:
                    if s["id"] == ngo_id_input or s["name"].lower() == ngo_id_input.lower():
                        # Create record in DB if not present
                        user = pool.fetch_one("select id from auth.users limit 1")
                        user_id = user["id"] if user else str(uuid.uuid4())
                        new_row = pool.fetch_one(
                            """
                            insert into ngo_profiles (user_id, name, mission, sectors, location, darpan_id)
                            values (%s, %s, %s, %s, %s, %s)
                            returning *
                            """,
                            (user_id, s["name"], s.get("mission"), s.get("sectors", []), s.get("location"), s.get("darpan_id")),
                        )
                        return str(new_row["id"]), new_row
            except Exception:
                pass

    raise HTTPException(status_code=404, detail=f"NGO profile not found for '{ngo_id_input}'")


def _fetch_verification_results(proposal_id: str) -> tuple[list[ClaimVerdict], float]:
    """Retrieve persisted verification results and calculate fabrication rate."""
    rows = pool.fetch_all(
        """
        select claim_text, verdict, evidence_span, confidence
        from verification_results
        where proposal_id = %s
        order by created_at asc
        """,
        (proposal_id,),
    )
    if not rows:
        return [], 0.0
    verdicts = [
        ClaimVerdict(
            claim_text=r["claim_text"],
            verdict=r["verdict"],
            evidence_span=r.get("evidence_span"),
            confidence=r.get("confidence"),
        )
        for r in rows
    ]
    unsupported = sum(1 for v in verdicts if v.verdict == "unsupported")
    rate = round(unsupported / len(verdicts), 3) if verdicts else 0.0
    return verdicts, rate


@router.get("/templates")
def list_templates() -> dict:
    """Return available proposal templates and their section definitions."""
    return {
        key: [
            {"key": s["key"], "title": s["title"], "instruction": s["instruction"]}
            for s in sections
        ]
        for key, sections in TEMPLATES.items()
    }


@router.post("/generate", response_model=ProposalResponse)
def generate(
    payload: GenerateProposalRequest,
    user: dict | None = Depends(maybe_user),
) -> ProposalResponse:
    """Generate a multi-section grant proposal grounded in NGO document chunks and funder guidelines."""
    resolved_ngo_id, ngo_profile = _resolve_ngo_profile(payload.ngo_id)

    # Optional ownership assert if user is logged in and not demo
    if user and isinstance(user, dict) and "id" in user:
        try:
            owned_ngo(resolved_ngo_id, user)
        except HTTPException:
            pass

    grant = pool.fetch_one("select * from grants where id = %s", (payload.grant_id,))
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found in catalogue")

    # Ensure application record exists
    app_row = pool.fetch_one(
        """
        insert into applications (ngo_id, grant_id, status)
        values (%s, %s, 'drafted')
        on conflict (ngo_id, grant_id)
        do update set status = 'drafted', updated_at = now()
        returning id
        """,
        (resolved_ngo_id, payload.grant_id),
    )
    application_id = str(app_row["id"])

    # Smart DB Caching: check if proposal already exists and force_regenerate is False
    if not payload.force_regenerate:
        existing_prop = pool.fetch_one(
            """
            select id, version, sections, status from proposals
            where application_id = %s
            order by version desc, created_at desc
            limit 1
            """,
            (application_id,),
        )
        if existing_prop and existing_prop.get("sections"):
            cached_sections = existing_prop["sections"]
            if isinstance(cached_sections, str):
                try:
                    cached_sections = json.loads(cached_sections)
                except Exception:
                    cached_sections = {}
            if cached_sections and isinstance(cached_sections, dict) and any(v.strip() for v in cached_sections.values() if isinstance(v, str)):
                logger.info("Serving proposal from DB cache (0 API calls): %s", existing_prop["id"])
                verdicts, rate = _fetch_verification_results(str(existing_prop["id"]))
                return ProposalResponse(
                    proposal_id=str(existing_prop["id"]),
                    application_id=application_id,
                    grant_id=payload.grant_id,
                    ngo_id=resolved_ngo_id,
                    template_type=payload.template_type,
                    sections=cached_sections,
                    verification_results=verdicts,
                    fabrication_rate=rate,
                    revision_count=max(0, int(existing_prop.get("version") or 1) - 1),
                    status="cached",
                )

    # Run section-by-section draft generation
    state = {
        "ngo_id": resolved_ngo_id,
        "ngo_profile": ngo_profile,
        "selected_grant_id": payload.grant_id,
        "template_type": payload.template_type,
        "draft_sections": {},
        "sections_to_revise": [],
    }

    result_state = draft_proposal(state)
    sections = result_state.get("draft_sections", {})

    if not sections or not any(v.strip() for v in sections.values() if isinstance(v, str)):
        err_msg = "; ".join(result_state.get("errors", [])) or "LLM failed to generate proposal content"
        logger.error("Proposal drafting produced no content: %s", err_msg)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Proposal drafting failed: {err_msg}. Please retry.",
        )

    # Persist proposal draft with auto-incrementing version per application
    prop_row = pool.fetch_one(
        """
        insert into proposals (application_id, version, sections, status)
        values (
            %s,
            coalesce((select max(version) from proposals where application_id = %s), 0) + 1,
            %s,
            'draft'
        )
        returning id, version
        """,
        (application_id, application_id, json.dumps(sections)),
    )
    proposal_id = str(prop_row["id"])
    proposal_version = int(prop_row.get("version") or 1)

    # Automatically execute Phase 4 claim extraction & entailment verification
    state["draft_sections"] = sections
    verdicts: list[ClaimVerdict] = []
    rate: float = 0.0
    status_str = "drafted"

    try:
        extract_state = extract_claims(state)
        claims = extract_state.get("claims", [])
        state["claims"] = claims
        verify_state = verify_claims(state)
        results = verify_state.get("verification_results", [])
        rate = verify_state.get("fabrication_rate", 0.0)

        for r in results:
            pool.execute(
                """
                insert into verification_results (proposal_id, claim_text, verdict, evidence_span, confidence, model_used)
                values (%s, %s, %s, %s, %s, 'gemini-3.5-flash')
                """,
                (proposal_id, r["claim_text"], r["verdict"], r.get("evidence_span"), r.get("confidence", 0.9)),
            )

        verdicts = [
            ClaimVerdict(
                claim_text=r["claim_text"],
                verdict=r["verdict"],
                evidence_span=r.get("evidence_span"),
                confidence=r.get("confidence"),
            )
            for r in results
        ]
        status_str = "verified"
        pool.execute("update proposals set status = 'verified', updated_at = now() where id = %s", (proposal_id,))
        logger.info("Auto-verification completed for proposal %s: %d claims, fabrication rate %.1f%%", proposal_id, len(verdicts), rate * 100)
    except Exception as ve:
        logger.warning("Auto-verification after drafting failed (%s); returning unverified draft", ve)

    return ProposalResponse(
        proposal_id=proposal_id,
        application_id=application_id,
        grant_id=payload.grant_id,
        ngo_id=resolved_ngo_id,
        template_type=payload.template_type,
        sections=sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=max(0, proposal_version - 1),
        status=status_str,
    )


@router.post("/batch-generate", response_model=list[ProposalResponse])
def batch_generate(
    payload: BatchGenerateRequest,
    user: dict | None = Depends(maybe_user),
) -> list[ProposalResponse]:
    """Generate proposals for multiple selected grants with rate-limiting to protect free-tier quotas."""
    import time

    results: list[ProposalResponse] = []
    for idx, grant_id in enumerate(payload.grant_ids):
        # Buffer requests by 1.5s if not first item and generating new
        if idx > 0 and payload.force_regenerate:
            time.sleep(1.5)

        single_req = GenerateProposalRequest(
            ngo_id=payload.ngo_id,
            grant_id=grant_id,
            template_type=payload.template_type,
            force_regenerate=payload.force_regenerate,
        )
        try:
            prop = generate(single_req, user=user)
            results.append(prop)
        except Exception as e:
            logger.error("Failed batch proposal for grant %s: %s", grant_id, e)

    return results



@router.get("/{proposal_id}", response_model=ProposalResponse)
def get_proposal(
    proposal_id: str,
    _user: dict | None = Depends(maybe_user),
) -> ProposalResponse:
    """Retrieve an existing proposal draft and its sections."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.application_id, p.sections, p.status,
               a.ngo_id, a.grant_id
        from proposals p
        join applications a on a.id = p.application_id
        where p.id = %s
        """,
        (proposal_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")

    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    verdicts, rate = _fetch_verification_results(proposal_id)

    return ProposalResponse(
        proposal_id=str(row["proposal_id"]),
        application_id=str(row["application_id"]),
        grant_id=str(row["grant_id"]),
        ngo_id=str(row["ngo_id"]),
        template_type="standard",
        sections=sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=0,
        status=row["status"],
    )


@router.post("/{proposal_id}/verify", response_model=ProposalResponse)
def verify_proposal_claims(
    proposal_id: str,
    _user: dict | None = Depends(maybe_user),
) -> ProposalResponse:
    """Extract factual claims and run entailment verification against NGO document vault."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.application_id, p.version, p.sections, p.status,
               a.ngo_id, a.grant_id
        from proposals p
        join applications a on a.id = p.application_id
        where p.id = %s
        """,
        (proposal_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")

    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    ngo_id = str(row["ngo_id"])
    state = {
        "ngo_id": ngo_id,
        "draft_sections": sections,
    }

    # 1. Extract atomic factual claims
    extract_state = extract_claims(state)
    claims = extract_state.get("claims", [])

    # 2. Verify claims against vault documents
    state["claims"] = claims
    verify_state = verify_claims(state)
    results = verify_state.get("verification_results", [])
    rate = verify_state.get("fabrication_rate", 0.0)

    # 3. Persist to verification_results table (replace older audit)
    pool.execute("delete from verification_results where proposal_id = %s", (proposal_id,))
    for r in results:
        pool.execute(
            """
            insert into verification_results (proposal_id, claim_text, verdict, evidence_span, confidence, model_used)
            values (%s, %s, %s, %s, %s, 'gemini-3.6-flash')
            """,
            (proposal_id, r["claim_text"], r["verdict"], r.get("evidence_span"), r.get("confidence", 0.9)),
        )

    pool.execute(
        "update proposals set status = 'verified', updated_at = now() where id = %s",
        (proposal_id,),
    )

    verdicts = [
        ClaimVerdict(
            claim_text=r["claim_text"],
            verdict=r["verdict"],
            evidence_span=r.get("evidence_span"),
            confidence=r.get("confidence"),
        )
        for r in results
    ]

    return ProposalResponse(
        proposal_id=proposal_id,
        application_id=str(row["application_id"]),
        grant_id=str(row["grant_id"]),
        ngo_id=ngo_id,
        template_type="standard",
        sections=sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=max(0, int(row.get("version") or 1) - 1),
        status="verified",
    )


@router.post("/{proposal_id}/revise", response_model=ProposalResponse)
def revise(
    proposal_id: str,
    payload: ReviseRequest,
    _user: dict | None = Depends(maybe_user),
) -> ProposalResponse:
    """Apply manual edits or trigger section regeneration."""
    row = pool.fetch_one("select * from proposals where id = %s", (proposal_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")

    current_sections = row["sections"]
    if isinstance(current_sections, str):
        try:
            current_sections = json.loads(current_sections)
        except Exception:
            current_sections = {}

    # Update sections with any human edits (accepting either 'sections' or 'edits')
    edits_map = payload.sections or payload.edits or {}
    for k, v in edits_map.items():
        current_sections[k] = v

    pool.execute(
        "update proposals set sections = %s, updated_at = now() where id = %s",
        (json.dumps(current_sections), proposal_id),
    )

    verdicts, rate = _fetch_verification_results(proposal_id)

    return ProposalResponse(
        proposal_id=proposal_id,
        application_id=str(row["application_id"]),
        sections=current_sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=max(0, int(row.get("version") or 1) - 1),
        status="revised",
    )


@router.get("/{proposal_id}/export")
def export(
    proposal_id: str,
    format: str = Query("markdown", pattern="^(markdown|txt|json)$"),
    _user: dict | None = Depends(maybe_user),
):
    """Export the proposal as Markdown or plain text."""
    row = pool.fetch_one(
        """
        select p.sections, g.title as grant_title, n.name as ngo_name
        from proposals p
        join applications a on a.id = p.application_id
        join grants g on g.id = a.grant_id
        join ngo_profiles n on n.id = a.ngo_id
        where p.id = %s
        """,
        (proposal_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")

    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    md_lines = [
        f"# Grant Proposal: {row['grant_title']}",
        f"**Applicant**: {row['ngo_name']}",
        f"**Generated via**: GrantSetu Multi-Agent System",
        "\n---\n",
    ]
    for key, content in sections.items():
        title = key.replace("_", " ").title()
        md_lines.append(f"## {title}\n")
        md_lines.append(f"{content}\n\n---\n")

    full_md = "\n".join(md_lines)
    return {
        "proposal_id": proposal_id,
        "format": format,
        "content": full_md,
    }
