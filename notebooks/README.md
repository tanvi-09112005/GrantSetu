# Evaluation notebooks

Phase 6 lives here. Every run writes to the `evaluation_runs` table, which is
the report's results section pre-structured — so a notebook that prints a number
without persisting it has not finished the job.

Planned notebooks:

- `01_eval_set.ipynb` — build the N≈20–30 (NGO profile, grant) evaluation set.
- `02_fabrication_ab.ipynb` — the headline result. For each pair, generate two
  drafts: **(a)** verification and revision disabled, **(b)** the full loop.
  Compute fabrication rate for both against the NGO's own documents, and report
  the mean per arm plus a breakdown by claim type (numeric vs qualitative —
  numeric is where LLMs fabricate most, so the split is the interesting part).
- `03_ragas.ipynb` — faithfulness, context precision, context recall, answer
  relevancy over the discovery + drafting RAG output.
- `04_deepeval.ipynb` — hallucination metric plus a custom G-Eval rubric
  ("does this section address the grant's stated priorities?").
- `05_minicheck_benchmark.ipynb` — the LLM-judge entailment check against
  MiniCheck on the same claims. This comparison is a methods contribution, not
  just an optimisation.

Run them against the same evaluation set, or the numbers are not comparable.
