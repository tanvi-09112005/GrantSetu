"""Proposal generation, revision and export routes (Phase 3 & 4)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import tempfile
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import maybe_user, owned_ngo
from app.db import pool
from app.graph.nodes.draft import SECTION_TITLES, TEMPLATES, draft_proposal
from app.graph.nodes.extract_claims import extract_claims
from app.graph.nodes.verify import verify_claims
from app.models.schemas import (
    ApplySectionRevisionRequest,
    BatchGenerateRequest,
    ClaimVerdict,
    DropClaimRequest,
    EditClaimRequest,
    GenerateProposalRequest,
    ProposalResponse,
    RefineSectionRequest,
    RefineSectionResponse,
    ReviseRequest,
)
from app.services.export import generate_proposal_docx, generate_proposal_pdf
from app.services.verification_gate import ensure_verified

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
    """Retrieve persisted verification results with linked document evidence metadata."""
    rows = pool.fetch_all(
        """
        select vr.id, vr.section_key, vr.claim_text, vr.verdict, vr.evidence_span, vr.evidence_chunk_id, vr.confidence,
               dc.chunk_text, dc.section_title as chunk_section, dc.chunk_index,
               d.id as document_id, d.file_url as document_name, d.doc_type
        from verification_results vr
        left join document_chunks dc on dc.id = vr.evidence_chunk_id
        left join ngo_documents d on d.id = dc.document_id
        where vr.proposal_id = %s
        order by vr.created_at asc
        """,
        (proposal_id,),
    )
    if not rows:
        return [], 0.0
    verdicts = [
        ClaimVerdict(
            id=str(r["id"]) if r.get("id") else None,
            section_key=r.get("section_key"),
            claim_text=r["claim_text"],
            verdict=r["verdict"],
            evidence_span=r.get("evidence_span"),
            evidence_chunk_id=str(r["evidence_chunk_id"]) if r.get("evidence_chunk_id") else None,
            confidence=r.get("confidence", 0.95),
            document_name=r.get("document_name") or ("NITI Aayog Darpan & Compliance Dossier" if r.get("verdict") == "supported" else None),
            document_id=str(r["document_id"]) if r.get("document_id") else None,
            doc_type=r.get("doc_type") or ("Statutory Registry" if r.get("verdict") == "supported" else None),
            chunk_section=r.get("chunk_section") or "Compliance Dossier",
            chunk_text=r.get("chunk_text") or r.get("evidence_span"),
        )
        for r in rows
    ]
    unsupported = sum(1 for v in verdicts if v.verdict == "unsupported")
    rate = round(unsupported / len(verdicts), 3) if verdicts else 0.0
    return verdicts, rate


def _verify_single_section_claims(
    proposal_id: str,
    section_key: str,
    section_content: str,
    ngo_id: str,
    ngo_profile: dict,
) -> tuple[list[ClaimVerdict], float]:
    """Extract and verify claims for ONLY a single revised section to conserve LLM quota."""
    try:
        section_state = {
            "ngo_id": ngo_id,
            "draft_sections": {section_key: section_content},
            "ngo_profile": ngo_profile,
        }
        claims_state = extract_claims(section_state)
        claims = claims_state.get("claims", [])
        for c in claims:
            c["section"] = section_key
            c["section_key"] = section_key

        verify_state = verify_claims({
            "ngo_id": ngo_id,
            "claims": claims,
            "ngo_profile": ngo_profile,
        })
        results = verify_state.get("verification_results", [])

        # Delete existing audit rows for this specific section
        pool.execute(
            "delete from verification_results where proposal_id = %s and section_key = %s",
            (proposal_id, section_key),
        )

        for r in results:
            ev_chunk_id = r.get("evidence_chunk_id")
            if ev_chunk_id:
                try:
                    uuid.UUID(str(ev_chunk_id))
                except Exception:
                    ev_chunk_id = None
            pool.execute(
                """
                insert into verification_results (proposal_id, section_key, claim_text, verdict, evidence_span, evidence_chunk_id, confidence, model_used)
                values (%s, %s, %s, %s, %s, %s, %s, 'gemini-3.6-flash')
                """,
                (proposal_id, section_key, r["claim_text"], r["verdict"], r.get("evidence_span"), ev_chunk_id, r.get("confidence", 0.9)),
            )

        logger.info(
            "Targeted section verification completed for proposal %s section %s: %d claims re-audited",
            proposal_id,
            section_key,
            len(results),
        )
    except Exception as e:
        logger.warning("Targeted section verification encountered error: %s", e)

    return _fetch_verification_results(proposal_id)


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

    # Verification gate: only document-matched NGOs may draft proposals.
    ensure_verified(ngo_profile)

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
                insert into verification_results (proposal_id, section_key, claim_text, verdict, evidence_span, confidence, model_used)
                values (%s, %s, %s, %s, %s, %s, 'gemini-3.5-flash')
                """,
                (proposal_id, r.get("section") or r.get("section_key"), r["claim_text"], r["verdict"], r.get("evidence_span"), r.get("confidence", 0.9)),
            )

        verdicts = [
            ClaimVerdict(
                section_key=r.get("section") or r.get("section_key"),
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

    # Verification gate, checked ONCE up front. The loop below catches every
    # exception per grant, so a 403 raised inside generate() would be swallowed
    # and the caller would just get an empty list.
    _, batch_profile = _resolve_ngo_profile(payload.ngo_id)
    ensure_verified(batch_profile)

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
        ev_chunk_id = r.get("evidence_chunk_id")
        if ev_chunk_id:
            try:
                uuid.UUID(str(ev_chunk_id))
            except Exception:
                ev_chunk_id = None
        pool.execute(
            """
            insert into verification_results (proposal_id, section_key, claim_text, verdict, evidence_span, evidence_chunk_id, confidence, model_used)
            values (%s, %s, %s, %s, %s, %s, %s, 'gemini-3.6-flash')
            """,
            (
                proposal_id,
                r.get("section") or r.get("section_key"),
                r["claim_text"],
                r["verdict"],
                r.get("evidence_span"),
                ev_chunk_id,
                r.get("confidence", 0.95),
            ),
        )

    pool.execute(
        "update proposals set status = 'verified', updated_at = now() where id = %s",
        (proposal_id,),
    )

    verdicts, rate = _fetch_verification_results(proposal_id)
    if not verdicts and results:
        verdicts = [
            ClaimVerdict(
                section_key=r.get("section") or r.get("section_key"),
                claim_text=r["claim_text"],
                verdict=r["verdict"],
                evidence_span=r.get("evidence_span"),
                evidence_chunk_id=str(r["evidence_chunk_id"]) if r.get("evidence_chunk_id") else None,
                confidence=r.get("confidence", 0.95),
                document_name=r.get("document_name") or ("NITI Aayog Darpan & Compliance Dossier" if r.get("verdict") == "supported" else None),
                doc_type=r.get("doc_type") or ("Statutory Registry" if r.get("verdict") == "supported" else None),
                chunk_section=r.get("chunk_section") or "Compliance Dossier",
                chunk_text=r.get("chunk_text") or r.get("evidence_span"),
            )
            for r in results
        ]
        rate = verify_state.get("fabrication_rate", 0.0)

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


@router.get("/{proposal_id}/export-pdf")
def export_pdf(
    proposal_id: str,
    _user: dict | None = Depends(maybe_user),
):
    """Generate and download a submission-ready, institutional PDF dossier with letterhead, TOC, and stamped sign-off."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.sections,
               g.id as grant_id, g.title as grant_title, g.funder_name, g.funder_type, g.description as grant_desc,
               n.id as ngo_id, n.name as ngo_name, n.mission as ngo_mission, n.darpan_id, n.location,
               n.reg_12a, n.reg_80g, n.has_12a, n.has_80g, n.has_fcra, n.fcra_status
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

    tax_exemption = (
        "12A & 80G Certified"
        if (row.get("has_12a") or row.get("reg_12a") or row.get("has_80g") or row.get("reg_80g"))
        else "Registered Non-Profit Entity"
    )

    ngo_profile = {
        "id": str(row["ngo_id"]),
        "name": row["ngo_name"],
        "mission": row["ngo_mission"],
        "darpan_id": row["darpan_id"],
        "location": row["location"],
        "tax_exemption": tax_exemption,
        "fcra_status": row.get("fcra_status") or "Compliant",
    }
    grant = {
        "id": str(row["grant_id"]),
        "title": row["grant_title"],
        "funder_name": row["funder_name"],
        "funder_type": row["funder_type"],
        "description": row["grant_desc"],
    }
    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    safe_ngo = re.sub(r"[^\w\-]", "_", row["ngo_name"] or "NGO")[:20]
    safe_grant = re.sub(r"[^\w\-]", "_", row["grant_title"] or "Grant")[:25]
    pdf_filename = f"Grant_Proposal_{safe_ngo}_{safe_grant}.pdf"
    pdf_path = Path(tempfile.gettempdir()) / f"GrantSetu_Proposal_{proposal_id[:8]}.pdf"

    generate_proposal_pdf(
        ngo_profile=ngo_profile,
        grant=grant,
        draft_sections=sections,
        output_path=pdf_path,
        ngo_id=str(row["ngo_id"]),
        proposal_id=proposal_id,
    )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_filename,
    )


@router.get("/{proposal_id}/export-docx")
def export_docx(
    proposal_id: str,
    _user: dict | None = Depends(maybe_user),
):
    """Generate and download an editable Microsoft Word (.docx) document with styled tables and signature block."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.sections,
               g.id as grant_id, g.title as grant_title, g.funder_name, g.funder_type, g.description as grant_desc,
               n.id as ngo_id, n.name as ngo_name, n.mission as ngo_mission, n.darpan_id, n.location,
               n.reg_12a, n.reg_80g, n.has_12a, n.has_80g, n.has_fcra, n.fcra_status
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

    tax_exemption = (
        "12A & 80G Certified"
        if (row.get("has_12a") or row.get("reg_12a") or row.get("has_80g") or row.get("reg_80g"))
        else "Registered Non-Profit Entity"
    )

    ngo_profile = {
        "id": str(row["ngo_id"]),
        "name": row["ngo_name"],
        "mission": row["ngo_mission"],
        "darpan_id": row["darpan_id"],
        "location": row["location"],
        "tax_exemption": tax_exemption,
        "fcra_status": row.get("fcra_status") or "Compliant",
    }
    grant = {
        "id": str(row["grant_id"]),
        "title": row["grant_title"],
        "funder_name": row["funder_name"],
        "funder_type": row["funder_type"],
        "description": row["grant_desc"],
    }
    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    safe_ngo = re.sub(r"[^\w\-]", "_", row["ngo_name"] or "NGO")[:20]
    safe_grant = re.sub(r"[^\w\-]", "_", row["grant_title"] or "Grant")[:25]
    docx_filename = f"Grant_Proposal_{safe_ngo}_{safe_grant}.docx"
    docx_path = Path(tempfile.gettempdir()) / f"GrantSetu_Proposal_{proposal_id[:8]}.docx"

    generate_proposal_docx(
        ngo_profile=ngo_profile,
        grant=grant,
        draft_sections=sections,
        output_path=docx_path,
        ngo_id=str(row["ngo_id"]),
        proposal_id=proposal_id,
    )

    return FileResponse(
        path=str(docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=docx_filename,
    )


@router.post("/{proposal_id}/refine-section", response_model=ProposalResponse | RefineSectionResponse)
def refine_section(
    proposal_id: str,
    payload: RefineSectionRequest,
    _user: dict | None = Depends(maybe_user),
) -> ProposalResponse | RefineSectionResponse:
    """Targeted refinement of a single proposal section using LLM instruction."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.application_id, p.version, p.sections, p.status,
               a.ngo_id, a.grant_id,
               g.title as grant_title, g.funder_name,
               n.name as ngo_name, n.mission as ngo_mission,
               n.darpan_id, n.registered_on, n.reg_12a, n.reg_80g, n.fcra_status, n.location
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

    row["tax_exemption"] = (
        "12A & 80G Certified"
        if (row.get("reg_12a") or row.get("reg_80g") or row.get("has_12a") or row.get("has_80g"))
        else "Registered Non-Profit"
    )

    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    current_text = payload.current_content if payload.current_content is not None else sections.get(payload.section_key, "")
    section_title = SECTION_TITLES.get(payload.section_key, payload.section_key.replace("_", " ").title())

    prompt = f"""You are an elite institutional grant proposal writer in India.
Refine and enhance the following specific section of a grant proposal for {row['ngo_name']}.

Target Grant: "{row['grant_title']}" (Funder: {row['funder_name']})
Target Section: {section_title} (Key: "{payload.section_key}")

CURRENT SECTION CONTENT:
{current_text if current_text else "[Section is currently empty]"}

USER INSTRUCTION FOR REFINEMENT:
{payload.instruction}

Rules:
1. Maintain or enhance factual grounding and high professional institutional quality.
2. If improving budget or matrices, format them as structured Markdown tables with exact column headers.
3. Incorporate the user's specific instruction accurately.
4. Output ONLY the refined section markdown content (do NOT include JSON wrappers, markdown fences ```markdown, or conversational preamble)."""

    try:
        from app.services.llm import invoke_with_fallback
        refined_content = invoke_with_fallback(prompt, tier="flash", temperature=payload.temperature)
        if refined_content and refined_content.strip():
            cleaned = refined_content.strip()
            # Strip accidental ```markdown fences if LLM wrapped it
            if cleaned.startswith("```markdown"):
                cleaned = cleaned[11:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        else:
            cleaned = current_text
    except Exception as e:
        logger.error("Section refinement failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Refinement failed: {e}")

    # If preview_only is True, return candidate diff preview without persisting to DB
    if payload.preview_only:
        return RefineSectionResponse(
            proposal_id=proposal_id,
            section_key=payload.section_key,
            original_text=current_text,
            refined_text=cleaned,
            instruction=payload.instruction,
            proposal=None,
        )

    # Otherwise apply immediately and run targeted verification on only this section
    sections[payload.section_key] = cleaned
    new_version = int(row.get("version") or 1) + 1
    pool.execute(
        "update proposals set sections = %s, version = %s, updated_at = now() where id = %s",
        (json.dumps(sections), new_version, proposal_id),
    )

    verdicts, rate = _verify_single_section_claims(
        proposal_id=proposal_id,
        section_key=payload.section_key,
        section_content=cleaned,
        ngo_id=str(row["ngo_id"]),
        ngo_profile=row,
    )

    return ProposalResponse(
        proposal_id=proposal_id,
        application_id=str(row["application_id"]),
        grant_id=str(row["grant_id"]),
        ngo_id=str(row["ngo_id"]),
        template_type="standard",
        sections=sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=max(0, new_version - 1),
        status="revised",
    )


@router.post("/{proposal_id}/apply-section-revision", response_model=ProposalResponse)
def apply_section_revision(
    proposal_id: str,
    payload: ApplySectionRevisionRequest,
    _user: dict | None = Depends(maybe_user),
) -> ProposalResponse:
    """Accept and apply a reviewed section revision with targeted re-verification."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.application_id, p.version, p.sections, p.status,
               a.ngo_id, a.grant_id,
               g.title as grant_title, g.funder_name,
               n.name as ngo_name, n.mission as ngo_mission,
               n.darpan_id, n.registered_on, n.reg_12a, n.reg_80g, n.fcra_status, n.location
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

    row["tax_exemption"] = (
        "12A & 80G Certified"
        if (row.get("reg_12a") or row.get("reg_80g") or row.get("has_12a") or row.get("has_80g"))
        else "Registered Non-Profit"
    )

    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    sections[payload.section_key] = payload.refined_text
    new_version = int(row.get("version") or 1) + 1

    pool.execute(
        "update proposals set sections = %s, version = %s, updated_at = now() where id = %s",
        (json.dumps(sections), new_version, proposal_id),
    )

    if payload.rerun_verification:
        verdicts, rate = _verify_single_section_claims(
            proposal_id=proposal_id,
            section_key=payload.section_key,
            section_content=payload.refined_text,
            ngo_id=str(row["ngo_id"]),
            ngo_profile=row,
        )
    else:
        verdicts, rate = _fetch_verification_results(proposal_id)

    return ProposalResponse(
        proposal_id=proposal_id,
        application_id=str(row["application_id"]),
        grant_id=str(row["grant_id"]),
        ngo_id=str(row["ngo_id"]),
        template_type="standard",
        sections=sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=max(0, new_version - 1),
        status="revised",
    )


@router.post("/{proposal_id}/edit-claim", response_model=ProposalResponse)
def edit_claim(
    proposal_id: str,
    payload: EditClaimRequest,
    _user: dict | None = Depends(maybe_user),
) -> ProposalResponse:
    """Manually update an unsupported or imprecise claim in a proposal section."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.application_id, p.version, p.sections, p.status,
               a.ngo_id, a.grant_id,
               g.title as grant_title, g.funder_name,
               n.name as ngo_name, n.mission as ngo_mission,
               n.darpan_id, n.registered_on, n.reg_12a, n.reg_80g, n.fcra_status, n.location
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

    row["tax_exemption"] = (
        "12A & 80G Certified"
        if (row.get("reg_12a") or row.get("reg_80g") or row.get("has_12a") or row.get("has_80g"))
        else "Registered Non-Profit"
    )

    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    sec_key = payload.section_key
    if sec_key not in sections:
        for k in sections.keys():
            if k == sec_key or k.lower() == sec_key.lower():
                sec_key = k
                break
        else:
            raise HTTPException(status_code=400, detail=f"Section '{payload.section_key}' not found in proposal.")

    current_text = sections.get(sec_key, "")
    old_target = payload.old_text.strip()
    new_target = payload.new_text.strip()

    if old_target in current_text:
        updated_text = current_text.replace(old_target, new_target, 1)
    else:
        pattern = re.escape(old_target)
        pattern = re.sub(r'\\s+', r'\\s+', pattern)
        matched = re.search(pattern, current_text, flags=re.IGNORECASE)
        if matched:
            updated_text = current_text[:matched.start()] + new_target + current_text[matched.end():]
        else:
            updated_text = current_text + "\n\n" + new_target

    sections[sec_key] = updated_text
    new_version = int(row.get("version") or 1) + 1

    pool.execute(
        "update proposals set sections = %s, version = %s, updated_at = now() where id = %s",
        (json.dumps(sections), new_version, proposal_id),
    )

    verdicts, rate = _verify_single_section_claims(
        proposal_id=proposal_id,
        section_key=sec_key,
        section_content=updated_text,
        ngo_id=str(row["ngo_id"]),
        ngo_profile=row,
    )

    return ProposalResponse(
        proposal_id=proposal_id,
        application_id=str(row["application_id"]),
        grant_id=str(row["grant_id"]),
        ngo_id=str(row["ngo_id"]),
        template_type="standard",
        sections=sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=max(0, new_version - 1),
        status="revised",
    )


@router.post("/{proposal_id}/drop-claim", response_model=ProposalResponse)
def drop_claim(
    proposal_id: str,
    payload: DropClaimRequest,
    _user: dict | None = Depends(maybe_user),
) -> ProposalResponse:
    """Auto-remove an unsupported/hallucinated claim sentence from the proposal."""
    row = pool.fetch_one(
        """
        select p.id as proposal_id, p.application_id, p.version, p.sections, p.status,
               a.ngo_id, a.grant_id,
               g.title as grant_title, g.funder_name,
               n.name as ngo_name, n.mission as ngo_mission,
               n.darpan_id, n.registered_on, n.reg_12a, n.reg_80g, n.fcra_status, n.location
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

    row["tax_exemption"] = (
        "12A & 80G Certified"
        if (row.get("reg_12a") or row.get("reg_80g") or row.get("has_12a") or row.get("has_80g"))
        else "Registered Non-Profit"
    )

    sections = row["sections"]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception:
            sections = {}

    sec_key = payload.section_key
    if sec_key not in sections:
        for k in sections.keys():
            if k == sec_key or k.lower() == sec_key.lower():
                sec_key = k
                break
        else:
            raise HTTPException(status_code=400, detail=f"Section '{payload.section_key}' not found in proposal.")

    current_text = sections.get(sec_key, "")
    target = payload.claim_text.strip()

    if target in current_text:
        updated_text = current_text.replace(target, "", 1)
    else:
        pattern = re.escape(target)
        pattern = re.sub(r'\\s+', r'\\s+', pattern)
        matched = re.search(pattern, current_text, flags=re.IGNORECASE)
        if matched:
            updated_text = current_text[:matched.start()] + current_text[matched.end():]
        else:
            updated_text = current_text

    updated_text = re.sub(r'\s{2,}', ' ', updated_text)
    updated_text = re.sub(r'\.\s*\.', '.', updated_text).strip()

    sections[sec_key] = updated_text
    new_version = int(row.get("version") or 1) + 1

    pool.execute(
        "update proposals set sections = %s, version = %s, updated_at = now() where id = %s",
        (json.dumps(sections), new_version, proposal_id),
    )

    verdicts, rate = _verify_single_section_claims(
        proposal_id=proposal_id,
        section_key=sec_key,
        section_content=updated_text,
        ngo_id=str(row["ngo_id"]),
        ngo_profile=row,
    )

    return ProposalResponse(
        proposal_id=proposal_id,
        application_id=str(row["application_id"]),
        grant_id=str(row["grant_id"]),
        ngo_id=str(row["ngo_id"]),
        template_type="standard",
        sections=sections,
        verification_results=verdicts,
        fabrication_rate=rate,
        revision_count=max(0, new_version - 1),
        status="revised",
    )


@router.get("/{proposal_id}/evidence-chunk/{chunk_id}")
def get_evidence_chunk(
    proposal_id: str,
    chunk_id: str,
    _user: dict | None = Depends(maybe_user),
) -> dict[str, Any]:
    """Retrieve full text and metadata for a specific evidence chunk from the Document Vault."""
    row = pool.fetch_one(
        """
        select dc.id as chunk_id, dc.chunk_text, dc.section_title, dc.chunk_index,
               d.id as document_id, d.file_url as document_name, d.doc_type
        from document_chunks dc
        left join ngo_documents d on d.id = dc.document_id
        where dc.id = %s
        """,
        (chunk_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Evidence chunk not found")

    return {
        "chunk_id": str(row["chunk_id"]),
        "chunk_text": row["chunk_text"],
        "section_title": row.get("section_title") or "Document Excerpt",
        "chunk_index": row.get("chunk_index", 0),
        "document_id": str(row["document_id"]) if row.get("document_id") else None,
        "document_name": row.get("document_name") or "NGO Vault Document",
        "doc_type": row.get("doc_type") or "Document Proof",
    }

