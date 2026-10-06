"""Unit tests for Task 5: Interactive Revision Agent (Human-in-the-Loop) & Targeted Verification."""

from unittest.mock import MagicMock, patch
import pytest

from app.models.schemas import (
    RefineSectionRequest,
    RefineSectionResponse,
    ApplySectionRevisionRequest,
    ClaimVerdict,
)
from app.api.proposals import (
    refine_section,
    apply_section_revision,
    _verify_single_section_claims,
)


def test_refine_section_preview_only():
    """Verify refine_section with preview_only=True returns diff candidate without mutating DB."""
    with patch("app.api.proposals.pool") as mock_pool, \
         patch("app.services.llm.invoke_with_fallback") as mock_llm:

        mock_pool.fetch_one.return_value = {
            "id": "prop-uuid-1",
            "application_id": "app-uuid-1",
            "version": 1,
            "sections": '{"problem_statement": "Old general problem statement text."}',
            "status": "draft",
            "ngo_id": "ngo-uuid-1",
            "grant_id": "grant-uuid-1",
            "grant_title": "CSR Education Fund",
            "funder_name": "Tata Trusts",
            "ngo_name": "Each One Teach One",
            "ngo_mission": "Education for all",
            "darpan_id": "MH/2016/0104829",
            "registered_on": "2016-01-01",
            "tax_exemption": "12A & 80G",
            "fcra_status": "never_held",
            "location": "Mumbai",
        }
        mock_llm.return_value = "Refined problem statement emphasizing rural girls' secondary school dropouts."

        req = RefineSectionRequest(
            section_key="problem_statement",
            instruction="Make this emphasize rural girls' dropouts",
            temperature=0.2,
            preview_only=True,
        )

        resp = refine_section("prop-uuid-1", req, _user=None)

        assert isinstance(resp, RefineSectionResponse)
        assert resp.section_key == "problem_statement"
        assert resp.original_text == "Old general problem statement text."
        assert "rural girls" in resp.refined_text
        assert resp.proposal is None

        # Verify pool.execute was NOT called to update proposals table
        update_calls = [c for c in mock_pool.execute.call_args_list if "update proposals" in str(c)]
        assert len(update_calls) == 0


def test_apply_section_revision_and_targeted_verification():
    """Verify apply_section_revision saves the revised section, increments version, and runs targeted verification."""
    with patch("app.api.proposals.pool") as mock_pool, \
         patch("app.api.proposals._verify_single_section_claims") as mock_targeted_verify:

        mock_pool.fetch_one.return_value = {
            "id": "prop-uuid-1",
            "application_id": "app-uuid-1",
            "version": 1,
            "sections": '{"problem_statement": "Old text", "budget": "Old budget"}',
            "status": "verified",
            "ngo_id": "ngo-uuid-1",
            "grant_id": "grant-uuid-1",
            "grant_title": "CSR Education Fund",
            "funder_name": "Tata Trusts",
            "ngo_name": "Each One Teach One",
            "ngo_mission": "Education for all",
            "darpan_id": "MH/2016/0104829",
            "registered_on": "2016-01-01",
            "tax_exemption": "12A & 80G",
            "fcra_status": "never_held",
            "location": "Mumbai",
        }

        updated_verdicts = [
            ClaimVerdict(
                section_key="problem_statement",
                claim_text="Program targets 500 rural girls in aspirational districts",
                verdict="supported",
                evidence_span="Document chunk #2 confirms rural student outreach",
                confidence=0.95,
            )
        ]
        mock_targeted_verify.return_value = (updated_verdicts, 0.0)

        req = ApplySectionRevisionRequest(
            section_key="problem_statement",
            refined_text="Program targets 500 rural girls in aspirational districts.",
            rerun_verification=True,
        )

        resp = apply_section_revision("prop-uuid-1", req, _user=None)

        assert resp.proposal_id == "prop-uuid-1"
        assert resp.revision_count == 1  # version incremented from 1 to 2 -> revision_count = 1
        assert resp.sections["problem_statement"] == "Program targets 500 rural girls in aspirational districts."
        assert len(resp.verification_results) == 1
        assert resp.verification_results[0].section_key == "problem_statement"
        assert resp.fabrication_rate == 0.0
        assert resp.status == "revised"

        # Verify pool.execute updated sections and version
        update_calls = [c for c in mock_pool.execute.call_args_list if "update proposals" in str(c)]
        assert len(update_calls) == 1
        assert "version = %s" in str(update_calls[0])


def test_verify_single_section_claims_targeted_delete_and_insert():
    """Verify _verify_single_section_claims targets only the specified section_key in verification_results."""
    with patch("app.api.proposals.pool") as mock_pool, \
         patch("app.api.proposals.extract_claims") as mock_extract, \
         patch("app.api.proposals.verify_claims") as mock_verify:

        mock_extract.return_value = {
            "claims": [
                {"section": "line_item_budget", "claim_text": "Admin overhead is ₹45,000", "type": "numeric"}
            ]
        }
        mock_verify.return_value = {
            "verification_results": [
                {
                    "claim_text": "Admin overhead is ₹45,000",
                    "verdict": "supported",
                    "evidence_span": "Audited expenditure schedule",
                    "confidence": 0.92,
                }
            ],
            "fabrication_rate": 0.0,
        }
        mock_pool.fetch_all.return_value = [
            {
                "section_key": "line_item_budget",
                "claim_text": "Admin overhead is ₹45,000",
                "verdict": "supported",
                "evidence_span": "Audited expenditure schedule",
                "confidence": 0.92,
            }
        ]

        verdicts, rate = _verify_single_section_claims(
            proposal_id="prop-uuid-1",
            section_key="line_item_budget",
            section_content="Admin overhead is ₹45,000.",
            ngo_id="ngo-uuid-1",
            ngo_profile={"name": "Each One Teach One"},
        )

        assert len(verdicts) == 1
        assert verdicts[0].section_key == "line_item_budget"
        assert rate == 0.0

        # Check delete targeted the section_key
        delete_calls = [c for c in mock_pool.execute.call_args_list if "delete from verification_results" in str(c)]
        assert len(delete_calls) == 1
        assert "section_key = %s" in str(delete_calls[0])

        # Check insert included section_key
        insert_calls = [c for c in mock_pool.execute.call_args_list if "insert into verification_results" in str(c)]
        assert len(insert_calls) == 1
        assert "line_item_budget" in str(insert_calls[0])
