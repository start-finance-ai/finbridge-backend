# FINANCE AI — Architecture

Last Updated: 2026-08-29

이 문서는 2026 금융 AI Challenge MVP의 AI / Backend / Data / Infra Architecture를 정의한다.

현재 Architecture는 실제 기업마당 지원사업정보 API 검증 결과를 기반으로 설계한다.

현재 Core 구현은 FastAPI와 OpenAI Responses API 설명 Provider를 사용한다.
Database와 Cloud Platform 등 운영 기술은 아직 확정하지 않는다.

기술 선택보다 다음을 우선한다.

* 실제 데이터 기반 동작
* 결정론적 금융 계산
* 설명 가능한 지원사업 Matching
* Evidence 유지
* Unsupported 처리
* Public Web MVP 안정성

# 1. Architecture Goal

FinBridge에서 사용자가 일반모드 또는 집중모드로 질문하면 다음 흐름을 실제 Backend에서 처리한다.

```text
사용자 진입
→ Interaction Mode Router
   ├─ 일반모드: 자연어 입력
   └─ 집중모드: 첫 대화 전 구조화 입력
→ 사용자 조건 파악
→ 지원사업 후보 탐색
→ 비정형 자격조건 구조화
→ 사용자 조건과 deterministic matching
→ 재무·리스크 계산
→ Evidence 검증
→ 생성형 AI 대화형 설명
→ 출처 및 다음 행동 제공
```

LLM이 지원사업 검색, 자격판정, 금융계산을 모두 직접 수행하는 구조는 사용하지 않는다.

[TEAM DECISION — 2026-08-29]

사용자에게 보이는 답변은 GPT/Claude와 유사한 텍스트 채팅 형식을 사용한다. 내부의 `MATCHED / NEEDS_REVIEW / UNKNOWN` 등 구조화 결과는 버리지 않고 AI 설명의 근거와 Frontend action 구성에 사용한다.

# 2. Verified Data Finding

[EXPERIMENT]

2026-08-28 기업마당 지원사업정보 API 실측 결과:

* API 호출 성공
* HTTP 200 확인
* 창업 분야 20건 JSON 확보
* Raw JSON 저장 완료
* 실제 Response Field 확인
* 상세 Eligibility가 `bsnsSumryCn` 자연어에 포함되는 사례 확인
* 신청기간이 고정 날짜뿐 아니라 `예산 소진시까지` 형태로도 존재
* 지원금액 역시 자연어 안에 포함되는 사례 확인

따라서 지원사업 데이터는

**완전한 정형 데이터도 아니고 완전한 비정형 문서도 아니다.**

다음 두 영역을 함께 처리해야 한다.

### Structured

* 공고 ID
* 공고명
* 기관
* 지원분야
* 등록일
* 수정일
* URL

### Unstructured / Semi-Structured

* 지역 조건
* 연령
* 창업 여부
* 창업 업력
* 사업장 소재지
* 업종
* 교육 이수
* 자격증
* 지원금액
* 추가 Eligibility 조건

# 3. High-Level Architecture

```text
┌─────────────────────────────┐
│          Frontend           │
│ Profile / Risk / AI Result  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│         Backend API         │
│ Validation / Orchestration  │
└──────────────┬──────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌───────────────┐  ┌────────────────┐
│ Program       │  │ Calculation    │
│ Retrieval     │  │ Engine         │
└───────┬───────┘  └───────┬────────┘
        │                  │
        ▼                  │
┌───────────────────────┐ │
│ Eligibility           │ │
│ Constraint Extraction │ │
└───────────┬───────────┘ │
            ▼             │
┌───────────────────────┐ │
│ Deterministic         │ │
│ Matching Engine       │ │
└───────────┬───────────┘ │
            │             │
            └──────┬──────┘
                   ▼
          ┌──────────────────┐
          │ Evidence         │
          │ Validation       │
          └────────┬─────────┘
                   ▼
          ┌──────────────────┐
          │ LLM Explanation  │
          └────────┬─────────┘
                   ▼
          ┌──────────────────┐
          │ Final Response   │
          │ + Source         │
          │ + Next Action    │
          └──────────────────┘
```

