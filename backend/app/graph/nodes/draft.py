"""draft_proposal — section-by-section generation (plan section 4.3).

Not one monolithic call: each section is drafted separately from the grant's
required format + the NGO profile + RAG context pulled from the NGO's own
documents. Smaller units are individually checkable, which is what makes the
verification stage meaningful.

On a revision pass, only the sections named in state["sections_to_revise"] are
regenerated — the rest are carried through untouched.

Phase 0: stub. Phase 3 fills in the Gemini calls (pro tier, low temperature for
factual sections, higher for narrative ones).
"""

from __future__ import annotations

import logging

from app.graph.state import GrantSetuState

logger = logging.getLogger(__name__)

# Default proposal skeleton; a grant with its own required format overrides this.
DEFAULT_SECTIONS: list[str] = [
    "executive_summary",
    "organisation_background",
    "problem_statement",
    "proposed_intervention",
    "implementation_plan",
    "monitoring_and_evaluation",
    "budget",
    "sustainability",
]


def draft_proposal(state: GrantSetuState) -> GrantSetuState:
    targets = state.get("sections_to_revise") or DEFAULT_SECTIONS
    logger.info("[stub] draft_proposal sections=%s", targets)

    sections = dict(state.get("draft_sections", {}))
    for key in targets:
        sections[key] = f"[stub] {key} — drafting lands in Phase 3"

    return {
        "draft_sections": sections,
        "sections_to_revise": [],
        "status": "drafted",
    }
