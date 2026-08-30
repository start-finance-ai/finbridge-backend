# FINANCE AI — Architecture

Last Updated: 2026-08-29

이 문서는 2026 금융 AI Challenge `FinBridge` MVP의 현재 AI / Backend / Data / Infra Architecture를 정의한다.

구현 여부는 `FINANCE_AI_DEV_STATUS.md`와 실제 코드·테스트 결과를 우선한다.

# 1. Architecture Goal

FinBridge의 목표는 다음 흐름을 하나의 안정적인 Public Web Service로 제공하는 것이다.

```text
사용자 상황
→ 실제 지원사업 Retrieval
→ 비정형 Eligibility 구조화
→ Deterministic Matching
→ Evidence
→ Deterministic Risk Calculation
→ AI Explanation
→ 공식 출처
→ 다음 행동
```

LLM 하나가 지원사업 검색·자격판정·금융계산을 모두 수행하는 구조는 사용하지 않는다.

# 2. Current Technology Stack

[TEAM DECISION / EXPERIMENT]

## Frontend

- React 19
- Vite 8
- TypeScript
- pnpm
- Target Hosting: `Vercel Hobby`

## Backend

- Python `3.14.3`
- FastAPI `0.141.1`
- Pydantic v2
- Uvicorn
- pytest
- Target Hosting: `Railway Hobby`

## AI

- OpenAI Python SDK
- Responses API
- Model: `gpt-5.6-luna`
- reasoning effort: `low`
- Provider failure: deterministic Template Fallback

## Database

MVP에서는 Database를 사용하지 않는다.

현재 데이터 요구는 Snapshot / Bootstrap 기반으로 충족한다.
PostgreSQL은 실제 영속 상태가 필요해질 때만 추가 검토한다.

# 3. High-Level Architecture

```text
┌────────────────────────────────────────────┐
│                 Vercel                     │
│        React + Vite + TypeScript            │
│                                            │
│ AI Mode / Programs / MyPage / Auth UI      │
└───────────────────┬────────────────────────┘
                    │ HTTPS REST
                    ▼
┌────────────────────────────────────────────┐
│             Railway — FastAPI              │
│                                            │
│ API / Validation / Orchestration           │
│                                            │
│ ┌─────────────┐ ┌───────────────────────┐ │
│ │ Retrieval   │ │ Risk Calculation      │ │
│ └──────┬──────┘ └───────────────────────┘ │
│        ▼                                   │
│ ┌───────────────────────┐                  │
│ │ Eligibility Extraction│                  │
│ └───────────┬───────────┘                  │
│             ▼                              │
│ ┌───────────────────────┐                  │
│ │ Deterministic Matching│                  │
│ └───────────┬───────────┘                  │
│             ▼                              │
│ ┌───────────────────────┐                  │
│ │ Evidence / Source     │                  │
│ └───────────┬───────────┘                  │
│             ▼                              │
│ ┌───────────────────────┐                  │
│ │ Chat Orchestration    │──────────────────┼──→ OpenAI
│ │ + Template Fallback   │                  │
│ └───────────────────────┘                  │
└───────────────────┬────────────────────────┘
                    │
                    ▼
          Bootstrap / Runtime Snapshot
                    ▲
                    │ manual refresh only
                    │
               Bizinfo API
```

# 4. Runtime Data Flow

사용자 요청에서 기업마당 API를 직접 호출하지 않는다.

```text
User Request
→ Local Repository
→ Retrieval
→ Eligibility
→ Matching
→ Evidence
→ Chat / Risk
```

기업마당 외부 호출은 별도 수동 Refresh 경로로 분리한다.

```text
BIZINFO_API_KEY
→ Bizinfo API
→ Raw Response Validation
→ timestamped Runtime Snapshot
→ Loader
→ Normalization
→ service-ready publish
```

실패 시 기존 정상 Snapshot을 유지한다.

# 5. Snapshot / Bootstrap Architecture

[EXPERIMENT]

현재 기업마당 창업 분야 Live Refresh 검증:

- HTTP 200
- Raw 69
- Unique 69
- Duplicate 0
- Loader 69
- Normalization 69

Public Deployment 기동용 Bootstrap:

```text
data/bootstrap/bizinfo_startup_bootstrap.json
```

현재 Bootstrap:

- 69 records
- unique ID 69
- duplicate 0
- Runtime latest verified Snapshot과 동일한 검증 데이터
- Secret 없음

Loader fallback chain:

```text
1. FINBRIDGE_BIZINFO_SNAPSHOT
2. valid runtime service-ready snapshot
3. tracked bootstrap snapshot
```

Runtime collected Snapshot은 Git에 저장하지 않는다.
Bootstrap 1개만 deployment artifact로 Git 추적한다.

# 6. Program Normalization

