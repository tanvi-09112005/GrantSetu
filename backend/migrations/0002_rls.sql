-- ===========================================================================
-- GrantSetu — row-level security.
--
-- Model: an NGO's documents, chunks, applications, proposals and verification
-- results are private to the auth.users row that owns the ngo_profile. Grants
-- are a public catalogue -- any signed-in user may read them, but only the
-- service role (scraper, seed script) may write. evaluation_runs is
-- service-role only; it is research data, not user data.
--
-- The FastAPI backend uses the service-role key and therefore bypasses RLS.
-- These policies protect the path where the React client talks to Supabase
-- directly with the anon key + a user JWT.
-- ===========================================================================

alter table ngo_profiles        enable row level security;
alter table ngo_documents       enable row level security;
alter table document_chunks     enable row level security;
alter table grants              enable row level security;
alter table applications        enable row level security;
alter table proposals           enable row level security;
alter table verification_results enable row level security;
alter table evaluation_runs     enable row level security;

-- --- ngo_profiles: owner-only -----------------------------------------------
drop policy if exists ngo_profiles_owner on ngo_profiles;
create policy ngo_profiles_owner on ngo_profiles
    for all to authenticated
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- --- helper: does the current user own this ngo? ----------------------------
create or replace function owns_ngo(target_ngo_id uuid) returns boolean
language sql stable security definer set search_path = public as $fn$
    select exists (
        select 1 from ngo_profiles
        where id = target_ngo_id and user_id = auth.uid()
    );
$fn$;

-- --- ngo_documents / document_chunks ---------------------------------------
drop policy if exists ngo_documents_owner on ngo_documents;
create policy ngo_documents_owner on ngo_documents
    for all to authenticated
    using (owns_ngo(ngo_id)) with check (owns_ngo(ngo_id));

drop policy if exists document_chunks_owner on document_chunks;
create policy document_chunks_owner on document_chunks
    for all to authenticated
    using (owns_ngo(ngo_id)) with check (owns_ngo(ngo_id));

-- --- grants: public read, service-role write --------------------------------
drop policy if exists grants_read on grants;
create policy grants_read on grants
    for select to authenticated, anon
    using (true);

-- --- applications -----------------------------------------------------------
drop policy if exists applications_owner on applications;
create policy applications_owner on applications
    for all to authenticated
    using (owns_ngo(ngo_id)) with check (owns_ngo(ngo_id));

-- --- proposals (owned transitively through applications) --------------------
drop policy if exists proposals_owner on proposals;
create policy proposals_owner on proposals
    for all to authenticated
    using (exists (
        select 1 from applications a
        where a.id = proposals.application_id and owns_ngo(a.ngo_id)))
    with check (exists (
        select 1 from applications a
        where a.id = proposals.application_id and owns_ngo(a.ngo_id)));

-- --- verification_results (owned through proposals -> applications) ---------
drop policy if exists verification_results_owner on verification_results;
create policy verification_results_owner on verification_results
    for all to authenticated
    using (exists (
        select 1 from proposals p
        join applications a on a.id = p.application_id
        where p.id = verification_results.proposal_id and owns_ngo(a.ngo_id)))
    with check (exists (
        select 1 from proposals p
        join applications a on a.id = p.application_id
        where p.id = verification_results.proposal_id and owns_ngo(a.ngo_id)));

-- evaluation_runs: no policy at all => service role only.
