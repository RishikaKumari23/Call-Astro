"""
Dev-only endpoint to trigger a backtest run. Not meant for production use.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.backtest_service import run_backtest, TestCase

router = APIRouter(prefix="/backtest", tags=["Backtest (dev only)"])


class BacktestCaseInput(BaseModel):
    label: str
    dob: str
    birth_time: str
    birth_place: str
    actual_marriage_date: str   # 'YYYY-MM' or 'YYYY-MM-DD'


class BacktestRequest(BaseModel):
    cases: List[BacktestCaseInput]
    dataset_label: Optional[str] = "unspecified"  # e.g. "development" or "held-out test"


@router.post("/marriage")
async def backtest_marriage(payload: BacktestRequest):
    cases = [
        TestCase(
            label=c.label, dob=c.dob, birth_time=c.birth_time,
            birth_place=c.birth_place, actual_marriage_date=c.actual_marriage_date,
        )
        for c in payload.cases
    ]
    return run_backtest(cases, dataset_label=payload.dataset_label)