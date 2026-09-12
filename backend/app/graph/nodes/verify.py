"""verify_claims — entailment check against the NGO's own documents.

For each atomic claim, retrieve top-k chunks from document_chunks scoped to
this NGO (never the grants knowledge base — a claim about the NGO's track
record can only be grounded in the NGO's own reports), then decide
supported / partially_supported / unsupported.

Phase 4 starts with an LLM-judge call returning structured JSON, then
benchmarks it against MiniCheck (Tang, Laban & Durrett, EMNLP 2024). That
comparison is a methods contribution in its own right, so keep the judge
behind this single function to make swapping it a one-file change.

fabrication_rate = unsupported / total claims.

Phase 0: stub.
"""

from __future__ import annotations

import logging

from app.graph.state import GrantSetuState

logger = logging.getLogger(__name__)


def compute_fabrication_rate(results: list[dict]) -> float:
    """unsupported / total. Empty claim list scores 0.0, not a division error."""
    if not results:
        return 0.0
    unsupported = sum(1 for r in results if r.get("verdict") == "unsupported")
    return unsupported / len(results)


def verify_claims(state: GrantSetuState) -> GrantSetuState:
    claims = state.get("claims", [])
    logger.info("[stub] verify_claims over %d claims", len(claims))
    results: list[dict] = []
    return {
        "verification_results": results,
        "fabrication_rate": compute_fabrication_rate(results),
        "status": "verified",
    }
