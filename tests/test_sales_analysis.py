from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.calculation.sales_analysis import (
    DISCLAIMER,
    calculate_sales_analysis,
)
from app.data.sales_upload import (
    MAX_DATA_ROWS,
    MAX_FILE_BYTES,
    SalesUploadError,
    parse_sales_upload,
)
from tests.conftest import ASGITestClient


SAMPLE_CSV_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "sales_analysis_sample.csv"
)


def csv_bytes(
    rows: list[tuple[str, str | int | float]],
    *,
    header: str = "transaction_date,sales_amount",
    encoding: str = "utf-8",
) -> bytes:
    lines = [header, *(f'{transaction_date},"{amount}"' for transaction_date, amount in rows)]
    return ("\n".join(lines) + "\n").encode(encoding)


def parsed_months(amounts: list[int], months: list[str] | None = None):
    month_names = months or [f"2026-{index:02d}" for index in range(1, len(amounts) + 1)]
    rows = [
        (f"{month}-15", amount)
        for month, amount in zip(month_names, amounts)
    ]
    return parse_sales_upload(filename="sales.csv", content=csv_bytes(rows))


def workbook_bytes(
    sheets: list[tuple[str, list[object], list[list[object]]]],
) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, headers, rows in sheets:
        worksheet = workbook.create_sheet(sheet_name)
        worksheet.append(headers)
        for row in rows:
            worksheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def assert_error(
    exc_info: pytest.ExceptionInfo[SalesUploadError], error_code: str
) -> SalesUploadError:
    assert exc_info.value.error_code == error_code
    return exc_info.value


def test_utf8_csv_and_summary_metrics() -> None:
    upload = parse_sales_upload(
        filename="sales.csv",
        content=SAMPLE_CSV_PATH.read_bytes(),
    )
    result = calculate_sales_analysis(upload)

    assert result.is_demo is False
    assert result.currency == "KRW"
    assert result.avg == 1_250_000
    assert result.summary.total_sales == 7_500_000
    assert result.summary.average_monthly_sales == result.avg
    assert result.summary.latest_month_sales == 1_500_000
    assert result.summary.highest_month.month == "2026-06"
    assert result.summary.lowest_month.month == "2026-01"
    assert result.summary.months_covered == 6
    assert result.summary.transaction_count == 6
    assert result.recent_trend.percent == 27.27
    assert result.recent_trend.direction == "UP"
    assert result.variability.standard_deviation == 170_782.51
    assert result.variability.coefficient_of_variation_percent == 13.66
    assert result.mom_change_percent == 7.14
    assert result.disclaimer == DISCLAIMER


def test_utf8_sig_csv_is_supported() -> None:
    content = csv_bytes([("2026-01-01", 100)]).decode("utf-8").encode("utf-8-sig")

    upload = parse_sales_upload(filename="sales.csv", content=content)

    assert upload.source_format == "CSV"
    assert upload.rows[0].sales_amount == 100


def test_cp949_korean_alias_headers_are_supported() -> None:
    content = csv_bytes(
        [("2026/01/01", 100)],
        header="거래일자,매출액",
        encoding="cp949",
    )

    upload = parse_sales_upload(filename="sales.csv", content=content)

    assert upload.rows[0].transaction_date == date(2026, 1, 1)
    assert upload.rows[0].sales_amount == 100


def test_comma_amount_and_extra_column_are_supported_and_recorded() -> None:
    content = (
        'transaction_date,sales_amount,memo\n2026-01-01,"1,200,000",ignored\n'
    ).encode()

    upload = parse_sales_upload(filename="sales.csv", content=content)

    assert upload.rows[0].sales_amount == 1_200_000
    assert upload.ignored_columns == ["memo"]


def test_empty_file_is_rejected() -> None:
    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=b"")

    assert_error(exc_info, "EMPTY_FILE")


def test_empty_data_rows_are_rejected() -> None:
    content = b"transaction_date,sales_amount\n,\n\n"

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=content)

    assert_error(exc_info, "EMPTY_DATA")


