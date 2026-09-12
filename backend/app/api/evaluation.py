"""Evaluation harness routes (dev/admin).

These drive the headline result: fabrication rate with vs without the
verification+revision loop, alongside RAGAS and DeepEval on the same eval set.
Every run lands in evaluation_runs, which is the report's results section.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import current_user
from app.db import pool
from app.models.schemas import EvalRunOut, EvalRunRequest

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.get("/runs", response_model=list[EvalRunOut])
def list_runs(_user: dict = Depends(current_user)) -> list[dict]:
    return pool.fetch_all("select * from evaluation_runs order by created_at desc limit 100")


@router.post("/run", response_model=EvalRunOut)
def trigger_run(payload: EvalRunRequest, _user: dict = Depends(current_user)) -> EvalRunOut:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="evaluation harness lands in Phase 6",
    )
