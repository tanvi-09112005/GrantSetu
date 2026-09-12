"""Phase 0 acceptance check — run this to confirm the setup is actually done.

    python -m scripts.verify_setup

Checks, in order of what blocks what:
  1. config loads and required env vars are present
  2. the LangGraph skeleton compiles and runs end to end on stub nodes
  3. Postgres reachable, pgvector installed, every table from the migration exists
  4. a live Gemini call against the configured model string succeeds
"""

from __future__ import annotations

import sys

from app.core.config import settings

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))


def check_config() -> None:
    missing = settings.missing_required()
    if missing:
        record("config", FAIL, f"missing: {', '.join(missing)}")
    else:
        record(
            "config", PASS, f"pro={settings.gemini_pro_model} flash={settings.gemini_flash_model}"
        )


def check_graph() -> None:
    try:
        from app.graph.graph import get_app
        from app.graph.state import initial_state

        final = get_app().invoke(initial_state(ngo_id="00000000-0000-0000-0000-000000000000"))
        record("langgraph", PASS, f"ran to status={final.get('status')}")
    except Exception as exc:  # noqa: BLE001
        record("langgraph", FAIL, str(exc))


EXPECTED_TABLES = {
    "ngo_profiles",
    "ngo_documents",
    "document_chunks",
    "grants",
    "applications",
    "proposals",
    "verification_results",
    "evaluation_runs",
}


def check_database() -> None:
    if not settings.database_url:
        record("database", SKIP, "DATABASE_URL not set")
        return
    try:
        from app.db import pool

        ext = pool.fetch_one("select 1 from pg_extension where extname = 'vector'")
        record(
            "pgvector", PASS if ext else FAIL, "extension present" if ext else "run 0001_init.sql"
        )

        rows = pool.fetch_all(
            "select table_name from information_schema.tables where table_schema = 'public'"
        )
        present = {r["table_name"] for r in rows}
        missing = EXPECTED_TABLES - present
        if missing:
            record("schema", FAIL, f"missing tables: {', '.join(sorted(missing))}")
        else:
            count = pool.fetch_one("select count(*) as n from grants")
            record("schema", PASS, f"all 8 tables present, grants rows={count['n']}")
    except Exception as exc:  # noqa: BLE001
        record("database", FAIL, str(exc))


def check_gemini() -> None:
    if not settings.google_api_key:
        record("gemini", SKIP, "GOOGLE_API_KEY not set")
        return
    try:
        from app.services.llm import get_llm, model_name

        reply = get_llm("flash").invoke("Reply with the single word: ready")
        text = (
            reply.content
            if isinstance(reply.content, str)
            else "".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in reply.content
            )
        )
        record("gemini", PASS, f"{model_name('flash')} -> {text.strip()[:40]!r}")
    except Exception as exc:  # noqa: BLE001
        record("gemini", FAIL, f"{model_name('flash')}: {exc}")


def main() -> int:
    check_config()
    check_graph()
    check_database()
    check_gemini()

    width = max(len(n) for n, _, _ in results)
    print()
    for name, status, detail in results:
        print(f"  [{status}] {name.ljust(width)}  {detail}")
    print()

    failed = [n for n, s, _ in results if s == FAIL]
    if failed:
        print(f"Phase 0 incomplete - failing: {', '.join(failed)}")
        return 1
    skipped = [n for n, s, _ in results if s == SKIP]
    if skipped:
        print(f"Phase 0 partially verified - skipped (no credentials): {', '.join(skipped)}")
        return 0
    print("Phase 0 setup verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
