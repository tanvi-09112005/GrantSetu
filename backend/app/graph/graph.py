"""The GrantSetu LangGraph (Implementation Plan section 4).

    discover_grants -> check_eligibility -> draft_proposal -> extract_claims
        -> verify_claims -> [conditional]
              fabrication_rate > threshold and revision_count < max
                  -> revise_section -> draft_proposal   (cycle)
              otherwise
                  -> human_review -> END

The cycle is the whole reason this is a StateGraph and not a linear chain.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.graph.nodes.discover import discover_grants
from app.graph.nodes.draft import draft_proposal
from app.graph.nodes.eligibility import check_eligibility
from app.graph.nodes.extract_claims import extract_claims
from app.graph.nodes.revise import human_review, revise_section
from app.graph.nodes.verify import verify_claims
from app.graph.state import GrantSetuState


def should_revise(state: GrantSetuState) -> str:
    """Conditional edge after verification.

    Returns the name of the next node: "revise" to loop back into drafting,
    "accept" to hand off to human review. Hitting the revision cap forces
    acceptance rather than looping — an unfixable claim must not stall the run.
    """
    rate = state.get("fabrication_rate", 0.0)
    revisions = state.get("revision_count", 0)
    if rate > settings.fabrication_threshold and revisions < settings.max_revision_cycles:
        return "revise"
    return "accept"


def build_graph() -> StateGraph:
    graph = StateGraph(GrantSetuState)

    graph.add_node("discover_grants", discover_grants)
    graph.add_node("check_eligibility", check_eligibility)
    graph.add_node("draft_proposal", draft_proposal)
    graph.add_node("extract_claims", extract_claims)
    graph.add_node("verify_claims", verify_claims)
    graph.add_node("revise_section", revise_section)
    graph.add_node("human_review", human_review)

    graph.set_entry_point("discover_grants")
    graph.add_edge("discover_grants", "check_eligibility")
    graph.add_edge("check_eligibility", "draft_proposal")
    graph.add_edge("draft_proposal", "extract_claims")
    graph.add_edge("extract_claims", "verify_claims")

    graph.add_conditional_edges(
        "verify_claims",
        should_revise,
        {"revise": "revise_section", "accept": "human_review"},
    )
    graph.add_edge("revise_section", "draft_proposal")
    graph.add_edge("human_review", END)

    return graph


_compiled = None


def get_app():
    """Compiled graph, built once per process."""
    global _compiled
    if _compiled is None:
        _compiled = build_graph().compile()
    return _compiled
