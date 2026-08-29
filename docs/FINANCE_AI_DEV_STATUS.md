# FINANCE AI — Development Status

Last Updated: 2026-08-29

이 문서는 2026 금융 AI Challenge Backend / AI / Data / Infra의 실제 개발 진행 상태를 기록한다.

구현되지 않은 기능을 완료된 것처럼 기록하지 않는다.

상태는 실제 코드, 데이터 검증, 테스트 결과를 기준으로 갱신한다.


# 1. Current Phase

Current Phase:

```text
G4 — Core Implementation IN PROGRESS
```

[TEAM DECISION — 2026-08-29]

- 팀명: `start`
- 서비스명: `FinBridge`
- Backend 구축·배포, 디자인, QA 내부 완료 목표: `2026-09-03~04`
- 팀 공유 제출 일정: `2026-09-07 오전` — 최종 제출 전 공식 공지 재확인

기업마당 Main Data Source의 최초 실측 검증은 완료되어 있다.

[RECOMMENDATION] 2026-08-28 문서에서는 Architecture Freeze 전에 다수의 추가 데이터 검증을 선행하려 했으나, 현재 일정에서는 **검증된 DS-001을 기준으로 최소 Schema와 API Contract를 빠르게 Freeze하고 Core Backend 구현으로 전환**하는 편이 안전하다.

검증된 기업마당 Snapshot을 사용하는 FinBridge Core Backend baseline을 구현하고 로컬 실행·API·자동화 테스트를 검증했다.

# 2. Repository

Backend Repository:

```text
start-finance-ai/backend
```

현재 주요 구조:

```text
backend/
├─ app/
│  ├─ api/
│  ├─ data/
│  ├─ eligibility/
│  ├─ schemas/
│  ├─ services/
│  └─ main.py
├─ tests/
├─ requirements.txt
├─ .gitignore
├─ AGENTS.md
├─ README.md
│
├─ docs/
│  ├─ FINANCE_AI_GROUND_TRUTH.md
│  ├─ FINANCE_AI_MVP_SCOPE.md
│  ├─ FINANCE_AI_ARCHITECTURE.md
│  ├─ DATA_SOURCES.md
│  ├─ FINANCE_AI_DEV_STATUS.md
│  │
│  └─ planning/
│     └─ 2026_금융_AI_Challenge_기획서_AI_Backend_Data_Infra_담당초안.md
│
└─ data/
   └─ raw/
      └─ bizinfo/
         └─ bizinfo_startup_sample.json
```

## Local Development Environment

- [x] Python 가상환경 `.venv` 생성 완료
- [x] 가상환경 활성화 및 Python 실행 확인
- [x] `.venv/`를 `.gitignore`에서 제외하도록 설정
- [x] `.env`, `.env.*`, `data/raw/` 등 개발 중 비공개/Raw 파일 제외 규칙 설정

`.venv/`는 로컬 개발환경이므로 Repository 구조에는 포함하지 않으며 Git에 커밋하지 않는다.


# 3. Documentation Status

## COMPLETED

- [x] `AGENTS.md`
- [x] `FINANCE_AI_GROUND_TRUTH.md`
- [x] `FINANCE_AI_MVP_SCOPE.md`
- [x] `DATA_SOURCES.md`
- [x] `FINANCE_AI_ARCHITECTURE.md`
- [x] AI / Backend / Data / Infra 담당 기획 초안 보관
- [x] `FINANCE_AI_DEV_STATUS.md` 최초 작성

## NOT YET FINAL

현재 문서는 개발 과정에서 계속 갱신한다.

특히 다음은 아직 최종 Freeze 상태가 아니다.

- Architecture
- Program Schema
- Eligibility Schema
- User Profile Schema
- Risk Calculation Formula
- API Contract
- Backend Hosting / 운영 Dependency 정책


# 3.1 2026-08-29 Team Decision Update

다음 내용이 새 Ground Truth / MVP Contract로 확정되었다.

