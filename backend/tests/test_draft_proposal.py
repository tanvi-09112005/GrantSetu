"""Isolated test for draft_proposal — no live DB, no live Gemini calls.

Mocks app.db.pool and app.services.llm.get_llm so this runs offline and fast.
Mirrors the mocking style expected for test_phase2_discovery_eligibility.py.

Updated for the batched version of draft_proposal: sections are now drafted
in up to 2 Gemini calls (grouped by temperature tier) instead of one call
per section, so mocked LLM responses must be JSON, and call-count
assertions reflect the smaller number of calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.graph.nodes.draft import DEFAULT_SECTIONS, draft_proposal
from app.graph.state import initial_state

FAKE_NGO_PROFILE = {
    "id": "ngo-1",
    "name": "Sample Trust",
    "mission": "Educating underprivileged children",
    "sectors": ["education"],
}

FAKE_GRANT = {
    "id": "grant-1",
    "title": "Education Empowerment Grant",
    "funder_name": "Example Foundation",
    "description": "Supports NGOs working in child education.",
}

FAKE_CHUNKS = [
    {"chunk_text": "In FY2025 we spent INR 12,00,000 on classroom infrastructure."},
    {"chunk_text": "The Trust was registered under the Societies Act in 2011."},
]


@pytest.fixture
def base_state():
    state = initial_state(ngo_id="ngo-1", selected_grant_id="grant-1")
    state["ngo_profile"] = FAKE_NGO_PROFILE
    return state


def _mock_llm_response(text_value: str) -> MagicMock:
    """A batched JSON response covering every possible section key.

    draft_proposal only reads the keys it actually requested in that call, so
    mapping every DEFAULT_SECTIONS key to the same value works regardless of
    which subset (low-temp group / high-temp group / a single revised
    section) is being drafted in a given test.
    """
    payload = {key: text_value for key in DEFAULT_SECTIONS}
    resp = MagicMock()
    resp.content = json.dumps(payload)
    return resp


@patch("app.graph.nodes.draft.get_llm")
@patch("app.graph.nodes.draft.embed_query")
@patch("app.graph.nodes.draft.pool")
def test_draft_proposal_fills_all_default_sections(
    mock_pool, mock_embed_query, mock_get_llm, base_state
):
    mock_pool.fetch_one.return_value = FAKE_GRANT
    mock_pool.fetch_all.return_value = FAKE_CHUNKS
    mock_embed_query.return_value = [0.0] * 1024

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("Drafted section text.")
    mock_get_llm.return_value = mock_llm

    result = draft_proposal(base_state)

    assert set(result["draft_sections"].keys()) == set(DEFAULT_SECTIONS)
    assert all(text == "Drafted section text." for text in result["draft_sections"].values())
    assert result["sections_to_revise"] == []
    assert result["status"] == "drafted"
    assert result["errors"] == []

    # retrieval is still per-section (separate, higher-quota embedding API)
    assert mock_embed_query.call_count == len(DEFAULT_SECTIONS)
    # drafting is now batched: 1 call for the low-temp group, 1 for the
    # high-temp group -- 2 total instead of 8.
    assert mock_llm.invoke.call_count == 2


@patch("app.graph.nodes.draft.get_llm")
@patch("app.graph.nodes.draft.embed_query")
@patch("app.graph.nodes.draft.pool")
def test_draft_proposal_only_regenerates_targeted_sections(
    mock_pool, mock_embed_query, mock_get_llm, base_state
):
    base_state["draft_sections"] = {s: f"old {s}" for s in DEFAULT_SECTIONS}
    base_state["sections_to_revise"] = ["budget"]

    mock_pool.fetch_one.return_value = FAKE_GRANT
    mock_pool.fetch_all.return_value = FAKE_CHUNKS
    mock_embed_query.return_value = [0.0] * 1024

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("Revised budget text.")
    mock_get_llm.return_value = mock_llm

    result = draft_proposal(base_state)

    assert result["draft_sections"]["budget"] == "Revised budget text."
    # untouched sections carried through unchanged
    assert result["draft_sections"]["executive_summary"] == "old executive_summary"
    # "budget" is alone in the low-temp group and no high-temp section was
    # requested -- only 1 call made, same as before batching.
    assert mock_llm.invoke.call_count == 1


@patch("app.graph.nodes.draft.get_llm")
@patch("app.graph.nodes.draft.embed_query")
@patch("app.graph.nodes.draft.pool")
def test_draft_proposal_survives_a_failed_section_group(
    mock_pool, mock_embed_query, mock_get_llm, base_state
):
    mock_pool.fetch_one.return_value = FAKE_GRANT
    mock_pool.fetch_all.return_value = FAKE_CHUNKS
    mock_embed_query.return_value = [0.0] * 1024

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError("Gemini quota exceeded")
    mock_get_llm.return_value = mock_llm

    result = draft_proposal(base_state)

    # doesn't raise; records one error per affected section, even though the
    # underlying failure happened once per group (2 calls, not 8)
    assert len(result["errors"]) == len(DEFAULT_SECTIONS)
    assert all(v == "" for v in result["draft_sections"].values())
    assert result["status"] == "drafted"
    assert mock_llm.invoke.call_count == 2


@patch("app.graph.nodes.draft.get_llm")
@patch("app.graph.nodes.draft.embed_query")
@patch("app.graph.nodes.draft.pool")
def test_draft_proposal_handles_malformed_json_response(
    mock_pool, mock_embed_query, mock_get_llm, base_state
):
    base_state["sections_to_revise"] = ["budget"]

    mock_pool.fetch_one.return_value = FAKE_GRANT
    mock_pool.fetch_all.return_value = FAKE_CHUNKS
    mock_embed_query.return_value = [0.0] * 1024

    mock_llm = MagicMock()
    resp = MagicMock()
    resp.content = "this is not json"
    mock_llm.invoke.return_value = resp
    mock_get_llm.return_value = mock_llm

    result = draft_proposal(base_state)

    # parse_json_response raises ValueError -> caught, recorded as an error
    assert any("budget" in e for e in result["errors"])
    assert result["status"] == "drafted"


@patch("app.graph.nodes.draft.pool")
def test_draft_proposal_handles_missing_ngo_id(mock_pool):
    state = initial_state(ngo_id="", selected_grant_id="grant-1")
    with patch("app.graph.nodes.draft.get_llm") as mock_get_llm, patch(
        "app.graph.nodes.draft.embed_query"
    ):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response("text")
        mock_get_llm.return_value = mock_llm
        mock_pool.fetch_one.return_value = FAKE_GRANT

        result = draft_proposal(state)

    # should still draft — grounding is best-effort, not required
    assert result["status"] == "drafted"
    assert len(result["draft_sections"]) == len(DEFAULT_SECTIONS)