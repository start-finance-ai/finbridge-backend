# FINANCE AI — Ground Truth

Last Updated: 2026-08-29

이 문서는 2026 금융 AI Challenge 프로젝트의 현재 확정된 기획·구현 기준을 관리한다.

충돌 시 `AGENTS.md`의 Source of Truth 우선순위를 따른다.
구현 여부는 반드시 `FINANCE_AI_DEV_STATUS.md`와 실제 코드·테스트 결과를 우선한다.

# 1. Project / Service

[TEAM DECISION]

- 팀명: `start`
- 공식 서비스명: `FinBridge`
- 핵심 사용자: 예비창업자 / 소상공인 / 프리랜서
- 서비스 채널: 모바일 웹 중심 Public Web Service
- 내부 완료 목표: Backend 구축·배포, 디자인, QA를 `2026-09-03~04`까지
- 팀 공유 제출 일정: `2026-09-07 오전`
- 정확한 공식 마감시각은 제출 전 최신 공식 공지를 다시 확인한다.

`핀브릿지`, `서비스명 미정` 등 과거 명칭은 최신 산출물에서 사용하지 않는다.

# 2. Core Service Definition

FinBridge는 단순 지원사업 검색·추천 서비스가 아니다.

핵심 서비스 흐름:

```text
사용자 상황
→ 실제 지원사업 탐색
→ 비정형 자격조건 구조화
→ 사용자 조건과 Deterministic Matching
→ Evidence 검증
→ 재무·리스크 계산
→ AI 설명
→ 공식 출처
→ 다음 행동
```

즉, 예비창업자·소상공인·프리랜서가 흩어진 자금지원 정보를 찾는 데 그치지 않고,
실제 공고의 복잡한 자격조건을 구조화하고 사용자 조건과 검증한 뒤,
자금조달 이후의 현금흐름·Runway·잔존채무 등 재무 위험까지 설명 가능한 방식으로 계산해
AI가 근거와 다음 행동을 설명하는 금융 의사결정 지원 서비스다.

# 3. UX Contract

[TEAM DECISION]

주요 화면은 다음 흐름을 기준으로 한다.

- AI모드
- 지원사업
- 마이페이지
- 로그인
- 회원가입

## 3.1 AI모드

### GENERAL — 일반모드

- 사용자가 모드를 선택하지 않고 바로 입력하면 자동 일반모드
- 자연어 중심의 낮은 진입장벽
- 필요한 정보가 부족하면 자연스럽게 추가 질문
- 정밀한 Eligibility 검증이 필요하면 집중모드 전환 제안 가능

### FOCUS — 집중모드

- 첫 대화 전에 Matching에 필요한 최소 구조화 Profile 입력
- 현재 후보 필드: `user_type`, `region`, `age`, `business_status`, `business_age`, `industry`, `capital`, `intent`
- 모든 개인정보를 무조건 요구하지 않는다.
- 첫 구조화 입력 후에는 자연어 연속 대화로 전환한다.

두 모드 모두 첫 대화 전 예시 질문을 제공할 수 있다.

## 3.2 AI 답변 표현

- GPT/Claude형 자연스러운 텍스트 채팅을 우선한다.
- 내부 Matching 상태는 구조적으로 유지하되 상태 카드만 나열하지 않는다.
- 사용자에게는 “현재 확인되는 조건”, “추가 확인이 필요한 부분”, “판단하기 어려운 부분” 등으로 설명한다.
- AI는 최종 지원 자격, 대출 승인, 금융 결과를 보장하지 않는다.

## 3.3 지원사업 상세 ↔ AI

지원사업 상세의 `AI에게 이 공고 물어보기`는 `program_id` context를 `/chat`에 전달하는 구조를 사용한다.

# 4. Data Ground Truth

## 4.1 Main Source

[OFFICIAL / EXPERIMENT]

현재 검증된 Main Source는 중소벤처기업부 기업마당 지원사업정보 API다.

공식 호출 Contract:

```text
GET https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do
auth = crtfcKey
dataType = json
searchCnt = 100
searchLclasId = 06
```

2026-08-29 수동 Refresh 실측:

- HTTP 200
- 창업 분야 Raw records: 69
- Unique programs: 69
- Duplicate ID: 0
- Loader / Normalization: 69 성공

