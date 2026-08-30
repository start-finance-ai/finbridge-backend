# FINANCE AI — Development Status

Last Updated: 2026-08-30

이 문서는 2026 금융 AI Challenge `FinBridge` Backend / AI / Data / Infra의 실제 개발 진행 상태를 기록한다.

구현되지 않은 기능을 완료된 것처럼 기록하지 않는다.
상태는 실제 코드, 실행, 테스트, Live Smoke 결과를 기준으로 한다.

# 1. Current Phase

Current Phase:

```text
G5 — Backend Public Deployment Verified
→ Remaining Backend Features + Frontend Integration
```

[TEAM DECISION]

- 팀명: `start`
- 서비스명: `FinBridge`
- 내부 완료 목표: `2026-09-03~04`
- 팀 공유 제출 일정: `2026-09-07 오전`
- 공식 최종 마감시각은 제출 전 최신 공지 재확인

# 2. Current Completion Summary

```text
Documentation / Contract          DONE / continuously updated
FastAPI Scaffold                 VERIFIED
Health Check                     VERIFIED
Bizinfo Live API                 VERIFIED
Manual Collector                 VERIFIED
Bootstrap Snapshot               VERIFIED locally
Program Normalization            VERIFIED
Eligibility Schema               IMPLEMENTED
Eligibility Extraction Baseline  VERIFIED
Deterministic Matching           VERIFIED
Structured/Keyword Retrieval     VERIFIED
Risk Calculation                 VERIFIED
OpenAI /chat                     VERIFIED
Template Fallback                VERIFIED
program_id Chat Context          VERIFIED
Frontend Local Build/Dev         VERIFIED
Backend Public Deployment        VERIFIED
Frontend API Integration         NOT YET
Frontend Public Deployment       NOT YET
Income Stability                 VERIFIED LOCALLY
Sales Upload/Analysis            NOT YET
Database                         NOT USED BY DESIGN
```

현재 전체 Backend test 상태:

```text
144 passed
```

# 3. Backend Technology

[EXPERIMENT / CURRENT]

- Python: `3.14.3`
- FastAPI: `0.141.1`
- Pydantic: `2.13.4`
- Uvicorn: `0.52.1`
- pytest: `9.1.1`
- OpenAI Python SDK: `3.6.0`
- Dependency: `requirements.txt`

Data Access:

```text
Local Snapshot / Bootstrap
→ lazy in-memory Repository
```

Database / ORM:

```text
MVP에서는 사용하지 않음
```

# 4. Current API Status

## VERIFIED

```text
GET  /health
GET  /programs
GET  /programs/{program_id}
POST /programs/match
POST /risk/calculate
POST /income-stability/calculate
POST /chat
```

## NOT IMPLEMENTED

```text
POST /sales/analyze
```

# 5. Data / Collector Status

## DS-001 기업마당

Status:

```text
VERIFIED
```

공식 API Contract:

```text
GET https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do
crtfcKey
dataType=json
searchCnt=100
searchLclasId=06
```

2026-08-29 Live Refresh:

- HTTP 200
- API call 1회
- Raw 69
- Unique 69
- Duplicate 0
- Loader 69
- Normalization 69

Collector:

```text
Manual CLI only
```

사용자 요청마다 기업마당을 호출하지 않는다.

현재 미구현:

- Pagination
- Scheduler
- Cron
- DB sync
- 다른 분야 자동 수집

# 6. Bootstrap Status

[EXPERIMENT]

검증된 69건 Bootstrap:

```text
data/bootstrap/bizinfo_startup_bootstrap.json
```

검증:

- records 69
- unique IDs 69
- duplicate 0
- Loader 성공
- Normalization 성공
- Eligibility / Retrieval 성공
- Secret scan 정상
- Runtime 외부 API 호출 없이 Fresh Deployment simulation 성공

Fallback:

```text
1. FINBRIDGE_BIZINFO_SNAPSHOT
2. valid runtime service-ready snapshot
3. tracked bootstrap snapshot
```

