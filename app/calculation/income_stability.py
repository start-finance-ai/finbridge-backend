from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.schemas.income_stability import (
    IncomeStabilityRequest,
    IncomeStabilityResponse,
)


PERIOD_MONTHS = 6
DISCLAIMER = (
    "본 결과는 월별 소득의 단순 변동만을 기준으로 한 참고 지표이며, "
    "계약 지속성·세금·부채·신용정보 등을 반영하지 않습니다. "
    "금융기관의 소득 인정 또는 신용평가를 의미하지 않습니다."
)

_HUNDRED = Decimal("100")
_TWO_DECIMAL_PLACES = Decimal("0.01")


def calculate_income_stability(
    request: IncomeStabilityRequest,
) -> IncomeStabilityResponse:
    incomes = request.monthly_incomes
    observation_count = Decimal(len(incomes))

    with localcontext() as context:
        context.prec = 50
        average_income = sum(incomes, start=Decimal("0")) / observation_count
        variance = (
            sum(
                ((income - average_income) ** 2 for income in incomes),
                start=Decimal("0"),
            )
            / observation_count
        )
        standard_deviation = variance.sqrt()
        coefficient_of_variation = (
            standard_deviation / average_income * _HUNDRED
            if average_income != 0
            else None
        )

    return IncomeStabilityResponse(
        period_months=PERIOD_MONTHS,
        average_income=_round_for_response(average_income),
        standard_deviation=_round_for_response(standard_deviation),
        coefficient_of_variation_percent=(
            _round_for_response(coefficient_of_variation)
            if coefficient_of_variation is not None
            else None
        ),
        minimum_income=_round_for_response(min(incomes)),
        maximum_income=_round_for_response(max(incomes)),
        disclaimer=DISCLAIMER,
    )


def _round_for_response(value: Decimal) -> float:
    rounded = value.quantize(_TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
    if rounded == 0:
        return 0.0
    return float(rounded)
