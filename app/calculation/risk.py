from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP, localcontext

from app.schemas.risk import RiskCalculationRequest, RiskCalculationResponse


ASSUMPTIONS = [
    "원리금균등상환",
    "입력한 월매출과 월지출이 동일하게 지속된다고 가정",
    "세금·수수료·매출 변동·추가 차입 등은 반영하지 않음",
]
DISCLAIMER = (
    "본 결과는 입력값을 기반으로 한 단순 재무 시뮬레이션이며 실제 대출 승인, "
    "신용평가 또는 사업 성과를 의미하지 않습니다."
)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_TWELVE = Decimal("12")
_TWO_DECIMAL_PLACES = Decimal("0.01")


def calculate_risk(request: RiskCalculationRequest) -> RiskCalculationResponse:
    with localcontext() as context:
        context.prec = 50

        available_cash = (
            request.own_capital + request.loan_amount - request.initial_cost
        )
        monthly_rate = request.annual_interest_rate / _HUNDRED / _TWELVE
        monthly_loan_payment = _monthly_loan_payment(
            principal=request.loan_amount,
            monthly_rate=monthly_rate,
            loan_term_months=request.loan_term_months,
        )
        monthly_cash_flow = (
            request.monthly_revenue
            - request.monthly_expense
            - monthly_loan_payment
        )
        monthly_cash_burn = (
            abs(monthly_cash_flow) if monthly_cash_flow < 0 else _ZERO
        )
        runway_months = _runway_months(available_cash, monthly_cash_flow)
        remaining_debt = _remaining_debt_at_runway(
            principal=request.loan_amount,
            monthly_rate=monthly_rate,
            monthly_payment=monthly_loan_payment,
            loan_term_months=request.loan_term_months,
            runway_months=runway_months,
        )

    return RiskCalculationResponse(
        available_cash=_round_for_response(available_cash),
        monthly_loan_payment=_round_for_response(monthly_loan_payment),
        monthly_cash_flow=_round_for_response(monthly_cash_flow),
        monthly_cash_burn=_round_for_response(monthly_cash_burn),
        runway_months=(
            _round_for_response(runway_months)
            if runway_months is not None
            else None
        ),
        remaining_debt_at_runway=(
            _round_for_response(remaining_debt)
            if remaining_debt is not None
            else None
        ),
        assumptions=list(ASSUMPTIONS),
        disclaimer=DISCLAIMER,
    )


def _monthly_loan_payment(
    *, principal: Decimal, monthly_rate: Decimal, loan_term_months: int
) -> Decimal:
    if principal == 0:
        return _ZERO
    if monthly_rate == 0:
        return principal / Decimal(loan_term_months)

    growth = (_ONE + monthly_rate) ** loan_term_months
    return principal * monthly_rate * growth / (growth - _ONE)


def _runway_months(
    available_cash: Decimal, monthly_cash_flow: Decimal
) -> Decimal | None:
    if available_cash <= 0:
        return _ZERO
    if monthly_cash_flow < 0:
        return available_cash / abs(monthly_cash_flow)
    return None


def _remaining_debt_at_runway(
    *,
    principal: Decimal,
    monthly_rate: Decimal,
    monthly_payment: Decimal,
    loan_term_months: int,
    runway_months: Decimal | None,
) -> Decimal | None:
    if runway_months is None:
        return None
    if principal == 0:
        return _ZERO

    payments_made = int(runway_months.to_integral_value(rounding=ROUND_FLOOR))
    payments_made = max(0, min(payments_made, loan_term_months))

    if monthly_rate == 0:
        remaining_debt = principal - monthly_payment * payments_made
    else:
        growth = (_ONE + monthly_rate) ** payments_made
        remaining_debt = (
            principal * growth
            - monthly_payment * (growth - _ONE) / monthly_rate
        )
    return max(remaining_debt, _ZERO)


def _round_for_response(value: Decimal) -> float:
    rounded = value.quantize(_TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
    if rounded == 0:
        return 0.0
    return float(rounded)