@pytest.mark.parametrize("filename", ["sales.xls", "sales.xlsm", "sales.ods", "sales.txt"])
def test_unsupported_extensions_are_rejected(filename: str) -> None:
    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename=filename, content=b"not-empty")

    error = assert_error(exc_info, "UNSUPPORTED_FILE_TYPE")
    assert error.status_code == 415


def test_file_size_limit_is_enforced_before_parsing() -> None:
    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(
            filename="sales.csv",
            content=b"x" * (MAX_FILE_BYTES + 1),
        )

    error = assert_error(exc_info, "FILE_TOO_LARGE")
    assert error.status_code == 413


def test_required_column_missing_is_rejected() -> None:
    content = b"transaction_date,category\n2026-01-01,online\n"

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=content)

    error = assert_error(exc_info, "REQUIRED_COLUMN_MISSING")
    assert error.field == "sales_amount"


def test_canonical_and_alias_column_conflict_is_rejected() -> None:
    content = (
        "transaction_date,거래일자,sales_amount\n"
        "2026-01-01,2026-01-01,100\n"
    ).encode("utf-8")

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=content)

    error = assert_error(exc_info, "COLUMN_CONFLICT")
    assert error.field == "transaction_date"


def test_invalid_date_reports_row_and_field() -> None:
    content = csv_bytes([("01/02/2026", 100)])

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=content)

    error = assert_error(exc_info, "INVALID_DATE")
    assert error.row_number == 2
    assert error.field == "transaction_date"


@pytest.mark.parametrize("amount", ["", "NaN", "Infinity", "KRW 1000", "12,34"])
def test_invalid_sales_amount_is_rejected(amount: str) -> None:
    content = csv_bytes([("2026-01-01", amount)])

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=content)

    error = assert_error(exc_info, "INVALID_SALES_AMOUNT")
    assert error.row_number == 2
    assert error.field == "sales_amount"


def test_negative_sales_amount_is_rejected() -> None:
    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(
            filename="sales.csv",
            content=csv_bytes([("2026-01-01", -1)]),
        )

    assert_error(exc_info, "NEGATIVE_SALES_AMOUNT")


def test_zero_sales_amount_is_valid() -> None:
    upload = parse_sales_upload(
        filename="sales.csv",
        content=csv_bytes([("2026-01-01", 0)]),
    )

    assert upload.rows[0].sales_amount == 0


def test_malformed_csv_is_rejected() -> None:
    content = b'transaction_date,sales_amount\n"2026-01-01,100\n'

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=content)

    assert_error(exc_info, "PARSE_ERROR")


def test_row_limit_accepts_boundary() -> None:
    row = "2026-01-01,1\n"
    content = ("transaction_date,sales_amount\n" + row * MAX_DATA_ROWS).encode()

    upload = parse_sales_upload(filename="sales.csv", content=content)

    assert upload.rows_received == MAX_DATA_ROWS
    assert len(upload.rows) == MAX_DATA_ROWS


def test_row_limit_rejects_first_excess_row() -> None:
    row = "2026-01-01,1\n"
    content = ("transaction_date,sales_amount\n" + row * (MAX_DATA_ROWS + 1)).encode()

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.csv", content=content)

    error = assert_error(exc_info, "ROW_LIMIT_EXCEEDED")
    assert error.status_code == 413
    assert error.row_number == MAX_DATA_ROWS + 2


def test_month_gap_is_not_filled_and_is_reported() -> None:
    result = calculate_sales_analysis(
        parsed_months([100, 300], months=["2026-01", "2026-03"])
    )

    assert [item.month for item in result.monthly_series] == ["2026-01", "2026-03"]
    assert result.data_quality.missing_months == ["2026-02"]
    assert result.recent_trend.reason == "INSUFFICIENT_MONTHS"
    assert result.mom_change_percent is None
    assert result.mom_change_reason == "NON_CONTIGUOUS_MONTHS"
    assert result.warnings == ["MISSING_CALENDAR_MONTHS: 2026-02"]


