"""GrantSetu FastAPI application.

A thin REST layer over the LangGraph app. The graph owns the reasoning; routes
own auth, validation and persistence.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import    grants, ngo, proposals
from app.api import  eligibility
from app.api import applications
from app.api import   evaluation
from app.core.config import settings
from app.db import pool
from app.graph.graph import get_app as get_graph
from app.services.llm import model_name

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = settings.missing_required()
    if missing:
        # Not fatal: the graph skeleton and /health stay inspectable during
        # Phase 0, before Supabase and Gemini keys exist.
        logger.warning("missing configuration: %s", ", ".join(missing))
    get_graph()  # compile once at boot so wiring errors surface immediately
    yield
    pool.close_pool()


app = FastAPI(
    title="GrantSetu API",
    description="NGO grant discovery, proposal drafting and claim verification.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    ngo.router,
    grants.router,
    eligibility.router,
    proposals.router,
    applications.router,
    evaluation.router,
):
    app.include_router(router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Boot check: what is configured, what is missing, which models are live."""
    missing = settings.missing_required()
    db_ok = False
    db_error = None
    try:
        pool.fetch_one("select 1 as ok")
        db_ok = True
    except Exception as exc:  # noqa: BLE001 - health must never raise
        db_error = str(exc)

    return {
        "status": "ok" if db_ok and not missing else "degraded",
        "database": {"connected": db_ok, "error": db_error},
        "missing_config": missing,
        "models": {
            "pro": model_name("pro"),
            "flash": model_name("flash"),
            "embedding": settings.embedding_model,
            "embedding_dim": settings.embedding_dim,
        },
    }


@app.get("/graph", tags=["meta"])
def graph_shape() -> dict:
    """The compiled graph's nodes and edges — useful for the report diagram."""
    compiled = get_graph()
    g = compiled.get_graph()
    return {
        "nodes": list(g.nodes),
        "edges": [
            {"source": e.source, "target": e.target, "conditional": e.conditional} for e in g.edges
        ],
    }


@app.get("/sample-ngos/profiles", tags=["sample-ngos"])
def get_sample_ngo_profiles():
    """Return curated genuine Indian NGO profiles (CRY, Pratham, Goonj, Akshaya Patra)."""
    from pathlib import Path
    import json
    json_path = Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / "sample_profiles.json"
    if not json_path.exists():
        return []
    return json.loads(json_path.read_text(encoding="utf-8"))


@app.post("/auth/auto-confirm", tags=["auth"])
def auto_confirm_email(payload: dict):
    """Auto-confirm user email in auth.users if Supabase email confirmation was enabled."""
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    pool.execute(
        "update auth.users set email_confirmed_at = now() where lower(email) = lower(%s) and email_confirmed_at is null",
        (email.strip(),),
    )
    return {"status": "confirmed", "email": email}


@app.get("/sample-ngos/download/{ngo_id}", tags=["sample-ngos"])
def download_sample_report(ngo_id: str):
    """Download official sample annual progress & compliance PDF for an NGO."""
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    pdf_path = Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / f"{ngo_id}_annual_report.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Sample report PDF not found")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"{ngo_id}_annual_report.pdf",
    )
