-- ===========================================================================
-- GrantSetu — Task 3: categorized Document Vault
--
-- 1. Widens ngo_documents.doc_type to cover every vault slot (statutory,
--    financial, impact) while keeping the legacy values older code still uses.
-- 2. Adds ngo_assets: branding images (logo / stamp / signature) stored per NGO.
--
-- Safe to re-run.
-- ===========================================================================

alter table ngo_documents drop constraint if exists ngo_documents_doc_type_check;
alter table ngo_documents add constraint ngo_documents_doc_type_check
    check (doc_type in (
        -- legacy values (kept so existing rows / older UI keep working)
        'registration', 'program_report', 'financial_statement', '12a_80g', 'fcra', 'other',
        -- statutory
        'darpan_certificate', 'cert_12a', 'cert_80g', 'cert_fcra', 'csr1',
        -- financial & audits
        'audited_balance_sheet', 'itr7', 'annual_budget',
        -- past impact & reports
        'past_proposal', 'annual_report', 'project_plan'
    ));

create table if not exists ngo_assets (
    id            uuid primary key default gen_random_uuid(),
    ngo_id        uuid not null references ngo_profiles (id) on delete cascade,
    asset_type    text not null check (asset_type in ('logo', 'stamp', 'signature')),
    filename      text,
    content_type  text not null default 'image/png',
    size_bytes    int  not null,
    data          bytea not null,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    unique (ngo_id, asset_type)
);

create index if not exists ngo_assets_ngo_id_idx on ngo_assets (ngo_id);

alter table ngo_assets enable row level security;
drop policy if exists ngo_assets_owner on ngo_assets;
create policy ngo_assets_owner on ngo_assets
    for all to authenticated
    using (owns_ngo(ngo_id))
    with check (owns_ngo(ngo_id));