주의:

Bootstrap 작업 최종 보고 시 해당 파일은 아직 unstaged 상태였다.
실제 Railway 배포 전에 반드시 Git stage / commit / push 여부를 재확인한다.

# 7. Eligibility Status

## Schema

`docs/ELIGIBILITY_SCHEMA.md`

구현 핵심:

- Program/Condition extraction status 분리
- 조건 부재 / Evidence 부족 분리
- DNF형 `common_conditions + eligibility_groups`
- `global_exclusions`
- `ELIGIBILITY_EXCEPTION` metadata-only
- Evidence 없는 `SUPPORTED` 차단
- YEAR/MONTH 분리
- `raw_value` + normalized operand 유지
- deterministic matching

## Extraction Baseline

지원 Pattern:

- AGE
- BUSINESS_AGE
- REGION
- PRE_FOUNDER
- BUSINESS_REGISTRATION_STATUS
- 안전한 OR Group

69건 Extraction:

```text
SUPPORTED       22
NEEDS_REVIEW    46
UNSUPPORTED      1
```

전체 공고·별첨 Eligibility 완전 Coverage는 아니다.

# 8. Matching Status

Status:

```text
VERIFIED
```

핵심 Case:

- 업력 7년 이하 / 사용자 3년 → MATCH
- 업력 7년 이하 / 사용자 9년 → NO_MATCH
- 업력 미입력 → NEEDS_REVIEW
- 지역 조건 자체 없음 → 지역 때문에 불확실해지지 않음
- 별첨 미확보 → MATCH 금지
- 법인 제외 / 법인 사용자 → global exclusion → NO_MATCH

실제 Raw Program에서도 MATCH / NEEDS_REVIEW HTTP 결과 검증 완료.

# 9. Retrieval Status

Status:

```text
VERIFIED
```

구현:

```text
Structured Filter
+ Exact / Keyword Search
+ deterministic ranking
+ Top-N
```

Endpoint:

```text
GET /programs
```

실제 Raw Query 예:

- `창업`
- `청년`
- `대구`
- `중소벤처기업부`
- 존재하지 않는 검색어

No-result에서 구조적으로 Program을 생성하지 않는다.

Vector / Semantic Retrieval:

```text
NOT IMPLEMENTED / currently not required
```

# 10. Risk Calculation Status

Status:

```text
VERIFIED
```

Endpoint:

```text
POST /risk/calculate
```

구현:

- available cash
- 원리금균등 monthly payment
- monthly cash flow
- cash burn
- runway
- remaining debt at runway

Validation:

- 음수 금액/금리 거부
- 대출금 > 0이면 기간 >= 1
- 0% 금리 처리
- 무대출 처리
- `runway=null` 의미 명시

Risk 작업 완료 시 전체 test:

```text
47 passed
```

이후 Regression 포함 현재 전체 test:

```text
144 passed
```

# 10.1 Freelancer Income Stability Status

Status:

```text
IMPLEMENTED / VERIFIED LOCALLY / PUBLIC NOT YET
```

Endpoint:

```text
POST /income-stability/calculate
```

입력·검증:

- 최근 6개월 월별 소득을 정확히 6개 입력
- 각 소득은 숫자이며 0 이상
- 0원인 달 허용, 음수·5개·7개 입력은 HTTP 422
- 결측값 보정 없음

Deterministic calculation:

- 평균 = `sum(monthly_incomes) / 6`
- 모집단 분산 = `Σ(x - mean)^2 / 6`
- 모집단 표준편차 = `sqrt(variance)`
- 변동계수(%) = `standard_deviation / mean * 100`
- 평균이 0이면 변동계수는 `null`
- 최저·최고 월 소득 반환
- 내부 계산은 `Decimal`, 최종 금액·비율 응답은 소수 둘째 자리 `ROUND_HALF_UP`

제한:

- LLM 호출 없음
- 소득 데이터 저장 없음
- 안정/주의/위험 등급 또는 금융점수 생성 없음
- 계약 지속성·세금·부채·신용정보 미반영
- 금융기관의 소득 인정·신용평가를 의미하지 않는 disclaimer 반환

검증:

```text
Income Stability tests  13 passed
Full Backend tests      144 passed
```

# 11. AI / Chat Status

Status:

```text
VERIFIED
```

Provider:

```text
OpenAI
Responses API
gpt-5.6-luna
reasoning effort = low
```

Endpoint:

```text
POST /chat
```

구현:

- GENERAL
- FOCUS
- optional focus_profile
- optional program_id
- stateless session contract
- Structured Program / Match / Evidence / Sources
- OpenAI Explanation
- Template Fallback
- suggest_focus_mode
- program_id detail context

OpenAI Live Smoke:

- HTTP 200
- `reply_source=LLM`
- non-empty reply
- latency 약 4.3초
- API Key 노출 없음

Railway Public `/chat` LLM Smoke (2026-08-30):

- OpenAI Responses API 호출 성공 (`gpt-5.6-luna`)
- `reply_source=LLM`, non-empty reply 확인
- Retrieval / Evidence / Source 유지 확인
- 기존 `max_output_tokens=500`에서 문장 중간 truncation 관찰
- 기본값을 `900`으로 상향하고 `OPENAI_MAX_OUTPUT_TOKENS` 환경변수로 조정 가능하게 보정
- 로컬 provider 및 `/chat` contract regression test 통과
- Railway 재배포 후 동일 Public `/chat` smoke 재검증 완료
- `reply_source=LLM`, `model=gpt-5.6-luna` 및 문장 절단 현상 해소 확인

Provider failure:

```text
TEMPLATE_FALLBACK
```

Structured Result / Evidence는 유지됨.

현재 미구현:

- Session Persistence
- LLM Eligibility Extraction
- General free-form user profile complete extraction
- Second LLM provider fallback

# 12. Security Status

[EXPERIMENT]

- `.env` Git ignore 확인
- 실제 `OPENAI_API_KEY` / `BIZINFO_API_KEY` local `.env` 저장
- Secret Source / 문서 literal scan: 이상 없음
- Runtime Snapshot metadata에 Secret 없음
- Bootstrap Secret marker 없음
- API Key URL 노출 없음
- `.env` git status 노출 없음

현재 Profile 포함 OpenAI Live Smoke는 개인정보 최소화·동의 정책 미확정으로 수행하지 않았다.

# 13. Frontend Status

Repository:

```text
start-finance-ai/frontend
```

2026-08-29 latest main pull 완료.

확인된 Stack:

- React 19.2.4
- React DOM 19.2.4
- Vite 8.0.5
- TypeScript 5.9.3
- pnpm

실제 로컬 검증:

```text
pnpm install  SUCCESS
pnpm build    SUCCESS
pnpm dev      SUCCESS
localhost:8443 화면 표시 SUCCESS
```

현재 GitHub Frontend의 `vite.config.ts`가 `.figma/make/site.json`을 요구하지만 해당 파일이 Git에 없었다.

로컬 검증에서는 임시 `{}` 파일을 UTF-8 BOM 없이 생성하여 build/dev를 성공시켰다.

이 임시 파일은 정식 Figma 설정으로 확정하지 않는다.

회의 이후 최신 디자인:

```text
아직 반영 대기
```

Frontend ↔ Backend API Integration:

```text
NOT STARTED
```

# 14. Deployment Decision

[TEAM DECISION — 2026-08-29]

```text
Frontend = Vercel Hobby
Backend  = Railway Hobby
DB       = None for MVP
```

Railway PostgreSQL은 현재 추가하지 않는다.

Backend Public URL:

```text
DEPLOYED / PUBLIC HTTPS VERIFIED
```

Frontend Public URL:

```text
NOT CREATED / NOT VERIFIED
```