def test_xlsx_native_date_and_metadata_are_supported() -> None:
    content = workbook_bytes(
        [
            (
                "Sales",
                ["transaction_date", "sales_amount", "memo"],
                [[datetime(2026, 1, 2, 10, 30), 1000, "ignored"]],
            )
        ]
    )

    upload = parse_sales_upload(filename="sales.xlsx", content=content)
    result = calculate_sales_analysis(upload)

    assert upload.sheet_name == "Sales"
    assert upload.rows[0].transaction_date == date(2026, 1, 2)
    assert result.data_quality.source_format == "XLSX"
    assert result.data_quality.sheet_name == "Sales"
    assert result.data_quality.ignored_columns == ["memo"]


def test_xlsx_native_float_amount_is_supported() -> None:
    content = workbook_bytes(
        [
            (
                "Sales",
                ["transaction_date", "sales_amount"],
                [[date(2026, 1, 1), 123.45]],
            )
        ]
    )

    upload = parse_sales_upload(filename="sales.xlsx", content=content)

    assert upload.rows[0].sales_amount == Decimal("123.45")


def test_xlsx_boolean_amount_is_rejected() -> None:
    content = workbook_bytes(
        [
            (
                "Sales",
                ["transaction_date", "sales_amount"],
                [[date(2026, 1, 1), True]],
            )
        ]
    )

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.xlsx", content=content)

    assert_error(exc_info, "INVALID_SALES_AMOUNT")


def test_xlsx_missing_columns_is_rejected() -> None:
    content = workbook_bytes([("Sheet1", ["date", "amount"], [["2026-01-01", 1]])])

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.xlsx", content=content)

    assert_error(exc_info, "REQUIRED_COLUMN_MISSING")


def test_malformed_xlsx_is_rejected() -> None:
    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.xlsx", content=b"not-an-xlsx")

    assert_error(exc_info, "PARSE_ERROR")


def test_xlsx_selects_only_matching_sheet() -> None:
    content = workbook_bytes(
        [
            ("Instructions", ["description"], [["FinBridge schema"]]),
            (
                "Sales",
                ["transaction_date", "sales_amount"],
                [[date(2026, 1, 1), 100]],
            ),
        ]
    )

    upload = parse_sales_upload(filename="sales.xlsx", content=content)

    assert upload.sheet_name == "Sales"


def test_xlsx_rejects_multiple_matching_sheets() -> None:
    content = workbook_bytes(
        [
            ("Sales1", ["transaction_date", "sales_amount"], [[date(2026, 1, 1), 100]]),
            ("Sales2", ["거래일자", "매출액"], [[date(2026, 2, 1), 200]]),
        ]
    )

    with pytest.raises(SalesUploadError) as exc_info:
        parse_sales_upload(filename="sales.xlsx", content=content)

    error = assert_error(exc_info, "MULTIPLE_VALID_SHEETS")
    assert error.context["sheet_names"] == ["Sales1", "Sales2"]


@pytest.mark.parametrize(
    ("amounts", "expected_percent", "expected_direction"),
    [
        ([100, 100, 100, 200, 200, 200], 100.0, "UP"),
        ([200, 200, 200, 100, 100, 100], -50.0, "DOWN"),
        ([100, 100, 100, 100, 100, 100], 0.0, "FLAT"),
    ],
)
def test_recent_trend_directions(
    amounts: list[int], expected_percent: float, expected_direction: str
) -> None:
    result = calculate_sales_analysis(parsed_months(amounts))

    assert result.recent_trend.percent == expected_percent
    assert result.recent_trend.direction == expected_direction
    assert result.recent_trend.reason is None


