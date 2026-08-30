from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TrendDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class MonthlySales(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    sales: float = Field(ge=0)
    transaction_count: int = Field(ge=1)


class SalesMonthSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    sales: float = Field(ge=0)
    transaction_count: int = Field(ge=1)


class SalesSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_sales: float = Field(ge=0)
    average_monthly_sales: float = Field(ge=0)
    latest_month_sales: float = Field(ge=0)
    highest_month: SalesMonthSummary
    lowest_month: SalesMonthSummary
    months_covered: int = Field(ge=1)
    transaction_count: int = Field(ge=1)


class SalesVariability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standard_deviation: float = Field(ge=0)
    coefficient_of_variation_percent: float | None = Field(default=None, ge=0)
    basis: str


class SalesRecentTrend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    percent: float | None
    direction: TrendDirection
    basis: str
    previous_3m_average: float | None = Field(default=None, ge=0)
    latest_3m_average: float | None = Field(default=None, ge=0)
    reason: str | None


class SalesDataQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_format: str
    sheet_name: str | None
    rows_received: int = Field(ge=1)
    rows_analyzed: int = Field(ge=1)
    months_covered: int = Field(ge=1)
    first_transaction_date: date
    last_transaction_date: date
    missing_months: list[str]
    ignored_columns: list[str]


class SalesAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_demo: bool
    currency: str
    monthly_series: list[MonthlySales]
    avg: float = Field(ge=0)
    summary: SalesSummary
    recent_trend: SalesRecentTrend
    variability: SalesVariability
    mom_change_percent: float | None
    mom_change_reason: str | None
    data_quality: SalesDataQuality
    warnings: list[str]
    disclaimer: str