# 4. Main Processing Flow

## 4.1 User Input

Frontend에서 사용자 입력을 받는다.

현재 Profile 후보:

* user_type
* region
* industry
* capital

기업마당 데이터 실측 결과 추가로 필요할 수 있는 정보:

* age
* business_status
* business_age
* business_location
* gender
* certificate
* education completion

[TEAM DECISION — 2026-08-29]

입력 UX는 `GENERAL` / `FOCUS` 두 모드로 분리한다.

### GENERAL — 일반모드

- 사용자가 자연어로 바로 시작할 수 있다.
- 사용자가 모드 버튼을 선택하지 않고 채팅창에 입력해도 일반모드로 처리한다.
- 자연어에서 확보 가능한 조건을 파싱하고, 실제 Matching에 필요한 정보가 부족하면 후속 질문을 한다.
- 구조화 입력이 유리한 시점에는 집중모드 전환을 제안할 수 있다.

### FOCUS — 집중모드

- 첫 대화 전에 지원사업 탐색과 Matching에 필요한 최소 입력을 체크·선택형 등 구조화된 UI로 받는다.
- 정확한 필드 목록은 최종 Eligibility/Profile Schema에 맞춰 최소화한다.
- 최초 구조화 입력 후에는 매 턴 폼을 강제하지 않고 일반 채팅 형태로 대화를 이어간다.

두 모드 모두 첫 대화 전 예시 질문 2개를 보여주는 방향으로 UI Contract를 고정한다.

## 4.1.1 Mode State — Draft

Backend/API에서 최소한 다음 상태를 표현할 수 있도록 검토한다.

```text
mode = GENERAL | FOCUS
focus_intake_completed = true | false
suggest_focus_mode = true | false
program_context_id = nullable
```

정확한 Request/Response 필드명은 API Contract Freeze 시 확정한다.

## 4.2 Request Validation

Backend API에서 사용자 입력을 검증한다.

검증 후보:

* 필수값
* Enum
* 숫자 범위
* 날짜
* 문자열 길이
* 파일 형식
* 비정상 입력

잘못된 입력을 그대로 Retrieval 또는 LLM에 전달하지 않는다.

## 4.3 Candidate Retrieval

지원사업 후보를 먼저 좁힌다.

우선순위:

1. Structured Filter
2. Exact / Keyword Search
3. 필요한 경우에만 Semantic Retrieval

예:

```text
사용자 = 예비창업자
관심 분야 = 창업
지역 = 경기
```

일 때 전체 공고를 LLM에 전달하지 않는다.

먼저 Backend에서 관련 후보군을 검색한다.

# 5. Program Retrieval

## 5.1 Structured Retrieval

다음은 RDB 또는 Structured Query를 우선한다.

* program_id
* category
* subcategory
* provider
* created_at
* updated_at
* 신청 상태
* 명확하게 구조화된 조건

## 5.2 Keyword Retrieval

다음은 Keyword / Exact Search 우선 후보이다.

* 공고명
* 기관명
* 업종 Keyword
* 지역 Keyword
* 지원분야

## 5.3 Semantic Retrieval

다음 경우에만 Semantic Retrieval을 검토한다.

* 사용자 표현과 공고 표현이 다른 경우
* 긴 공고문에서 관련 조건을 찾아야 하는 경우
* Keyword Search만으로 Recall이 낮은 경우

Vector DB 사용은 아직 확정하지 않는다.

단순 DB + Text Search로 충분하면 Vector DB를 도입하지 않는다.

# 6. Eligibility Constraint Extraction

2026-08-29 현재 실제 Raw Snapshot 20건에는 보수적인 deterministic Regex
baseline을 먼저 적용한다. LLM Extraction은 아직 구현하지 않았다.

현재 baseline은 기업마당 `bsnsSumryCn`의 명시적 지원대상 구절에서 다음만
구조화한다.