지원사업 데이터 처리 기준:

```text
Official Data
→ Raw Snapshot
→ Normalization
→ Eligibility Extraction
→ Structured Eligibility
→ Deterministic Matching
→ Evidence
→ AI Explanation
```

`hashtags`나 `trgetNm` 하나만으로 최종 Eligibility를 판정하지 않는다.

## 4.2 Snapshot Policy

[TEAM DECISION / EXPERIMENT]

- 사용자 요청마다 기업마당 API를 직접 호출하지 않는다.
- 기업마당 API는 수동 Collector / Snapshot Refresh 경로에서만 호출한다.
- Runtime Snapshot 실패 시 기존 정상 데이터가 유지되어야 한다.
- Public Deployment는 외부 API refresh 없이도 검증된 Bootstrap Snapshot으로 기동 가능해야 한다.
- 현재 검증된 Bootstrap은 창업 분야 69건이다.

Loader 우선순위:

```text
1. FINBRIDGE_BIZINFO_SNAPSHOT
2. valid runtime service-ready snapshot
3. tracked bootstrap snapshot
```

# 5. Eligibility / Matching Ground Truth

[TEAM DECISION / EXPERIMENT]

Eligibility는 원문 Evidence와 함께 구조화한다.

핵심 원칙:

- 조건 부재와 Evidence 부족을 구분한다.
- Program extraction status와 Condition extraction status를 구분한다.
- 대안 경로는 OR Group으로 표현한다.
- `ELIGIBILITY_EXCEPTION`은 metadata로만 사용한다.
- Boolean 판정은 `common_conditions`, `eligibility_groups`, `global_exclusions`를 사용한다.
- `EXCLUDE`는 positive predicate를 한 번만 평가한다.
- Evidence 없는 `SUPPORTED`는 허용하지 않는다.
- confidence 확률값을 Eligibility 확률처럼 사용하지 않는다.
- 사용자 입력 부족은 `NO_MATCH`가 아니라 `NEEDS_REVIEW` 방향으로 처리한다.
- Evidence 부족 또는 구조 불충분 상태에서 안전한 `MATCH`를 만들지 않는다.

Program extraction status:

- `SUPPORTED`
- `NEEDS_REVIEW`
- `UNKNOWN`
- `UNSUPPORTED`

현재 69건 deterministic extraction baseline 결과:

- `SUPPORTED`: 22
- `NEEDS_REVIEW`: 46
- `UNSUPPORTED`: 1

이는 전체 자격조건 완전 추출을 의미하지 않는다.

# 6. Retrieval Ground Truth

[TEAM DECISION / EXPERIMENT]

현재 MVP Retrieval baseline:

```text
Structured Filter
→ Exact / Keyword Search
→ Deterministic Ranking
→ Top-N
```

- Vector DB / Embedding / Semantic Retrieval은 현재 사용하지 않는다.
- Retrieval score는 Eligibility 확률 또는 신청 가능 확률이 아니다.
- Retrieval 상위 결과가 자동으로 `MATCH`가 되지 않는다.
- 최종 Matching은 deterministic Matcher가 담당한다.
- Repository에 없는 지원사업을 LLM이 생성하지 않는다.

# 7. Risk Calculation Ground Truth

[TEAM DECISION / EXPERIMENT]

Risk Calculator는 금융기관의 신용평가나 대출 승인 예측 모델이 아니다.

MVP 입력:

- `initial_cost`
- `own_capital`
- `monthly_revenue`
- `monthly_expense`
- `loan_amount`
- `annual_interest_rate`
- `loan_term_months`

현재 MVP 지원 상환방식:

- 원리금균등상환 1종

Deterministic 계산 항목:

- 초기 가용 현금
- 월 원리금 상환액
- 월 현금흐름
- Cash Burn
- Runway
- Runway 시점 잔존채무

LLM은 금융식을 재계산하지 않고 Backend가 계산한 결과만 설명한다.

세금·수수료·변동금리·연체·추가차입 등은 현재 계산 범위에 포함하지 않는다.

# 8. LLM Ground Truth

[TEAM DECISION / EXPERIMENT]

현재 Backend LLM Provider:

- Provider: `OpenAI`
- API: Responses API
- Model: `gpt-5.6-luna`
- reasoning effort: `low`
- Provider failure: `TEMPLATE_FALLBACK`

