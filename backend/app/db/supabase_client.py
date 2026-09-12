"""Supabase client — auth and storage only.

All relational reads/writes go through app.db.pool (raw SQL), because hybrid
retrieval needs tsvector + pgvector in one query. This client exists so the
backend can verify a user JWT and issue signed URLs for uploaded NGO documents.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    """Service-role client. Bypasses RLS — never hand this to the browser."""
    if not (settings.supabase_url and settings.supabase_service_role_key):
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def user_from_token(access_token: str) -> dict | None:
    """Resolve a Supabase user JWT to a user record, or None if invalid."""
    try:
        response = get_supabase().auth.get_user(access_token)
    except Exception:
        return None
    return response.user.model_dump() if response and response.user else None