* 구체 지역 / 소재지
* 숫자로 명시된 연령 범위 또는 상·하한
* 예비창업자
* 숫자로 명시된 사업 업력과 YEAR / MONTH 단위
* 명시적인 기존 사업체 상태

`hashtags`와 coarse target인 `trgetNm`은 Eligibility Evidence로 사용하지 않는다.
공고문·별첨 참조, 숫자 없는 청년 표현, 복잡한 업종·추천·교육·자격 및 불완전한
OR 관계는 값을 추측하지 않고 Program-level `NEEDS_REVIEW`, `UNKNOWN` 또는
`UNSUPPORTED`로 차단한다.

예시 원문:

```text
공고일 기준 영월군 관내 주소지를 둔 자 또는
사업자 선정 후 1개월 이내 영월군에 주소 이전 가능한 자

18세 이상 45세 이하

예비창업자 또는 창업 후 7년 이내
```

완전한 대안 경로는 Eligibility Schema v0.1의 Group 내부 AND / Group 사이 OR로
변환한다. 일부 Condition이 추출되었다는 이유만으로 Program 전체를 자동
`SUPPORTED`로 올리지 않는다.

중요:

추출된 값 자체가 최종 Truth는 아니다.

원문 Evidence와 함께 저장한다.

# 7. Eligibility Evidence

각 구조화 조건은 가능한 경우 다음 정보를 가진다.

```text
condition_type
operator + normalized operand
raw_value
unit
source_field
evidence_text
extraction_method
extraction_status
```

예:

```json
{
  "condition_type": "AGE",
  "operator": "BETWEEN",
  "min_value": 18,
  "max_value": 45,
  "unit": "YEAR",
  "raw_value": "18세 이상 45세 이하",
  "source_field": "bsnsSumryCn",
  "evidence_text": "18세 이상 45세 이하",
  "extraction_method": "REGEX",
  "extraction_status": "SUPPORTED"
}
```

원문 Evidence 없이 구조화 값만 저장하는 방식은 피한다.
Schema와 Regex baseline 자체가 추출 정확도를 보장한다고 주장하지 않는다.

# 8. Deterministic Matching Engine

LLM이 사용자의 최종 지원 가능 여부를 직접 판정하지 않는다.

구조화된 Eligibility와 사용자 Profile을 코드에서 비교한다.

예:

```text
User
region = 경기

Program
region = 영월군

Result
REGION = NOT_MATCHED
```

또는:

```text
User
age = 27

Program
age_min = 18
age_max = 45

Result
AGE = MATCHED
```

# 9. Match Status

초기 상태 후보:

## MATCHED

현재 확보된 사용자 정보와 공고 조건이 일치한다.

## NOT_MATCHED

명확한 공고 조건과 사용자의 정보가 불일치한다.

## NEEDS_REVIEW

공고 조건이 복잡하거나 현재 사용자 정보가 부족해 자동 판정하기 어렵다.

## UNKNOWN

원천 데이터 자체에서 조건을 확인할 수 없다.

최종 Enum 이름은 구현 단계에서 조정할 수 있다.

# 10. Matching Result

지원사업별로 단순 Score만 반환하지 않는다.

예시:

```json
{
  "program_id": "PBLN_xxx",
  "status": "NEEDS_REVIEW",
  "conditions": [
    {
      "type": "AGE",
      "status": "MATCHED"
    },
    {
      "type": "REGION",
      "status": "NOT_MATCHED"
    },
    {
      "type": "BUSINESS_AGE",
      "status": "UNKNOWN"
    }
  ]
}
```

사용자는 왜 이런 결과가 나왔는지 확인할 수 있어야 한다.

# 10.1 Match Status Presentation Rule

[TEAM DECISION — 2026-08-29]

Backend는 조건별 상태를 구조화해 반환한다.

Frontend의 기본 사용자 경험은 상태 칩만 나열하는 판정 화면이 아니라 **대화형 AI 답변**이다.

예:

```text
현재 입력하신 정보로는 연령 조건은 맞습니다.
다만 이 공고는 사업장 소재지 조건이 추가로 있어 현재 정보만으로는 최종 판단하기 어렵습니다.
공식 공고에서 해당 조건을 한 번 더 확인해 주세요.
```

필요한 경우 지원사업 카드·상세 화면에서는 조건 요약 또는 근거 UI를 보조적으로 사용할 수 있다.

# 11. Adaptive Question / Focus Mode Suggestion

일반모드에서 처음부터 모든 Profile을 요구하지 않는다.

```text
자연어 질문
→ 현재 정보로 후보 탐색
→ 공고에 필요한 추가 조건 파악
→ 간단한 후속 질문 또는 집중모드 제안
→ 추가 정보 확보
→ Matching 갱신
```

집중모드에서는 첫 대화 전에 최소 구조화 Profile을 입력받아 초기 Matching 정확도를 높인다.

집중모드 전환 권장 문구:

> 조금 더 정확하게 확인해볼까요? 지역·나이·사업 단계 등 몇 가지 조건만 입력하면, FinBridge가 공고별 조건을 비교해 맞는 부분과 추가 확인할 부분을 더 구체적으로 보여드릴 수 있어요.

MVP에서는 복잡한 동적 폼 생성까지 구현하지 않아도 된다. 고정된 최소 Focus Intake + 필요한 후속 질문 조합을 우선한다.

# 12. Calculation Engine

금융 및 리스크 계산은 별도 Calculation Engine에서 수행한다.

LLM에게 계산을 맡기지 않는다.

2026-08-29 MVP 구현 Contract 입력:

* initial_cost
* own_capital
* monthly_revenue
* monthly_expense
* loan_amount
* annual_interest_rate — 연 이자율 %, 사용자 직접 입력
* loan_term_months — 개월

MVP에서 지원하는 상환방식은 원리금균등상환 1종이다. 거치기간, 변동금리, 세금, 수수료, 매출 변동, 추가 차입은 반영하지 않는다. 정책자금 금리를 자동으로 삽입하지 않는다.

출력:

* available_cash
* monthly_loan_payment
* monthly_cash_flow
* monthly_cash_burn
* runway_months
* remaining_debt_at_runway

핵심 계산식:

```text
available_cash = own_capital + loan_amount - initial_cost
monthly_rate = annual_interest_rate / 100 / 12
monthly_cash_flow = monthly_revenue - monthly_expense - monthly_loan_payment
monthly_cash_burn = max(-monthly_cash_flow, 0)

available_cash <= 0                 → runway_months = 0
available_cash > 0 AND
monthly_cash_flow < 0               → runway_months = available_cash / monthly_cash_burn
monthly_cash_flow >= 0              → runway_months = null
```

월 원리금 상환액은 대출 0원이면 0, 0% 금리이면 `loan_amount / loan_term_months`, 그 외에는 `P × r × (1+r)^n / ((1+r)^n - 1)`이다. 유한 Runway 시점의 잔존채무는 `P × (1+r)^k - A × ((1+r)^k - 1) / r`이며, `k=floor(runway_months)`를 대출기간 범위로 제한한다. 0% 금리는 `max(P - A × k, 0)`을 사용하고 Runway가 `null`이면 잔존채무도 `null`이다.

내부 계산은 Decimal로 수행하고 최종 금액과 Runway만 `ROUND_HALF_UP`으로 소수 둘째 자리까지 반올림한 JSON number로 반환한다.

# 13. Calculation Requirements

Calculation Engine은 다음 원칙을 따른다.

* 동일 입력 → 동일 결과
* 명확한 단위
* 명확한 계산식
* 경계값 정의
* 결측 처리 정의
* 테스트 작성

예:

```text
월매출
- 월지출
- 월상환액
= 월 현금흐름
```

이 계산은 사용자 입력 기반 단순 시뮬레이션이며 신용평가, 대출 승인 예측 또는 실제 사업 성과 보장이 아니다.

# 14. Evidence Validation

