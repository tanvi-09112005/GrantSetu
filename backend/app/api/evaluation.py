"""Evaluation harness routes (dev/admin).

These drive the headline result: fabrication rate with vs without the
verification+revision loop, alongside RAGAS and DeepEval on the same eval set.
Every run lands in evaluation_runs, which is the report's results section.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import current_user
from app.db import pool
from app.models.schemas import EvalRunOut, EvalRunRequest
from app.services.eval_service import run_evaluation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.get("/runs", response_model=list[EvalRunOut])
def list_runs(_user: dict = Depends(current_user)) -> list[dict]:
    rows = pool.fetch_all("select * from evaluation_runs order by created_at desc limit 100")
    results = []
    for row in rows:
        m = row.get("metrics_json")
        if isinstance(m, str):
            try:
                m = json.loads(m)
            except Exception:
                m = {}
        results.append({
            "id": str(row["id"]),
            "run_type": row["run_type"],
            "metrics_json": m if isinstance(m, dict) else {},
            "sample_size": row.get("sample_size"),
            "notes": row.get("notes"),
            "created_at": row["created_at"],
        })
    return results


@router.get("/runs/{run_id}", response_model=EvalRunOut)
def get_run(run_id: str, _user: dict = Depends(current_user)) -> dict:
    row = pool.fetch_one("select * from evaluation_runs where id = %s", (run_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    m = row.get("metrics_json")
    if isinstance(m, str):
        try:
            m = json.loads(m)
        except Exception:
            m = {}
    return {
        "id": str(row["id"]),
        "run_type": row["run_type"],
        "metrics_json": m if isinstance(m, dict) else {},
        "sample_size": row.get("sample_size"),
        "notes": row.get("notes"),
        "created_at": row["created_at"],
    }


@router.post("/run", response_model=EvalRunOut)
def trigger_run(payload: EvalRunRequest, _user: dict = Depends(current_user)) -> EvalRunOut:
    try:
        result = run_evaluation(
            run_type=payload.run_type,
            sample_size=payload.sample_size or 3,
            proposal_id=payload.proposal_id,
            notes=payload.notes,
        )
        return EvalRunOut(**result)
    except Exception as e:
        logger.exception("Evaluation benchmark execution failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation execution failed: {e}",
        )
