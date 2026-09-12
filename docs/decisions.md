# Decisions

Choices made during the build that the plan left open, or that a reader of the
code would otherwise have to reverse-engineer. Add to this as you go — it is the
raw material for the report's methodology section.

## Phase 0

**Raw SQL for relational access, Supabase client for auth/storage only.**
Discovery needs `tsvector` ranking and `pgvector` similarity in the same query
path, then RRF over the two lists. That does not fit the supabase-py REST
client, so the backend holds a `psycopg` pool against `DATABASE_URL` and uses
the Supabase client only to verify user JWTs and sign upload URLs.

**Route handlers that touch the DB are `def`, not `async def`.** The pool is
synchronous and embedding is CPU-bound; Starlette runs sync handlers in a
threadpool, which avoids blocking the event loop without an async/sync split
through every service.

**RLS is written even though the backend bypasses it.** The backend runs as the
service role, so `app/api/deps.py:owned_ngo` is what actually enforces ownership
on the API path. The policies in `0002_rls.sql` protect the second path — the
React client reading Supabase directly with the anon key — which the app will
use for profile and application reads once auth is wired.

**Model access is by tier, never by name.** `get_llm("flash" | "pro")` resolves
through `app/core/config.py`. A test asserts no `gemini-` string appears under
`app/graph/nodes/`. This is the Addendum §3 rule made mechanical rather than
remembered.

**Embeddings are L2-normalised at generation time**, in `embed_texts`, so cosine
distance in pgvector is a dot product and the ingestion and query sides cannot
drift apart on this detail.

**`grants.source_url` carries a unique index.** The scheduled scraper re-runs
over the same pages, so the seed loader and the scraper both upsert on it rather
than accumulating duplicate schemes.

**Seed rows carry `verified=no`.** The eligibility engine is deterministic, so a
guessed `requires_12a` produces a confidently wrong verdict rather than a soft
one. The column forces a human pass over each row against its source URL before
the flags are trusted.

## Open questions

- Reranker for discovery: LLM rerank (flash tier) or a cross-encoder? Decide in
  Phase 2 and record the latency/quality trade-off here.
- Whether `document_chunks` needs a per-NGO partitioned vector index once the
  corpus grows past a few NGOs — currently one HNSW index over the whole table,
  filtered by `ngo_id`.