최종 사용자 응답에 들어가기 전에 Evidence를 검증한다.

검증 대상:

* 지원사업 실제 존재 여부
* Program ID
* 공고 URL
* 추출 Eligibility
* 신청기간
* 지원금액
* 계산 결과

지원사업 데이터와 LLM 답변이 충돌할 경우 원본 데이터가 우선한다.

# 15. LLM Role

[IMPLEMENTED — 2026-08-29]

`POST /chat`의 설명 Provider는 OpenAI 공식 Python SDK와 Responses API를
사용한다. 모델과 timeout은 환경변수로 주입하며 기본값은
`gpt-5.6-luna`, 10초이다. reasoning effort는 설명 역할에 맞춰 `low`로
고정했다. Provider 호출은 Router가 아니라 Chat Service 뒤의 작은 Provider
경계에서 수행한다.

현재 `/chat` 구현은 아래 역할 중 Explanation만 사용한다. Input Understanding과
Eligibility Extraction은 아직 구현 후보이며 완료 상태가 아니다.

## Input Understanding

* 사용자 자연어 질문 이해
* 필요한 조건 추출
* 추가 질문 생성

## Eligibility Extraction

* 비정형 지원사업 설명에서 자격조건 후보 추출

## Explanation

검증된 결과를 사용자가 이해하기 쉽게 설명한다.

예:

```text
현재 입력하신 정보 기준으로 연령 조건은 충족하지만,
해당 사업은 영월군 거주 또는 선정 후 주소 이전 조건이 있어
지역 조건 확인이 추가로 필요합니다.
```

## Conversational Response

[TEAM DECISION — 2026-08-29]

* GPT/Claude와 유사한 자연스러운 채팅 문장 생성
* 조건 충족·추가 확인·판단 불가를 문장 안에 포함
* 근거가 있는 추천 우선순위 설명
* 일반모드에서 구조화 입력이 필요할 때 집중모드 전환 제안

## Summary

* 지원내용 요약
* 중요한 자격조건 요약
* 신청 시 확인해야 할 사항 안내

# 16. LLM Must Not Do

LLM이 직접 수행하지 않는 영역:

* 존재하지 않는 지원사업 생성
* 지원금액 생성
* 대출금리 생성
* 최종 자격 보장
* 금융계산
* 신청기간 계산
* 날짜 비교
* Top-N 산술
* 최종 Eligibility Logic
* 데이터에 없는 제도 생성

# 17. Recommended Runtime Flow

사용자가 지원사업 탐색을 요청했을 때:

```text
1. Frontend Request

2. API Validation

3. User Profile Parsing

4. Candidate Program Retrieval

5. Program Eligibility Load

6. 누락 시 Eligibility Extraction

7. Deterministic Matching

8. Evidence Validation

9. LLM Explanation

10. API Response

11. Frontend Result
```

# 18. Data Collection Flow

기업마당 데이터는 사용자 요청 때마다 무조건 외부 API에서 전부 가져오는 구조를 우선하지 않는다.

권장 방향:

```text
기업마당 API
→ Collector
→ Raw Snapshot
→ Normalization
→ Eligibility Extraction
→ Validation
→ Service DB
```

사용자 요청:

```text
Frontend
→ Backend
→ Service DB
→ Matching
```

이렇게 분리하면 외부 API 장애와 Latency 영향을 줄일 수 있다.

# 19. Raw Data

Raw 데이터는 원본 형태로 보존한다.

현재:

```text
data/
└─ raw/
   └─ bizinfo/
      └─ bizinfo_startup_sample.json
```

원본을 수정하여 덮어쓰지 않는다.

실제 운영 수집 방식은 추후 결정한다.

# 20. Normalized Data

Raw API 데이터를 서비스 내부 공통 Schema로 변환한다.

예:

```text
Raw:
pblancId

Normalized:
program_id
```

```text
Raw:
pblancNm

Normalized:
program_name
```

Source별 필드명 차이를 Service Layer까지 그대로 전파하지 않는다.

# 21. Backend Logical Modules

