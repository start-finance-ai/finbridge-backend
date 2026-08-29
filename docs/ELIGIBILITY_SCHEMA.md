# Bizinfo Eligibility Schema v0.1 Draft

Status: DRAFT / NOT FROZEN

Scope: Schema design only

Evidence date: 2026-08-28

이 문서는 기업마당 지원사업의 자격조건을 향후 Deterministic Matching Engine이 소비할 수 있는 최소 구조로 정의한다.

아직 Python Schema, Pydantic Model, JSON Schema, DB Table, API Model 또는 Matching Engine을 구현한 것이 아니다. 팀 검토와 추가 Human Validation 전까지 확정 Ground Truth로 취급하지 않는다.

# 1. 목적

Eligibility Schema v0.1의 목적은 다음 흐름에서 `자격조건 구조화`와 `Deterministic Matching` 사이의 계약 경계를 정의하는 것이다.

```text
사용자 상황
→ 실제 지원사업 탐색
→ 자격조건 구조화
→ Deterministic Matching
→ Evidence 검증
→ AI 설명
```

이 Schema는 LLM 또는 Regex가 자유 형식 문장을 저장하는 용도가 아니다. 어떤 대상에 대한 어떤 조건인지, 포함인지 제외인지, 실제 신청자격인지 계산·사후·문맥 정보인지, 어떤 Evidence에 근거하는지를 명시적으로 구분한다.

# 2. 범위 / Non-goals

## 2.1 범위

v0.1은 다음을 정의한다.

* Program-level Eligibility 구조
* 최소 Condition 필드와 타입
* 현재 검토된 12개 condition type의 Normalized 이름
* AND / OR 및 전역 제외 표현
* Evidence와 추출 상태 규칙
* 향후 Matching 결과 상태의 경계
* 48건 Review Pack Human Evidence의 표현 가능성

## 2.2 Non-goals

v0.1에서는 다음을 하지 않는다.

* Regex 개선 또는 새로운 추출 규칙 작성
* LLM Extractor 구현
* Matching Engine 구현
* User Profile Schema 확정
* 행정구역·업종·자격증의 최종 표준 코드 체계 확정
* 신청기간 또는 지원금액 Schema 통합
* 금융한도·상환조건 계산식 구현
* 임의 confidence 점수 도입
* 범용 Rule Engine 또는 재귀 Expression Tree 설계
* DB, API, Pydantic, JSON Schema 구현

# 3. 실험 근거

v0.1은 다음 실제 자료를 근거로 한다.

* 기업마당 금융 100건, 창업 73건, 경영 100건: 총 273건
* 273건 전체 Field / Eligibility Candidate / Period / Amount 자동 Profile
* 12 condition type × (`REGEX_CANDIDATE` 3건 + `NEGATIVE_CONTROL` 1건)
* AI-assisted human-reviewed evaluation set: 총 48건
* Baseline Review-Pack 결과: TP 27 / FP 9 / TN 9 / FN 3
* `candidate_precision_proxy`: 75.00%
* `review_pack_negative_control_false_negative_rate`: 25.00%

48건은 stratified Human-reviewed Review Pack이며 독립 무작위 표본이나 독립 전문가 Gold Standard가 아니다. 위 수치를 전체 273건의 precision, recall 또는 accuracy로 일반화하지 않는다.

실험에서 확인된 핵심 문제는 다음과 같다.

* 기관명·사업명과 실제 지역 Eligibility의 혼동
* `21세기`, `2026 세종` 등 숫자 문맥의 연령 오탐
* 부정·배제 방향의 반전
* 금융 거치·상환기간과 사업 업력의 혼동
* `개월` 단위 업력 미탐
* 열거형 산업·제품 범주 미탐
* 제외형 사업자 유형 미탐
* Eligibility와 금융한도 계산 문맥의 혼동
* 신청 대상과 지원내용의 성별 표현 혼동
* 사전 보유 자격과 선정 후 부여되는 인증의 혼동

# 4. 설계 원칙

1. Evidence 없는 값을 생성하지 않는다.
2. 원문이 불명확하면 숫자·단위·대상·방향을 임의 보정하지 않는다.
3. 결측값을 `0`, 빈 문자열, 평균값 또는 임의 Enum으로 대체하지 않는다.
4. `subject`, `polarity`, `condition_role`을 분리한다.
5. 추출 방식과 추출·검토 상태를 분리한다.
6. Matching에는 명시적으로 허용된 role과 `SUPPORTED` Condition만 참여한다.
7. 사용자 값이 없거나 Source가 불명확하면 `NO_MATCH`로 처리하지 않는다.
8. 원문 표현은 `raw_value`와 `evidence_text`로 보존하고, 비교 가능한 값만 별도 필드에 정규화한다.
9. `hashtags`는 Eligibility Evidence로 사용하지 않는다.
10. Schema는 오류를 표현하고 차단할 경계를 제공하지만, Extractor의 의미 판독 정확성을 자동으로 보장하지 않는다.

# 5. Program-level Eligibility 구조

## 5.1 최종 v0.1 구조

```json
{
  "eligibility_schema_version": "0.1",
  "program_id": "PBLN_xxx",
  "source_url": "https://example.invalid/program",
  "eligibility_extraction_status": "SUPPORTED",
  "common_conditions": [],
  "eligibility_groups": [
    {
      "group_id": "G1",
      "conditions": []
    }
  ],
  "global_exclusions": [],
  "non_eligibility_conditions": []
}
```

| 필드 | 타입 | 필수 | 의미 |
| --- | --- | --- | --- |
| `eligibility_schema_version` | string | Yes | Draft 호환성 식별자. v0.1은 `0.1` |
| `program_id` | string | Yes | 상위 Program 식별자 |
| `source_url` | string 또는 null | Yes | 상위 Program 원출처. Source에 없을 때만 null |
| `eligibility_extraction_status` | enum | Yes | Program 전체 자격조건 구조화 상태 |
| `common_conditions` | Condition[] | Yes | 모든 허용 경로에 공통으로 적용되는 AND 조건 |
| `eligibility_groups` | EligibilityGroup[] | Yes | Group 내부 AND, Group 사이 OR |
| `global_exclusions` | Condition[] | Yes | 모든 허용 경로보다 우선하는 전역 제외 조건 |
| `non_eligibility_conditions` | Condition[] | Yes | 계산·사후·문맥 보존용. Matching 제외 |

