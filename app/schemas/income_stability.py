from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _require_numeric(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("monthly income must be a number")
    return value


NonNegativeIncome = Annotated[
    Decimal,
    BeforeValidator(_require_numeric),
    Field(ge=0, allow_inf_nan=False),
]


class IncomeStabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_incomes: list[NonNegativeIncome] = Field(
        min_length=6,
        max_length=6,
    )


class IncomeStabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_months: int
    average_income: float = Field(ge=0)
    standard_deviation: float = Field(ge=0)
    coefficient_of_variation_percent: float | None = Field(default=None, ge=0)
    minimum_income: float = Field(ge=0)
    maximum_income: float = Field(ge=0)
    disclaimer: str