기업마당 Raw의 다음 값을 중심으로 Program 구조를 만든다.

- `pblancId`
- `pblancNm`
- `jrsdInsttNm`
- `excInsttNm`
- category / subcategory
- `trgetNm`
- `hashtags`
- `reqstBeginEndDe`
- `bsnsSumryCn`
- `reqstMthPapersCn`
- `pblancUrl`
- source created / updated time

Missing 값은 임의 보정하지 않는다.

신청기간 예:

```text
고정 날짜 범위 → FIXED_DATE
예산 소진시까지 → UNTIL_BUDGET_EXHAUSTED
파싱 불가 → UNKNOWN
```

임의 D-day를 생성하지 않는다.

# 7. Eligibility Architecture

Eligibility Extraction baseline은 deterministic regex / normalization을 사용한다.

현재 P0 지원 범위:

- AGE
- BUSINESS_AGE
- REGION
- PRE_FOUNDER
- BUSINESS_REGISTRATION_STATUS
- 안전하게 표현 가능한 OR Group

현재 69건 상태:

```text
SUPPORTED       22
NEEDS_REVIEW    46
UNSUPPORTED      1
```

핵심 Schema:

```text
Program extraction status
Condition extraction status
condition type
operator
polarity
role
raw_value
normalized operands
unit
evidence
source_field
common_conditions
eligibility_groups
global_exclusions
```

Boolean 구조:

```text
common_conditions
AND
(group_1 OR group_2 OR ...)
AND
NOT global_exclusions
```

Evidence 없는 `SUPPORTED`는 허용하지 않는다.

복잡한 별첨/공고문 참조, 주소 이전 대안, 미지원 조건은
`NEEDS_REVIEW / UNKNOWN / UNSUPPORTED` 경계를 유지한다.

# 8. Deterministic Matching

LLM은 Match 상태를 계산하지 않는다.

현재 핵심 결과:

- `MATCH`
- `NO_MATCH`
- `NEEDS_REVIEW`
- `UNKNOWN`

규칙:

- 조건 부재는 불확실 상태를 만들지 않는다.
- 필요한 사용자 값이 없으면 `NO_MATCH`가 아니라 `NEEDS_REVIEW`.
- Evidence가 부족하면 안전한 `MATCH`를 만들지 않는다.
- OR Group은 하나 이상 충족 시 대안 자격 경로 충족.
- global exclusion이 발동하면 `NO_MATCH`.
- `EXCLUDE` polarity는 positive predicate를 한 번만 평가한다.

# 9. Retrieval Architecture

현재 baseline:

```text
Structured Filter
→ Exact / Keyword Search
→ Deterministic Ranking
→ Top-N
```

검색 대상:

- Program name
- Provider / executing organization
- Category / subcategory
- Target raw text
- Eligibility evidence
- Summary
- Hashtags — 보조 점수만

Retrieval score와 Eligibility Match는 분리한다.

Semantic / Vector Retrieval은 현재 미사용이다.

# 10. Risk Calculation Architecture

Endpoint:

```text
POST /risk/calculate
```

입력:

```text
initial_cost
own_capital
monthly_revenue
monthly_expense
loan_amount
annual_interest_rate
loan_term_months
```

지원 상환방식:

```text
원리금균등상환
```

Deterministic 결과:

- available_cash
- monthly_loan_payment
- monthly_cash_flow
- monthly_cash_burn
- runway_months
- remaining_debt_at_runway

내부 계산은 Decimal을 사용하고 최종 Response에서만 반올림한다.

이 기능은 단순 재무 시뮬레이션이며 신용평가·대출승인 예측이 아니다.

# 11. Chat Architecture

Endpoint:

```text
POST /chat
```

Request 개념:

```json
{
  "mode": "GENERAL",
  "message": "...",
  "focus_profile": null,
  "program_id": null,
  "session_id": null
}
```

Response는 문자열 하나가 아니라 Structured Result를 함께 유지한다.

```text
reply
reply_source
model
programs
matches
evidence
sources
actions
suggest_focus_mode
program_context_id
```

## GENERAL

지원사업 탐색 의도가 확인되면:

```text
message
→ Retrieval
→ Top-N Program
→ optional deterministic Match
→ Structured Context
→ OpenAI Explanation or Template Fallback
```

Risk 등 Program Retrieval이 필요 없는 intent에는 검색을 강제하지 않는다.

## FOCUS

`focus_profile`이 있으면 기존 deterministic Matcher를 재사용한다.

## program_id Context

```text
program_id
→ Exact Program
→ Eligibility
→ Evidence
→ optional Match
→ LLM explanation
```

잘못된 ID에서 LLM이 가짜 공고를 생성하지 않는다.

## LLM Failure

```text
OpenAI success → reply_source = LLM
OpenAI failure → reply_source = TEMPLATE_FALLBACK
```