`program_id`와 `source_url`은 Program 상위 객체에서 한 번만 보존한다. 각 Condition에 반복 저장하지 않는다.

## 5.2 논리식

v0.1의 허용 판단 구조는 다음과 같다.

```text
no global_exclusion is triggered
AND
all common_conditions
AND
(
  eligibility_groups가 비어 있으면 TRUE
  또는
  any eligibility_group where all group.conditions match
)
```

특정 `condition_type`의 Condition이 없다는 사실은 그 유형의 제한이 없다는 뜻이다. 예를 들어 공고에 성별 제한이 실제로 없으면 `gender` Condition을 만들지 않으며, 사용자의 성별 값이 없어도 그 이유로 `UNKNOWN`이 되지 않는다.

`common_conditions`와 `eligibility_groups`가 모두 비어 있다는 사실만으로 결과를 결정하지 않는다.

* 확보한 공식 Evidence 범위에서 자격 제한이 실제로 없다고 확인되어 Program-level 상태가 `SUPPORTED`라면, Eligibility 식은 `global_exclusions`를 제외하고 `TRUE`다. 빈 조건 때문에 `UNKNOWN`을 만들지 않는다.
* 본문·별첨 등 필요한 Evidence가 없어서 비어 있다면 Program-level 상태는 `UNKNOWN` 또는 `NEEDS_REVIEW`이며, `MATCH`로 단정하지 않는다.

## 5.3 EligibilityGroup

| 필드 | 타입 | 필수 | 의미 |
| --- | --- | --- | --- |
| `group_id` | string | Yes | Program 내 고유 Group ID |
| `conditions` | Condition[] | Yes | 모두 충족해야 하는 AND 조건 |

v0.1은 Group 중첩을 허용하지 않는다. 더 복잡한 괄호식은 DNF 형태로 펼칠 수 있을 때만 저장하고, 안전하게 펼칠 수 없으면 `NEEDS_REVIEW`로 남긴다.

# 6. Condition Schema

## 6.1 최종 Condition 필드

| 필드 | 목적 | 데이터 타입 | Nullable | 허용값 / 검증 규칙 | Matching 사용 |
| --- | --- | --- | --- | --- | --- |
| `condition_id` | Program 내 조건 식별 및 Evidence 추적 | string | No | Program 내 unique | 간접 사용 |
| `condition_type` | 비교할 속성 종류 | enum | No | §7.1의 12개 Normalized type | Yes |
| `subject` | 조건이 적용되는 대상 | enum | No | §7.2 | Yes |
| `operator` | 비교 연산 | enum | No | §7.3 | Yes |
| `raw_value` | 원문 조건값 표현 보존 | string | No | `SUPPORTED`이면 non-empty | Evidence / 감사 |
| `value` | 단일 정규화 값 | string, number, boolean, null | Yes | Operator별 상호배타 규칙 | Yes |
| `values` | 복수 정규화 값 | array 또는 null | Yes | `IN`에서만 non-empty | Yes |
| `min_value` | 포함형 범위의 하한 | number 또는 null | Yes | `BETWEEN`에서만 사용 | Yes |
| `max_value` | 포함형 범위의 상한 | number 또는 null | Yes | `BETWEEN`에서만 사용 | Yes |
| `unit` | 숫자 의미와 비교 단위 | enum | No | §7.4, 범주형은 `NONE` | Yes |
| `polarity` | 포함·제외 방향 | enum | No | §7.5 | Yes |
| `condition_role` | 실제 Eligibility인지 다른 문맥인지 구분 | enum | No | §7.6 | Matching 참여 결정 |
| `evidence_text` | 판단 근거 원문 구절 | string | No | 모든 Condition에서 non-empty | Evidence Validation |
| `source_field` | Evidence가 나온 Source field | string | No | 실제 Source field명 | Evidence Validation |
| `evidence_start` | 정규화된 Source text 기준 시작 offset | integer 또는 null | Yes | 0 이상, 현재 CSV에는 없음 | No |
| `evidence_end` | 정규화된 Source text 기준 종료 offset | integer 또는 null | Yes | start보다 큼, 현재 CSV에는 없음 | No |
| `extraction_method` | Condition 생성 방식 | enum | No | §7.7 | No |
| `extraction_status` | 의미 구조화·검토 상태 | enum | No | §7.8 | Matching 참여 결정 |

## 6.2 Value shape 규칙

한 Condition은 다음 중 하나의 operand 형태만 사용한다.

| Operator | 사용 필드 | 사용하지 않는 필드 |
| --- | --- | --- |
| `EQ`, `GT`, `GTE`, `LT`, `LTE` | `value` | `values`, `min_value`, `max_value` |
| `IN` | `values` | `value`, `min_value`, `max_value` |
| `BETWEEN` | `min_value`, `max_value` | `value`, `values` |
| `EXISTS` | 없음 | `value`, `values`, `min_value`, `max_value` |

`BETWEEN`의 양 끝은 포함한다. `0원 초과 5천만원 이하`처럼 경계 포함 여부가 다르면 `GT 0`과 `LTE 50000000` 두 Condition으로 나눈다.

## 6.3 `raw_value`와 Normalized 값

별도 `normalized_value` 객체는 v0.1에서 추가하지 않는다. `operator`, `value`, `values`, `min_value`, `max_value`, `unit`의 조합 자체가 Normalized 값이다.

예:

```json
{
  "raw_value": "5인 미만",
  "operator": "LT",
  "value": 5,
  "values": null,
  "min_value": null,
  "max_value": null,
  "unit": "PERSON"
}
```

원문과 정규화 결과가 충돌하면 원문 Evidence가 우선하며 Condition은 `NEEDS_REVIEW` 또는 `UNSUPPORTED`로 내려야 한다.

# 7. Enum 정의

## 7.1 `condition_type`

