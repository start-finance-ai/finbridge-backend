# FINANCE AI — Development Status

Last Updated: 2026-09-05

이 문서는 2026 금융 AI Challenge `FinBridge` Backend / AI / Data / Infra와 Frontend 연동의 실제 개발 진행 상태를 기록한다.

구현되지 않은 기능을 완료된 것처럼 기록하지 않는다. 상태는 실제 코드, 테스트, Railway Public Smoke, QA 재검증 결과를 기준으로 한다.

# 1. Current Phase

Current Phase:

```text
G6 — Submission Candidate / Code Freeze
→ Public E2E Final Double-check + Submission Documents
```

[TEAM DECISION]

- 팀명: `start`
- 서비스명: `FinBridge`
- 내부 완료 목표: `2026-09-03~04`
- 팀 공유 제출 일정: `2026-09-07 오전`
- 공식 최종 마감시각은 제출 전 최신 공식 공지를 다시 확인한다.

# 2. Current Completion Summary

```text
Documentation / Contract                 DONE / continuously updated
FastAPI Scaffold                        VERIFIED
Health Check                            PUBLIC VERIFIED
Bizinfo Live API                        VERIFIED
Manual Collector                        VERIFIED
Bootstrap Snapshot                      VERIFIED
Program Normalization                   VERIFIED
Eligibility Schema                      IMPLEMENTED
Eligibility Extraction Baseline         VERIFIED
Deterministic Matching                  VERIFIED
Structured/Keyword Retrieval            VERIFIED
Regional Deterministic Ranking          PUBLIC VERIFIED
Application Status / Date Logic         PUBLIC VERIFIED
Risk Calculation                        PUBLIC VERIFIED
OpenAI /chat                            PUBLIC VERIFIED
Template Fallback                       VERIFIED
program_id Chat Context                 VERIFIED
Income Stability                        PUBLIC VERIFIED
Sales CSV/XLSX Analysis                 PUBLIC VERIFIED
Backend Railway Deployment              PUBLIC VERIFIED
Frontend Local Build/Dev                VERIFIED
Frontend Production Build               VERIFIED
Frontend API Integration                PUBLIC VERIFIED
Frontend Vercel Deployment              PUBLIC VERIFIED
Database                                NOT USED BY DESIGN
Vector DB / Graph DB / Multi-Agent      NOT IMPLEMENTED / NOT REQUIRED FOR MVP
```

2026-09-05 현재 새 기능 추가를 중단하고 제출 후보를 대상으로 최종 확인하는 Code Freeze 단계다.

현재 전체 Backend regression test 상태:

```text
222 passed
```

# 3. Backend Technology

[EXPERIMENT / CURRENT]

- Python: `3.14.3`
- FastAPI: `0.141.1`
- Pydantic: `2.13.4`
- Uvicorn: `0.52.1`
- pytest: `9.1.1`
- OpenAI Python SDK: `3.6.0`
- OpenAI Responses API
- Model: `gpt-5.6-luna`
- Deployment: Railway Hobby
- Dependency management: `requirements.txt`

Data Access:

```text
Official Bizinfo API
→ Raw Snapshot / Bootstrap
→ Normalization
→ In-memory Repository
→ Retrieval / Eligibility / Matching
```

Database / ORM:

```text
MVP에서는 사용하지 않음
```

# 4. Public Deployment Status

[EXPERIMENT / PUBLIC VERIFIED]

Backend Public URL:

```text
https://backend-production-1620.up.railway.app
```

Railway:

- Region: Southeast Asia / Singapore
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Public `/health`: HTTP 200 verified
- Public `/docs`: accessible
- Root `/`: 404 is expected because no root route is defined

Current OpenAI production settings used for the final P0 verification:

```text
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_OUTPUT_TOKENS=2000
```

Secret values are not recorded in this document.

# 5. Current API Status

## PUBLIC VERIFIED / VERIFIED

```text
GET  /health
GET  /programs
GET  /programs/{program_id}
POST /programs/match
POST /risk/calculate
POST /chat
POST /income-stability/calculate
POST /sales-analysis/analyze
```

# 6. Data / Collector Status

## DS-001 기업마당 지원사업정보 API

Status:

```text
VERIFIED
```

현재 검증된 Main Source는 중소벤처기업부 기업마당 지원사업정보 API다.

수집/운영 원칙:

```text
기업마당 API
→ Raw Snapshot
→ Normalization
→ Eligibility Extraction
→ Structured Eligibility
→ Deterministic Matching
→ Evidence
→ LLM Explanation
```

