# GrantSetu

NGO grant discovery, proposal drafting and claim verification — a multi-agent
RAG system for small and mid-sized Indian NGOs without dedicated grant-writing staff.

**Group 22 · TSEC, Dept. of Information Technology · AY 2026–27**
Jiya Aswani · Deepmalika Das · Tanvi Khadatkar · Ojasvi Maladkar
Guide: Dr. Shachi Natu

The research contribution is the **verification stage**: FActScore-style atomic
claim decomposition plus an entailment check against the NGO's *own* documents,
reported as a **fabrication rate**, with a controlled A/B (verification loop on
vs. off) as the headline result.

---

## Repository layout

```
backend/          FastAPI + LangGraph
  app/core/       config — every model string and threshold, read from env
  app/graph/      GrantSetuState + the agent graph (nodes/ holds one file per node)
  app/api/        REST routes (plan section 5)
  app/services/   Gemini client factory, BGE-M3 embeddings
  app/db/         Postgres pool (raw SQL for hybrid retrieval) + Supabase auth client
  migrations/     0001 schema, 0002 RLS, 0003 FCRA state
  scripts/        verify_setup, check_embedding_compute, seed_grants
  tests/
frontend/         React (Vite) + Tailwind, Supabase Auth
data/             manual downloads (provenance-tracked), test NGO profiles
notebooks/        evaluation scripts (RAGAS / DeepEval / fabrication-rate A/B)
docs/             data-source inventory, decisions log
```

## Architecture

```
Knowledge base pipeline
  NGO docs, grant/scheme data
    -> parse -> OCR (if scanned) -> chunk (~350 tok / 60 overlap) -> BGE-M3 embed
    -> pgvector + BM25 index

Agent workflow (LangGraph)
  discover_grants (hybrid RAG: BM25 + vector, fused with RRF, reranked)
    -> check_eligibility (deterministic rules engine — no LLM)
    -> draft_proposal (Gemini, section by section)
    -> extract_claims (FActScore-style atomic decomposition)
    -> verify_claims (retrieve NGO's own chunks, entailment check)
    -> fabrication_rate > threshold and revisions left ?
         yes -> revise_section -> back into draft_proposal
         no  -> human_review / export

Evaluation harness
  RAGAS + DeepEval + fabrication-rate A/B -> evaluation_runs
```

The revision loop is a cycle, which is why this is a LangGraph `StateGraph` and
not a linear chain.

---

## Setup

### 1. Supabase

Create a project, then run both migrations in the SQL editor (or with `psql`):

```bash
psql "$DATABASE_URL" -f backend/migrations/0001_init.sql
psql "$DATABASE_URL" -f backend/migrations/0002_rls.sql
psql "$DATABASE_URL" -f backend/migrations/0003_fcra_status.sql
```

`0001` enables `pgvector` and creates all eight tables. `0002` adds row-level
security so the React client can talk to Supabase directly with the anon key.
`0003` makes FCRA a dated, revocable state and flags foreign-contribution grants.

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in Supabase + Gemini keys
uvicorn app.main:app --reload
```

`http://localhost:8000/health` reports what is configured and what is missing.
`http://localhost:8000/docs` is the API surface.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### 4. Verify Phase 0

```bash
cd backend
python -m scripts.verify_setup          # config, graph, DB, live Gemini call
python -m scripts.check_embedding_compute   # is BGE-M3 usable on this machine?
# python -m scripts.seed_grants        # once a sourced grants CSV exists
pytest
```

---

## Two rules that are easy to break

**Never hardcode a Gemini model string in node code.** The 2.5 series is already
shut down and Flash-tier releases have been landing every few weeks. Models live
in `.env`, are read in `app/core/config.py`, and reach nodes only as a *tier*
(`get_llm("flash")` / `get_llm("pro")`). `tests/test_graph_skeleton.py` fails the
build if a version string appears under `app/graph/nodes/`. Re-check the
[Gemini deprecations page](https://ai.google.dev/gemini-api/docs/deprecations)
before each phase kickoff.

**Embedding dimension has three homes and they must agree**: `EMBEDDING_DIM`,
every `vector(...)` column in `0001_init.sql`, and the model itself. Run
`check_embedding_compute` in week 1 — before the schema is load-bearing — and if
BGE-M3 is too slow, drop to `BAAI/bge-small-en-v1.5` (384) and change all three
together.

---

## Data sourcing

**Read `docs/data-sources.md` (domestic government + CSR) and
`docs/data-sources-foreign.md` (foreign funders + FCRA) before writing any
ingestion code.** It is a
live-verified inventory (7 Sep 2026) of every source, tiered by whether we can
lawfully and technically collect it.

The short version:

- **Build scrapers for two sources first**: `grants-msje.gov.in` (eAnudaan --
  covers Social Justice *and* Disability Empowerment; publishes NAPDDR, AVYAY,
  SHRESHTA, SMILE plus dated application notices) and `ngo.tribal.gov.in`
  (Tribal Affairs -- guidelines and FY 2026-27 timeline PDFs). Both are public,
  no login, no CAPTCHA.
- **Never automate `csr.gov.in`** -- every data view, including the aggregate MIS
  reports, is CAPTCHA-gated. **Never automate `data.gov.in`** -- its robots.txt
  is a site-wide `Disallow: /`. Both are manual download only; see
  `data/manual/README.md`.
- **myScheme is crawlable but mostly the wrong corpus** -- 4,772 schemes, of
  which the large majority are citizen-facing individual benefit schemes whose
  eligibility keys off age/caste/gender, not 12A/80G/FCRA. Ingest a filtered
  subset, not the whole thing.
- **The official index is partly rotted.** Three ministry grant portals listed by
  NGO Darpan do not resolve in DNS at all; another advertises a deadline from
  2019. Health-check every source on every run and alert on staleness.
- **Foreign funding: `grants.gov` is keyless, live and already returns India
  opportunities with real deadlines** -- start there. The FCRA portal
  (`fcraonline.nic.in`) is the strategic source but was unreachable from the
  recon network; retest it locally. **Never auto-assert eligibility for a
  foreign grant** -- FCRA is a legal gate, so surface the text and let a human
  decide. Note USAID was dissolved in 2025; any list showing it as live is wrong.
- CSR data is **post-hoc spend disclosure** (e-form AOC-4 Segment III), not open
  calls. Treat the CSR half as *funder prospecting*, not deadline-driven
  discovery -- there is no official database of open Indian CSR calls.

The verified seed dataset lives at `data/grants_seed.csv` (69 rows: 40
government schemes from 13 ministries + 29 CSR/foundation programs from 15
funders, all `verified=yes`).  The original LLM-generated file was quarantined
on 7 Sep 2026 (`data/grants_seed.UNVERIFIED-LLM-GENERATED.csv.bak`).

## Phase status

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Repo, schema + pgvector, FastAPI/LangGraph skeleton | **done** |
| 0.5 | Data-source reconnaissance (`docs/data-sources.md`) | **done** |
| 1 | Scrapers (DST CFP, myScheme, data.gov.in); ingestion pipeline; seed CSV | **in progress** |
| 2 | `/grants/discover` + `/eligibility/check` end to end | not started |
| 3 | Section-by-section drafting | not started |
| 4 | Claim extraction, entailment, fabrication rate, revision loop | not started |
| 5 | PDF/DOCX export, onboarding UI, application tracker | not started |
| 6 | RAGAS + DeepEval + fabrication-rate A/B | not started |
| 7 | Hardening, demo script, report, viva prep | not started |