| Analyzer type | Normalized Schema type | 결정 |
| --- | --- | --- |
| `region_or_location` | `region_or_location` | 유지. `subject`로 신청자 거주지와 사업장 소재지를 구분 |
| `explicit_numeric_age` | `age` | 변경. `explicit_numeric`은 Analyzer 탐지 방식이며 실서비스 의미가 아님 |
| `pre_founder` | `pre_founder` | 유지 |
| `business_registration_status` | `business_registration_status` | 유지 |
| `business_age` | `business_age` | 유지 |
| `industry` | `industry` | 유지 |
| `business_type` | `business_type` | 유지 |
| `sales_or_income` | `sales_or_income` | 유지 |
| `employee_count` | `employee_count` | 유지 |
| `gender` | `gender` | 유지 |
| `qualification_or_certification` | `qualification_or_certification` | 유지 |
| `education_completion` | `education_completion` | 유지 |

현재 Evidence에 없는 condition type을 미리 확장하지 않는다. 새로운 명시적 조건이 Human Review에서 반복 확인될 때 별도 버전에서 추가한다.

## 7.2 `subject`

| Enum | 의미 | 실제 근거 |
| --- | --- | --- |
| `APPLICANT` | 개인 신청자 또는 예비창업자 | 거주지, 예비창업, 교육 이수 |
| `REPRESENTATIVE` | 기업 대표자 | 대표자 연령·성별 |
| `BUSINESS` | 신청 기업·사업자 | 사업장, 업력, 매출, 직원 수, 기업 유형 |
| `PRODUCT` | 신청 대상 제품 또는 제품 범주 | 농·수·축산물, 식품, 화장품, 공산품 |
| `ORGANIZATION` | 수행기관·제공기관 | 기관명 속 지역·성별 문맥 구분 |
| `FACILITY` | 지원 대상 시설 | 여성전용 시설 지원과 신청자 성별 구분 |
| `PROGRAM` | 사업명·지원내용·금융기간 등 Program 문맥 | `21세기`, 거치·상환기간 등 |

`EMPLOYEE`는 v0.1에서 제외한다. 현재 확인된 `employee_count`는 특정 직원의 속성이 아니라 `BUSINESS`의 상시근로자 수이기 때문이다. 특정 직원 개인이 Eligibility subject인 실제 Evidence가 확인되면 추가한다.

### 7.2.1 Matching role의 type / subject 호환성

`ELIGIBILITY_REQUIRED`와 `ELIGIBILITY_EXCEPTION`에는 다음 조합만 허용한다. 이 표에 없는 조합은 자동 Matching에 참여시키지 않고 `NEEDS_REVIEW`로 보낸다.

| condition_type | 허용 subject |
| --- | --- |
| `region_or_location` | `APPLICANT`, `REPRESENTATIVE`, `BUSINESS` |
| `age` | `APPLICANT`, `REPRESENTATIVE` |
| `pre_founder` | `APPLICANT` |
| `business_registration_status` | `BUSINESS` |
| `business_age` | `BUSINESS` |
| `industry` | `BUSINESS`, `PRODUCT` |
| `business_type` | `BUSINESS` |
| `sales_or_income` | `APPLICANT`, `BUSINESS` |
| `employee_count` | `BUSINESS` |
| `gender` | `APPLICANT`, `REPRESENTATIVE` |
| `qualification_or_certification` | `APPLICANT`, `BUSINESS`, `PRODUCT` |
| `education_completion` | `APPLICANT`, `REPRESENTATIVE` |

`ORGANIZATION`, `FACILITY`, `PROGRAM`은 v0.1에서 Matching role과 결합할 수 없다. 이 subject의 Condition은 `CALCULATION_ONLY`, `POST_SELECTION`, `CONTEXT_ONLY` 중 하나여야 한다.

## 7.3 `operator`

v0.1의 최소 Enum:

* `EQ`
* `GT`
* `GTE`
* `LT`
* `LTE`
* `BETWEEN`
* `IN`
* `EXISTS`

`NE`와 `NOT_IN`은 v0.1에서 제외한다. 부정 연산자와 `polarity=EXCLUDE`를 함께 허용하면 이중 부정으로 방향이 뒤집힐 위험이 있다. 제외는 양의 대상 값과 `EXCLUDE` polarity로만 표현한다.

## 7.4 `unit`

* `NONE`: 범주형·Boolean 값
* `YEAR`: 만 나이 또는 사업 업력의 년 단위
* `MONTH`: 사업 업력의 개월 단위
* `PERSON`: 상시근로자 수
* `KRW`: 매출·소득 금액
* `PERCENT`: 명시적 비율

단위가 다른 값은 Matching 직전에 원값을 보존한 채 정확한 변환 규칙으로 비교한다. `business_age`의 `YEAR`와 `MONTH`를 정수 년으로 반올림하지 않는다. 월 단위로 비교할 수 있는 경우 `YEAR × 12`만 사용하며, Source가 단순히 `2년`이라고 표현한 경우 이를 임의의 일수로 변환하지 않는다.

## 7.5 `polarity`

* `INCLUDE`: 양의 predicate가 참이면 해당 Eligibility 조건을 충족
* `EXCLUDE`: 양의 predicate가 참이면 제외 조건이 발동하여 신청자에게 불리함
* `NOT_APPLICABLE`: Eligibility 방향이 없는 계산·사후·문맥 정보

v0.1의 단일 평가 규칙은 다음과 같다.

```text
predicate_result = evaluate(operator, normalized_operand, user_value)

INCLUDE + predicate_result=TRUE
→ common condition 또는 group condition 충족

INCLUDE + predicate_result=FALSE
→ 해당 common condition 또는 group path 불충족

EXCLUDE + predicate_result=TRUE
→ global exclusion triggered
→ Program NO_MATCH

EXCLUDE + predicate_result=FALSE
→ 해당 exclusion이 발동하지 않음
→ 그 자체로 positive condition을 충족한 것은 아님
```

`EXCLUDE`라고 해서 predicate를 `NOT(...)`으로 다시 뒤집지 않는다. 예를 들어 `법인 제외`는 `EQ CORPORATION`을 한 번 평가하고, 그 결과가 참이면 `EXCLUDE`가 발동한다.