Collector는 사용자 요청마다 외부 API를 직접 호출하지 않는다.

현재 MVP 운영 방식:

```text
Manual / one-time refresh
→ Snapshot update
→ local/service data use
→ external API failure 시 기존 Snapshot fallback
```

현재 사용 Bootstrap:

```text
69 programs
```

# 7. Eligibility / Matching Status

[EXPERIMENT]

구현 핵심:

- Program / Condition extraction status 분리
- 조건 부재와 Evidence 부족 분리
- `common_conditions + eligibility_groups` 기반 대안 경로 처리
- `global_exclusions`
- Evidence 없는 최종 지원 가능 단정 방지
- 원문 Evidence 유지
- 명시적 조건 비교는 deterministic matching

기존 69건 Extraction baseline:

```text
SUPPORTED       22
NEEDS_REVIEW    46
UNSUPPORTED      1
```

지원 Pattern 예:

- REGION / LOCATION
- AGE
- PRE_FOUNDER
- BUSINESS_AGE
- BUSINESS_REGISTRATION_STATUS
- 안전한 OR Group

주의:

전체 공고문·별첨의 모든 자격조건을 완전 구조화한 것은 아니다. Evidence가 부족하면 `NEEDS_REVIEW`, `UNKNOWN`, `UNSUPPORTED` 계열로 처리한다.

# 8. Retrieval / Regional Ranking Status

[EXPERIMENT / PUBLIC VERIFIED — 2026-09-01]

기본 Retrieval:

```text
Structured Filter
+ Exact / Keyword Search
+ Deterministic Ranking
+ Top-N
```

GENERAL 자연어에서도 다음 프로필을 제한적으로 구조화한다.

- region
- age
- pre-founder / existing business state
- business age
- business registration status

지역 조건이 명시된 경우 일반 keyword score보다 먼저 deterministic region tier를 적용한다.

```text
1. SAME_REGION
2. NATIONWIDE
3. OTHER_REGION_WITH_EXPLICIT_EXCEPTION
4. REGION_UNKNOWN
5. EXPLICIT_OTHER_REGION_ONLY → exclude
```

검증된 동작:

- `대구` → `대구 동구/서구`는 하위 지역 상세정보가 필요하면 `REGION_DETAIL_REQUIRED`
- 대구 사용자에게 명백한 울산/안산 등 타지역 전용 공고가 상위를 지배하지 않음
- 전국 대상 공고는 유지
- 영월 주소 이전 가능, 울산 타지역민 별도조건, 전남 타지역민 예외처럼 실제 예외 Evidence가 있으면 후보를 완전히 삭제하지 않고 `NEEDS_REVIEW` 가능
- 짧은 질문과 긴 종합 질문에서 동일 structured profile을 유지하도록 회귀 테스트 추가

# 9. Application Status / Date Logic

[EXPERIMENT / PUBLIC VERIFIED]

한국 기준 현재 날짜를 사용해 다음 상태를 deterministic하게 계산한다.

```text
OPEN
UPCOMING
CLOSED
NEEDS_CONFIRMATION
```

구현 원칙:

- `Asia/Seoul` 기준
- Windows timezone data 부재 시 한국 UTC+09 fallback
- “지금 신청 가능한” 요청에서 `CLOSED` / `UPCOMING` 제외
- 고정 마감일 OPEN 공고는 마감일 가까운 순 정렬 가능
- `예산 소진시까지`는 임의 D-day 계산 금지
- 예산 소진 여부를 확인할 수 없으면 `NEEDS_CONFIRMATION`

# 10. Risk Calculation Status

[EXPERIMENT / PUBLIC VERIFIED]

Endpoint:

```text
POST /risk/calculate
```

입력 예:

- initial_cost
- own_capital
- monthly_revenue
- monthly_expense
- loan_amount
- annual_interest_rate
- loan_term_months

결정론적 계산:

- available cash
- 원리금균등 monthly payment
- monthly cash flow
- cash burn
- runway
- remaining debt at runway

Decimal / `ROUND_HALF_UP` 기반 계산을 사용한다.

주의:

금융기관의 실제 대출 승인·신용평가 결과를 의미하지 않는다.

# 11. Income Stability Status

[EXPERIMENT / PUBLIC VERIFIED]

Endpoint:

```text
POST /income-stability/calculate
```

입력:

```text
최근 6개월 월별 소득
```

결정론적 지표:

- 평균
- 모집단 표준편차
- 변동계수(CV)
- 최소 / 최대

