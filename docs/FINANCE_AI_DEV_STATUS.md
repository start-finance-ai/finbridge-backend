# FINANCE AI — Development Status

Last Updated: 2026-08-31

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
Income Stability                 PUBLIC VERIFIED
Sales Upload/Analysis            PUBLIC VERIFIED
Database                         NOT USED BY DESIGN
```

현재 전체 Backend test 상태:

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
- openpyxl: `3.1.5`
- python-multipart: `0.0.32`
- defusedxml: `0.7.1`
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
POST /sales-analysis/analyze
POST /chat
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
215 passed
```

# 10.1 Freelancer Income Stability Status

Status:

```text
IMPLEMENTED / VERIFIED LOCALLY / PUBLIC VERIFIED
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

Railway Public Smoke (2026-08-30):

- 일반 6개월 입력 → HTTP 200, 평균 `3000000`, 모집단 표준편차 `129099.44`, CV `4.3`, 최저 `2800000`, 최고 `3200000`, disclaimer 정상
- 전월 0원 입력 → HTTP 200, 평균 `0`, 표준편차 `0`, CV `null`, 최저·최고 `0`

# 10.2 Sales Spreadsheet Analysis Status

Status:

```text
IMPLEMENTED / VERIFIED LOCALLY / PUBLIC VERIFIED
```

Endpoint:

```text
POST /sales-analysis/analyze
Content-Type: multipart/form-data
```

구현:

- FinBridge Sample Schema 기반 `.csv`, `.xlsx` 실제 업로드 분석
- CSV UTF-8 / UTF-8-SIG / CP949 지원
- XLSX required-column sheet 탐색; 유효 sheet 복수이면 모호성 오류
- canonical/명시적 한국어 alias header만 지원
- 최대 파일 5 MB, 최대 데이터 50,000행
- Decimal 기반 월별 집계, 평균, 합계, 최고·최저 월, 모집단 표준편차/CV
- 연속 최근 6개월의 최근 3개월 대 직전 3개월 추세
- 최근 월 MoM 및 계산 불가 reason
- missing calendar month 탐지; 0원 month 자동 생성 없음
- Data Quality metadata와 구조화 validation error
- 실제 업로드 성공 시 `is_demo=false`, currency `KRW`
- 업로드 원문 영구 저장·로그·LLM 전달 없음
- openpyxl read-only/data-only와 defusedxml XML 보호 사용

계약 문서:

```text
docs/SALES_UPLOAD_SCHEMA.md
```

검증:

```text
Sales Analysis tests  45 passed
Full Backend tests    215 passed
```

Railway Public Smoke (2026-08-30):

- CSV → HTTP 200, `is_demo=false`, `source_format=CSV`, monthly series·평균·summary·최근 추세·변동성·MoM·Data Quality 정상, missing months·warnings 없음
- XLSX → HTTP 200, `is_demo=false`, `source_format=XLSX`, `sheet_name=매출`, monthly series·평균·summary·최근 추세·변동성·MoM·Data Quality 정상
- `sales_amount` 필수 컬럼 누락 CSV → `REQUIRED_COLUMN_MISSING`, field `sales_amount`, missing columns `["sales_amount"]` 확인

현재 미검증:

- Frontend 실제 파일 업로드 연동

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
- Railway 재배포 후 동일 Public `/chat` smoke에서 당시 문장 절단 해소 확인

Local QA P0 보강 (2026-08-31, **NOT PUBLIC VERIFIED**):

- 후속 QA 장문 질문에서 문장 중간 절단과 `TEMPLATE_FALLBACK` 반복 재현
- Responses API `status=incomplete`와 `incomplete_details.reason=max_output_tokens` 감지
- incomplete 부분 문장 폐기 후 structured deterministic fallback 사용
- LLM 상세 후보를 상위 3건으로 제한하고 나머지는 추가 후보로 축약; Response의 programs 계약은 유지
- timeout/rate limit/server transient 오류만 최대 1회 재시도; auth/quota/config 오류는 재시도하지 않음
- 안전한 provider error class/reason code만 로그하고 API Key·전체 user prompt는 로그하지 않음
- 기본 timeout `30초`, 기본 `max_output_tokens=1200`으로 조정
- fallback에 현재 후보·조건·부족정보·준비사항 1/2/3·신청기간·공식 출처 반영
- GENERAL 메시지의 명시적 지역·연령·예비/기창업·업력·사업자등록 상태를 제한적으로 구조화해 기존 matcher/retrieval에 전달
- 한국 날짜 기준 `OPEN / UPCOMING / CLOSED / NEEDS_CONFIRMATION` 계산 및 현재 신청 가능/마감 임박 정렬 구현
- 전체 Backend tests `215 passed`
- 이번 보강은 Railway 재배포 및 Public `/chat` 재검증 전이므로 PUBLIC VERIFIED로 간주하지 않음

Local QA 안정화 (2026-09-01, **NOT PUBLIC VERIFIED**):

- Railway 로그에서 확인된 `/chat` fallback 원인은 `TIMEOUT`과 `MAX_OUTPUT_TOKENS`
- timeout `30초`, max output `1200`, transient retry 최대 1회 및 incomplete structured fallback 유지
- 동일한 69건 bootstrap·대구 28세 예비창업 질문에서 LLM Context JSON을
  `10,786자 / 14,854 bytes`에서 `2,982자 / 4,178 bytes`로 약 72% 축소
- LLM 상세 후보 최대 3건, 후보별 핵심 Eligibility/Match/기간/상태/신청방법 요약/공식 URL만 전달;
  Response의 programs/evidence/sources/actions 계약은 유지
- 답변 visible token 상한 900과 준비사항 1/2/3 마지막 출력 규칙을 prompt에 명시
- 명시적 타 시·도 local-only Evidence 추출을 보강하고 전국 공고는 유지;
  주소 이전·타지역민 허용 Evidence는 자동 제외 대신 `NEEDS_REVIEW` 유지
- 예비창업자와 업력 조건의 정방향·역방향 OR를 보존하고, 충족되지 않은 다른 OR 경로의
  업력 누락은 LLM Context와 structured fallback 준비사항에서 제외
- 전체 Backend tests `219 passed`; Railway 재배포·Public 재검증 전이므로 PUBLIC VERIFIED 아님

Local GENERAL 지역 우선순위 안정화 (2026-09-01, **NOT PUBLIC VERIFIED**):

- Public QA 전달 장문을 69건 bootstrap에서 재현하고 짧은 질문과 동일한
  `region=대구 / age=28 / pre_founder=true / business_status=UNREGISTERED` 추출 확인
- 일반 keyword score보다 앞서는 deterministic region tier 적용:
  `SAME_REGION → NATIONWIDE → OTHER_REGION_WITH_EXPLICIT_EXCEPTION → REGION_UNKNOWN`
- 명시적 타지역 전용은 제외하고 주소 이전·타지역민 예외 공고는 `NEEDS_REVIEW` 후보로 유지
- 전체 Backend tests `222 passed`; 수정 후 Railway Public 재검증 전이므로 PUBLIC VERIFIED 아님

Provider failure:

```text
TEMPLATE_FALLBACK
```

Structured Result / Evidence는 유지됨.

현재 미구현:

- Session Persistence
- LLM Eligibility Extraction
- General free-form user profile complete extraction (명시적 P0 필드의 제한적 추출만 구현)
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
- 2026-08-30 출력 토큰 보정 재배포 당시 Public `/chat` 문장 절단 해소 확인
- 2026-08-31 후속 QA 재현에 대한 로컬 P0 보강은 Public 재검증 대기

Config as Code 파일과 `.railway/railway.ts`는 사용하지 않는다. 현재 상태는 Railway
Dashboard-based deployment 및 Public HTTPS smoke `VERIFIED`이다. `/health`, `/programs`,
`/risk/calculate`, `/chat`을 외부에서 검증했고, 2026-08-30 출력 토큰 보정 당시
`/chat`도 재검증했다. 2026-08-31 로컬 P0 보강은 재배포 전이며 Public 재검증이
필요하다. `MISE_PYTHON_COMPILE=1`은 사전 설정하지 않는다.

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

1. 최신 디자이너 Frontend 반영 확인
2. Frontend ↔ Backend 연동
3. Vercel Public Deployment
4. Public End-to-End QA

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
1. 최신 디자이너 Frontend 반영 확인
2. Frontend ↔ Backend 연동
3. Vercel Public Deployment
4. Public E2E QA
```

# 18. Submission Rule

- 공식 기능명세서에는 최종 Public URL에서 실제 구현·검증된 기능만 작성한다.
- 기획서에서는 현재 구현 범위와 향후 확장 방향을 명확히 구분한다.
- `PLANNED`, `DRAFT`, `DEMO`, 미구현 기능을 실제 완료 기능처럼 쓰지 않는다.
- Public URL / Frontend Integration / Deployment는 실제 외부 검증 전까지 완료로 표시하지 않는다.