Matching용 `INCLUDE`는 `common_conditions` 또는 `eligibility_groups`에만, Matching용 `EXCLUDE`는 `global_exclusions`에만 둔다. `NOT_APPLICABLE`은 Matching 대상이 아닌 `CALCULATION_ONLY`, `POST_SELECTION`, `CONTEXT_ONLY` role에서만 허용하며 해당 Condition은 `non_eligibility_conditions`에 둔다.

## 7.6 `condition_role`

* `ELIGIBILITY_REQUIRED`: 실제 신청자격 또는 신청 전제조건
* `ELIGIBILITY_EXCEPTION`: 대안 Eligibility Path에 속한 조건임을 설명하는 metadata
* `CALCULATION_ONLY`: 지원금·융자한도·비율 계산에만 사용
* `POST_SELECTION`: 선정 이후 발생하거나 부여되는 조건·결과
* `CONTEXT_ONLY`: 기관명, 사업명, 지원내용 등 설명 문맥

Matching에 참여할 수 있는 role은 `ELIGIBILITY_REQUIRED`, `ELIGIBILITY_EXCEPTION`뿐이다. 다만 Boolean 의미는 role 이름이 아니라 Condition이 놓인 `common_conditions`, `eligibility_groups`, `global_exclusions` 위치로만 결정한다. `ELIGIBILITY_EXCEPTION`은 `eligibility_groups` 안에서만 허용하고, 같은 Group의 다른 Condition처럼 양의 predicate로 평가한다. 이 role 하나만으로 `ELIGIBILITY_REQUIRED` Condition 또는 `global_exclusions`를 override할 수 없다. 나머지 role은 `non_eligibility_conditions`에 저장하고 Matching에서 제외한다.

v0.1에서는 Review Evidence가 대안 경로였음을 보존하기 위해 `ELIGIBILITY_EXCEPTION`을 metadata로 유지한다. Matching Engine이 별도 예외 분기나 우선순위 규칙을 구현하지 않도록 제한함으로써 `eligibility_groups`와의 역할 중복을 제거한다. 향후 이 metadata가 실제 감사·설명에 쓰이지 않는다면 다음 Schema 버전에서 제거할 수 있다.

## 7.7 `extraction_method`

* `STRUCTURED`: Source의 명시적 정형 필드에서 생성
* `REGEX`: Regex baseline이 후보를 생성
* `LLM`: 향후 LLM Extractor가 후보를 생성
* `HUMAN`: 사람이 Evidence에서 직접 구조화

추출 방식은 검증 상태가 아니다. 예를 들어 `extraction_method=REGEX`이면서 Human Review 후 `extraction_status=SUPPORTED`일 수 있다.

## 7.8 `extraction_status`

* `SUPPORTED`: Evidence와 정규화 의미가 명시적으로 일치함
* `NEEDS_REVIEW`: 조건 후보는 있으나 subject, role, 방향, 값 또는 논리구조가 불명확함
* `UNKNOWN`: 조건이 있음을 시사하는 Evidence는 있으나 Source가 조건 구조 또는 값을 충분히 제공하지 않음
* `UNSUPPORTED`: 검토 결과 실제 Condition이 아니거나 Evidence와 정규화 값이 충돌함

`SUPPORTED`는 해당 사용자가 자격을 충족한다는 의미가 아니다. 오직 Condition 구조화가 Evidence로 지지된다는 뜻이다.

임의의 `confidence=0.87`과 같은 확률값은 calibration 근거가 없으므로 v0.1에 포함하지 않는다.

# 8. AND / OR 구조

## 8.1 기본 규칙

* `common_conditions`: 모두 AND
* 한 `eligibility_group.conditions`: 모두 AND
* 여러 `eligibility_groups`: 서로 OR
* `global_exclusions`: 하나라도 사용자와 일치하면 전체 경로에서 제외
* `non_eligibility_conditions`: 논리식에 참여하지 않음

v0.1에서 `polarity=EXCLUDE`인 Matching Condition은 `global_exclusions`에만 둘 수 있다. Group별 조건부 제외는 지원하지 않는다.

Eligibility 경로의 대안은 반드시 별도의 `eligibility_groups`로 표현한다. `ELIGIBILITY_EXCEPTION`은 대안 경로라는 출처 의미를 보존할 뿐, 기존 required condition을 암묵적으로 무효화하지 않는다. 따라서 실제 Boolean semantics는 Group 구조와 `global_exclusions`만으로 결정된다.

## 8.2 OR 실제 사례

Review `BIZ-ELIG-009`의 Evidence:

```text
예비창업자 또는 업력 7년 이내 기창업자
```

표현:

```json
{
  "common_conditions": [],
  "eligibility_groups": [
    {
      "group_id": "G1",
      "conditions": [
        {
          "condition_type": "pre_founder",
          "subject": "APPLICANT",
          "operator": "EQ",
          "value": true,
          "unit": "NONE",
          "polarity": "INCLUDE",
          "condition_role": "ELIGIBILITY_REQUIRED"
        }
      ]
    },
    {
      "group_id": "G2",
      "conditions": [
        {
          "condition_type": "business_age",
          "subject": "BUSINESS",
          "operator": "LTE",
          "value": 7,
          "unit": "YEAR",
          "polarity": "INCLUDE",
          "condition_role": "ELIGIBILITY_REQUIRED"
        }
      ]
    }
  ]
}
```

실제 저장 시 각 Condition에는 §6의 나머지 필수 필드와 Evidence를 모두 포함해야 한다.

## 8.3 전역 제외

`global_exclusions`는 모든 OR 경로에 공통 적용되는 명시적 배제만 저장한다. 특정 Group에서만 적용되는 중첩 제외는 v0.1에서 범용식으로 확장하지 않는다. 안전한 DNF 변환이 불가능하면 `NEEDS_REVIEW`다.

# 9. Evidence 규칙

