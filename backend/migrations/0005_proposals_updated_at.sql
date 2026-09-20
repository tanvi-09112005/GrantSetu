-- Add updated_at column to proposals table for tracking edits and verification updates
alter table proposals
    add column if not exists updated_at timestamptz not null default now();
