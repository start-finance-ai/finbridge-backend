# FINANCE AI — Development Status

Last Updated: 2026-08-28

이 문서는 2026 금융 AI Challenge Backend / AI / Data / Infra의 실제 개발 진행 상태를 기록한다.

구현되지 않은 기능을 완료된 것처럼 기록하지 않는다.

상태는 실제 코드, 데이터 검증, 테스트 결과를 기준으로 갱신한다.


# 1. Current Phase

Current Phase:

G2 — Data Verification
→ G3 Architecture Freeze 준비 단계

현재는 대규모 Backend 구현 전 단계이다.

기업마당 Main Data Source의 최초 실측 검증은 완료했으며, Eligibility Schema와 정책자금 데이터, 리스크 계산식 등을 추가 검증한 뒤 Architecture Freeze를 진행한다.


# 2. Repository

Backend Repository:

```text
start-finance-ai/backend
```

현재 주요 구조:

```text
backend/
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
├─ scripts/
│  └─ collect_bizinfo_samples.py
│
└─ data/
   └─ raw/
      └─ bizinfo/
         ├─ bizinfo_finance_sample.json
         ├─ bizinfo_management_sample.json
         ├─ bizinfo_startup_sample.json
         └─ bizinfo_startup_sample_100.json
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

특히 다음은 아직 Freeze 상태가 아니다.

- Architecture
- Program Schema
- Eligibility Schema
- User Profile Schema
- Risk Calculation Formula
- API Contract
- Technology Stack


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
- [x] 금융 분야 Sample 100건 확보 (`totCnt` 220)
- [x] 창업 분야 확대 Sample 73건 확보 (`totCnt` 73)
- [x] 경영 분야 Sample 100건 확보 (`totCnt` 461)
- [x] 3개 분야 총 273건 Raw Sample 확보
- [x] 3개 분야 모두 HTTP 200 확인
- [x] Sample Collector Exit Code 0 확인
- [x] `data/raw/` Git 제외 규칙 적용 확인
- [x] `scripts/analyze_bizinfo_samples.py` 구현
- [x] 273건 전체 Field / Eligibility Review Candidate / 신청기간 / 금액 표현 Profile 완료

Raw Files:

```text
data/raw/bizinfo/bizinfo_finance_sample.json
data/raw/bizinfo/bizinfo_management_sample.json
data/raw/bizinfo/bizinfo_startup_sample.json
data/raw/bizinfo/bizinfo_startup_sample_100.json
```

창업 분야는 `searchCnt=100` 요청에 대한 전체 결과가 73건이므로 73건 수집을 정상으로 확인했다.

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

### Full 273-Item Field Profile

- 전체 Item 273건, 고유 `pblancId` 273건, 중복 0건
- 발견 Field 22개
- 기본 Field 19개 모두 273/273 non-empty (100%)
- `fileNm`: 185/273 (67.77%)
- `flpthNm`: 185/273 (67.77%)
- `rceptEngnHmpgUrl`: 128/273 (46.89%)

위 세 Field는 Optional로 다뤄야 한다. Eligibility Review Candidate 자동 분석은 완료했지만 Human Label 검증과 Eligibility Schema Draft는 아직 완료되지 않았다.


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

정규식 기반 Review Candidate 수는 지역/소재지 232, 연령 24(명시적 숫자 연령 19), 예비창업 29, 사업자 여부 91, 사업 업력 62, 업종 69, 사업자 유형 220, 매출/소득 16, 직원 수 6, 성별 7, 특정 자격/인증 14, 교육 이수 5, 추천/선정/평가 7건이다. 이 수치는 실제 Eligibility 확정 건수가 아니다.

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

전체 273건의 실제 값은 고유 7개뿐인 비교적 큰 범주다.

- 창업벤처
- 여성기업

최종 Eligibility 판정에는 부족하다.


## 5.4 `hashtags` 단독 사용 불가

해시태그는 후보 검색과 Recall 향상에는 활용 가능하지만 최종 지원 자격의 단독 Evidence로 사용하지 않는다.

273건 Eligibility Review Candidate 자동 분석에서도 `hashtags`를 Evidence에서 제외했다.


## 5.5 신청기간 Parsing 필요

확인 사례:

```text
2026-10-08 ~ 2026-10-12
```

```text
예산 소진시까지
```

따라서 단순 `start_date / end_date` 구조만으로는 부족하다.

273건 분류 결과는 명확한 날짜 범위 146, 예산 소진 시까지 97, 상시/수시 14, 별도 공지/참고 3, 차수/분야/세부사업별 상이 4, 기타 비정형 9, 결측 0건이다.


## 5.6 지원금액 표현 Profile

- 금액/한도 Keyword Review Candidate: 127건
- 실제 금액 표현 탐지: 115건
- 지원·융자·대출·보증 등 지원 문맥 동반 Review Candidate: 111건

세 지표는 탐지 범위가 다르며 서로 같은 값으로 해석하지 않는다. Human Review 전에는 실제 지원금액 확정 건수로 사용하지 않는다.


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


# 7. Implemented Code

현재:

Data Verification Sample Collector 구현 및 실제 실행 검증 완료.

Bizinfo 273건 자동 프로파일링 분석 스크립트 구현 및 실행 완료.

Implemented:

- `scripts/collect_bizinfo_samples.py`
- 환경변수 `BIZINFO_API_KEY` 기반 인증
- 금융(01), 창업(06), 경영(07) 분야별 `searchCnt=100` 요청
- Raw Response Bytes 보존 저장
- HTTP, Network, JSON, Response Structure, File Save 오류 처리
- 실제 실행 결과 Exit Code 0 및 Raw Sample 총 273건 저장 확인
- `scripts/analyze_bizinfo_samples.py`
- 273건 전체 Field 출현율, Eligibility Review Candidate, 신청기간, 금액 표현 Profile
- 네트워크·LLM·DB 없이 Raw JSON 읽기 전용 분석

아직 실제 Backend Application Scaffold를 생성하지 않았다.

현재 단계에서 다음은 구현 완료 상태가 아니다.

- Backend API
- Database
- Normalizer
- Retrieval
- Eligibility Extraction
- Matching Engine
- Calculation Engine
- Evidence Validator
- LLM Integration
- Deployment


# 8. Backend API Status

현재 모든 API Endpoint는 Draft 또는 미구현 상태이다.

후보:

```text
GET /health
POST /programs/match
GET /programs/{program_id}
POST /risk/calculate
POST /ai/explain
```

Status:

NOT IMPLEMENTED

Frontend와 API Contract를 합의한 이후 최종 확정한다.


# 9. Database Status

Status:

NOT DECIDED

현재 확정되지 않은 항목:

- Database Product
- ORM
- Table Schema
- Migration Tool

DB를 결정하기 전에 다음을 먼저 진행한다.

- Program Schema 검증
- Eligibility Schema 검증
- User Profile Schema 확정


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

Status:

DESIGN ONLY

현재 Baseline:

```text
Structured Filter
+
Keyword Search
```

Vector Retrieval:

NOT DECIDED

Structured + Keyword Baseline의 실제 성능을 확인한 뒤 필요한 경우에만 추가한다.


# 12. Eligibility Status

Status:

DESIGN / DATA ANALYSIS

- Automated Candidate Profile: COMPLETED (273 items)
- Human Label Set: NOT STARTED
- Eligibility Schema Draft: TODO

현재 Draft Schema 후보:

- region
- age_min
- age_max
- business_status
- business_age_min
- business_age_max
- business_location
- industry
- gender_condition
- required_certificate
- required_education
- required_recommendation
- additional_condition_text
- evidence_text

아직 Schema Freeze 전이다.


# 13. Calculation Engine Status

Status:

NOT DEFINED

현재 기획상 계산 후보:

- 월 현금흐름
- Cash Burn
- Runway
- 대출 상환
- 사업 악화 시 재무상태
- 폐업 가정 시 잔존채무

아직 다음이 확정되지 않았다.

- 최종 입력값
- 계산식
- 상환방식
- 거치기간 처리
- 폐업 Scenario
- 경계값

금융 검증 이후 구현한다.


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

NOT STARTED

현재 Backend API Contract가 Freeze되지 않았다.

Frontend 담당과 추후 확정할 내용:

- Profile Input Schema
- Program Result Schema
- Match Status
- Evidence 표시 방식
- Risk Input Schema
- Risk Result Schema
- AI Explanation Response
- Error Response


# 17. Infrastructure Status

Status:

NOT DECIDED

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
- Health Check
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
- [x] `.env.example` 생성
- [ ] 운영 Secret 관리 방식 확정
- [ ] 금융정보 Logging 정책 구현

## Security Issue

기업마당 API Key가 개발 과정 중 화면/채팅 등에 노출된 경우 기존 Key를 재발급 또는 교체하고 노출된 Key를 사용하지 않는다.

새 Key는 Git 또는 문서에 기록하지 않는다.


# 19. Tests

현재 자동화 Test:

NONE

### Collector Execution Verification

- [x] 금융, 창업, 경영 분야 실제 API 호출 성공
- [x] 3개 요청 모두 HTTP 200
- [x] Collector Exit Code 0
- [x] Raw JSON 총 273건 저장
- [x] `data/raw/` Git 제외 확인

위 결과는 Data Verification Script의 실행 검증이며 Backend API 자동화 테스트가 아니다.

### Analyzer Execution Verification

- [x] Raw Sample 273건 전체 분석
- [x] `pblancId` 고유 273건 / 중복 0건 확인
- [x] Field / Eligibility Review Candidate / 신청기간 / 금액 표현 Profile 산출

위 결과도 자동 후보 분석 실행 검증이며 Human Label 정확도 평가나 Backend API 자동화 테스트가 아니다.

추후 최소 테스트 대상:

- Data Normalization
- Eligibility Parsing
- Deterministic Matching
- Date Parsing
- Calculation Engine
- Unsupported Detection
- API Validation
- Prompt Injection


# 20. Evaluation

Status:

NOT STARTED

Human Label Set: NOT STARTED

향후 Evaluation Set 후보:

- 정상 지원사업 질문
- 지역 불일치
- 연령 불일치
- 업력 불일치
- 사용자 정보 부족
- 공고정보 부족
- 예산 소진시까지
- 복합 자격조건
- 지원금액 추출
- 계산 질문
- 데이터에 없는 지원사업 질문


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


# 22. Current Blockers

현재 즉시 개발을 막는 핵심 미확정 사항:

1. Eligibility Schema 최종 형태
2. Policy Loan 공식 Source
3. Risk Calculation Formula
4. User Profile 최소 입력
5. Backend Technology Stack
6. Frontend API Contract


# 23. Immediate Next Tasks

우선순위 순서:

## P0

1. 분야 및 조건 유형별 Human Review Sample 선정
2. 원문 Evidence 기반 Human Labeling
3. false positive / 모호 사례 분석 후 Eligibility Schema Draft 작성

## P1

4. 정책자금 공식 Source 검증
5. K-Startup 실측 검증
6. 리스크 계산식 확정

## P2

7. User Profile Schema 확정
8. Architecture Freeze
9. Backend Technology Stack 결정
10. API Contract 결정

## P3

11. Backend Scaffold
12. 운영 Data Collector
13. Normalizer
14. Database
15. Matching Engine
16. Calculation Engine
17. LLM Integration


# 24. Current Completion Snapshot

Documentation:

```text
AGENTS                       DONE
GROUND_TRUTH                 DONE
MVP_SCOPE                    DONE
DATA_SOURCES                 DONE
ARCHITECTURE                 DONE
DEV_STATUS                   DONE
```

Data:

```text
Bizinfo Official Source      DONE
Bizinfo API Access           DONE
Bizinfo API Call             DONE
Bizinfo 20 Sample            DONE
Bizinfo Raw JSON             DONE
Bizinfo Schema Check         DONE
Bizinfo Sample Collector     VERIFIED
Bizinfo Large Sample         DONE (273 items)
Bizinfo Sample Analyzer      DONE (273 items)
Eligibility Candidate Profile DONE (automated)
Human Label Set              NOT STARTED
Eligibility Schema Draft     TODO
K-Startup API                TODO
Policy Loan Data             TODO
```

Backend:

```text
Framework                    TODO
Database                     TODO
API                          TODO
Retrieval                    TODO
Eligibility Extraction       TODO
Matching                     TODO
Calculation                  TODO
LLM                          TODO
Tests                        TODO
```

Infra:

```text
Hosting                      TODO
Database Hosting             TODO
Public URL                   TODO
Health Check                 TODO
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