1. 모든 Condition은 non-empty `evidence_text`와 실제 `source_field`를 가진다.
2. `SUPPORTED`는 Evidence 없이는 허용하지 않는다.
3. `evidence_text`는 정규화된 Source field 안에서 확인할 수 있어야 한다.
4. `raw_value`는 Evidence에서 가져온 조건 표현을 보존한다.
5. Source 전체 문장은 상위 Raw Snapshot에 보존한다. Condition은 필요한 Evidence span만 중복한다.
6. `source_program_id`와 `source_url`은 Program-level에 보존하고 Condition마다 복제하지 않는다.
7. `evidence_start`와 `evidence_end`는 현재 Review CSV에 없으므로 nullable이다. 향후 추가 시 정규화된 Source text의 문자 offset 기준을 사용한다.
8. `hashtags`는 Eligibility Evidence로 사용할 수 없다.
9. Evidence가 Context, 계산 또는 사후 결과만 지지한다면 실제 문구가 맞더라도 `ELIGIBILITY_REQUIRED`로 승격하지 않는다.

# 10. Extraction Status 규칙

## 10.1 Condition 생성

* 명시적 의미와 Evidence가 일치하면 `SUPPORTED`
* 조건 존재는 보이지만 구조가 불명확하면 `NEEDS_REVIEW`
* 조건이 있음을 시사하지만 Source가 세부값·방향을 제공하지 않으면 `UNKNOWN`
* 오탐 또는 의미 충돌이 확인되면 `UNSUPPORTED`

공고에 해당 `condition_type`의 제한이 실제로 없으면 Condition을 생성하지 않는다. 제한의 부재는 Condition-level `UNKNOWN`이 아니며, 다른 Eligibility 조건의 Matching을 방해하지 않는다.

반대로 `지원대상은 별첨 참조`처럼 조건이 존재함을 알 수 있으나 값·방향·범위를 확인할 Evidence가 없으면 이를 제한 부재로 해석하지 않는다. 확인 가능한 Evidence 구절은 `UNKNOWN` 또는 `NEEDS_REVIEW`로 보존하고, Program-level 완전성도 함께 낮춘다. Evidence 구절조차 없어 Condition 객체를 안전하게 만들 수 없다면 임의 placeholder를 생성하지 않고 Program-level 상태로 미확보 범위를 표시한다.

## 10.2 Program-level 상태

Condition-level `extraction_status`는 개별 조건 표현의 근거 상태이고, Program-level `eligibility_extraction_status`는 공고의 Eligibility 구조화 완전성 상태다. 둘은 독립적으로 판정한다.

* `SUPPORTED`: 현재 확보된 공식 Evidence 범위에서 Matching에 필요한 Eligibility 구조화가 완료됨
* `NEEDS_REVIEW`: 조건은 존재하지만 의미, 범위, 예외, AND/OR 관계 또는 별첨 등을 추가 검토해야 함
* `UNKNOWN`: 원문 또는 필요한 Evidence가 부족하여 Eligibility 구조 자체를 충분히 알 수 없음
* `UNSUPPORTED`: 확인된 Eligibility 구조를 현재 Schema v0.1으로 안전하게 표현할 수 없음

일부 Condition이 `SUPPORTED`라고 해서 Program 전체를 자동 `SUPPORTED`로 올리지 않는다. 본문의 두 조건을 올바르게 구조화했더라도 `세부 지원대상은 별첨 참조`이고 별첨을 확보하지 못했다면 Program-level은 `SUPPORTED`가 될 수 없다. 별첨에 조건이 있음을 알지만 검토가 남은 경우 `NEEDS_REVIEW`, 원문·별첨 부재로 Eligibility 범위 자체를 알기 어려운 경우 `UNKNOWN`으로 둔다.

# 11. Matching Boundary

## 11.1 Condition 평가 결과 후보

* `MATCH`: 사용자 값이 명시적 Condition과 일치
* `NO_MATCH`: 사용자 값과 명시적 Condition이 확실히 불일치
* `UNKNOWN`: 존재가 시사된 Source 조건의 구조 또는 정규화 값이 부족해 비교 기준을 만들 수 없음
* `NEEDS_REVIEW`: 사용자 입력 부족, 추출 상태 미확정, 지원하지 않는 논리 또는 추가 확인 필요

공고가 `업력 7년 이하`이고 사용자 업력이 미입력이라면 `NO_MATCH`가 아니다. v0.1에서는 사용자 입력 부족이므로 `NEEDS_REVIEW`로 처리한다. Source가 업력 기준 자체를 제공하지 않으면 `UNKNOWN`이다.

## 11.2 Matching 참여 조건

Condition은 다음을 모두 만족할 때만 자동 Matching에 참여할 수 있다.

* `condition_role`이 `ELIGIBILITY_REQUIRED` 또는 `ELIGIBILITY_EXCEPTION`
* `extraction_status=SUPPORTED`
* `evidence_text`와 `source_field`가 존재
* Operator에 필요한 operand와 unit이 완전함
* User Profile에 subject와 condition type에 대응하는 값이 존재

마지막 항목이 없으면 자동 `NO_MATCH`가 아니라 `NEEDS_REVIEW`다.

## 11.3 집계 우선순위

Program-level `eligibility_extraction_status`가 `SUPPORTED`가 아니면 완전한 Eligibility를 근거로 `MATCH`를 단정하지 않는다. 그 경계를 먼저 적용한 뒤, 비교 가능한 Condition은 다음 순서로 집계한다.

1. predicate가 참인 `global_exclusions`가 있으면 `NO_MATCH`
2. 공통 조건이 명확히 불일치하면 `NO_MATCH`
3. 하나의 OR Group이라도 완전히 충족하면 `MATCH`
4. 확정 가능한 모든 Group이 불일치하고 불명확 조건이 없으면 `NO_MATCH`
5. 사용자 입력 부족이나 검토 필요 Condition이 있으면 `NEEDS_REVIEW`
6. Source 조건을 구성할 수 없으면 `UNKNOWN`

`non_eligibility_conditions`는 위 집계에 절대 참여하지 않는다.

## 11.4 Matching 경계 사례

