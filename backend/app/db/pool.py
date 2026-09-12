"""Postgres connection pool.

Discovery needs BM25-adjacent tsvector ranking and pgvector similarity in the
same query path, plus RRF over the two result lists -- none of which fits the
supabase-py REST client. So the backend talks to Postgres directly and keeps
the Supabase client for auth and storage only.

Route handlers that touch the DB are declared `def` (not `async def`) so
Starlette runs them in a threadpool; the pool below is the sync one to match.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not set -- see .env.example")
        # open=False + explicit open() so import order never triggers a connect.
        _pool = ConnectionPool(
            settings.database_url, min_size=1, max_size=10, open=False, kwargs={"autocommit": True}
        )
        _pool.open()
        _register_vector()
    return _pool


def _register_vector() -> None:
    """Teach psycopg the pgvector type so vectors round-trip as lists."""
    try:
        from pgvector.psycopg import register_vector

        with _pool.connection() as conn:  # type: ignore[union-attr]
            register_vector(conn)
    except ImportError:  # pragma: no cover
        logger.warning("pgvector adapter not installed; vectors will be passed as strings")


@contextmanager
def cursor() -> Iterator[Any]:
    """Yield a dict-row cursor from the pool."""
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def fetch_all(sql: str, params: Any = None) -> list[dict]:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql: str, params: Any = None) -> dict | None:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql: str, params: Any = None) -> None:
    with cursor() as cur:
        cur.execute(sql, params)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