- 공식 서비스명 `FinBridge`
- 기존 디자이너 UI의 전체 톤앤매너 유지
- Backend/AI 요구사항을 먼저 UI/Backend Handoff로 정리하고 Figma와 Backend가 같은 기준을 사용
- AI모드: 일반모드 / 집중모드
- 모드 미선택 후 바로 입력 → 일반모드
- 집중모드 첫 대화 전 구조화 입력, 이후 자연어 대화
- 두 모드 첫 대화 전 예시 질문 2개
- AI 답변은 GPT/Claude형 텍스트 대화
- 내부 Matching 상태는 대화형 답변의 근거로 유지
- 지원사업 리스트 카드에 공고 이미지 영역 추가
- 지원사업 상세 → AI 채팅 이동 시 `program_id` context 전달 방향
- 매출장표 분석은 Public URL에 진입점 유지; 일정 부족 시 명시적 `DEMO SAMPLE`
- 프리랜서 소득 안정성은 간이 deterministic 분석 + 회색 주의사항

UI/Backend Handoff 문서:

```text
docs/design/0829_FinBridge_UI_Backend_연동_디자인핸드오프_v1.md
```

위 문서는 구현 완료를 의미하지 않으며 화면/API 요구사항 Contract로 사용한다.

# 4. Data Verification Status

## DS-001 기업마당 지원사업정보 API

Status:

VERIFIED

### Verified

- [x] 공식 API 존재 확인
- [x] API 사용 신청
- [x] 인증키 발급
- [x] 실제 GET 호출 성공
- [x] HTTP 200 확인
- [x] JSON Response 확인
- [x] 창업 분야 20건 Sample 확보
- [x] Response Item Count = 20 확인
- [x] Sample 기준 totCnt = 71 확인
- [x] Raw JSON 저장
- [x] 실제 Response Field 확인
- [x] 상세 지원조건이 `bsnsSumryCn`에 존재함을 확인
- [x] 비정형 신청기간 존재 확인
- [x] 지원금액이 자연어에 포함되는 사례 확인
- [x] 지자체 지원사업 존재 확인

Raw File:

```text
data/raw/bizinfo/bizinfo_startup_sample.json
```

### Confirmed Raw Fields

- trgetNm
- updtPnttm
- hashtags
- inqireCo
- creatPnttm
- pblancNm
- pblancId
- printFlpthNm
- refrncNm
- pblancUrl
- jrsdInsttNm
- excInsttNm
- totCnt
- reqstMthPapersCn
- pldirSportRealmLclasCodeNm
- reqstBeginEndDe
- bsnsSumryCn
- pldirSportRealmMlsfcCodeNm
- printFileNm


# 5. Important Data Findings

[EXPERIMENT]

기업마당 실제 데이터 검증 결과 다음을 확인했다.

## 5.1 Structured Data

다음은 비교적 직접적인 Structured Data로 사용할 수 있다.

- 공고 ID
- 공고명
- 기관
- 지원분야
- 등록일
- 수정일
- 공고 URL
- 공고문 URL


## 5.2 Eligibility는 대부분 비정형

실제 지원 가능 여부에 중요한 조건은 `bsnsSumryCn`에 자연어로 포함되는 경우가 많다.

확인된 조건 유형:

- 지역
- 연령
- 예비창업 여부
- 창업 업력
- 사업자등록 상태
- 여성 여부
- 사업장 소재지
- 업종
- 교육 이수
- 특정 자격
- 특정 기관 추천
- 기타 복합조건


## 5.3 `trgetNm` 단독 사용 불가

실제 값은 다음과 같이 비교적 큰 범주다.

- 창업벤처
- 여성기업

최종 Eligibility 판정에는 부족하다.


## 5.4 `hashtags` 단독 사용 불가

해시태그는 후보 검색과 Recall 향상에는 활용 가능하지만 최종 지원 자격의 단독 Evidence로 사용하지 않는다.


## 5.5 신청기간 Parsing 필요

확인 사례:

```text
2026-10-08 ~ 2026-10-12
```

```text
예산 소진시까지
```

따라서 단순 `start_date / end_date` 구조만으로는 부족하다.


# 6. Current Architecture Decision

현재 우선 Architecture:

```text
Official Data
→ Raw Snapshot
→ Normalization
→ Eligibility Constraint Extraction
→ Structured Eligibility
→ Deterministic Matching
→ Deterministic Calculation
→ Evidence Validation
→ LLM Explanation
→ Final Result + Source
```

핵심 원칙:

- LLM이 최종 지원 가능 여부를 임의로 판단하지 않는다.
- 금융계산은 Backend Code에서 수행한다.
- Eligibility Extraction 결과는 원문 Evidence와 함께 관리한다.
- 데이터에 없는 사실을 생성하지 않는다.
- AI 장애 시 Structured Result는 유지한다.