| Case | 공고 / Evidence 상태 | 사용자 | 결과 | 근거 |
| --- | --- | --- | --- | --- |
| 1 | 업력 7년 이하 | 업력 3년 | `MATCH` 후보 | `business_age LTE 7 YEAR`의 predicate가 참이고 다른 조건·전역 제외·Program 완전성 검사를 통과한다는 전제 |
| 2 | 업력 7년 이하 | 업력 9년 | `NO_MATCH` | 명시적 required condition의 predicate가 거짓 |
| 3 | 업력 7년 이하 | 업력 미입력 | `NEEDS_REVIEW`; `NO_MATCH` 금지 | 필요한 사용자 비교값이 없음 |
| 4 | 지역 조건 없음 | 지역 미입력 | 지역 때문에 `UNKNOWN`이 되지 않음 | `region_or_location` Condition 자체를 생성하지 않고 다른 Eligibility로 정상 평가 |
| 5 | `세부 지원대상 별첨 참조`, 별첨 미확보 | 값과 무관 | Program Eligibility `UNKNOWN` 또는 `NEEDS_REVIEW`; `MATCH` 단정 금지 | 필요한 공식 Evidence와 Program-level 완전성이 부족 |
| 6 | 법인 제외 | 법인 | global exclusion → `NO_MATCH` | `EQ CORPORATION` predicate가 참이고 `polarity=EXCLUDE`이므로 제외 발동 |

Case 1의 `MATCH`는 단일 Condition 결과만으로 최종 자격을 보장하지 않는 후보 상태다. Program-level 상태, 나머지 공통·OR 조건, 전역 제외를 모두 통과해야 한다.

# 12. 실제 Review Pack Mapping Example

아래 표는 각 condition type에 대해 Human Review에서 확인된 실제 Evidence 하나 이상을 v0.1으로 표현한 결과다. Evidence 문구는 Review CSV에서 가져왔다.

| Normalized type | Review ID | Human Evidence | v0.1 표현 |
| --- | --- | --- | --- |
| `region_or_location` | `BIZ-ELIG-001` | `인천광역시 소재 소상공인` | subject `BUSINESS`, `EQ "인천광역시"`, unit `NONE`, role `ELIGIBILITY_REQUIRED` |
| `age` | `BIZ-ELIG-006` | `공고일 기준, 만 19세 이상 예비 창업자 등` | subject `APPLICANT`, `GTE 19`, unit `YEAR` |
| `pre_founder` | `BIZ-ELIG-009` | `예비창업자 또는 업력 7년 이내 기창업자` | `EQ true`, 첫 번째 OR Group |
| `business_registration_status` | `BIZ-ELIG-013` | `광주광역시 소재 청년 창업기업` | subject `BUSINESS`, `EXISTS`; 기존 사업체 존재만 표현하고 등록증 보유까지 확대 해석하지 않음 |
| `business_age` | `BIZ-ELIG-018` | `경상남도 소재 업력 7년 이내 스타트업` | subject `BUSINESS`, `LTE 7`, unit `YEAR` |
| `industry` | `BIZ-ELIG-021` | `별첨 1「지원가능 업종」에 해당하는 기업` | 업종 목록을 별첨에서 확보하기 전에는 `UNKNOWN`; 목록 확보 후 `IN values` |
| `business_type` | `BIZ-ELIG-025` | `전남 소재 소상공인` | subject `BUSINESS`, `EQ SMALL_BUSINESS` |
| `sales_or_income` | `BIZ-ELIG-030` | `2025년도 연 매출액이 0원 초과 5천만원 이하인 업체` | 같은 Group에 `GT 0 KRW` AND `LTE 50000000 KRW` |
| `employee_count` | `BIZ-ELIG-033` | `광업ㆍ제조ㆍ건설ㆍ운수업(10인 미만), 그 외(5인 미만)` | 산업별 OR Group에 `LT 10 PERSON` 또는 `LT 5 PERSON` |
| `gender` | `BIZ-ELIG-037` | `공고일 기준 대구지역여성 중 예비창업자` | subject `APPLICANT`, `EQ FEMALE` |
| `qualification_or_certification` | `BIZ-ELIG-041` | `실증특례확인서를 받은 특구사업자` | subject `BUSINESS`, `EQ REGULATORY_SANDBOX_CONFIRMATION` |
| `education_completion` | `BIZ-ELIG-045` | `소상공인 행복드림센터 교육 또는 ... 재창업 교육 수료자` | 교육별 OR Group에서 subject `APPLICANT`, `EQ` canonical course value |

`BIZ-ELIG-013`처럼 Evidence가 기창업 상태만 지지하는 경우 `사업자등록증 보유`를 임의 생성하지 않는다. `BIZ-ELIG-021`처럼 별첨에 실제 값이 있는 경우 별첨을 확보하기 전에는 비교 가능한 `values`를 만들어 내지 않는다.

이하 JSON은 의미 구분을 보여주기 위한 핵심 필드 fragment다. 실제 저장 객체에는 §6.1의 모든 필수 필드와 Operator shape에 맞는 nullable operand 필드를 포함한다.

## 12.1 필수 사례 A — 개월 단위 업력

Review `BIZ-ELIG-020`:

```json
{
  "condition_type": "business_age",
  "subject": "BUSINESS",
  "operator": "GTE",
  "raw_value": "사업경력이 2개월 이상",
  "value": 2,
  "unit": "MONTH",
  "polarity": "INCLUDE",
  "condition_role": "ELIGIBILITY_REQUIRED",
  "evidence_text": "사업경력이 2개월 이상 경과한 소상공인",
  "source_field": "bsnsSumryCn",
  "extraction_method": "HUMAN",
  "extraction_status": "SUPPORTED"
}
```

`2개월`을 `0년` 또는 `1년`으로 반올림하지 않는다.

## 12.2 필수 사례 B — 제외형 사업자 유형

Review `BIZ-ELIG-028`의 `법인 제외`:

```json
{
  "condition_type": "business_type",
  "subject": "BUSINESS",
  "operator": "EQ",
  "raw_value": "법인 제외",
  "value": "CORPORATION",
  "unit": "NONE",
  "polarity": "EXCLUDE",
  "condition_role": "ELIGIBILITY_REQUIRED",
  "evidence_text": "만18~45세의 청년(법인 제외) 중 신규창업 또는 업력 7년 미만의 사업자",
  "source_field": "bsnsSumryCn",
  "extraction_method": "HUMAN",
  "extraction_status": "SUPPORTED"
}
```

