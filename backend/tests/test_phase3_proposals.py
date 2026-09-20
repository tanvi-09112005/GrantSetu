"""Unit tests for Phase 3/4 proposal generation, versioning, and revisions."""

from unittest.mock import patch, MagicMock
import pytest
from app.models.schemas import GenerateProposalRequest, ReviseRequest
from app.api.proposals import generate, revise, _resolve_ngo_profile


def test_proposal_version_increment_on_conflict():
    """Verify that multiple proposal generations for the same application increment the version."""
    mock_app_id = "d07db9cf-abc2-48b1-a323-7367fb4daff8"
    mock_ngo_id = "b6b3f1a9-01ed-4def-8b14-58e4c3e0863e"
    mock_grant_id = "7f3b8b1a-2c3d-4e5f-a6b7-8c9d0e1f2a3b"

    with patch("app.api.proposals._resolve_ngo_profile") as mock_resolve, \
         patch("app.api.proposals.pool") as mock_pool, \
         patch("app.api.proposals.draft_proposal") as mock_draft, \
         patch("app.api.proposals.extract_claims") as mock_extract, \
         patch("app.api.proposals.verify_claims") as mock_verify:

        mock_resolve.return_value = (mock_ngo_id, {"id": mock_ngo_id, "name": "Each One Teach One"})
        mock_pool.fetch_one.side_effect = [
            {"id": mock_grant_id, "title": "Test Grant"},  # grant lookup
            {"id": mock_app_id},  # application insert
            {"id": "prop-uuid-v2", "version": 2},  # proposal insert with version
        ]
        mock_draft.return_value = {
            "draft_sections": {"executive_summary": "Test summary", "budget": "Test budget"}
        }
        mock_extract.return_value = {"claims": ["Claim 1"]}
        mock_verify.return_value = {
            "verification_results": [{"claim_text": "Claim 1", "verdict": "supported", "confidence": 0.95}],
            "fabrication_rate": 0.0,
        }

        req = GenerateProposalRequest(
            ngo_id=mock_ngo_id,
            grant_id=mock_grant_id,
            template_type="standard",
            force_regenerate=True,
        )

        resp = generate(req, user=None)

        assert resp.proposal_id == "prop-uuid-v2"
        assert resp.revision_count == 1  # version 2 - 1 = 1 revision
        assert resp.status == "verified"
        assert len(resp.verification_results) == 1
        assert resp.fabrication_rate == 0.0

        # Confirm that the insert SQL included coalesce((select max(version) from proposals ...), 0) + 1
        insert_calls = [call for call in mock_pool.fetch_one.call_args_list if "insert into proposals" in str(call)]
        assert len(insert_calls) == 1
        sql_used = insert_calls[0][0][0]
        assert "max(version)" in sql_used
        assert "version" in sql_used


def test_revise_endpoint_accepts_sections_and_edits():
    """Verify that revise accepts payload with 'sections' and retains version."""
    with patch("app.api.proposals.pool") as mock_pool, \
         patch("app.api.proposals._fetch_verification_results") as mock_fetch:

        mock_pool.fetch_one.return_value = {
            "id": "prop-uuid-1",
            "application_id": "app-uuid-1",
            "version": 2,
            "sections": '{"executive_summary": "Old summary"}',
        }
        mock_fetch.return_value = ([], 0.0)

        req = ReviseRequest(
            sections={"executive_summary": "Updated summary by human"},
            rerun_verification=False,
        )

        resp = revise("prop-uuid-1", req)

        assert resp.proposal_id == "prop-uuid-1"
        assert resp.sections["executive_summary"] == "Updated summary by human"
        assert resp.revision_count == 1
        assert resp.status == "revised"


def test_verify_proposal_claims_endpoint():
    """Verify that verify_proposal_claims audits claims and updates status without column errors."""
    from app.api.proposals import verify_proposal_claims

    with patch("app.api.proposals.pool") as mock_pool, \
         patch("app.api.proposals.extract_claims") as mock_extract, \
         patch("app.api.proposals.verify_claims") as mock_verify:

        mock_pool.fetch_one.return_value = {
            "proposal_id": "prop-uuid-1",
            "application_id": "app-uuid-1",
            "version": 1,
            "ngo_id": "ngo-uuid-1",
            "grant_id": "grant-uuid-1",
            "sections": '{"executive_summary": "Each One Teach One has Darpan ID MH/2016/0104829"}',
            "status": "draft",
        }
        mock_extract.return_value = {"claims": ["Darpan ID is MH/2016/0104829"]}
        mock_verify.return_value = {
            "verification_results": [
                {
                    "claim_text": "Darpan ID is MH/2016/0104829",
                    "verdict": "supported",
                    "evidence_span": "MH/2016/0104829",
                    "confidence": 1.0,
                }
            ],
            "fabrication_rate": 0.0,
        }

        resp = verify_proposal_claims("prop-uuid-1", _user=None)

        assert resp.proposal_id == "prop-uuid-1"
        assert resp.status == "verified"
        assert len(resp.verification_results) == 1
        assert resp.verification_results[0].verdict == "supported"
        assert resp.fabrication_rate == 0.0

        # Assert execute was called for delete, insert verification_results, and update proposals
        update_calls = [c for c in mock_pool.execute.call_args_list if "update proposals" in str(c)]
        assert len(update_calls) == 1
        assert "status = 'verified'" in str(update_calls[0])