2026-08-29 Core Backend baseline 기술 결정:

- Framework: FastAPI `0.141.1`
- Validation / Model: Pydantic v2 `2.13.4`
- Runtime: Python `.venv` + Uvicorn `0.52.1`
- Test: pytest `9.1.1` + httpx ASGI transport
- Data Access: 기업마당 Raw JSON Snapshot을 읽는 lazy in-memory Repository
- Database / ORM: 이번 baseline에는 도입하지 않음


# 7. Implemented Code

Status: `CORE BACKEND BASELINE IMPLEMENTED / VERIFIED LOCALLY`

구현 완료:

- FastAPI Application Scaffold
- `GET /health`
- 기업마당 Raw Snapshot Loader와 예외처리
- Program Repository / ID 조회
- Program 최소 Normalization과 신청기간 Parser
- `docs/ELIGIBILITY_SCHEMA.md` v0.1 기반 Pydantic Model
- DNF `common_conditions + eligibility_groups + global_exclusions` Matcher
- Condition별 Evidence / Match Result
- `GET /programs/{program_id}`
- `POST /programs/match`
- `POST /risk/calculate`
- 원리금균등 상환·현금흐름·Runway·잔존채무 Calculation
- 핵심 자동화 테스트

아직 구현 완료 상태가 아님:

- Raw 공고 Eligibility Extraction / 실제 20건 구조화
- Database / ORM
- LLM Integration
- Frontend Integration
- Public Deployment


# 8. Backend API Status

Status:

`CORE ENDPOINTS IMPLEMENTED / VERIFIED LOCALLY`

구현·검증 완료:

```text
GET /health
POST /programs/match
GET /programs/{program_id}
POST /risk/calculate
```

실제 Uvicorn 로컬 프로세스에서 다음을 확인했다.

- `/health`: HTTP 200
- 실제 `program_id` 상세: HTTP 200
- 없는 `program_id`: HTTP 404
- `/programs/match`: HTTP 200
- `/risk/calculate`: 정상 입력 HTTP 200, 잘못된 입력 HTTP 422

Raw Snapshot에는 아직 구조화된 Eligibility가 없으므로 실제 공고 Match API는 이를 임의 추출하지 않고 `UNKNOWN`을 반환한다.

아직 미구현인 Endpoint 후보:

```text
POST /chat
POST /income-stability/calculate
POST /sales/analyze   # 실제 매출장표 분석 구현 시에만
```

`/chat`은 일반모드/집중모드, 후속 대화, 선택적 `program_id` context를 처리하는 Orchestration 후보이다.

# 9. Database Status

Status: `LOCAL SNAPSHOT BASELINE IMPLEMENTED / SERVICE DB NOT DECIDED`

현재 Core API는 DB 없이 검증된
`data/raw/bizinfo/bizinfo_startup_sample.json`을 Repository 경계에서 읽는다.
비즈니스 로직은 Raw Loader와 분리되어 향후 Service DB 또는 다른 Snapshot으로 교체할 수 있다.

현재 확정되지 않은 항목:

- Database Product
- ORM
- Table Schema
- Migration Tool

DB 부재가 현재 Snapshot 기반 Core API 실행을 막지는 않는다.


# 10. AI / LLM Status

Status:

NOT DECIDED

아직 확정하지 않은 사항:

- LLM Provider
- Model
- Embedding Model
- Vector DB
- Agent Framework

현재 AI 역할 후보:

1. 사용자 자연어 이해
2. 비정형 Eligibility 조건 추출
3. 검증된 결과 설명

현재 AI가 담당하지 않는 영역:

- 금융계산
- 날짜비교
- 최종 Eligibility Matching
- 존재 여부 판단
- 지원금액 생성


# 11. Retrieval Status

Status: `SNAPSHOT PROGRAM RETRIEVAL IMPLEMENTED`

현재 구현 Baseline:

```text
Raw Snapshot
→ Program Normalization
→ in-memory ID Repository
```

구현됨:

- Snapshot 20건 로딩
- `pblancId` 기준 상세 조회
- 누락·잘못된 JSON·잘못된 구조 예외처리

미구현:

- 목록 검색 / Structured Filter
- Keyword Search

Vector Retrieval:

NOT DECIDED

Structured + Keyword Baseline의 실제 성능을 확인한 뒤 필요한 경우에만 추가한다.


# 12. Eligibility Status