현재 권장 관심사:

```text
backend/
│
├─ api/
│
├─ services/
│
├─ data/
│  ├─ collectors/
│  ├─ normalizers/
│  └─ repositories/
│
├─ retrieval/
│
├─ eligibility/
│  ├─ extraction/
│  ├─ matching/
│  └─ validation/
│
├─ calculation/
│
├─ ai/
│
├─ schemas/
│
├─ models/
│
├─ evaluation/
│
└─ tests/
```

현재 구현은 FastAPI Router / Service / Schema 경계를 따른다.

# 22. API Structure

```text
GET /health
```

서비스 상태 확인.

```text
POST /chat
```

일반모드/집중모드 공통 대화 Orchestration. 2026-08-29 기준 로컬 구현 및
실제 OpenAI smoke test를 완료했다.

Request 후보:

```json
{
  "mode": "GENERAL",
  "message": "카페 창업 준비 중인데 받을 수 있는 지원사업이 있을까요?",
  "focus_profile": null,
  "program_id": null,
  "session_id": null
}
```

지원사업 상세에서 `AI에게 이 공고 물어보기`를 누르는 경우 `program_id`를
context로 전달한다. `focus_profile`이 함께 있으면 기존 deterministic Matcher를
실행하며, LLM은 그 결과를 다시 판정하지 않는다. General 자연어 기반 전체 공고
탐색과 session persistence는 아직 구현하지 않았다.

```text
POST /programs/match
```

사용자 Profile 기반 지원사업 Matching.

```text
GET /programs/{program_id}
```

지원사업 상세 조회.

```text
POST /risk/calculate
```

재무·창업 리스크 계산.

```text
POST /income-stability/calculate
```

프리랜서 간이 소득 안정성 계산 후보.

```text
POST /sales/analyze
```

매출장표 실제 분석을 구현하는 경우의 후보. 일정 부족 시 이 Endpoint를 억지로 만들지 않고 Frontend `DEMO SAMPLE`과 실제 Backend 기능을 명확히 분리한다.

기존 `POST /ai/explain` 역할은 `/chat` Orchestration 내부 또는 별도 Endpoint로 유지할 수 있다.

실제 Endpoint는 Frontend 계약과 함께 확정한다.

# 23. API Response Principle

Frontend가 LLM 자연어만 받는 구조를 피한다.

대화형 UI를 사용하더라도 Backend는 Structured Result를 함께 반환한다.

Draft:

```json
{
  "mode": "GENERAL",
  "reply": "현재 입력하신 정보 기준으로...",
  "programs": [],
  "match": {},
  "evidence": [],
  "source": {},
  "actions": [],
  "suggest_focus_mode": false
}
```

즉,

**Structured Result + AI Conversational Reply + Evidence + UI Action**

을 함께 반환한다.

`reply`가 실패하더라도 Structured Matching/Evidence까지 사라지지 않게 한다.

# 24. Unsupported Handling

Backend에서 다음 상태를 지원해야 한다.

## DATA_NOT_FOUND

관련 데이터가 존재하지 않는다.

## INSUFFICIENT_USER_INPUT

판단에 필요한 사용자 정보가 부족하다.

## ELIGIBILITY_UNKNOWN

공고 자체에서 자격조건을 명확하게 확인할 수 없다.

## EXTERNAL_API_ERROR

외부 Data Source 호출 실패.

## LLM_ERROR

LLM 호출 실패.

LLM 실패 시 Structured Matching 결과까지 사라지지 않도록 한다.

# 25. LLM Failure Fallback

정상:

```text
Structured Matching
+
LLM Explanation
```

LLM 장애:

```text
Structured Matching
+
Evidence
+
Template Explanation
```

LLM 장애가 전체 서비스를 중단시키지 않아야 한다.

# 26. External API Failure

기업마당 API 장애 시 사용자 요청 전체가 즉시 실패하지 않게 한다.

가능한 방향:

```text
기업마당 API
     ↓
Local Service DB / Snapshot
```

