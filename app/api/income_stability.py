from __future__ import annotations

from fastapi import APIRouter

from app.calculation.income_stability import calculate_income_stability
from app.schemas.income_stability import (
    IncomeStabilityRequest,
    IncomeStabilityResponse,
)


router = APIRouter(prefix="/income-stability", tags=["income-stability"])


@router.post("/calculate", response_model=IncomeStabilityResponse)
def calculate(payload: IncomeStabilityRequest) -> IncomeStabilityResponse:
    return calculate_income_stability(payload)