Status: `SCHEMA v0.1 MODEL + MATCHER IMPLEMENTED / EXTRACTION NOT IMPLEMENTED`

구현됨:

- Program / Condition extraction status 분리
- 12개 condition type, subject, operator, unit, polarity, role Enum
- `raw_value` + normalized operands + Evidence
- `common_conditions` AND
- `eligibility_groups` 내부 AND / Group 사이 OR
- `global_exclusions` 우선
- `EXCLUDE` positive predicate 단일 평가
- 조건 부재 / Evidence 부족 / 사용자 입력 부족 분리

Raw 20건에서 실제 Eligibility를 자동 추출하거나 구조화하는 Extractor는 아직 없다. 따라서 실제 Raw Program은 Program extraction `UNKNOWN`이며 안전한 `MATCH`를 만들지 않는다.


# 13. Calculation Engine Status

Status: `MVP CONTRACT FROZEN / IMPLEMENTED / VERIFIED LOCALLY`

입력:

- `initial_cost`
- `own_capital`
- `monthly_revenue`
- `monthly_expense`
- `loan_amount`
- `annual_interest_rate` — 연 %, 사용자 직접 입력
- `loan_term_months`

구현 계산:

- 초기 가용 현금
- 원리금균등 월 상환액
- 월 현금흐름 / 현금소진액
- 단순 현금소진 Runway
- 유한 Runway 시점 예상 잔존채무

내부 계산은 Decimal로 수행하고 최종 응답에서만 `ROUND_HALF_UP` 소수 둘째 자리 반올림을 적용한다. `loan_amount=0`이면 기간이 0이어도 상환액과 잔존채무는 0이다. 월 현금흐름이 0 이상이면 Runway와 해당 시점 잔존채무는 `null`이다.

MVP 제외:

- 다른 상환방식
- 거치기간 / 변동금리
- 세금 / 수수료 / 연체 / 중도상환
- 매출 변동 / 추가 차입
- 신용평가 / 대출 승인 예측


# 14. Policy Loan Data Status

Status:

INVESTIGATING

아직 공식 Source를 확정하지 않았다.

검증 필요:

- 소상공인시장진흥공단
- 중소벤처기업진흥공단
- 공공데이터포털
- 기타 공식 정책자금 Source

확보 필요 항목:

- 금리
- 한도
- 상환기간
- 거치기간
- 자격조건
- 기준일


# 15. K-Startup Status

Status:

OFFICIAL_FOUND / NOT VERIFIED

다음 검증 예정:

- 실제 API 호출
- Response Schema
- 기업마당 동일 공고 Mapping
- 지원지역 정형화 수준
- 업력 정형화 수준
- 연령 정형화 수준

기업마당 대비 실질적인 정보 개선이 있는 경우에만 MVP Source로 추가한다.


# 16. Frontend Integration Status

Status:

`UI/BACKEND HANDOFF DRAFTED / IMPLEMENTATION NOT STARTED`

2026-08-29 기준 디자이너와 Backend가 공통으로 사용할 스크롤형 Handoff 문서를 작성했다.

확정된 UX:

- AI모드 / 지원사업 / 마이페이지 / 로그인 / 회원가입 IA
- 일반모드 / 집중모드
- 일반모드 자동 진입
- 집중모드 최초 구조화 입력
- GPT형 대화 답변
- 지원사업 카드 공고 이미지 영역
- 지원사업 상세 ↔ AI 채팅 연결
- 매출장표 분석 진입점
- 소득 안정성 주의사항

아직 Freeze가 필요한 API Contract:

- Focus Profile Input Schema
- Chat Request / Response Schema
- Program Result Schema
- Match/Evidence Schema
- Risk Input/Result Schema
- Income Stability Input/Result Schema
- Error Response
- Program Detail → Chat Context 전달 방식

# 17. Infrastructure Status

Status: `LOCAL RUNTIME / HEALTH VERIFIED, HOSTING NOT DECIDED`

현재 미확정:

- Backend Hosting
- Database Hosting
- LLM Provider
- Cloud
- Domain
- CI/CD

최종 MVP 요구:

- Public URL
- HTTPS
- Health Check — local verified
- Environment Variables
- Restart Recovery
- Logging
- Timeout
- Error Handling


# 18. Security Status

## Required

