from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.data.sales_upload import ParsedSalesUpload
from app.schemas.sales_analysis import (
    MonthlySales,
    SalesAnalysisResponse,
    SalesDataQuality,
    SalesMonthSummary,
    SalesRecentTrend,
    SalesSummary,
    SalesVariability,
    TrendDirection,
)


DISCLAIMER = (
    "본 결과는 업로드한 매출 자료를 단순 집계·분석한 참고 지표이며, "
    "세금·비용·환불·부채·신용정보 등을 반영하지 않습니다. "
    "회계·세무 판단 또는 금융기관의 신용평가를 의미하지 않습니다."
)

VARIABILITY_BASIS = "MONTHLY_SALES_POPULATION"
TREND_BASIS = "LATEST_3M_VS_PREVIOUS_3M"

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_TWO_DECIMAL_PLACES = Decimal("0.01")


def calculate_sales_analysis(
    upload: ParsedSalesUpload,
) -> SalesAnalysisResponse:
    sales_by_month: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    count_by_month: dict[str, int] = defaultdict(int)
    for row in upload.rows:
        month = row.transaction_date.strftime("%Y-%m")
        sales_by_month[month] += row.sales_amount
        count_by_month[month] += 1

    months = sorted(sales_by_month)
    raw_monthly = [
        (month, sales_by_month[month], count_by_month[month])
        for month in months
    ]

    with localcontext() as context:
        context.prec = 50
        month_count = Decimal(len(raw_monthly))
        total_sales = sum(
            (sales for _, sales, _ in raw_monthly), start=_ZERO
        )
        average_monthly_sales = total_sales / month_count
        variance = (
            sum(
                (
                    (sales - average_monthly_sales) ** 2
                    for _, sales, _ in raw_monthly
                ),
                start=_ZERO,
            )
            / month_count
        )
        standard_deviation = variance.sqrt()
        coefficient_of_variation = (
            standard_deviation / average_monthly_sales * _HUNDRED
            if average_monthly_sales != 0
            else None
        )
        recent_trend = _recent_trend(raw_monthly)
        mom_change_percent, mom_change_reason = _month_over_month(raw_monthly)

    highest = max(raw_monthly, key=lambda item: item[1])
    lowest = min(raw_monthly, key=lambda item: item[1])
    latest = raw_monthly[-1]
    missing_months = _missing_months(months)
    warnings = (
        ["MISSING_CALENDAR_MONTHS: " + ", ".join(missing_months)]
        if missing_months
        else []
    )

    monthly_series = [
        MonthlySales(
            month=month,
            sales=_round_for_response(sales),
            transaction_count=transaction_count,
        )
        for month, sales, transaction_count in raw_monthly
    ]
    average_response = _round_for_response(average_monthly_sales)
    return SalesAnalysisResponse(
        is_demo=False,
        currency="KRW",
        monthly_series=monthly_series,
        avg=average_response,
        summary=SalesSummary(
            total_sales=_round_for_response(total_sales),
            average_monthly_sales=average_response,
            latest_month_sales=_round_for_response(latest[1]),
            highest_month=_month_summary(highest),
            lowest_month=_month_summary(lowest),
            months_covered=len(raw_monthly),
            transaction_count=len(upload.rows),
        ),
        recent_trend=recent_trend,
        variability=SalesVariability(
            standard_deviation=_round_for_response(standard_deviation),
            coefficient_of_variation_percent=(
                _round_for_response(coefficient_of_variation)
                if coefficient_of_variation is not None
                else None
            ),
            basis=VARIABILITY_BASIS,
        ),
        mom_change_percent=(
            _round_for_response(mom_change_percent)
            if mom_change_percent is not None
            else None
        ),
        mom_change_reason=mom_change_reason,
        data_quality=SalesDataQuality(
            source_format=upload.source_format,
            sheet_name=upload.sheet_name,
            rows_received=upload.rows_received,
            rows_analyzed=len(upload.rows),
            months_covered=len(raw_monthly),
            first_transaction_date=min(row.transaction_date for row in upload.rows),
            last_transaction_date=max(row.transaction_date for row in upload.rows),
            missing_months=missing_months,
            ignored_columns=list(upload.ignored_columns),
        ),
        warnings=warnings,
        disclaimer=DISCLAIMER,
    )


