"""Phase 0 acceptance: the graph compiles, runs, and its revision loop is bounded."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.graph.graph import build_graph, should_revise
from app.graph.nodes.verify import compute_fabrication_rate
from app.graph.state import initial_state

NGO_ID = "00000000-0000-0000-0000-000000000000"


def test_graph_compiles_and_runs_end_to_end():
    final = build_graph().compile().invoke(initial_state(ngo_id=NGO_ID))
    assert final["status"] == "human_review"
    assert final["revision_count"] == 0  # stub verification finds nothing to fix


def test_graph_contains_every_planned_node():
    nodes = set(build_graph().compile().get_graph().nodes)
    assert {
        "discover_grants",
        "check_eligibility",
        "draft_proposal",
        "extract_claims",
        "verify_claims",
        "revise_section",
        "human_review",
    } <= nodes


@pytest.mark.parametrize(
    ("rate", "revisions", "expected"),
    [
        (0.0, 0, "accept"),  # clean draft
        (0.5, 0, "revise"),  # over threshold, budget left
        (0.5, settings.max_revision_cycles, "accept"),  # budget exhausted -> forced accept
        (settings.fabrication_threshold, 0, "accept"),  # at threshold is not over it
    ],
)
def test_should_revise(rate, revisions, expected):
    state = initial_state(ngo_id=NGO_ID)
    state["fabrication_rate"] = rate
    state["revision_count"] = revisions
    assert should_revise(state) == expected


def test_fabrication_rate():
    assert compute_fabrication_rate([]) == 0.0
    assert compute_fabrication_rate([{"verdict": "supported"}]) == 0.0
    assert compute_fabrication_rate([{"verdict": "unsupported"}, {"verdict": "supported"}]) == 0.5


def test_model_strings_are_not_hardcoded_in_nodes():
    """Addendum section 3: node code must never name a Gemini version."""
    from pathlib import Path

    nodes_dir = Path(__file__).resolve().parents[1] / "app" / "graph" / "nodes"
    offenders = [
        p.name for p in nodes_dir.glob("*.py") if "gemini-" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"hardcoded model string in {offenders}"