- [x] API Key를 Source Code에 넣지 않는 원칙 정의
- [x] Secret을 환경변수로 관리하는 원칙 정의
- [x] `.gitignore` 생성 및 기본 제외 규칙 검증
- [x] `.venv/` Git 제외 설정
- [x] `.env.example` 생성 및 Secret 미포함 확인
- [ ] 운영 Secret 관리 방식 확정
- [ ] 금융정보 Logging 정책 구현

## Security Issue

기업마당 API Key가 개발 과정 중 화면/채팅 등에 노출된 경우 기존 Key를 재발급 또는 교체하고 노출된 Key를 사용하지 않는다.

새 Key는 Git 또는 문서에 기록하지 않는다.


# 19. Tests

2026-08-29 실제 실행 결과:

```text
47 passed, 0 failed
```

검증 범위:

- `/health`
- 실제 20건 Snapshot 로딩과 Program Normalization
- 고정 날짜 / 예산 소진 / Unknown 신청기간
- YEAR / MONTH 업력 비교
- Raw Snapshot 무변경
- Matching Case 1~6
- OR Group 충족 / 전체 실패
- global exclusion 우선 및 이중 부정 방지
- Evidence 없는 `SUPPORTED` 거부
- 잘못된 Operator operand 거부
- Unsupported Program의 안전한 `NEEDS_REVIEW`
- 정상 Program 상세 / 404
- 실제 Raw Program Match의 안전한 `UNKNOWN`
- 잘못된 Enum 422
- 잘못된 숫자 범위 422
- 잘못된 `jsonArray` 구조 거부
- Snapshot 누락 시 Health 유지 및 Program API 503
- Risk 필수 Case 1~12
- 0% / 일반 금리 원리금균등 상환액
- 음수·기간 오류 422
- 유한/0/null Runway 경계
- 0% / 양의 금리 잔존채무
- 최종 Response 2자리 반올림

미검증 / 미구현 테스트:

- LLM / Prompt Injection
- Frontend Integration
- Public Deployment


# 20. Evaluation

Status: `ELIGIBILITY REVIEW-PACK BASELINE COMPLETE / BACKEND MATCHER CASES VERIFIED`

- AI-assisted Human-reviewed Review Pack 48건 평가 완료
- TP 27 / FP 9 / TN 9 / FN 3
- `candidate_precision_proxy`: 75.00%
- `review_pack_negative_control_false_negative_rate`: 25.00%
- Backend Matcher 경계 Case 1~6 자동화 테스트 완료

Review-Pack 지표는 전체 273건의 정식 precision / recall / accuracy가 아니다. 실제 Raw 공고 Eligibility Extraction과 End-to-End Matching 평가는 아직 미완료다.


# 21. Current Risks

## R1. Eligibility Extraction Accuracy

기업마당 세부조건이 자연어에 존재하므로 조건 추출 정확도가 핵심 Risk이다.

Mitigation:

- 원문 Evidence 보존
- Human Labeled Evaluation Set
- Deterministic Matching
- UNKNOWN / NEEDS_REVIEW 지원


## R2. Scope Overload

기획에 많은 기능이 존재한다.

Mitigation:

MVP MUST 우선.

핵심:

```text
실제 지원사업 데이터
→ Matching
→ Evidence
→ Risk Calculation
→ AI Explanation
```


## R3. Policy Loan Data

정책자금의 정형 공식 데이터를 확보하지 못할 가능성이 있다.

Mitigation:

공식 Source 검증 후 확보 범위에 맞춰 MVP 기능을 제한한다.


## R4. LLM Hallucination

LLM이 없는 조건이나 금액을 생성할 위험.

Mitigation:

- Evidence First
- Structured Output
- Validation
- Unsupported Handling
- Deterministic Calculation


## R5. Deployment Time

문서와 AI 기능에 시간을 과도하게 사용하면 Public MVP 배포 일정이 부족할 수 있다.

Mitigation:

Architecture Freeze 이후 Core Backend부터 빠르게 구현한다.



## R6. UI Contract와 Backend Scope 불일치

Handoff에는 화면 요구사항이 많지만 Backend 구현 시간이 짧다.

Mitigation:

- 화면에 필요한 최소 필드부터 Freeze
- Structured Result + AI Reply 중심
- 부가 기능보다 핵심 경로 우선
- 디자이너 UI 톤을 갈아엎지 않음


## R7. Demo와 실제 구현 혼동

