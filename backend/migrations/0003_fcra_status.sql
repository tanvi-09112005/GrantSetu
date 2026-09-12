-- ===========================================================================
-- GrantSetu — FCRA as a dated, revocable state rather than a bare string.
--
-- Why: for foreign contribution, FCRA is binary admission, not a ranking
-- signal. An Indian NGO without valid FCRA registration cannot lawfully
-- receive foreign money at all. A registration number alone cannot answer
-- "may this NGO accept foreign funds today?" because:
--   * certificates are valid 5 years and renewed via Form FC-3C,
--   * registrations are cancelled in bulk (5,789 in one round),
--   * MHA issues blanket validity extensions by notification, so a printed
--     expiry date is not authoritative on its own.
--
-- See docs/data-sources-foreign.md.
-- ===========================================================================

alter table ngo_profiles
    add column if not exists fcra_valid_until date,
    -- active | expired | cancelled | suspended | never_held | unknown
    add column if not exists fcra_status text not null default 'unknown',
    -- when a human last checked this against fcraonline.nic.in
    add column if not exists fcra_verified_on date,
    -- FCRA Account at SBI Main Branch, New Delhi — mandatory for renewal
    add column if not exists fcra_sbi_account_last4 text;

do $mig$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'ngo_profiles_fcra_status_check'
    ) then
        alter table ngo_profiles add constraint ngo_profiles_fcra_status_check
            check (fcra_status in
                ('active', 'expired', 'cancelled', 'suspended', 'never_held', 'unknown'));
    end if;
end
$mig$;

-- A grant that disburses foreign contribution. Separate from funder_type:
-- an international funder may disburse through an Indian entity (no FCRA
-- needed), and a domestic-looking programme may be foreign-funded (FCRA
-- needed). Only this flag drives the hard gate.
alter table grants
    add column if not exists is_foreign_contribution boolean not null default false,
    -- eligibility text quoted verbatim from the source, shown to the user.
    -- Never parsed into an automatic "you are eligible" verdict for foreign
    -- opportunities -- a confident wrong answer here has legal consequences.
    add column if not exists eligibility_text text;

create index if not exists grants_is_foreign_contribution_idx
    on grants (is_foreign_contribution) where is_foreign_contribution;

comment on column ngo_profiles.fcra_status is
    'Verified FCRA state. Drives the hard gate on foreign-contribution grants.';
comment on column grants.is_foreign_contribution is
    'True when accepting this grant requires FCRA registration or prior permission.';