이 Condition은 `global_exclusions`에 둔다. 사용자가 법인이면 `NO_MATCH`, 법인이 아니면 이 제외 조건을 통과한다.

## 12.3 필수 사례 C — Eligibility가 아닌 계산조건

Review `BIZ-ELIG-029`:

```json
{
  "condition_type": "sales_or_income",
  "subject": "BUSINESS",
  "operator": "EXISTS",
  "raw_value": "최근 결산년도 매출액의 1/3과 지원 한도 중 적은 금액이 최대한도",
  "value": null,
  "unit": "NONE",
  "polarity": "NOT_APPLICABLE",
  "condition_role": "CALCULATION_ONLY",
  "evidence_text": "최근 결산년도 매출액의 1/3과 지원 한도 중 적은 금액이 최대한도",
  "source_field": "bsnsSumryCn",
  "extraction_method": "HUMAN",
  "extraction_status": "SUPPORTED"
}
```

이는 의미가 확인된 계산 문맥이지만 Eligibility Matching에서는 제외한다. 계산식 자체의 구조화는 향후 Calculation Schema 책임이다.

## 12.4 필수 사례 D — 선정 후 인증

Review `BIZ-ELIG-043`:

```json
{
  "condition_type": "qualification_or_certification",
  "subject": "BUSINESS",
  "operator": "EXISTS",
  "raw_value": "청년기업 3년간 인증",
  "value": null,
  "unit": "NONE",
  "polarity": "NOT_APPLICABLE",
  "condition_role": "POST_SELECTION",
  "evidence_text": "청년기업 3년간 인증, 인증 청년기업 제품ㆍ서비스 우선 구매ㆍ이용(권고)",
  "source_field": "bsnsSumryCn",
  "extraction_method": "HUMAN",
  "extraction_status": "SUPPORTED"
}
```

인증 문구는 맞지만 사전 보유자격이 아니므로 Matching에서 제외한다.

## 12.5 필수 사례 E — 예비창업자 OR 업력 7년 이내

`BIZ-ELIG-009`는 §8.2처럼 두 Eligibility Group으로 표현한다.

```text
Group G1: pre_founder EQ true
OR
Group G2: business_age LTE 7 YEAR
```

두 Condition을 하나의 AND 배열에 넣으면 의미가 반대로 바뀌므로 금지한다.

## 12.6 필수 사례 F — 지역 제한과 타 지역민 예외

Review `BIZ-ELIG-046`:

```text
사업자 등록을 하지 않은 예비창업자
AND
(
  전남도민
  OR
  전남지식재산센터 IP창업Zone 수료생
)
```

v0.1 표현:

```text
common_conditions:
  pre_founder EQ true

eligibility_groups:
  G1:
    region_or_location / APPLICANT / EQ 전라남도
    condition_role = ELIGIBILITY_REQUIRED

  G2:
    education_completion / APPLICANT / EQ IP_STARTUP_ZONE_COMPLETED
    condition_role = ELIGIBILITY_EXCEPTION
```

이 구조의 Boolean 의미는 `G1 OR G2`다. G2의 `ELIGIBILITY_EXCEPTION` metadata가 G1의 지역 Condition을 직접 override하는 것이 아니다.

Source가 대안 경로를 `전남도민 OR (타지역민 AND IP창업Zone 수료)`처럼 명시한다면 구조도 다음처럼 보존해야 한다.

```text
eligibility_groups:
  G1:
    region_or_location EQ 전라남도

  G2:
    region_or_location EQ <검증된 타지역 positive canonical scope>
    AND
    education_completion EQ IP_STARTUP_ZONE_COMPLETED
```

꺾쇠 부분은 실제 저장값이 아니라 필요한 canonical scope를 설명한 표기다. v0.1은 `NOT_IN`이나 이중 부정을 도입하지 않는다. `타지역민`을 양의 canonical scope로 안전하게 정규화할 수 없다면 G2의 지역 Condition을 조용히 생략하거나 `ELIGIBILITY_EXCEPTION`으로 override하지 않고, 해당 Program을 `NEEDS_REVIEW` 또는 `UNSUPPORTED`로 둔다.

Review Evidence에는 전남 소재 학교 재학생, 타기관 창업지원사업 선정자이면서 전남 창업 예정자 등 다른 예외도 존재한다. 이 Review row가 직접 Label한 `IP창업Zone 수료` 예외는 v0.1로 표현 가능하다. 나머지 예외를 현재 12개 type에 억지로 넣지 않으며, 별도 Human Review 후 type 확장 또는 `NEEDS_REVIEW`로 처리한다.

# 13. Failure Case가 Schema에서 어떻게 방지되는지

Schema는 다음 검증 경계를 제공한다. 다만 Extractor가 잘못된 subject·role을 선택하면 오류가 남을 수 있으므로 Schema만으로 추출 정확도가 자동 보장되지는 않는다.

| 실제 failure mode | v0.1 방지·격리 방식 |
| --- | --- |
| `울산창조경제혁신센터` | subject `ORGANIZATION`, role `CONTEXT_ONLY` 또는 Condition 미생성. BUSINESS/APPLICANT 지역 Matching 금지 |
| `21세기` → 21세 | subject와 unit이 명시된 실제 연령 Evidence가 아니면 `UNSUPPORTED`; 단순 숫자 span만으로 `age/SUPPORTED` 금지 |
| `2026 세종` → 26세 | 연도·사업명 문맥은 subject `PROGRAM`, role `CONTEXT_ONLY`; 신청자 연령으로 승격 금지 |
| `사업자 미등록 개인 신청불가` | `business_registration_status EQ UNREGISTERED`, polarity `EXCLUDE`로 방향 보존 |
| `3년 거치, 5년 균분상환` | subject `PROGRAM`, role `CONTEXT_ONLY` 또는 별도 금융조건 원문으로 보존; `business_age` Matching 금지 |
| `사업경력 2개월 이상` | `business_age GTE 2 MONTH`; YEAR 반올림 금지 |
| 농·수·축산물, 식품, 화장품, 공산품 | subject `PRODUCT`, `industry IN values`; canonical mapping 미확정 시 `NEEDS_REVIEW` |
| `법인 제외` | 양의 값 `CORPORATION` + polarity `EXCLUDE`; 이중 부정 연산자 미사용 |
| `매출액의 1/3` | role `CALCULATION_ONLY`; Eligibility Matching 제외 |
| 여성전용 시설 지원 | subject `FACILITY`, role `CONTEXT_ONLY`; APPLICANT/REPRESENTATIVE gender Matching 제외 |
| 선정 후 청년기업 인증 | role `POST_SELECTION`; 사전 보유자격 Matching 제외 |