def test_recent_trend_previous_average_zero_is_unknown() -> None:
    result = calculate_sales_analysis(parsed_months([0, 0, 0, 100, 100, 100]))

    assert result.recent_trend.percent is None
    assert result.recent_trend.direction == "UNKNOWN"
    assert result.recent_trend.previous_3m_average == 0
    assert result.recent_trend.latest_3m_average == 100
    assert result.recent_trend.reason == "PREVIOUS_3M_AVERAGE_ZERO"


def test_recent_trend_under_six_months_is_unknown() -> None:
    result = calculate_sales_analysis(parsed_months([100] * 5))

    assert result.recent_trend.percent is None
    assert result.recent_trend.direction == "UNKNOWN"
    assert result.recent_trend.reason == "INSUFFICIENT_MONTHS"


def test_recent_trend_with_gap_in_latest_six_is_unknown() -> None:
    result = calculate_sales_analysis(
        parsed_months(
            [100] * 6,
            months=["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-07"],
        )
    )

    assert result.recent_trend.percent is None
    assert result.recent_trend.direction == "UNKNOWN"
    assert result.recent_trend.reason == "NON_CONTIGUOUS_MONTHS"


def test_variability_uses_population_formula() -> None:
    result = calculate_sales_analysis(parsed_months([0, 100]))

    assert result.avg == 50
    assert result.variability.standard_deviation == 50
    assert result.variability.coefficient_of_variation_percent == 100
    assert result.variability.basis == "MONTHLY_SALES_POPULATION"


def test_zero_monthly_mean_returns_null_cv() -> None:
    result = calculate_sales_analysis(parsed_months([0, 0]))

    assert result.avg == 0
    assert result.variability.standard_deviation == 0
    assert result.variability.coefficient_of_variation_percent is None


def test_month_over_month_previous_zero_returns_reason() -> None:
    result = calculate_sales_analysis(parsed_months([0, 100]))

    assert result.mom_change_percent is None
    assert result.mom_change_reason == "PREVIOUS_MONTH_SALES_ZERO"


def test_highest_and_lowest_month_ties_use_earliest_month() -> None:
    result = calculate_sales_analysis(parsed_months([100, 100]))

    assert result.summary.highest_month.month == "2026-01"
    assert result.summary.lowest_month.month == "2026-01"


def test_money_rounding_is_two_decimal_half_up() -> None:
    result = calculate_sales_analysis(
        parse_sales_upload(
            filename="sales.csv",
            content=csv_bytes(
                [("2026-01-01", "0.01"), ("2026-02-01", "0.02")]
            ),
        )
    )

    assert result.avg == 0.02


def test_api_multipart_upload_returns_required_contract(
    client: ASGITestClient,
) -> None:
    response = client.post(
        "/sales-analysis/analyze",
        files={
            "file": (
                "sales.csv",
                SAMPLE_CSV_PATH.read_bytes(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_demo"] is False
    assert payload["currency"] == "KRW"
    assert payload["monthly_series"]
    assert payload["avg"] == payload["summary"]["average_monthly_sales"]
    assert payload["recent_trend"]["basis"] == "LATEST_3M_VS_PREVIOUS_3M"
    assert payload["variability"]["basis"] == "MONTHLY_SALES_POPULATION"
    assert payload["data_quality"]["rows_analyzed"] == 6
    assert payload["data_quality"]["first_transaction_date"] == "2026-01-10"
    assert payload["data_quality"]["last_transaction_date"] == "2026-06-10"
    assert payload["disclaimer"] == DISCLAIMER


def test_api_returns_structured_validation_error(client: ASGITestClient) -> None:
    response = client.post(
        "/sales-analysis/analyze",
        files={
            "file": (
                "sales.csv",
                csv_bytes([("invalid", 100)]),
                "text/csv",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "error_code": "INVALID_DATE",
        "message": "transaction_date must use YYYY-MM-DD or YYYY/MM/DD",
        "row_number": 2,
        "field": "transaction_date",
        "reason": "UNSUPPORTED_OR_INVALID_DATE",
    }
