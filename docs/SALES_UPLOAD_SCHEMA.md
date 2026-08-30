# FinBridge Sales Upload Schema

Last Updated: 2026-08-30

이 문서는 소상공인 매출장표 실제 업로드 분석의 지원 범위와 deterministic 계산 계약을 고정한다.
범용 회계 파일 해석, LLM column inference, 매출 예측은 지원하지 않는다.

# 1. API

```text
POST /sales-analysis/analyze
Content-Type: multipart/form-data
Field: file
```

정상 분석은 실제 업로드 파일 결과이므로 `is_demo=false`, 화폐 단위는 `KRW`를 반환한다.
파일 원문과 row 데이터는 DB에 저장하거나 LLM에 전달하지 않는다.

# 2. Supported Files and Limits

지원:

- `.csv`: UTF-8, UTF-8-SIG, CP949를 `utf-8-sig → cp949` 순서로 시도
- `.xlsx`: openpyxl read-only/data-only mode와 defusedxml 보호 사용

미지원:

- `.xls`, `.xlsm`, `.ods` 및 기타 확장자

Resource limit:

- 최대 파일 크기: 5 MB (`5 * 1024 * 1024` bytes)
- 최대 데이터 행: 50,000
- 완전히 빈 행은 데이터 행에서 제외
- required 값이 비어 있거나 잘못된 행은 skip하지 않고 전체 요청을 실패 처리

사용자 filename은 확장자 확인에만 사용하며 서버 path로 사용하지 않는다.

# 3. FinBridge Sample Schema

Canonical required columns:

```text
transaction_date
sales_amount
```

Canonical optional columns:

```text
transaction_id
category
```

명시적 alias:

| Alias | Canonical |
| --- | --- |
| 거래일자, 매출일자 | transaction_date |
| 매출액, 판매금액 | sales_amount |
| 거래ID, 거래번호 | transaction_id |
| 카테고리, 분류 | category |

Header 앞뒤 whitespace는 제거한다. fuzzy matching과 대소문자 추론은 하지 않는다.
동일 canonical로 해석되는 column이 둘 이상이면 `COLUMN_CONFLICT`로 거부한다.
추가 column은 분석에서 제외하고 `data_quality.ignored_columns`에 기록한다.

# 4. XLSX Sheet Selection

각 worksheet의 첫 non-empty row를 header로 검사한다.

1. required columns를 만족하는 worksheet가 정확히 하나면 해당 sheet를 사용한다.
2. 만족하는 worksheet가 없으면 `REQUIRED_COLUMN_MISSING`을 반환한다.
3. 만족하는 worksheet가 둘 이상이면 임의 선택하지 않고 `MULTIPLE_VALID_SHEETS`를 반환한다.
4. 선택한 worksheet 이름은 `data_quality.sheet_name`에 반환한다.

# 5. Field Validation

## transaction_date

CSV와 문자열 XLSX cell:

```text
YYYY-MM-DD
YYYY/MM/DD
```

XLSX native date/datetime cell도 허용한다. 애매한 날짜 형식은 추론하지 않는다.
오류가 한 행이라도 있으면 `INVALID_DATE`와 1-based physical row number를 반환한다.

## sales_amount

허용:

- int, finite float, Decimal
- 숫자 문자열: `1200000`, `1,200,000`
- 0

불허:

- 음수
- NaN, Infinity
- 빈 값, boolean
- 통화 단위가 포함되거나 comma grouping이 잘못된 문자열

음수 환불·취소 거래는 현재 Sample Schema에서 지원하지 않으며 `NEGATIVE_SALES_AMOUNT`로 거부한다.
값을 임의로 0으로 보정하지 않는다.

# 6. Aggregation and Metrics

`transaction_date`를 기준으로 `YYYY-MM` 집계 후 월 오름차순으로 정렬한다.

월별:

- `sales`: 해당 월 `sales_amount` 합계
- `transaction_count`: 해당 월 valid row 수