실제 FP 9건은 `subject`, `polarity`, `condition_role`, `extraction_status`의 조합으로 오탐 의미를 격리할 수 있다. 실제 FN 3건은 다음처럼 표현 가능하다.

* `사업경력 2개월 이상`: `business_age`, `GTE`, `2`, `MONTH`
* 열거형 제품·산업: `industry`, subject `PRODUCT`, `IN values`
* `법인 제외`: `business_type`, `EQ CORPORATION`, `EXCLUDE`

# 14. UNKNOWN / NEEDS_REVIEW 처리

## 14.1 조건 제한이 실제로 없음

공식 Evidence 범위에서 특정 `condition_type`의 제한이 실제로 없으면 그 Condition을 생성하지 않는다. 예를 들어 성별 제한이 없는 공고는 `gender` Condition이 없으며, 이는 `gender=UNKNOWN`이라는 뜻이 아니다. 사용자의 성별 입력이 없어도 다른 Eligibility 조건으로 정상 Matching을 계속한다.

단, 제한이 없다고 확인한 것과 제한을 확인할 Source가 없는 것은 다르다. 후자는 다음 절의 Evidence 부족 상태다.

## 14.2 Source / Evidence 부족

다음은 `UNKNOWN`이다.

* Source에 Eligibility 본문이 없음
* `지원가능 업종은 별첨 참고`이나 별첨을 확보하지 못함
* 필요한 Eligibility 범위나 Condition 존재 여부 자체를 Source에서 확인할 수 없음

`UNKNOWN`은 실패나 불일치가 아니다.

조건 존재는 보이지만 의미·범위·방향·예외 또는 별첨을 추가 판독해야 하면 `NEEDS_REVIEW`로 둘 수 있다.

* Evidence는 있으나 subject, polarity, role 또는 값이 모호함
* Condition은 명시되었지만 원문·별첨 추가 확인이 필요함
* canonical region, industry, business type 값으로 안전하게 정규화하지 못함

확인된 구조가 현재 v0.1의 DNF·전역 제외 제약으로 안전하게 표현되지 않으면 Program-level `UNSUPPORTED`다. `UNKNOWN`과 `NEEDS_REVIEW` 모두 실제 필수조건의 Evidence가 충분해질 때까지 Program-level `MATCH`를 만들 수 없다.

## 14.3 사용자 입력 부족

다음은 `NEEDS_REVIEW`다.

* 사용자 Profile에 필요한 값이 없음

Source Condition이 명확하고 구조화도 완료되었으나 사용자 값만 없다면 Source 추출 상태를 낮추지는 않는다. 이는 Program/Condition extraction 문제가 아니라 Matching 입력 완전성 문제이며, v0.1의 결과는 `NEEDS_REVIEW`다. `NO_MATCH`로 처리하지 않는다.

## 14.4 금지되는 전환

```text
사용자 값 없음 → NO_MATCH       금지
Source 값 없음 → NO_MATCH       금지
정규화 실패 → 값 임의 생성      금지
Evidence 없음 → SUPPORTED        금지
NEEDS_REVIEW → MATCH/NO_MATCH    자동 전환 금지
```

요약하면, 제한 부재는 Condition 미생성, Evidence 부족은 Program/Condition `UNKNOWN` 또는 `NEEDS_REVIEW`, 사용자 입력 부족은 Matching 결과 `NEEDS_REVIEW`다. 이 세 경우를 같은 결측 처리 규칙으로 합치지 않는다.

# 15. v0.1 한계

1. 48건 stratified Review Pack을 근거로 하므로 전체 273건 표현 범위를 보장하지 않는다.
2. 행정구역·업종·사업자 유형·교육·인증 canonical value 체계가 아직 확정되지 않았다.
3. User Profile Schema가 확정되지 않아 subject별 입력 계약도 아직 Draft다.
4. DNF형 2단계 Group만 지원하며 재귀 중첩, 조건부 제외, 우선순위 Rule은 지원하지 않는다.
5. `global_exclusions`가 특정 Group에서만 적용되는 경우 안전한 DNF 변환이 필요하다.
6. Source field 전체와 공고문·별첨의 논리관계가 다를 수 있다.
7. 현재 Review CSV에는 Evidence offset이 없어 문구 위치를 자동 검증할 수 없다.
8. `CONTEXT_ONLY`·`POST_SELECTION` 정보를 실제 저장할지 추출 단계에서 폐기할지는 구현 전 결정이 필요하다.
9. Schema는 의미 구분 칸을 제공할 뿐 Regex·LLM의 subject, role, polarity 판정 오류를 스스로 고치지 않는다.
10. Matching 결과 집계 규칙은 경계 정의이며 구현·테스트로 검증되지 않았다.

# 16. 다음 구현 단계

1. 이 문서를 팀 검토해 v0.1 필드와 Enum을 승인하거나 수정한다.
2. 48건 Human Evidence를 Condition fixture로 수작업 매핑해 representability를 재검증한다.
3. 별도의 독립 Human Review 표본으로 누락 condition type과 DNF 한계를 확인한다.
4. Region, industry, business type의 최소 canonical value 정책을 결정한다.
5. User Profile이 각 subject/condition type에 제공해야 하는 입력 계약을 Draft한다.
6. 승인 후에만 Python/Pydantic 또는 JSON Schema를 구현한다.
7. Condition validation test를 먼저 작성한다.
8. 그 다음 Deterministic Matching baseline을 구현하고 `MATCH / NO_MATCH / UNKNOWN / NEEDS_REVIEW` 경계를 테스트한다.
9. Regex 또는 LLM Extractor 개선은 Schema·fixture·평가 기준이 고정된 뒤 별도 단계에서 수행한다.