사용자 요청은 Local DB를 우선 조회하는 구조를 검토한다.

데이터 최신 기준일을 화면에 표시할 수 있어야 한다.

# 26.1 Support Program Poster Asset Rule

[TEAM DECISION — 2026-08-29]

지원사업 리스트 카드에는 공고 이미지 영역을 둔다.

- 이미지는 Frontend/UI 자산으로 취급한다.
- 이미지 안의 문구를 Backend Truth 또는 Eligibility Evidence로 파싱하지 않는다.
- 공고명·대상·기간·금액·기관 등 실제 정보는 검증된 데이터 Source를 기준으로 표시한다.
- 이미지와 실제 공고가 매핑되는 경우 `program_id` 등 명시적 매핑을 사용한다.

# 27. Security

다음을 Source Code에 직접 작성하지 않는다.

* 기업마당 인증키
* LLM API Key
* Database Password
* Cloud Secret
* Access Token

환경변수를 사용한다.

```text
.env
```

는 Git에서 제외한다.

```text
.env.example
```

에는 변수명만 작성한다.

# 28. User Financial Data

사용자의 매출·소득 등 금융정보는 최소 범위만 처리한다.

MVP에서는 가능한 경우:

```text
Frontend
→ Backend 처리
→ 결과 반환
→ 원본 장기 저장하지 않음
```

방향을 우선 검토한다.

민감 원문을 일반 Application Log에 기록하지 않는다.

# 29. Logging

기록 후보:

* Request ID
* API Endpoint
* Status Code
* Processing Time
* External API 상태
* LLM 성공/실패
* Parsing 상태
* Matching 상태

기록하지 않는 것:

* API Key
* Password
* 전체 금융 원문
* 불필요한 개인정보

# 30. Health Check

Public MVP에는 Health Check Endpoint를 제공하는 방향을 우선한다.

예:

```text
GET /health
```

확인 후보:

* Backend Process
* Database Connection

외부 LLM 또는 외부 API가 잠시 실패했다고 Health Check 전체를 반드시 Down으로 만들 필요는 없다.

# 31. Evaluation Architecture

실제 서비스 기능뿐 아니라 내부 Evaluation을 준비한다.

추천 Dataset:

```text
evaluation/
├─ retrieval_cases
├─ eligibility_cases
├─ calculation_cases
├─ unsupported_cases
└─ prompt_injection_cases
```

측정 후보:

* Retrieval Accuracy
* Eligibility Extraction Accuracy
* Matching Accuracy
* Calculation Accuracy
* Unsupported Detection
* Hallucination Rate
* Latency

# 32. Eligibility Evaluation

특히 중요하다.

공고 Sample 일부를 사람이 직접 정답 Label로 만든다.

예:

```json
{
  "program_id": "PBLN_xxx",
  "region": "영월군",
  "age_min": 18,
  "age_max": 45,
  "business_age_max": 7
}
```

AI Extractor 결과와 비교하여 정확도를 측정한다.

이 검증 없이 Eligibility Extraction이 정확하다고 주장하지 않는다.

# 33. Retrieval Baseline

처음부터 Vector Retrieval을 사용하지 않는다.

Baseline:

```text
Structured Filter
+
Keyword Search
```

이후 실제 Evaluation에서 Recall 문제가 확인되는 경우에만

```text
Structured
+
Keyword
+
Vector
```

를 비교한다.

성능 개선이 없으면 Vector Retrieval을 제거한다.

# 34. Infrastructure Requirements

최종 MVP는 다음 조건을 만족해야 한다.

* Public URL
* HTTPS
* Frontend / Backend 연결
* Backend 자동 재시작 가능
* 환경변수 관리
* 외부 API Timeout
* LLM Timeout
* DB 연결 안정성
* Error Handling
* Health Check
* Logging
* 브라우저 새로고침 정상 동작

# 35. Deployment Architecture — Draft

현재 특정 Cloud는 확정하지 않는다.

논리 구조:

```text
Internet
   ↓
Frontend Hosting
   ↓ HTTPS
Backend Service
   ↓
Service Database
   ↓
External Data Source / LLM API
```