달력상 중간 month가 없더라도 0원 month를 생성하지 않는다. 누락 month는
`data_quality.missing_months`와 `warnings`에 표시한다.

Summary:

- `total_sales`: 전체 valid row 매출 합계
- `average_monthly_sales` / `avg`: 관측된 month별 매출 평균
- `latest_month_sales`: 가장 최근 관측 month 매출
- `highest_month`, `lowest_month`: 최고·최저 월; 동률이면 시간상 먼저인 month
- `months_covered`: 실제 관측 month 수
- `transaction_count`: 전체 valid row 수

Variability는 월별 매출 모집단 기준이다.

```text
mean = Σ(month_sales) / N
variance = Σ(month_sales - mean)^2 / N
standard_deviation = sqrt(variance)
CV(%) = standard_deviation / mean * 100
```

`mean == 0`이면 CV는 `null`이다. 등급·점수·threshold는 생성하지 않는다.

# 7. Recent Trend and Month-over-Month

최근 관측 6개 month가 달력상 연속일 때:

```text
previous_3m_average = 앞 3개월 평균
latest_3m_average = 뒤 3개월 평균
recent_trend_percent =
  (latest_3m_average - previous_3m_average) / previous_3m_average * 100
```

- 양수 `UP`, 음수 `DOWN`, 0 `FLAT`
- 6개월 미만 또는 gap 존재 시 `UNKNOWN`, percent `null`
- `previous_3m_average == 0`이면 `UNKNOWN`, percent `null`
- 계산 불가 이유는 `recent_trend.reason`에 반환

MoM은 가장 최근 month와 직전 달력 month가 모두 존재할 때 계산한다.

```text
mom_change_percent = (latest - previous) / previous * 100
```

month gap, 2개월 미만, `previous == 0`이면 `null`이며 `mom_change_reason`을 반환한다.

# 8. Rounding

모든 내부 금액·비율 계산은 `Decimal` precision 50을 사용한다.
중간값을 반올림하지 않고 최종 응답에서만 소수 둘째 자리 `ROUND_HALF_UP`을 적용한다.

# 9. Response Contract

최상위 호환 field:

```text
monthly_series
avg
recent_trend
variability
is_demo
```

추가 field:

```text
currency
summary
mom_change_percent
mom_change_reason
data_quality
warnings
disclaimer
```

`avg`와 `summary.average_monthly_sales`는 동일하다.

Data quality:

```text
source_format
sheet_name
rows_received
rows_analyzed
months_covered
first_transaction_date
last_transaction_date
missing_months
ignored_columns
```

# 10. Error Contract

기능 validation 오류는 FastAPI `detail` 아래에 다음 구조로 반환한다.

```json
{
  "detail": {
    "error_code": "INVALID_DATE",
    "message": "transaction_date must use YYYY-MM-DD or YYYY/MM/DD",
    "row_number": 2,
    "field": "transaction_date",
    "reason": "UNSUPPORTED_OR_INVALID_DATE"
  }
}
```

주요 error code:

- `UNSUPPORTED_FILE_TYPE` — HTTP 415
- `FILE_TOO_LARGE` — HTTP 413
- `EMPTY_FILE`, `EMPTY_DATA`
- `REQUIRED_COLUMN_MISSING`, `COLUMN_CONFLICT`, `MULTIPLE_VALID_SHEETS`
- `INVALID_DATE`, `INVALID_SALES_AMOUNT`, `NEGATIVE_SALES_AMOUNT`
- `ROW_LIMIT_EXCEEDED` — HTTP 413
- `PARSE_ERROR`

# 11. Limitations

- Sample Schema 밖의 회계파일 자동 해석 없음
- 음수 환불·취소 거래 미지원
- 누락 month 매출을 0으로 추정하지 않음
- 다른 통화 추론·환산 없음
- 세금·비용·이익·부채 추론 없음
- 회계·세무 판단, 신용평가, 미래 매출 예측 없음
- OCR, LLM, ML, DB 저장, 회원별 파일 보관 없음
