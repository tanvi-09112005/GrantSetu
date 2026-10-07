"""Standalone Evaluation Harness CLI (Phase 6).

Executes RAGAS, DeepEval, and Fabrication Rate A/B benchmarks across live NGO Vault proposals.
Persists results directly to the PostgreSQL `evaluation_runs` table for reporting and research.

Usage:
    python backend/scripts/run_eval.py --type all --sample-size 3
    python backend/scripts/run_eval.py --type ragas
    python backend/scripts/run_eval.py --type deepeval
    python backend/scripts/run_eval.py --type fabrication_rate
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add backend directory to path if run from root
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.services.eval_service import run_evaluation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("eval_runner")


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))
    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    lines = [sep]
    lines.append("| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |")
    lines.append(sep)
    for row in rows:
        lines.append("| " + " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) + " |")
    lines.append(sep)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GrantSetu Evaluation Harness (RAGAS + DeepEval + Fabrication A/B)")
    parser.add_argument(
        "--type",
        choices=["ragas", "deepeval", "fabrication_rate", "all"],
        default="all",
        help="Evaluation benchmark to run (default: all)",
    )
    parser.add_argument("--sample-size", type=int, default=3, help="Number of proposals to sample (default: 3)")
    parser.add_argument("--proposal-id", type=str, default=None, help="Target specific proposal UUID")
    parser.add_argument("--notes", type=str, default=None, help="Custom notes for evaluation_runs log")
    args = parser.parse_args()

    print("=" * 80)
    print("  GRANTSETU PHASE 6 EVALUATION BENCHMARK SUITE")
    print(f"  Target Run Type: {args.type.upper()} | Sample Size: {args.sample_size}")
    if args.proposal_id:
        print(f"  Target Proposal ID: {args.proposal_id}")
    print("=" * 80)
    print("\nExecuting evaluation pipeline against live NGO Document Vault proposals...")

    result = run_evaluation(
        run_type=args.type,
        sample_size=args.sample_size,
        proposal_id=args.proposal_id,
        notes=args.notes,
    )

    metrics = result.get("metrics_json", {})
    run_id = result.get("id")

    print("\n" + "=" * 80)
    print(f"  BENCHMARK COMPLETED SUCCESSFULLY (Run ID: {run_id})")
    print("=" * 80 + "\n")

    if args.type in ("ragas", "all"):
        ragas_data = metrics.get("ragas") if args.type == "all" else metrics
        if ragas_data:
            print("--- [RAGAS METRICS] ---")
            print(f"  * Faithfulness (LLM Entailment):   {ragas_data.get('faithfulness', 0.0):.4f}")
            print(f"  * Answer Relevancy (Question Sim): {ragas_data.get('answer_relevancy', 0.0):.4f}")
            print(f"  * Context Precision:               {ragas_data.get('context_precision', 0.0):.4f}")
            print(f"  * Context Recall:                  {ragas_data.get('context_recall', 0.0):.4f}")
            print(f"  * Evaluated Samples:               {ragas_data.get('sample_count', 0)}\n")

    if args.type in ("deepeval", "all"):
        deepeval_data = metrics.get("deepeval") if args.type == "all" else metrics
        if deepeval_data:
            print("--- [DEEPEVAL METRICS] ---")
            print(f"  * Grounding Score:                 {deepeval_data.get('grounding_score', 0.0):.4f}")
            print(f"  * Hallucination Rate:              {deepeval_data.get('hallucination_rate', 0.0):.4f}")
            print(f"  * Grant RFP Priority Alignment:    {deepeval_data.get('grant_priority_alignment', 0.0):.4f}")
            print(f"  * Institutional Credibility:       {deepeval_data.get('institutional_credibility', 0.0):.4f}")
            print(f"  * Evaluated Samples:               {deepeval_data.get('sample_count', 0)}\n")

    if args.type in ("fabrication_rate", "all"):
        fab_data = metrics.get("fabrication_rate") if args.type == "all" else metrics
        if fab_data:
            print("--- [FABRICATION RATE A/B STUDY] ---")
            unv = fab_data.get("unverified_arm", {})
            aud = fab_data.get("audited_arm", {})
            rows = [
                ["Arm A (Unverified LLM Generation)", f"{unv.get('fabrication_rate', 0)*100:.1f}%", f"{unv.get('entailment_accuracy', 0)*100:.1f}%", f"{unv.get('hallucinated_numerical_claims_pct', 0):.1f}%"],
                ["Arm B (GrantSetu Multi-Agent Audited)", f"{aud.get('fabrication_rate', 0)*100:.1f}%", f"{aud.get('entailment_accuracy', 0)*100:.1f}%", f"{aud.get('hallucinated_numerical_claims_pct', 0):.1f}%"],
            ]
            print(format_table(["Study Arm", "Fabrication Rate", "Entailment Acc", "Hallucinated Numbers"], rows))
            print(f"\n  >> Relative Fabrication Reduction: {fab_data.get('relative_fabrication_reduction')}%")
            print(f"  >> Conclusion: {fab_data.get('conclusion')}\n")

    print(f"Record successfully saved to PostgreSQL `evaluation_runs` (ID: {run_id}).")


if __name__ == "__main__":
    main()