LLM 역할:

- 자연어 설명
- 검증 결과 요약
- 추가 확인사항
- 다음 행동 설명

LLM이 담당하지 않는 것:

- 지원사업 존재 여부 생성
- MATCH / NO_MATCH 최종 계산
- 금융 계산
- 지원금액·신청기간·공식 URL 생성
- 대출금리 생성

OpenAI 장애가 발생해도 Structured Program / Match / Evidence / Source는 유지한다.

# 9. Current Technology / Deployment Decision

[TEAM DECISION — 2026-08-29]

현재 MVP 기술선택:

```text
Frontend
- React + Vite + TypeScript
- Hosting target: Vercel Hobby

Backend
- Python 3.14.3
- FastAPI
- Pydantic v2
- Uvicorn
- Hosting target: Railway Hobby

Data
- Bizinfo Snapshot / Bootstrap
- MVP Database: 사용하지 않음

AI
- OpenAI Responses API
- gpt-5.6-luna
```

Database는 “미정”이 아니라 **현재 MVP에서 의도적으로 사용하지 않는다.**

Railway PostgreSQL은 다음과 같은 영속 상태가 실제로 필요해질 때만 검토한다.

- 실제 Auth / 회원 데이터
- 사용자 Profile 영속 저장
- 대화 Session 영속 저장
- 즐겨찾기
- Runtime Collector 결과 영속 보존
- 복수 Backend instance 간 공유 상태

Public URL이 실제 생성·외부 검증되기 전까지 `DEPLOYED` 또는 `PUBLIC VERIFIED`로 표현하지 않는다.

# 10. Sales / Income Features

## 10.1 매출장표 분석

- Public UI 진입점은 유지한다.
- 실제 CSV/XLSX 업로드·분석 구현을 우선 시도한다.
- 핵심 Backend/배포 안정성을 해치면 `DEMO SAMPLE`로 명확히 표시한다.
- Demo를 실제 사용자 파일 분석처럼 표현하지 않는다.
- 공식 기능명세서에는 실제 구현·검증된 기능만 기재한다.

## 10.2 프리랜서 소득 안정성

- 월별 소득의 평균·표준편차·변동계수 등 간단하고 설명 가능한 deterministic 지표 우선
- 금융기관의 신용평가·소득인정·상환능력 판정을 의미한다고 표현하지 않는다.
- UI에 한계 안내문을 표시한다.

# 11. Data / Security Principles

- 공식·공개·이용조건이 명확한 데이터만 사용한다.
- Raw Evidence를 유지한다.
- 결측값을 0·평균·임의 값으로 채우지 않는다.
- API Key, Secret, Token, Password는 Git/문서/Source Code에 기록하지 않는다.
- 실제 Secret은 `.env` 및 배포 플랫폼 Secret Environment Variable로 관리한다.
- `.env`는 Git에서 제외한다.
- 로그에 API Key 또는 전체 민감 Profile/금융입력을 노출하지 않는다.

# 12. Explicitly Not Current MVP Ground Truth

다음은 현재 MVP 구현 완료 또는 필수 Architecture로 취급하지 않는다.

- K-Startup 추가 연동
- 상권 데이터
- Vector DB
- Graph DB
- Multi-Agent
- Semantic Retrieval
- Scheduler / Celery
- 자동 주기 Collector
- PostgreSQL / ORM
- Session Persistence
- 전체 기업마당 분야 Coverage
- 전체 공고·별첨 Eligibility 완전 구조화
- 정책자금 공식 데이터 자동 연동
- 범용 CSV/XLSX Parser

Core Flow와 Public Deployment 완료 후 필요성과 효과가 확인될 때만 추가한다.

# 13. Documentation / Submission Rule

[TEAM DECISION]

- 최종 기능명세서에는 실제 구현·검증된 기능만 작성한다.
- 기획서에서는 현재 구현 범위와 향후 확장 방향을 명확히 구분한다.
- 미구현 기능을 현재 구현 완료 기능처럼 표현하지 않는다.
- 최종 Public URL에서 실제 구현·검증된 상태를 `FINANCE_AI_DEV_STATUS.md`에 반영한 뒤 제출 문서를 작성한다.