## Railway Public Deployment

Status:

```text
PUBLIC VERIFIED
```

구현·검증:

- Region = Southeast Asia / Singapore
- Railway Dashboard-based deployment contract 확정
- Builder = Railpack
- `.python-version` = `3.14.3`
- Start Command = `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check = `/health`
- Public Networking = Generate Domain
- Database / Volume / Docker 없음
- `FINBRIDGE_CORS_ORIGINS` exact-origin parser와 CORS middleware
- default local origin `http://localhost:8443`
- wildcard origin 거부
- Secret·`.env`·runtime Snapshot 없는 clean venv/import 성공
- 실제 Uvicorn TCP 기동 후 `/health`, `/programs`, `/chat` template fallback,
  `/risk/calculate`, allowed/disallowed CORS 검증
- Public HTTPS Backend 정상 접근
- Public `GET /health` → HTTP 200, `{"status":"ok","service":"FinBridge"}`
- Public `GET /programs?query=창업&limit=5` → HTTP 200, BIZINFO 지원사업 5건
- Public `POST /risk/calculate` → HTTP 200, deterministic calculation 정상
- Public `POST /chat` → HTTP 200, `reply_source=LLM`, `model=gpt-5.6-luna`
- Public `/chat` Retrieval / Evidence / Source 유지
- 출력 토큰 보정 재배포 후 Public `/chat` 문장 절단 현상 해소 확인

Config as Code 파일과 `.railway/railway.ts`는 사용하지 않는다. 현재 상태는 Railway
Dashboard-based deployment 및 Public HTTPS smoke `VERIFIED`이다. `/health`, `/programs`,
`/risk/calculate`, `/chat`을 외부에서 검증했고, 출력 토큰 보정 재배포 후 `/chat`도
재검증했다. `MISE_PYTHON_COMPILE=1`은 사전 설정하지 않는다.

현재 배포 P0:

- 최종 Vercel URL 확정 후 CORS Variable 설정
- 최신 디자이너 Frontend 반영 확인
- Frontend ↔ Backend 연동
- Vercel Public Deployment
- Public End-to-End QA

# 15. Current Repository / Git Note

이번 문서 최신화 시작 전 `git status`는 clean이었다.
이번 작업은 문서만 수정하며 commit / push는 수행하지 않는다.

Frontend에서는 로컬 실행을 위해 만든:

- `.gitignore`
- `.figma/make/site.json`

이 정식 팀 변경인지 아직 확정하지 않았다.
디자이너 최신 push와 충돌하지 않도록 임의 commit을 피한다.

# 16. Current Blockers

## P0

1. 매출장표 CSV/XLSX 실제 업로드 분석
2. 최신 디자이너 Frontend 반영 확인
3. Frontend ↔ Backend 연동
4. Vercel Public Deployment
5. Public End-to-End QA

## P1

- 대표 Demo 공고 5~10건 Human Review
- Profile/개인정보 외부 LLM 전달 정책 최소 확정

## Not Current Blocker

- K-Startup
- Vector DB
- Graph DB
- Multi-Agent
- PostgreSQL
- Scheduler
- 전체 기업마당 분야 Coverage

# 17. Immediate Next Tasks

현재 순서:

```text
1. 매출장표 CSV/XLSX 실제 업로드 분석
2. 최신 디자이너 Frontend 반영 확인
3. Frontend ↔ Backend 연동
4. Vercel Public Deployment
5. Public E2E QA
```

# 18. Submission Rule

- 공식 기능명세서에는 최종 Public URL에서 실제 구현·검증된 기능만 작성한다.
- 기획서에서는 현재 구현 범위와 향후 확장 방향을 명확히 구분한다.
- `PLANNED`, `DRAFT`, `DEMO`, 미구현 기능을 실제 완료 기능처럼 쓰지 않는다.
- Public URL / Frontend Integration / Deployment는 실제 외부 검증 전까지 완료로 표시하지 않는다.