원칙:

- 정확히 6개월
- 0 허용
- 음수 / 잘못된 타입 거부
- 평균 0이면 CV는 `null`
- 임의의 “안정/불안정” 금융기관 판정 기준을 생성하지 않음

한계 안내:

신용평가·소득인정·상환능력 판정을 의미하지 않는 참고 지표다.

# 12. Sales Spreadsheet Analysis Status

[EXPERIMENT / PUBLIC VERIFIED]

Endpoint:

```text
POST /sales-analysis/analyze
```

상태:

```text
REAL CSV/XLSX ANALYSIS IMPLEMENTED
NOT DEMO SAMPLE
```

구현:

- CSV / XLSX multipart upload
- 명시적 column alias 처리
- 날짜 / 매출금액 validation
- 최대 5MB / 50,000 rows
- 평균 매출
- trend
- CV
- MoM
- 결측 월을 임의 0으로 채우지 않음
- 음수 매출은 현재 refund 모델 미지원으로 오류 처리
- 파일 영구 저장 없음
- LLM 미사용

P1 잔여 QA:

- 동일 거래의 exact duplicate row에 대한 warning 추가 검토

# 13. AI / Chat Status

[EXPERIMENT / PUBLIC VERIFIED — 2026-09-01]

Endpoint:

```text
POST /chat
```

지원:

- `GENERAL`
- `FOCUS`
- optional `focus_profile`
- optional `program_id`
- stateless session contract
- structured programs / matches / evidence / sources / actions
- OpenAI explanation
- deterministic template fallback
- `suggest_focus_mode`

Provider:

```text
OpenAI Responses API
gpt-5.6-luna
```

LLM 역할:

- 자연어 의도 / 사용자 조건 보조 해석
- 검증된 retrieval / matching / calculation 결과 설명
- Evidence 종합
- 추가 확인사항 / 다음 행동 설명

LLM이 최종 자격조건, 신청기간, 지원금, 금융수치를 임의 생성하도록 하지 않는다.

## 13.1 Prompt / Output Hardening

QA 이후 Public 장애 원인:

```text
AIProviderTimeoutError         reason=TIMEOUT
AIProviderMaxOutputTokensError reason=MAX_OUTPUT_TOKENS
```

수정:

- provider `status` / `incomplete_details` 검사
- incomplete partial output 사용자 노출 차단
- transient timeout/rate/server error 최대 1회 retry
- auth/quota/config/incomplete는 불필요 retry 금지
- fallback 구조화
- LLM prompt 상세 후보 최대 3건
- Response structured programs는 5건 유지
- 불필요한 전체 HTML summary / 중복 evidence / sources context 제거
- visible reply 목표 약 700~900 token
- Railway timeout 30초 유지
- production `max_output_tokens` 2000으로 조정

동일 QA 질문 기준 prompt context 측정:

```text
Context JSON: 10,786 chars / 14,854 bytes
→ 2,982 chars / 4,178 bytes

약 72% 감소
```

Structured API Contract는 유지:

```text
programs 5
sources 5
actions 10
```

# 14. QA P0 Closure — PUBLIC VERIFIED

[EXPERIMENT / PUBLIC VERIFIED — 2026-09-01]

QA 담당자 검증 이후 발견된 P0 문제와 최종 상태:

| P0 | 문제 | 최종 상태 |
|---|---|---|
| 1 | AI 답변 문장 절단 | PUBLIC VERIFIED FIXED |
| 2 | 반복 `TEMPLATE_FALLBACK / model=null` | PUBLIC VERIFIED FIXED for regression cases |
| 3 | 준비사항 1/2/3 부재 | PUBLIC VERIFIED FIXED |
| 4 | 대구 사용자에게 명시적 타지역 공고 상위 노출 | PUBLIC VERIFIED FIXED |
| 5 | “지금 신청 가능한” 날짜/상태/마감일 정렬 부재 | PUBLIC VERIFIED FIXED |

최종 복합 회귀 질문에서 확인:

```text
reply_source = LLM
model = gpt-5.6-luna
대구 공고 우선 정렬
문장 절단 없음
준비사항 1/2/3 출력
신청기간 출력
공식 출처 출력
```

따라서 2026-09-01 기준 AI Chat P0는 Public 환경에서 검증 완료로 기록한다.

주의:

