-- Add NGO Darpan unique identifier (NITI Aayog registration)
-- Mandatory for voluntary organisations seeking Central Government grants.
alter table ngo_profiles
    add column if not exists darpan_id text;

create index if not exists ngo_profiles_darpan_id_idx
    on ngo_profiles (darpan_id);