매출장표 분석을 일정 부족 시 Demo로 보여줄 수 있으나 실제 분석처럼 보이면 제출 문서와 서비스 신뢰성에 문제가 생긴다.

Mitigation:

- `DEMO SAMPLE` 명시
- 샘플 입력/결과와 실제 Backend 분석 분리
- 공식 기능명세서에는 실제 검증 완료 범위만 작성

# 22. Current Blockers

현재 Core 진행 Blocker / 미완료 결정:

1. 실제 Raw Program용 Eligibility Extraction / 구조화 데이터
2. `/chat` LLM Provider와 API Contract
3. Backend Hosting / Public 배포 방식
4. Frontend Integration Contract 최종 연결

[RECOMMENDATION] Core 구현의 필수 선행조건에서 제외할 항목:

- K-Startup 실측 완료
- 상권 데이터
- 범용 CSV/Excel Parser
- Vector DB
- Graph DB
- Multi-Agent

정책자금 공식 Source가 일정 내 확보되지 않으면 임의 데이터를 만들지 않고 확보 범위만 사용한다.

# 23. Immediate Next Tasks

[RECOMMENDATION — 2026-08-29]

2026-09-03~04 내부 완료 목표 기준 우선순위.

## P0 — 다음 작업

1. 실제 Raw Program Eligibility 구조화 baseline 결정
2. `/chat` LLM Provider / API Contract Freeze
3. Structured Result 기반 `/chat` + LLM 장애 Fallback 구현

## P1 — Core User Flow

4. 실제 Program Eligibility 데이터 연결
5. Structured / Keyword Program 목록 Retrieval
6. 지원사업 상세 ↔ `program_id` Chat Context

## P2 — 유형별 기능 / 배포

7. 프리랜서 소득 안정성 간이 계산
8. 매출장표 실제 분석 구현 가능 여부 판단
9. 실제 분석 미완성 시 `DEMO SAMPLE` Fallback 적용
10. Frontend Integration
11. Public Deployment

## P3 — QA

12. 정상/오류/경계값 테스트
13. LLM/API Failure Fallback
14. 모바일 웹 주요 화면 점검
15. Public URL 재접속 / Restart Recovery
16. 기능 구현 상태 기준 공식 기능명세서 작성 준비

K-Startup, 상권, Vector Retrieval 등은 Core 완료 후 시간이 남을 때만 검토한다.

# 24. Current Completion Snapshot

Documentation:

```text
Service Name FinBridge       LOCKED
UI/Backend Handoff           DRAFTED
AGENTS                       UPDATED 2026-08-29
GROUND_TRUTH                 UPDATED 2026-08-29
MVP_SCOPE                    UPDATED 2026-08-29
DATA_SOURCES                 UPDATED 2026-08-29
ARCHITECTURE                 UPDATED 2026-08-29
DEV_STATUS                   UPDATED 2026-08-29
```

Data:

```text
Bizinfo Official Source      DONE
Bizinfo API Access           DONE
Bizinfo API Call             DONE
Bizinfo 20 Sample            DONE
Bizinfo Raw JSON             DONE
Bizinfo Schema Check         DONE
Bizinfo Large Sample 273     DONE
Eligibility Review Pack 48   DONE
Baseline Evaluation          DONE
K-Startup API                TODO
Policy Loan Data             TODO
```

Backend:

```text
Framework                    IMPLEMENTED
Database                     TODO
API                          VERIFIED LOCALLY
Snapshot Retrieval           VERIFIED
Program Normalization        VERIFIED
Eligibility Model v0.1       IMPLEMENTED
Eligibility Extraction       TODO
Matching                     VERIFIED
Calculation — Risk MVP       VERIFIED
LLM                          TODO
Tests                        47 PASSED
```

Infra:

```text
Hosting                      TODO
Database Hosting             TODO
Public URL                   TODO
Health Check                 VERIFIED LOCALLY
CI/CD                        TODO
```


# 25. Development Rule

다음 작업부터는 주요 구현 또는 검증이 끝날 때마다 이 파일을 업데이트한다.

최소 기록:

- 무엇을 구현했는가
- 무엇을 실제 검증했는가
- 어떤 테스트를 통과했는가
- 어떤 기술을 확정했는가
- 현재 Blocker는 무엇인가
- 다음 작업은 무엇인가

코드 상태와 이 문서의 상태가 다르면 코드와 실제 테스트 결과를 기준으로 이 문서를 수정한다.
