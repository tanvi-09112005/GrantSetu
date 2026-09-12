-- ===========================================================================
-- GrantSetu — initial schema (Implementation Plan section 3)
-- Supabase / Postgres + pgvector. Run in the Supabase SQL editor, or:
--   psql "$DATABASE_URL" -f backend/migrations/0001_init.sql
--
-- Embedding dimension is 1024 (BGE-M3). If the week-1 compute check forces a
-- fallback to bge-small (384), change EVERY vector(1024) below and the
-- EMBEDDING_DIM env var together -- they must agree or inserts will fail.
-- ===========================================================================

create extension if not exists vector;
create extension if not exists pg_trgm;

-- ---------------------------------------------------------------------------
-- NGO side
-- ---------------------------------------------------------------------------
create table if not exists ngo_profiles (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references auth.users (id) on delete cascade,
    name            text not null,
    mission         text,
    sectors         text[] not null default '{}',
    location        text,
    -- Indian compliance registrations. Stored as the registration number when
    -- held, null when not held -- "is not null" is the eligibility predicate.
    reg_12a         text,
    reg_80g         text,
    reg_fcra        text,
    registered_on   date,          -- drives min_years_registered eligibility
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists ngo_profiles_user_id_idx on ngo_profiles (user_id);
create index if not exists ngo_profiles_sectors_idx on ngo_profiles using gin (sectors);

create table if not exists ngo_documents (
    id              uuid primary key default gen_random_uuid(),
    ngo_id          uuid not null references ngo_profiles (id) on delete cascade,
    doc_type        text not null check (
                        doc_type in ('registration', 'annual_report',
                                     'program_report', 'financial_statement', 'other')),
    file_url        text,
    raw_text        text,
    -- pending | parsing | chunking | embedding | ready | failed
    ingest_status   text not null default 'pending',
    ingest_error    text,
    created_at      timestamptz not null default now()
);

create index if not exists ngo_documents_ngo_id_idx on ngo_documents (ngo_id);

create table if not exists document_chunks (
    id              uuid primary key default gen_random_uuid(),
    document_id     uuid not null references ngo_documents (id) on delete cascade,
    ngo_id          uuid not null references ngo_profiles (id) on delete cascade,
    chunk_text      text not null,
    chunk_index     int  not null,
    -- section heading when the parser could infer one (section-aware chunking)
    section_title   text,
    embedding       vector(1024),
    created_at      timestamptz not null default now(),
    unique (document_id, chunk_index)
);

create index if not exists document_chunks_ngo_id_idx on document_chunks (ngo_id);
-- Evidence retrieval for verification is always scoped to one NGO, so the
-- vector index only has to be good within that partition.
create index if not exists document_chunks_embedding_idx
    on document_chunks using hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- Grant side
-- ---------------------------------------------------------------------------
create table if not exists grants (
    id                uuid primary key default gen_random_uuid(),
    title             text not null,
    funder_name       text not null,
    funder_type       text check (funder_type in ('govt', 'csr', 'foundation', 'international')),
    description       text,
    -- {requires_12a, requires_80g, requires_fcra, min_years_registered,
    --  sectors: [], geography: [], min_budget, max_budget}
    eligibility_json  jsonb not null default '{}'::jsonb,
    sectors           text[] not null default '{}',
    geography         text[] not null default '{}',
    deadline          date,
    source_url        text,
    -- provenance: 'seed_csv' for the hand-curated layer, scraper name otherwise
    source            text not null default 'seed_csv',
    last_seen_at      timestamptz not null default now(),
    is_active         boolean not null default true,
    embedding         vector(1024),
    tsv               tsvector generated always as (
                          to_tsvector('english',
                              coalesce(title, '') || ' ' ||
                              coalesce(funder_name, '') || ' ' ||
                              coalesce(description, ''))
                      ) stored,
    created_at        timestamptz not null default now()
);

-- A scraper re-run must update rather than duplicate an existing scheme.
-- Keyed on (funder_name, title), not source_url: a ministry commonly lists
-- several distinct schemes on one page, so URLs are not unique per scheme.
create unique index if not exists grants_funder_title_key
    on grants (funder_name, title);
create index if not exists grants_source_url_idx on grants (source_url);
create index if not exists grants_tsv_idx        on grants using gin (tsv);
create index if not exists grants_sectors_idx    on grants using gin (sectors);
create index if not exists grants_geography_idx  on grants using gin (geography);
create index if not exists grants_deadline_idx   on grants (deadline);
create index if not exists grants_embedding_idx
    on grants using hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- Workflow
-- ---------------------------------------------------------------------------
create table if not exists applications (
    id           uuid primary key default gen_random_uuid(),
    ngo_id       uuid not null references ngo_profiles (id) on delete cascade,
    grant_id     uuid not null references grants (id) on delete cascade,
    status       text not null default 'matched' check (
                     status in ('matched', 'eligible', 'ineligible', 'drafted',
                                'verified', 'exported', 'submitted', 'funded', 'rejected')),
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),
    unique (ngo_id, grant_id)
);

create index if not exists applications_ngo_id_idx on applications (ngo_id);

create table if not exists proposals (
    id              uuid primary key default gen_random_uuid(),
    application_id  uuid not null references applications (id) on delete cascade,
    -- {"executive_summary": "...", "budget": "...", ...}
    sections        jsonb not null default '{}'::jsonb,
    version         int  not null default 1,
    status          text not null default 'draft' check (
                        status in ('draft', 'verifying', 'needs_revision',
                                   'verified', 'human_review', 'exported')),
    created_at      timestamptz not null default now(),
    unique (application_id, version)
);

create index if not exists proposals_application_id_idx on proposals (application_id);

create table if not exists verification_results (
    id                 uuid primary key default gen_random_uuid(),
    proposal_id        uuid not null references proposals (id) on delete cascade,
    section_key        text,
    claim_text         text not null,
    -- FActScore-style atomic claim verdict
    verdict            text not null check (
                           verdict in ('supported', 'unsupported', 'partially_supported')),
    evidence_chunk_id  uuid references document_chunks (id) on delete set null,
    evidence_span      text,
    confidence         float,
    model_used         text,
    created_at         timestamptz not null default now()
);

create index if not exists verification_results_proposal_id_idx
    on verification_results (proposal_id);

create table if not exists evaluation_runs (
    id           uuid primary key default gen_random_uuid(),
    run_type     text not null check (run_type in ('ragas', 'deepeval', 'fabrication_rate')),
    -- for the fabrication-rate A/B: {"arm": "verified" | "unverified", ...}
    metrics_json jsonb not null default '{}'::jsonb,
    sample_size  int,
    notes        text,
    created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- updated_at triggers
-- ---------------------------------------------------------------------------
create or replace function set_updated_at() returns trigger
language plpgsql as $fn$
begin
    new.updated_at = now();
    return new;
end;
$fn$;

drop trigger if exists ngo_profiles_set_updated_at on ngo_profiles;
create trigger ngo_profiles_set_updated_at before update on ngo_profiles
    for each row execute function set_updated_at();

drop trigger if exists applications_set_updated_at on applications;
create trigger applications_set_updated_at before update on applications
    for each row execute function set_updated_at();
