from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_cost: Decimal = Field(ge=0, allow_inf_nan=False)
    own_capital: Decimal = Field(ge=0, allow_inf_nan=False)
    monthly_revenue: Decimal = Field(ge=0, allow_inf_nan=False)
    monthly_expense: Decimal = Field(ge=0, allow_inf_nan=False)
    loan_amount: Decimal = Field(ge=0, allow_inf_nan=False)
    annual_interest_rate: Decimal = Field(ge=0, allow_inf_nan=False)
    loan_term_months: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_loan_term(self) -> "RiskCalculationRequest":
        if self.loan_amount > 0 and self.loan_term_months < 1:
            raise ValueError(
                "loan_term_months must be at least 1 when loan_amount is positive"
            )
        return self


class RiskCalculationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_cash: float
    monthly_loan_payment: float = Field(ge=0)
    monthly_cash_flow: float
    monthly_cash_burn: float = Field(ge=0)
    runway_months: float | None
    remaining_debt_at_runway: float | None
    assumptions: list[str]
    disclaimer: str