def _recent_trend(
    monthly: list[tuple[str, Decimal, int]],
) -> SalesRecentTrend:
    if len(monthly) < 6:
        return SalesRecentTrend(
            percent=None,
            direction=TrendDirection.UNKNOWN,
            basis=TREND_BASIS,
            previous_3m_average=None,
            latest_3m_average=None,
            reason="INSUFFICIENT_MONTHS",
        )

    latest_six = monthly[-6:]
    if not _are_consecutive([month for month, _, _ in latest_six]):
        return SalesRecentTrend(
            percent=None,
            direction=TrendDirection.UNKNOWN,
            basis=TREND_BASIS,
            previous_3m_average=None,
            latest_3m_average=None,
            reason="NON_CONTIGUOUS_MONTHS",
        )

    previous_average = sum(
        (sales for _, sales, _ in latest_six[:3]), start=_ZERO
    ) / Decimal("3")
    latest_average = sum(
        (sales for _, sales, _ in latest_six[3:]), start=_ZERO
    ) / Decimal("3")
    if previous_average == 0:
        return SalesRecentTrend(
            percent=None,
            direction=TrendDirection.UNKNOWN,
            basis=TREND_BASIS,
            previous_3m_average=_round_for_response(previous_average),
            latest_3m_average=_round_for_response(latest_average),
            reason="PREVIOUS_3M_AVERAGE_ZERO",
        )

    percent = (latest_average - previous_average) / previous_average * _HUNDRED
    if percent > 0:
        direction = TrendDirection.UP
    elif percent < 0:
        direction = TrendDirection.DOWN
    else:
        direction = TrendDirection.FLAT
    return SalesRecentTrend(
        percent=_round_for_response(percent),
        direction=direction,
        basis=TREND_BASIS,
        previous_3m_average=_round_for_response(previous_average),
        latest_3m_average=_round_for_response(latest_average),
        reason=None,
    )


def _month_over_month(
    monthly: list[tuple[str, Decimal, int]],
) -> tuple[Decimal | None, str | None]:
    if len(monthly) < 2:
        return None, "INSUFFICIENT_MONTHS"
    previous, latest = monthly[-2], monthly[-1]
    if not _are_consecutive([previous[0], latest[0]]):
        return None, "NON_CONTIGUOUS_MONTHS"
    if previous[1] == 0:
        return None, "PREVIOUS_MONTH_SALES_ZERO"
    return (latest[1] - previous[1]) / previous[1] * _HUNDRED, None


def _month_summary(item: tuple[str, Decimal, int]) -> SalesMonthSummary:
    return SalesMonthSummary(
        month=item[0],
        sales=_round_for_response(item[1]),
        transaction_count=item[2],
    )


def _missing_months(months: list[str]) -> list[str]:
    observed = set(months)
    current = _parse_month(months[0])
    end = _parse_month(months[-1])
    missing: list[str] = []
    while current <= end:
        month = f"{current[0]:04d}-{current[1]:02d}"
        if month not in observed:
            missing.append(month)
        current = _next_month(current)
    return missing


def _are_consecutive(months: list[str]) -> bool:
    parsed = [_parse_month(month) for month in months]
    return all(
        current == _next_month(previous)
        for previous, current in zip(parsed, parsed[1:])
    )


def _parse_month(value: str) -> tuple[int, int]:
    year_text, month_text = value.split("-", maxsplit=1)
    return int(year_text), int(month_text)


def _next_month(value: tuple[int, int]) -> tuple[int, int]:
    year, month = value
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _round_for_response(value: Decimal) -> float:
    rounded = value.quantize(_TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
    if rounded == 0:
        return 0.0
    return float(rounded)
