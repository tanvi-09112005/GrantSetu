"""extract_claims — FActScore-style atomic decomposition (Min et al., 2023).

Breaks each drafted section into atomic factual claims, tagged numeric vs
qualitative. The split matters for the report: numeric claims are where LLMs
fabricate most, and the evaluation plan reports fabrication rate broken down by
claim type.

Phase 0: stub. Phase 4 prompts the flash-tier model for structured JSON.
"""

from __future__ import annotations

import logging

from app.graph.state import GrantSetuState

logger = logging.getLogger(__name__)


def extract_claims(state: GrantSetuState) -> GrantSetuState:
    sections = state.get("draft_sections", {})
    logger.info("[stub] extract_claims over %d sections", len(sections))
    return {
        "claims": [],
        "status": "claims_extracted",
    }
