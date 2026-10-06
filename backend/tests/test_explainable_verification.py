"""Unit tests for Task 6: Explainable Verification, Evidence Highlighting, and Claim Remediation."""

from unittest.mock import MagicMock, patch
import json
import uuid
import pytest

from app.models.schemas import (
    ClaimVerdict,
    DropClaimRequest,
    EditClaimRequest,
    ProposalResponse,
)
from app.api.proposals import (
    edit_claim,
    drop_claim,
    get_evidence_chunk,
    _fetch_verification_results,
    _verify_single_section_claims,
)
from app.graph.nodes.verify import _find_best_chunk


def test_edit_claim_updates_section_and_triggers_verification():
    """Verify edit_claim replaces unsupported claim text, increments proposal version, and re-verifies section."""
    with patch("app.api.proposals.pool") as mock_pool, \
         patch("app.api.proposals._verify_single_section_claims") as mock_verify:

        mock_pool.fetch_one.return_value = {
            "proposal_id": "prop-123",
            "application_id": "app-123",
            "version": 2,
            "sections": json.dumps({
                "problem_statement": "The dropout rate is 45% among adolescents in rural Nashik.",
                "executive_summary": "Summary text here.",
            }),
            "status": "verified",
            "ngo_id": "ngo-123",
            "grant_id": "grant-123",
            "grant_title": "Tribal Welfare Scheme",
            "funder_name": "Ministry of Tribal Affairs",
            "ngo_name": "Samarpan Foundation",
            "ngo_mission": "Tribal education and welfare",
            "darpan_id": "MH/2018/0192837",
            "registered_on": "2018-04-12",
            "reg_12a": "12A-123",
            "reg_80g": "80G-123",
            "fcra_status": "never_held",
            "location": "Nashik, Maharashtra",
        }

        mock_verify.return_value = (
            [
                ClaimVerdict(
                    claim_text="The dropout rate is 28% among adolescents according to UDISE+ data.",
                    verdict="supported",
                    evidence_span="According to UDISE+ 2022-23, adolescent dropout is 28.2%",
                    confidence=0.98,
                    document_name="Samarpan_Annual_Report_2023-24.pdf",
                    doc_type="annual_report",
                    chunk_section="Educational Impact",
                )
            ],
            0.0,
        )

        req = EditClaimRequest(
            section_key="problem_statement",
            old_text="The dropout rate is 45% among adolescents in rural Nashik.",
            new_text="The dropout rate is 28% among adolescents according to UDISE+ data.",
        )

        resp = edit_claim("prop-123", req, _user=None)

        assert isinstance(resp, ProposalResponse)
        assert resp.proposal_id == "prop-123"
        assert resp.revision_count == 2  # new_version was 3, revision_count = 3 - 1 = 2
        assert "28% among adolescents" in resp.sections["problem_statement"]
        assert "45%" not in resp.sections["problem_statement"]
        assert len(resp.verification_results) == 1
        assert resp.verification_results[0].verdict == "supported"
        assert resp.fabrication_rate == 0.0

        # Verify pool.execute updated sections in proposals table
        update_calls = [c for c in mock_pool.execute.call_args_list if "update proposals" in str(c)]
        assert len(update_calls) == 1


def test_drop_claim_removes_sentence_and_reverifies():
    """Verify drop_claim removes unsupported sentence from section, cleans whitespace, and re-verifies."""
    with patch("app.api.proposals.pool") as mock_pool, \
         patch("app.api.proposals._verify_single_section_claims") as mock_verify:

        mock_pool.fetch_one.return_value = {
            "proposal_id": "prop-123",
            "application_id": "app-123",
            "version": 1,
            "sections": json.dumps({
                "problem_statement": "Valid needs assessment. Hallucinated claim that organization trained 50,000 teachers in 2020. Additional ongoing community work.",
            }),
            "status": "verified",
            "ngo_id": "ngo-123",
            "grant_id": "grant-123",
            "grant_title": "Tribal Welfare Scheme",
            "funder_name": "Ministry of Tribal Affairs",
            "ngo_name": "Samarpan Foundation",
            "ngo_mission": "Tribal education and welfare",
            "darpan_id": "MH/2018/0192837",
            "registered_on": "2018-04-12",
            "reg_12a": "12A-123",
            "reg_80g": "80G-123",
            "fcra_status": "never_held",
            "location": "Nashik, Maharashtra",
        }

        mock_verify.return_value = ([], 0.0)

        req = DropClaimRequest(
            section_key="problem_statement",
            claim_text="Hallucinated claim that organization trained 50,000 teachers in 2020.",
        )

        resp = drop_claim("prop-123", req, _user=None)

        assert isinstance(resp, ProposalResponse)
        assert "50,00,000" not in resp.sections["problem_statement"]
        assert "Valid needs assessment" in resp.sections["problem_statement"]
        assert "Additional ongoing community work." in resp.sections["problem_statement"]
        assert "50,000 teachers" not in resp.sections["problem_statement"]


def test_get_evidence_chunk_retrieves_vault_metadata():
    """Verify get_evidence_chunk joins document_chunks and ngo_documents."""
    with patch("app.api.proposals.pool") as mock_pool:
        chunk_uuid = str(uuid.uuid4())
        doc_uuid = str(uuid.uuid4())
        mock_pool.fetch_one.return_value = {
            "chunk_id": chunk_uuid,
            "chunk_text": "Samarpan Foundation holds valid 12A (AAATS1234F) and 80G tax exemptions granted by CIT(E) Pune.",
            "section_title": "Tax Compliance & Statutory Status",
            "chunk_index": 2,
            "document_id": doc_uuid,
            "document_name": "12A_80G_Order_Samarpan.pdf",
            "doc_type": "12a_80g",
        }

        res = get_evidence_chunk("prop-123", chunk_uuid, _user=None)

        assert res["chunk_id"] == chunk_uuid
        assert "AAATS1234F" in res["chunk_text"]
        assert res["document_name"] == "12A_80G_Order_Samarpan.pdf"
        assert res["doc_type"] == "12a_80g"
        assert res["section_title"] == "Tax Compliance & Statutory Status"


def test_find_best_chunk_keyword_overlap_matching():
    """Verify _find_best_chunk matches exact evidence sentence to its parent chunk and document."""
    chunk_1_id = str(uuid.uuid4())
    chunk_2_id = str(uuid.uuid4())

    chunks = [
        {
            "chunk_id": chunk_1_id,
            "chunk_text": "General overview of geographical presence in Maharashtra and Madhya Pradesh.",
            "document_name": "Intro_Brochure.pdf",
            "doc_type": "program_report",
            "section_title": "Introduction",
        },
        {
            "chunk_id": chunk_2_id,
            "chunk_text": "The foundation's total audited program expenditure for FY 2023-24 stood at INR 42,50,000 across 3 rural districts.",
            "document_name": "Audited_Balance_Sheet_2023-24.pdf",
            "doc_type": "audited_balance_sheet",
            "section_title": "Financial Schedule III",
        },
    ]

    best = _find_best_chunk(chunks, "audited program expenditure for FY 2023-24 was INR 42,50,000")
    assert best is not None
    assert best["chunk_id"] == chunk_2_id
    assert best["document_name"] == "Audited_Balance_Sheet_2023-24.pdf"
    assert best["doc_type"] == "audited_balance_sheet"