외부 API Key는 서버 환경변수에서 관리한다.

Frontend에 Secret을 노출하지 않는다.

# 36. Technology Decisions Not Yet Frozen

현재 확정하지 않은 사항:

* Database
* ORM
* Embedding Model
* Vector DB
* Agent Framework
* Cloud Provider
* Frontend Hosting
* Backend Hosting
* Scheduler
* Queue
* Cache

필요성과 구현기간을 검토한 뒤 Architecture Freeze 시 확정한다.

현재 구현에 한해 확정한 사항:

* LLM Explanation Provider: OpenAI Responses API
* Default Explanation Model: `gpt-5.6-luna` (환경변수로 변경 가능)
* Failure handling: Structured Result 유지 + deterministic template fallback

# 37. Architecture Freeze Conditions

[RECOMMENDATION — 2026-08-29]

2026-08-29 일정 제약을 반영해 모든 데이터 후보 검증이 끝날 때까지 Backend 구현을 미루지 않는다.

Core Implementation을 시작하기 위한 최소 Freeze 조건:

* DS-001 기업마당을 Main Source로 사용
* MVP용 최소 Program Schema
* MVP용 최소 Eligibility Schema
* 일반모드 / 집중모드 입력 Contract
* 지원사업 결과 / Evidence Contract
* 핵심 리스크 계산 입력·출력
* Public 배포 방식

K-Startup, 상권 데이터, 범용 CSV/Excel Parser 등은 Core 구현의 선행조건으로 두지 않는다.

아직 미확정인 세부 기술은 단순한 baseline을 먼저 선택하고 필요성이 확인될 때만 확장한다.

# 38. Current Architecture Decision

[TEAM DECISION / CURRENT]

현재 핵심 Backend Architecture는 다음을 우선한다.

```text
Official Data
→ Raw Snapshot
→ Normalization
→ Eligibility Extraction
→ Structured Eligibility
→ Deterministic Matching
→ Deterministic Calculation
→ Evidence Validation
→ LLM Explanation
→ Final Result + Source
```

핵심 원칙:

1. LLM이 최종 자격조건을 임의 판정하지 않는다.
2. 금융 계산은 Backend 코드에서 수행한다.
3. 구조화 가능한 조건은 구조화한다.
4. 원문 Evidence를 유지한다.
5. 데이터에 없는 사실을 생성하지 않는다.
6. AI 장애가 전체 서비스 장애로 이어지지 않게 한다.
7. 기술 수보다 실제 동작하는 MVP를 우선한다.

# 39. Immediate Next Step

[TEAM DECISION: 내부 완료 일정 / RECOMMENDATION: 아래 구현 순서 — 2026-08-29]

Backend 구축·배포, 디자인, QA를 2026-09-03~04까지 내부 완료하는 것을 목표로 한다.

따라서 다음 순서로 진행한다.

1. FinBridge UI/Backend Handoff 기준으로 화면별 최소 API 요구사항 Freeze
2. 최소 Profile / Focus Intake Schema Freeze
3. 최소 Program / Eligibility Schema Freeze
4. 핵심 리스크 계산식 확정
5. Backend Technology Stack과 배포 방식 즉시 결정
6. Backend Scaffold + `/health`
7. 기업마당 Snapshot/DB 기반 Retrieval
8. Deterministic Matching
9. Risk Calculation
10. `/chat` 또는 동등한 AI Orchestration
11. 지원사업 상세 ↔ Chat `program_id` context 연동
12. 프리랜서 소득 안정성 간이 계산
13. 매출장표 실제 분석은 시간 확인 후 구현; 부족하면 명시적 Demo Fallback
14. Frontend Integration
15. Public Deployment
16. QA / Evaluation / Error Handling
17. `FINANCE_AI_DEV_STATUS.md` 즉시 최신화

Secondary Source 확대, Vector DB, Graph DB, Multi-Agent 등은 위 흐름 완료 전 추가하지 않는다.