- 특정 외부 LLM 호출은 네트워크/Provider 특성상 향후 일시 실패할 수 있다.
- 이 경우 structured result / Evidence를 유지하는 deterministic Template Fallback을 서비스 안전장치로 사용한다.
- `PUBLIC VERIFIED`는 모든 가능한 자연어 입력의 완전 무오류를 의미하지 않으며, 정의된 P0 regression cases가 Public 환경에서 통과했음을 의미한다.

# 15. Test Status

현재 전체 Backend regression:

```text
222 passed
```

QA hardening 과정의 test progression:

```text
189 passed  — Sales analysis 포함 기존 baseline
215 passed  — 1차 Chat P0 hardening
219 passed  — compact context / region / OR 보정
222 passed  — long-query profile + deterministic regional tier 보정
```

`git diff --check`도 각 수정 단계에서 통과했다.

# 16. Security Status

[EXPERIMENT]

- `.env` Git ignore
- OpenAI / Bizinfo Secret은 환경변수 사용
- Secret literal을 문서 / Source에 기록하지 않음
- Raw file 영구 업로드 저장 없음
- API 응답에서 Secret 미노출
- safe provider log는 error class / reason 수준만 기록

# 17. Frontend Status

Repository:

```text
start-finance-ai/frontend_v2
```

확인된 Stack:

- React 19
- Vite 8
- TypeScript
- pnpm

Local:

```text
Production build  VERIFIED
```

Frontend ↔ Backend API Integration:

```text
PUBLIC VERIFIED
```

Frontend Public Vercel Deployment:

```text
PUBLIC VERIFIED
https://finbridge-start.vercel.app
```

제출 후보 Public URL에서 확인된 연결:

- `GET /programs` 실제 기업마당 데이터 목록
- `GET /programs/{program_id}` 지원사업 상세
- `POST /chat` 실제 LLM 응답
- 지원사업 상세 → AI `program_id` context
- `GENERAL` / `FOCUS` 모드
- GENERAL 응답의 `suggest_focus_mode=true` 시 "집중모드로 전환" 배너
- 집중모드 전환 후 기존 대화와 context 유지
- `POST /risk/calculate` deterministic 계산
- `POST /sales-analysis/analyze` 실제 CSV/XLSX 업로드·분석
- `POST /income-stability/calculate` deterministic 계산

Frontend 마감 반영:

- AI Markdown 렌더링 개선
- `NEEDS_REVIEW` 상태와 실제 API Error UI 구분
- 지원사업 카드의 임의·반복 이미지 제거
- Auth / Login / Signup Public flow 제거

주의:

- 지원사업 카드 이미지는 Evidence로 사용하지 않는다.
- Auth / Login / Signup은 현재 Public 제출 범위에 포함하지 않는다.

# 18. Submission Candidate / Code Freeze

현재 상태:

```text
Backend                     PUBLIC VERIFIED
Frontend Vercel             PUBLIC VERIFIED
Frontend ↔ Railway Backend  PUBLIC VERIFIED
Frontend Production Build   VERIFIED
Submission Candidate        READY FOR FINAL DOUBLE-CHECK
```

운영 원칙:

- 새 기능을 추가하지 않는다.
- 제출 후보에서 회귀를 유발할 수 있는 비필수 변경을 하지 않는다.
- 미구현·Mock·Planned 기능을 제출 기능으로 기재하지 않는다.
- Public E2E 최종 더블체크 결과에 따라 문서의 검증 상태만 사실대로 조정한다.

# 19. Current Blockers

## Submission P0 / Remaining Work

1. 제출 후보 Public URL의 핵심 E2E 최종 더블체크
2. 제출 기능명세서 / 기획서 최종화
3. 공식 제출 공지와 최종 마감시각 재확인

## Not Current Blocker

- K-Startup 추가 Source
- Vector DB
- Graph DB
- Multi-Agent
- PostgreSQL
- Scheduler / Cron
- 전체 기업마당 분야 Coverage

# 20. Immediate Next Tasks

```text
1. Public E2E 최종 더블체크
2. 기능명세서 / 기획서 최종화
3. 공식 제출 공지 재확인
```

# 21. Submission Rule

- 공식 기능명세서에는 최종 Public URL에서 실제 구현·검증된 기능만 작성한다.
- 기획서에서는 실제 구현 범위와 향후 확장 방향을 구분한다.
- `PLANNED`, `DRAFT`, `DEMO`, 미구현 기능을 실제 완료 기능처럼 작성하지 않는다.
- AI가 최종 지원자격, 대출 승인, 금융기관 판정을 보장한다고 표현하지 않는다.
- 지원사업의 실제 정보는 공식 Source / Snapshot / Evidence에서 확인된 값만 표시한다.