Provider failure에도 Program / Match / Evidence / Source는 유지한다.

# 12. Current API Surface

현재 구현·검증된 Endpoint:

```text
GET  /health
GET  /programs
GET  /programs/{program_id}
POST /programs/match
POST /risk/calculate
POST /income-stability/calculate
POST /chat
```

현재 구현하지 않은 Endpoint:

```text
POST /sales/analyze
```

미구현 API를 제출 기능명세서에서 구현 완료로 기재하지 않는다.

# 13. Security / Secret Architecture

Local:

```text
.env
```

Production:

```text
Railway Secret Environment Variables
```

Secret 후보:

- `OPENAI_API_KEY`
- `BIZINFO_API_KEY`

Non-secret configuration 후보:

- `OPENAI_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `BIZINFO_TIMEOUT_SECONDS`
- `FINBRIDGE_BIZINFO_SNAPSHOT`
- production CORS origins

원칙:

- Secret hardcode 금지
- `.env` Git 제외
- API Key 로그 금지
- 사용자 전체 Profile / 금융 입력 전체 로그 금지
- Bootstrap에 Secret 포함 금지

# 14. Deployment Architecture

[TEAM DECISION — 2026-08-29]

```text
Frontend Hosting = Vercel Hobby
Backend Hosting  = Railway Hobby
Database         = None for MVP
```

Backend Production Start baseline:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check:

```text
GET /health
```

Railway 배포 시 다음을 우선한다.

- GitHub `start-finance-ai/backend` 연결
- Config as Code 파일 없이 Railway Dashboard에서 직접 설정
- Builder: Railpack
- Python: `3.14.3` (`.python-version`)
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`
- Public Networking: Generate Domain
- application sleep 비활성화 권장
- `FINBRIDGE_CORS_ORIGINS`에 production Vercel URL을 exact origin으로 설정
- `OPENAI_API_KEY`를 Secret으로 설정
- `BIZINFO_API_KEY`는 Collector 운영이 필요할 때만 Secret으로 설정 가능
- Runtime DB / Volume은 현재 추가하지 않음
- Docker 및 `.railway/railway.ts`는 현재 도입하지 않음

Public URL을 실제 생성·외부 검증하기 전에는 배포 완료로 기록하지 않는다.
Python `3.14.3` Railway 실제 build는 Public deployment에서 최종 검증하며,
사전 `MISE_PYTHON_COMPILE=1` 설정은 사용하지 않는다.

기본 CORS는 `http://localhost:8443`만 허용한다. 배포 환경변수는 comma-separated
exact origin 목록이며 whitespace·빈 항목을 제거하고 wildcard `*`는 거부한다.
현재 Auth Cookie를 사용하지 않으므로 credentialed CORS는 활성화하지 않는다.

# 15. Frontend Architecture / Current Boundary

현재 Frontend Repository:

```text
start-finance-ai/frontend
```

확인된 Stack:

- React
- Vite
- TypeScript
- pnpm

2026-08-29 실제 로컬 검증:

- `pnpm install` 성공
- `pnpm build` 성공
- `pnpm dev` 성공
- `localhost:8443` 화면 표시 확인

현재 GitHub 코드에는 Figma Make용:

```text
.figma/make/site.json
```

이 누락되어 로컬에서는 임시 `{}` 설정으로 실행 검증했다.

이 임시 파일은 정식 디자인 설정으로 간주하지 않는다.

회의 이후 최신 디자인은 아직 반영 대기 상태이므로,
대규모 Frontend API Integration은 최신 디자인 수령 후 진행한다.

# 16. Database Decision

현재 MVP에서 DB를 추가하지 않는다.

이유:

- Program data는 Bootstrap / Snapshot으로 제공 가능
- `/chat`은 stateless
- Session persistence 미구현
- 실제 Auth backend 미구현
- Public MVP 핵심 흐름에 DB가 필수 dependency가 아님

Railway PostgreSQL은 실제 영속 상태가 필요한 경우에만 후속 도입한다.

# 17. Current Non-Goals

Core Public MVP 완료 전 다음을 추가하지 않는다.

- Vector DB
- Graph DB
- Multi-Agent
- Semantic Retrieval
- K-Startup 추가 Source
- 상권 데이터
- Scheduler / Celery
- 자동 주기 Collector
- PostgreSQL
- Session DB
- Microservice
- Kubernetes

# 18. Immediate Architecture Priority

현재 우선순위:

```text
1. 매출장표 CSV/XLSX 실제 업로드 분석
2. 최신 디자이너 Frontend 반영 확인
3. Frontend ↔ Backend Core API Integration
4. Vercel Public Frontend
5. Cross-origin / Public End-to-End QA
```

단, 신규 Backend 기능이 기존 Public Backend 안정성을 위협하면 회귀 검증을 우선한다.
