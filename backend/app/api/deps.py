"""Shared route dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import pool
from app.db.supabase_client import user_from_token

bearer = HTTPBearer(auto_error=True)
bearer_optional = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    """Resolve the Supabase session JWT the React client sends."""
    user = user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        )
    return user


def maybe_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_optional),
) -> dict | None:
    """Optionally resolve Supabase JWT if present, returning None if unauthenticated."""
    if not credentials:
        return None
    return user_from_token(credentials.credentials)


def owned_ngo(ngo_id: str, user: dict = Depends(current_user)) -> str:
    """Assert the caller owns `ngo_id` and return it.

    The backend runs as the service role and so bypasses RLS — ownership has to
    be checked here, explicitly, on every NGO-scoped route.
    """
    row = pool.fetch_one(
        "select 1 from ngo_profiles where id = %s and user_id = %s",
        (ngo_id, user["id"]),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
    return ngo_id
