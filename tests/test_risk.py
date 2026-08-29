from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.calculation.risk import ASSUMPTIONS, DISCLAIMER, calculate_risk
from app.schemas.risk import RiskCalculationRequest
from tests.conftest import ASGITestClient


def risk_request(**overrides) -> RiskCalculationRequest:
    values = {
        "initial_cost": 0,
        "own_capital": 1_000,
        "monthly_revenue": 500,
        "monthly_expense": 300,
        "loan_amount": 0,
        "annual_interest_rate": 0,
        "loan_term_months": 0,
    }
    values.update(overrides)
    return RiskCalculationRequest(**values)


def test_case_1_no_loan_has_zero_monthly_payment() -> None:
    result = calculate_risk(risk_request(annual_interest_rate=4.5))

    assert result.monthly_loan_payment == 0


def test_case_2_zero_interest_uses_principal_divided_by_months() -> None:
    result = calculate_risk(
        risk_request(loan_amount=1_200, annual_interest_rate=0, loan_term_months=12)
    )

    assert result.monthly_loan_payment == 100


def test_case_3_equal_payment_formula_matches_known_value() -> None:
    result = calculate_risk(
        risk_request(
            loan_amount=20_000_000,
            annual_interest_rate=Decimal("4.5"),
            loan_term_months=60,
        )
    )

    assert result.monthly_loan_payment == pytest.approx(372_860.38, abs=0.001)


def test_case_4_negative_cash_flow_with_cash_has_finite_runway() -> None:
    result = calculate_risk(
        risk_request(monthly_revenue=0, monthly_expense=100, own_capital=1_000)
    )

    assert result.available_cash == 1_000
    assert result.monthly_cash_flow == -100
    assert result.monthly_cash_burn == 100
    assert result.runway_months == 10


def test_case_5_zero_cash_flow_has_no_runway_or_remaining_debt_point() -> None:
    result = calculate_risk(
        risk_request(monthly_revenue=100, monthly_expense=100)
    )

    assert result.monthly_cash_flow == 0
    assert result.runway_months is None
    assert result.remaining_debt_at_runway is None


def test_case_6_positive_cash_flow_has_no_runway() -> None:
    result = calculate_risk(
        risk_request(monthly_revenue=200, monthly_expense=100)
    )

    assert result.monthly_cash_flow == 100
    assert result.monthly_cash_burn == 0
    assert result.runway_months is None


def test_case_7_non_positive_available_cash_has_zero_runway() -> None:
    result = calculate_risk(
        risk_request(initial_cost=1_000, own_capital=500, monthly_expense=0)
    )

    assert result.available_cash == -500
    assert result.runway_months == 0


def test_case_8_finite_runway_calculates_remaining_debt() -> None:
    result = calculate_risk(
        risk_request(
            own_capital=1_000,
            monthly_revenue=0,
            monthly_expense=100,
            loan_amount=1_200,
            annual_interest_rate=0,
            loan_term_months=12,
        )
    )

    assert result.runway_months == 11
    assert result.remaining_debt_at_runway == 100


def test_positive_interest_remaining_debt_uses_amortization_balance() -> None:
    result = calculate_risk(
        risk_request(
            own_capital=0,
            monthly_revenue=0,
            monthly_expense=0,
            loan_amount=1_200,
            annual_interest_rate=12,
            loan_term_months=12,
        )
    )

    assert result.runway_months == 11.26
    assert result.remaining_debt_at_runway == 105.56


def test_case_9_no_loan_has_zero_remaining_debt_at_finite_runway() -> None:
    result = calculate_risk(
        risk_request(monthly_revenue=0, monthly_expense=100, loan_amount=0)
    )

    assert result.runway_months == 10
    assert result.remaining_debt_at_runway == 0


@pytest.mark.parametrize(
    "field_name",
    [
        "initial_cost",
        "own_capital",
        "monthly_revenue",
        "monthly_expense",
        "loan_amount",
        "annual_interest_rate",
    ],
)
def test_case_10_negative_financial_inputs_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        risk_request(**{field_name: -1})


def test_case_11_positive_loan_requires_at_least_one_month() -> None:
    with pytest.raises(ValidationError):
        risk_request(loan_amount=1, loan_term_months=0)


def test_case_12_risk_api_returns_http_200(client: ASGITestClient) -> None:
    response = client.post(
        "/risk/calculate",
        json={
            "initial_cost": 30_000_000,
            "own_capital": 20_000_000,
            "monthly_revenue": 6_000_000,
            "monthly_expense": 5_000_000,
            "loan_amount": 20_000_000,
            "annual_interest_rate": 4.5,
            "loan_term_months": 60,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["available_cash"] == 10_000_000
    assert payload["monthly_loan_payment"] == 372_860.38
    assert payload["monthly_cash_flow"] == 627_139.62
    assert payload["monthly_cash_burn"] == 0
    assert payload["runway_months"] is None
    assert payload["remaining_debt_at_runway"] is None
    assert payload["assumptions"] == ASSUMPTIONS
    assert payload["disclaimer"] == DISCLAIMER


def test_risk_api_returns_422_for_negative_input(client: ASGITestClient) -> None:
    response = client.post(
        "/risk/calculate",
        json={
            "initial_cost": -1,
            "own_capital": 0,
            "monthly_revenue": 0,
            "monthly_expense": 0,
            "loan_amount": 0,
            "annual_interest_rate": 0,
            "loan_term_months": 0,
        },
    )

    assert response.status_code == 422


def test_rounding_is_applied_only_to_response_values() -> None:
    result = calculate_risk(
        risk_request(
            own_capital=1,
            monthly_revenue=0,
            monthly_expense=Decimal("0.03"),
        )
    )

    assert result.monthly_cash_flow == -0.03
    assert result.runway_months == 33.33
