from __future__ import annotations

from fastapi import APIRouter

from app.calculation.risk import calculate_risk
from app.schemas.risk import RiskCalculationRequest, RiskCalculationResponse


router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/calculate", response_model=RiskCalculationResponse)
def calculate(payload: RiskCalculationRequest) -> RiskCalculationResponse:
    return calculate_risk(payload)
