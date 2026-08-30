from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.calculation.income_stability import (
    DISCLAIMER,
    calculate_income_stability,
)
from app.schemas.income_stability import IncomeStabilityRequest
from tests.conftest import ASGITestClient


def income_request(*incomes: int | float | Decimal) -> IncomeStabilityRequest:
    return IncomeStabilityRequest(monthly_incomes=list(incomes))


def test_normal_six_month_income_calculation() -> None:
    result = calculate_income_stability(
        income_request(
            3_000_000,
            3_200_000,
            2_800_000,
            3_100_000,
            2_900_000,
            3_000_000,
        )
    )

    assert result.period_months == 6
    assert result.average_income == 3_000_000
    assert result.standard_deviation == 129_099.44
    assert result.coefficient_of_variation_percent == 4.3
    assert result.minimum_income == 2_800_000
    assert result.maximum_income == 3_200_000
    assert result.disclaimer == DISCLAIMER


def test_identical_incomes_have_zero_deviation_and_cv() -> None:
    result = calculate_income_stability(income_request(*([2_500_000] * 6)))

    assert result.average_income == 2_500_000
    assert result.standard_deviation == 0
    assert result.coefficient_of_variation_percent == 0
    assert result.minimum_income == 2_500_000
    assert result.maximum_income == 2_500_000


def test_all_zero_incomes_return_null_cv() -> None:
    result = calculate_income_stability(income_request(*([0] * 6)))

    assert result.average_income == 0
    assert result.standard_deviation == 0
    assert result.coefficient_of_variation_percent is None
    assert result.minimum_income == 0
    assert result.maximum_income == 0


def test_partial_zero_incomes_are_valid() -> None:
    result = calculate_income_stability(income_request(0, 100, 100, 100, 100, 100))

    assert result.average_income == 83.33
    assert result.standard_deviation == 37.27
    assert result.coefficient_of_variation_percent == 44.72
    assert result.minimum_income == 0
    assert result.maximum_income == 100


@pytest.mark.parametrize("count", [5, 7])
def test_income_count_other_than_six_is_rejected(count: int) -> None:
    with pytest.raises(ValidationError):
        IncomeStabilityRequest(monthly_incomes=[100] * count)


def test_negative_income_is_rejected() -> None:
    with pytest.raises(ValidationError):
        income_request(100, 100, -1, 100, 100, 100)


def test_numeric_string_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IncomeStabilityRequest(
            monthly_incomes=[100, 100, 100, 100, 100, "100"]
        )


def test_response_rounding_uses_two_decimal_half_up() -> None:
    result = calculate_income_stability(
        income_request(Decimal("0.03"), 0, 0, 0, 0, 0)
    )

    assert result.average_income == 0.01


def test_income_stability_api_returns_expected_contract(
    client: ASGITestClient,
) -> None:
    response = client.post(
        "/income-stability/calculate",
        json={
            "monthly_incomes": [
                3_000_000,
                3_200_000,
                2_800_000,
                3_100_000,
                2_900_000,
                3_000_000,
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "period_months": 6,
        "average_income": 3_000_000.0,
        "standard_deviation": 129_099.44,
        "coefficient_of_variation_percent": 4.3,
        "minimum_income": 2_800_000.0,
        "maximum_income": 3_200_000.0,
        "disclaimer": DISCLAIMER,
    }


@pytest.mark.parametrize(
    "monthly_incomes",
    [
        [100] * 5,
        [100] * 7,
        [100, 100, -1, 100, 100, 100],
    ],
    ids=["five-months", "seven-months", "negative-income"],
)
def test_income_stability_api_rejects_invalid_input(
    client: ASGITestClient, monthly_incomes: list[int]
) -> None:
    response = client.post(
        "/income-stability/calculate",
        json={"monthly_incomes": monthly_incomes},
    )

    assert response.status_code == 422
