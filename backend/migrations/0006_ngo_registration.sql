-- ===========================================================================
-- GrantSetu — Task 1: NGO registration wizard
--
-- Adds the admin/identity and statutory fields collected by the 3-step wizard,
-- plus a verification status, and widens the ngo_documents.doc_type check so
-- the Darpan / 12A / 80G certificates can be stored as their own types.
--
-- Safe to re-run (every statement is idempotent).
-- ===========================================================================

alter table ngo_profiles
    add column if not exists admin_name          text,
    add column if not exists admin_designation   text,
    add column if not exists admin_phone         text,
    add column if not exists admin_email         text,
    add column if not exists state               text,
    add column if not exists district            text,
    add column if not exists incorporation_year  int,
    add column if not exists has_12a             boolean not null default false,
    add column if not exists has_80g             boolean not null default false,
    add column if not exists has_fcra            boolean not null default false,
    -- pending_review  : registered, but no usable proof yet
    -- format_verified : Darpan ID format OK + certificate uploaded
    -- document_matched: ... and the Darpan ID was found inside the uploaded PDF
    -- rejected        : reserved for a future human reviewer
    add column if not exists verification_status text not null default 'pending_review',
    add column if not exists verified_at         timestamptz;

do $mig$
begin
    if not exists (select 1 from pg_constraint where conname = 'ngo_profiles_verification_status_check') then
        alter table ngo_profiles add constraint ngo_profiles_verification_status_check
            check (verification_status in
                ('pending_review', 'format_verified', 'document_matched', 'rejected'));
    end if;
end
$mig$;

-- Darpan IDs are unique per organisation: block two accounts claiming one ID.
-- (Partial index so the existing sample NGOs with NULL / duplicate test data
-- don't break the migration; only non-null IDs are enforced.)
create unique index if not exists ngo_profiles_darpan_id_unique
    on ngo_profiles (upper(darpan_id)) where darpan_id is not null and darpan_id <> '';

-- Widen the doc_type check to include the certificate types.
alter table ngo_documents drop constraint if exists ngo_documents_doc_type_check;
alter table ngo_documents add constraint ngo_documents_doc_type_check
    check (doc_type in ('registration', 'annual_report', 'program_report',
                        'financial_statement', 'other',
                        'darpan_certificate', 'cert_12a', 'cert_80g'));
