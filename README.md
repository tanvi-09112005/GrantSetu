# GrantSetu (अनुदान सेतु)

> **Autonomous Multi-Agent Grant Intelligence, Grounded Proposal Drafting & Fact-Checking Engine for Indian NGOs**

**Group 22 · Thadomal Shahani Engineering College (TSEC), Dept. of Information Technology · AY 2026–27**  
*Jiya Aswani · Deepmalika Das · Tanvi Khadatkar · Ojasvi Maladkar*  
*Project Guide: Dr. Shachi Natu*

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38bdf8.svg)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue.svg)](https://github.com/pgvector/pgvector)
[![Tests](https://img.shields.io/badge/Tests-24%20Passing-emerald.svg)](https://docs.pytest.org/)

---

## 1. Overview & Problem Statement

India is home to over 3.2 million non-governmental organisations (NGOs), yet the vast majority of small and mid-sized voluntary organisations lack dedicated fundraising and proposal-writing staff. Consequently, hundreds of crore rupees in CSR funds and Central/State Government Grants-in-Aid (GIA) remain underutilised.

**GrantSetu** is an autonomous multi-agent platform designed to bridge this divide:
1. **Discovers** relevant domestic CSR and Government grant schemes using hybrid dense + sparse search (BM25 + pgvector with Reciprocal Rank Fusion).
2. **Audits statutory eligibility** deterministically (NITI Aayog Darpan ID, Section 12A, 80G, FCRA status, and operational vintage).
3. **Synthesises multi-section grant proposals** across Standard, CSR, and Government formats, strictly grounded in the NGO's certified document vault.
4. **Audits every factual claim** using a FActScore-style atomic verification engine, combining deterministic arithmetic/credential checks and LLM Natural Language Inference (NLI) entailment to quantify a precise **Fabrication Rate**.
5. **Exports formal institutional proposals** via both print-perfect in-browser CSS layouts and backend ReportLab PDF/DOCX generation.

---

## 2. Core Architecture

```mermaid
graph TD
    A[NGO Documents Vault<br/>Annual Reports, Audit Filings, 12A/80G/FCRA/Darpan] -->|Chunk & Embed| B[(pgvector + BM25<br/>BGE-M3 1024-dim)]
    C[Grant Catalogue<br/>Central Ministries, CSR Portals] -->|Hybrid Retrieval| D[LangGraph Agent Graph]

    subgraph "LangGraph Agentic Pipeline"
        D --> E[1. discover_grants<br/>BM25 + Vector RRF]
        E --> F[2. check_eligibility<br/>Deterministic Rules Engine<br/>Darpan ID, 12A/80G, FCRA, Vintage]
        F --> G[3. draft_proposal<br/>Multi-Template Synthesis<br/>Standard / CSR / Govt GIA]
        G --> H[4. extract_claims<br/>Atomic Claim Decomposition<br/>FActScore Framework]
        H --> I[5. verify_claims<br/>Deterministic + LLM NLI Entailment]
        I --> J{Fabrication Rate > 10%<br/>& Retries Left?}
        J -->|Yes| K[revise_section<br/>Targeted Self-Correction]
        K --> G
        J -->|No| L[Verified Draft Ready]
    end

    L --> M[Interactive Workspace & Editor]
    L --> N[FActScore Claim Audit Breakdown]
    L --> O[A4 Clean Print & PDF/DOCX Export]
```

---

## 3. Key Technical Contributions

### A. Hybrid Search & Deterministic Hard Gates
* **Dense + Sparse RRF Search**: Balances semantic topic matching (pgvector cosine similarity over BGE-M3 1024-dim embeddings) with exact keyword matching (PostgreSQL `tsvector` with English BM25 ranking).
* **Deterministic Statutory Gates**: Zero hallucination risk on legal eligibility. Enforces:
  * NITI Aayog NGO Darpan unique identifier format (`XX/YYYY/0123456`) and existence for Government GIA schemes.
  * Ministry of Home Affairs (MHA) FCRA active status for international grants.
  * Operational registration vintage arithmetic ($2026 - \text{registered\_year} \ge \text{min\_years}$).

### B. Genuine Multi-Template Proposal Drafting
* **No Synthetic / Hardcoded Fallbacks**: 100% real LLM drafting grounded in document chunks and official NGO profiles.
* **Three Dedicated Grant Frameworks**:
  1. **Standard Template**: Executive summary, problem statement, FLN & remedial intervention, activity-impact matrix, line-item budget, M&E, sustainability.
  2. **CSR Template**: Schedule VII Company Act 2013 alignment, baseline needs assessment, logical framework (logframe), milestone-linked disbursement tranches.
  3. **Government (GIA) Template**: Ministry scheme convergence, target demographics, technical SOPs, itemized Grants-in-Aid norms, UC & inspection framework.
* **Budget Overlap Detection**: Uses subset-sum analysis to catch double-counted aggregates and breakdowns before export.

### C. FActScore-Style Hybrid Claim Verification Engine
The platform extracts atomic factual claims from drafted sections and audits them against the document vault:
1. **Deterministic Verification Layer**:
   * **Darpan ID**: Exact regex matching and cross-referencing against official NITI Aayog profiles.
   * **Vintage & Incorporation Arithmetic**: Catches claimed operational tenure exaggerations.
   * **Statutory Compliance**: Direct checks for 12A, 80G, and FCRA registration validity.
   * **Audited Financial Cross-Referencing**: Ensures claimed budget totals exist in verified balance sheet chunks.
2. **LLM Entailment Layer**: Natural Language Inference (NLI) auditing qualitative program claims against retrieved chunks.
3. **Metric Calculation**:
   $$\text{Fabrication Rate} = \frac{\text{Unsupported Claims}}{\text{Total Atomic Claims}}$$
   Every audited claim presents an exact status badge (**Supported**, **Partially Supported**, **Unsupported**) alongside the direct evidence quote.

### D. Multi-Provider LLM Resilience
* **Dynamic Candidate Rotation**: Automatically rotates across `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.6-flash`, `gemini-3.8-flash`, and `gemini-3.7-flash`.
* **High-Capacity Groq Failover**: Supports `llama-3.3-70b-versatile` on Groq (1,000 free requests/day).
* **Fault-Tolerant Cooldowns**: Catches `504 Deadline Exceeded` (5-min cooldown), `503 High Demand` (5-min cooldown), and `429 Quota Exhausted` (2-hour cooldown) without breaking user workflows.

### E. Institutional PDF & Print Generation
* **In-Browser CSS Print Isolation**: Hides navigation headers, buttons, and status cards during printing; enforces `@page { size: A4; margin: 14mm 12mm; }` with zero blank pages and signature block orphan prevention.
* **ReportLab Export Service**: Backend institutional formatting with serif typography, automated table of contents, and dynamic INR digit grouping (`app/services/export.py`).

---

## 4. Phase Status Matrix

| Phase | Milestone | Deliverable | Status |
|:---:|:---|:---|:---:|
| **Phase 0** | **Foundations** | PostgreSQL schema + `pgvector`, FastAPI & LangGraph state machine | **Done** ✅ |
| **Phase 0.5**| **Reconnaissance**| Domestic (CSR, Darpan, eAnudaan) & Foreign (FCRA) data sourcing inventory | **Done** ✅ |
| **Phase 1** | **Grant Ingestion**| Verified Seed Dataset (69 schemes: 40 Govt, 29 CSR across 15 funders) | **Done** ✅ |
| **Phase 2** | **Discovery & Rules**| Hybrid Search (BM25 + pgvector RRF) + Deterministic Eligibility Gates | **Done** ✅ |
| **Phase 3** | **Proposal Drafting**| Multi-Template Synthesis (Standard, CSR, Govt) + Gemini 3.x/Groq rotation | **Done** ✅ |
| **Phase 4** | **Claim Verification**| FActScore Claim Extraction, Entailment Auditing & Fabrication Rate Metric | **Done** ✅ |
| **Phase 5** | **Export & Workflow**| Print-perfect A4 CSS layout + ReportLab Export + Workspace Section Editor | **Done** ✅ |
| **Phase 5b**| **Refinement**| OCR for scanned certs, financial table parsing, automatic revision trigger | **In Progress** 🔄 |
| **Phase 6** | **Evaluation Harness**| RAGAS + DeepEval benchmark suite, controlled A/B fabrication study | **Next Up** ⏳ |
| **Phase 7** | **Final Packaging**| Deployment hardening, live demo walkthrough, technical report & viva prep | **Scheduled** ⏳ |

---

## 5. Repository Structure

```
GrantSetu/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints (grants, eligibility, proposals, ngo)
│   │   ├── core/            # Configuration & multi-provider settings (Pydantic)
│   │   ├── db/              # Raw SQL pool (psycopg) + Supabase Client
│   │   ├── graph/           # LangGraph StateGraph & workflow nodes
│   │   │   └── nodes/       # discover, check_eligibility, draft, extract_claims, verify
│   │   ├── models/          # Pydantic schemas & response models
│   │   └── services/        # LLM rotation factory, Groq client, embeddings, export service
│   ├── migrations/          # 0001_init, 0002_rls, 0003_fcra, 0004_darpan, 0005_updated_at
│   ├── scripts/             # Offline verification, ingestion, and sync utilities
│   └── tests/               # 24 unit tests covering discovery, drafting, versioning & verification
├── frontend/
│   ├── src/
│   │   ├── components/      # ProposalWorkspace, GrantDiscoveryCard, Navbar, etc.
│   │   ├── lib/             # API client & Supabase auth
│   │   └── App.jsx          # Main application portal
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── grants_seed.csv      # 69 verified Indian government & CSR grants
│   └── sample_ngos/         # Authentic profiles (CRY, EOTO, Pratham, Goonj, Akshaya Patra)
└── docs/                    # Data sources inventory, legal guidelines, decisions log
```

---

## 6. Quickstart Guide

### Prerequisites
* **Python**: 3.12+
* **Node.js**: 18+ & npm
* **Database**: PostgreSQL 15+ with `pgvector` enabled (e.g. Supabase)

### 1. Database Setup
Execute migrations in your PostgreSQL instance:
```bash
psql "$DATABASE_URL" -f backend/migrations/0001_init.sql
psql "$DATABASE_URL" -f backend/migrations/0002_rls.sql
psql "$DATABASE_URL" -f backend/migrations/0003_fcra_status.sql
psql "$DATABASE_URL" -f backend/migrations/0004_darpan_id.sql
psql "$DATABASE_URL" -f backend/migrations/0005_proposals_updated_at.sql
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

Ensure `.env` contains:
```ini
DATABASE_URL=postgresql://postgres:...@db...supabase.co:5432/postgres
GOOGLE_API_KEY=your_gemini_api_key
# Optional high-capacity fallback (1,000 free requests/day):
GROQ_API_KEY=your_groq_api_key
LLM_PROVIDER=auto
```

Start the FastAPI development server:
```bash
uvicorn app.main:app --reload --port 8000
```
* **API Docs**: `http://localhost:8000/docs`
* **Health Check**: `http://localhost:8000/health`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 7. Running Tests

GrantSetu maintains **100% offline, fixture-mocked test execution** with zero external LLM billing risk during automated testing:

```bash
cd backend
python -m pytest tests/ -v
```

Expected Output:
```
tests/test_draft_proposal.py::test_draft_proposal_fills_all_default_sections PASSED
tests/test_draft_proposal.py::test_draft_proposal_only_regenerates_targeted_sections PASSED
tests/test_draft_proposal.py::test_draft_proposal_survives_a_failed_section_group PASSED
tests/test_draft_proposal.py::test_draft_proposal_handles_malformed_json_response PASSED
tests/test_draft_proposal.py::test_draft_proposal_handles_missing_ngo_id PASSED
tests/test_graph_skeleton.py::test_graph_compiles_and_runs_end_to_end PASSED
tests/test_graph_skeleton.py::test_graph_contains_every_planned_node PASSED
tests/test_graph_skeleton.py::test_should_revise PASSED
tests/test_graph_skeleton.py::test_fabrication_rate PASSED
tests/test_phase2_discovery_eligibility.py PASSED
tests/test_phase3_proposals.py::test_proposal_version_increment_on_conflict PASSED
tests/test_phase3_proposals.py::test_revise_endpoint_accepts_sections_and_edits PASSED
tests/test_phase3_proposals.py::test_verify_proposal_claims_endpoint PASSED
tests/test_seed_csv.py PASSED
======================= 24 passed in 1.62s =======================
```

To test the frontend production build:
```bash
cd frontend
npm run build
```

---

## 8. License & Acknowledgements

Developed as an Academic Capstone Project under the Department of Information Technology, Thadomal Shahani Engineering College (TSEC), Mumbai. Special thanks to our project guide **Dr. Shachi Natu** for invaluable architectural guidance on verification frameworks.
