"""revise_section — the loop-back node, plus the terminal human-review node.

Above the fabrication threshold, only the sections that contained unsupported
claims are queued for regeneration; the loop is capped at MAX_REVISION_CYCLES
so latency stays predictable and a stubborn claim cannot spin forever.

Phase 0: stub for the flag/redact logic; the loop wiring itself is real.
"""

from __future__ import annotations

import logging

from app.graph.state import GrantSetuState

logger = logging.getLogger(__name__)


def revise_section(state: GrantSetuState) -> GrantSetuState:
    """Queue the sections whose claims came back unsupported."""
    unsupported = [
        r for r in state.get("verification_results", []) if r.get("verdict") == "unsupported"
    ]
    claims_by_id = {c.get("claim_id"): c for c in state.get("claims", [])}
    sections = {claims_by_id.get(r.get("claim_id"), {}).get("section_key") for r in unsupported}
    sections.discard(None)

    revision_count = state.get("revision_count", 0) + 1
    logger.info("[stub] revise_section cycle=%d sections=%s", revision_count, sorted(sections))
    return {
        "sections_to_revise": sorted(sections),  # type: ignore[arg-type]
        "revision_count": revision_count,
        "status": "needs_revision",
    }


def human_review(state: GrantSetuState) -> GrantSetuState:
    """Terminal node: the draft is either clean enough, or out of revision budget."""
    logger.info(
        "human_review fabrication_rate=%.3f revisions=%d",
        state.get("fabrication_rate", 0.0),
        state.get("revision_count", 0),
    )
    return {"status": "human_review"}
