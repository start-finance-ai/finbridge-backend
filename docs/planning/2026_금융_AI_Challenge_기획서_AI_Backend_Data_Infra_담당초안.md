# 2026 금융 AI Challenge 기획서 — AI / Backend / Data / Infra 담당 초안 v3

> **담당:** AI / Backend / Data / Infra Lead
> **작성 기준:** 팀 최신 기획서 + 공식 기획서/기능명세서 양식 + 2026-08-29 팀 회의 결정 + 2026-08-28 실제 데이터 검증 결과
> **용도:** 팀원별 기획서 초안 통합용
> **상태 기준:** 구현 완료 여부는 `FINANCE_AI_DEV_STATUS.md`를 우선하며, 본 문서의 설계 내용이 곧 구현 완료를 의미하지 않는다.

---

## 0. 2026-08-29 팀 확정사항 반영

[TEAM DECISION]

- 팀명: `start`
- 공식 서비스명: `FinBridge`
- Backend 구축·배포, 디자인, QA를 2026-09-03~04까지 내부 완료하는 것을 목표로 한다.
- 기존 디자이너 UI의 전체 톤앤매너를 유지하면서 Backend가 필요한 정보 구조만 추가한다.
- AI모드는 `일반모드 / 집중모드`로 구성한다.
- 모드 미선택 상태에서 바로 채팅을 입력하면 일반모드로 시작한다.
- 집중모드는 첫 대화 전 구조화된 조건을 상대적으로 세밀하게 받고, 이후에는 자연어 채팅으로 이어간다.
- AI 답변은 GPT/Claude와 유사한 텍스트 대화 형식으로 제공한다.
- 조건 충족/추가 확인/판단 불가 등은 Backend의 structured result로 유지하되 사용자에게는 대화형 문장으로 설명한다.
- 지원사업 리스트 카드에 공고 이미지 영역을 추가하되 공고 이미지는 Evidence가 아니다.
- 매출장표 분석은 Public URL에 진입점을 유지하며, 실제 분석이 일정 내 미완성일 경우 `DEMO SAMPLE`을 명확히 표시한다.
- 프리랜서 소득 안정성은 간이 deterministic 분석으로 제공하고 회색 주의사항을 표시한다.

## 2. 아이디어 기획 핵심내용(요약) — 기술 관점 보완안

- 예비창업자·소상공인·프리랜서의 **유형·지역·업종·자본금 등 사용자 정보**와 실제 정부지원사업 데이터를 연결해, 사용자의 상황과 관련 있는 지원사업 후보를 찾고 자격조건별 근거를 제시하는 AI 기반 금융 의사결정 지원 서비스를 구현한다.
- 지원사업을 단순히 키워드로 검색하거나 LLM이 임의 추천하지 않고, **실제 공고 데이터 → 자격조건 구조화 → 사용자 조건과 Matching → Evidence 확인**의 흐름으로 처리한다. `[TEAM DECISION]`
- 사용자가 입력한 초기비용·매출·지출·대출조건 등을 바탕으로 **현금흐름, 버틸 수 있는 기간, 사업 악화·폐업 가정 시 잔존채무 등 금융·리스크 지표를 Backend에서 결정론적으로 계산**하고, 생성형 AI는 검증된 계산 결과를 사용자가 이해하기 쉬운 언어로 설명한다. `[TEAM DECISION]`
- 생성형 AI는 금융정보를 직접 만들어내는 역할이 아니라, **비정형 공고의 복잡한 조건을 구조화하고, 검증된 검색·Matching·계산 결과를 종합해 설명하는 역할**에 집중한다. `[TEAM DECISION]`
- 사용자 경험은 **일반모드(자연어 중심) / 집중모드(첫 대화 전 구조화 입력)**로 분리하며, 내부 structured result를 GPT형 대화 답변으로 설명한다. `[TEAM DECISION — 2026-08-29]`

---

## 4. 서비스 컨셉 및 차별성 — AI·Backend 관점 보완안

### 4-1. 실제 공고 기반 맞춤 탐색

단순 추천 문장을 생성하는 방식이 아니라 공식 지원사업 데이터를 기반으로 후보를 탐색한다.

현재 실제 검증한 기업마당 지원사업정보 API를 기준으로

`공식 지원사업 데이터`
→ `후보 공고 검색`
→ `자격조건 구조화`
→ `사용자 조건 비교`
→ `근거 표시`

의 흐름을 우선한다.

### 4-2. 비정형 자격조건을 구조화하는 AI

[EXPERIMENT]

기업마당 API 실제 데이터 검증 결과, 공고 ID·기관·지원분야 등은 정형 필드로 제공되지만 실제 지원자격에 중요한 다음 조건들은 `bsnsSumryCn` 등의 자연어 안에 포함되는 사례가 확인되었다.

- 지역
- 연령
- 예비창업 여부
- 창업 업력
- 사업자등록 상태
- 사업장 소재지
- 업종
- 여성 여부
- 교육 이수
- 특정 자격·신고증
- 특정 기관 추천
- 지원금액

따라서 AI의 핵심 역할 중 하나는 **비정형 공고에서 자격조건 후보를 추출하여 구조화하는 것**이다.

단, AI가 추출한 결과를 곧바로 최종 지원 가능 판정으로 사용하지 않는다.

### 4-3. 자격 판정은 조건별 Deterministic Matching

구조화된 자격조건은 사용자 프로필과 Backend 로직에서 비교한다. `[TEAM DECISION]`

예:

`사용자 나이 27세`
vs
`공고 조건 18세 이상 45세 이하`
→ `MATCHED`

반면 데이터가 부족하거나 공고 조건이 복잡한 경우에는 임의로 결론내리지 않고 다음 상태로 분리한다.

- `MATCHED`
- `NOT_MATCHED`
- `NEEDS_REVIEW`
- `UNKNOWN`

최종 상태명은 구현 단계에서 조정할 수 있다.

### 4-4. 계산과 설명의 역할 분리

다음 수치 계산은 생성형 AI가 아니라 Backend Calculation Engine에서 수행한다. `[TEAM DECISION]`

- 현금흐름
- 대출 원리금
- 자금 소진 속도
- 버틸 수 있는 기간
- 잔존채무
- 날짜 비교
- 신청기간 판단

생성형 AI는 계산식 자체를 대신 수행하기보다 **검증된 결과가 사용자에게 어떤 의미인지 설명하는 역할**에 집중한다.

### 4-5. 서비스 차별화 흐름

현재 서비스의 핵심 차별화 흐름은 다음과 같다.

`사용자 상황`
→ `실제 지원사업 탐색`
→ `비정형 자격조건 구조화`
→ `조건별 Matching`
→ `재무·리스크 계산`
→ `Evidence 검증`
→ `AI 설명`
→ `다음 행동`

기존의 단순 지원사업 검색 또는 범용 금융 챗봇과 달리, **지원사업 탐색과 금융 리스크 계산을 하나의 근거 기반 의사결정 흐름으로 연결**하는 것을 목표로 한다.

---

## 5. 활용 데이터 및 생성형 AI 모델 적용 방안

### 5-1. 지원사업 데이터

#### DS-001 기업마당 지원사업정보 API

Status: `VERIFIED`

Provider:
중소벤처기업부 기업마당

[EXPERIMENT]

2026-08-28 실제 API 호출을 통해 다음을 확인했다.

- GET 호출 성공
- HTTP 200
- JSON 응답 확인
- 창업 분야 20건 Sample 확보
- 실제 응답 Item 수 20건 확인
- Sample 기준 `totCnt = 71` 확인
- Raw JSON 저장 완료
- 실제 Response Schema 확인

현재 Raw Sample:
`data/raw/bizinfo/bizinfo_startup_sample.json`

실제 확인된 주요 원천 필드:

- `pblancId`: 공고 ID
- `pblancNm`: 공고명
- `jrsdInsttNm`: 소관기관
- `excInsttNm`: 수행기관
- `pldirSportRealmLclasCodeNm`: 지원분야 대분류
- `pldirSportRealmMlsfcCodeNm`: 지원분야 중분류
- `trgetNm`: 지원대상 대분류
- `hashtags`: 해시태그
- `creatPnttm`: 등록일
- `updtPnttm`: 수정일
- `reqstBeginEndDe`: 신청기간
- `bsnsSumryCn`: 사업개요·지원대상·지원내용
- `reqstMthPapersCn`: 신청방법
- `pblancUrl`: 상세공고 URL
- `printFlpthNm`: 공고문 파일 경로
- `printFileNm`: 공고문 파일명

#### 실제 데이터에서 확인한 한계

`trgetNm`은 `창업벤처`, `여성기업` 등 큰 범주이므로 세부 자격판정에 충분하지 않았다.

`hashtags` 역시 여러 지역·분야·기관 Keyword가 함께 포함될 수 있으므로 최종 자격조건의 단독 Evidence로 사용하기 어렵다.

세부 자격조건은 주로 `bsnsSumryCn` 자연어 안에 존재한다.

따라서 기업마당 데이터는 다음과 같이 처리한다. `[TEAM DECISION]`

`Raw JSON`
→ `정형 필드 Normalization`
→ `비정형 Eligibility Constraint Extraction`
→ `Structured Eligibility`
→ `User Profile Matching`
→ `Evidence Validation`
→ `LLM Explanation`

### 5-2. 기업마당 외 데이터 후보

#### K-Startup 창업지원사업 Open API

Status: `OFFICIAL_FOUND / NOT VERIFIED`

기업마당보다 다음 정보를 더 구조적으로 제공하는지 실제 검증 후 보조 Source로 사용할지 결정한다.

- 지원지역
- 신청대상
- 사업업력
- 사업대상연령
- 모집 진행 여부

기업마당과 대부분 중복되고 Matching 정확도 개선이 작다면 MVP에서는 Source를 불필요하게 늘리지 않는다.

#### 정책자금 대출 데이터

Status: `INVESTIGATING`

현재 기획에는 정책자금 대출 정보가 포함되지만 실제 MVP에서 사용할 공식 Source와 정형 Schema는 아직 확정하지 않았다.

확인 필요 항목:

- 금리
- 한도
- 상환기간
- 거치기간
- 지원대상
- 자격조건
- 기준일
- 갱신주기

공식적으로 확보되지 않은 대출조건을 임의로 생성하지 않는다.

#### 상권 데이터

Status: `OPTIONAL`

소상공인시장진흥공단 상가(상권)정보 API 등은 후보로 확인했지만 현재 핵심 지원사업 Matching에는 필수로 확정하지 않았다.

핵심 MVP가 완성된 이후 실제 리스크 계산 정확도나 사용자 가치 개선이 확인될 경우에만 추가한다.

### 5-3. 사용자 프로필 데이터

Source:
사용자 직접 입력

현재 기본 후보:

- 사용자 유형
- 지역
- 업종
- 자본금

기업마당 Sample 검증 결과 추가로 필요한 조건 후보:

- 연령
- 예비창업/기창업 여부
- 창업 업력
- 사업장 소재지
- 성별 조건
- 특정 자격·교육 여부

다만 모든 정보를 회원가입 단계에서 일괄 요구하지 않고, 지원사업 후보가 요구하는 조건에 따라 추가 정보를 요청하는 방식도 검토한다. `[TEAM DECISION]`

### 5-4. 사용자 금융 입력 데이터

현재 리스크 계산용 입력 후보:

- 초기 비용
- 자기자본
- 월매출
- 월지출
- 대출금액
- 금리
- 대출기간

위 항목은 최종 계산식 확정 전 Draft이며, 실제 Calculation Engine 설계 후 필요한 최소 입력값만 남긴다.

### 5-5. CSV / Excel 데이터

Status: `OPTIONAL — 실제 Backend 분석 / UI 진입점은 유지`

[TEAM DECISION — 2026-08-29]

소상공인 매출장표 분석은 Public URL에서 사용자가 진입할 수 있도록 유지한다.

실제 CSV/Excel 업로드·분석은 핵심 Matching, Risk, AI, 배포가 안정적으로 완성된 뒤 일정 내 구현한다.

구현할 경우 임의의 모든 회계 파일을 처리하지 않고 팀이 정의한 Sample Schema부터 지원한다.

2026-09-03~04까지 실제 분석을 안정적으로 완성하지 못하면:

- `DEMO SAMPLE` 라벨을 명확히 표시
- 샘플 입력/결과임을 사용자에게 고지
- 실제 업로드 분석 또는 실제 AI 분석으로 표현하지 않음
- 공식 기능명세서에는 실제 검증된 범위만 작성

### 5-5-1. 프리랜서 소득 안정성

Status: `PLANNED — 간이 deterministic 분석`

기간별 소득 입력을 기반으로 설명 가능한 간이 안정성 지표를 계산한다.

금융기관 수준의 신용평가로 표현하지 않으며, UI에는 결과의 한계를 알리는 작은 회색 안내문을 표시한다.

최종 계산식은 구현·테스트 후 확정한다.

### 5-6. 생성형 AI의 역할

생성형 AI는 다음 역할에 우선 활용한다. `[TEAM DECISION]`

#### A. 자연어 이해 / Interaction Mode
- 일반모드: 사용자의 자연어 질문 의도 파악
- 모드 미선택 상태의 직접 입력은 일반모드로 처리
- 집중모드: 첫 대화 전 구조화 Profile 입력을 받고 이후 자연어 대화로 전환
- 일반모드에서 구조화 입력이 필요한 시점에 집중모드 전환 제안
- 필요한 조건 파악
- 추가 정보가 필요한 경우 질문 생성

#### B. Eligibility Constraint Extraction
비정형 지원사업 설명 및 공고문에서 다음 자격조건 후보를 구조화한다.

- 지역
- 연령
- 창업 여부
- 창업 업력
- 업종
- 추가 자격조건
- 지원금액 표현

추출된 값은 원문 Evidence와 함께 관리한다.

#### C. 공고문 설명
복잡한 행정·금융 용어를 사용자에게 이해하기 쉬운 표현으로 설명한다.

#### D. 검증 결과 설명
Backend가 생성한 검색 결과, Matching 결과, Evidence, 금융·리스크 계산 결과를 사용자 상황에 맞게 종합해 설명한다.

#### E. 다음 행동 안내
- 추가 확인이 필요한 조건
- 신청 전 확인사항
- 공식 원문 확인 필요 여부

등을 안내한다.

### 5-7. 생성형 AI가 직접 수행하지 않는 영역

다음 항목은 Deterministic Code 또는 Structured Query를 우선한다.

- 명시적 지원자격 비교
- 금융수치 계산
- 대출 원리금 계산
- 잔존채무 계산
- 날짜 비교
- 신청기간 판단
- 정렬·집계
- Top-N

생성형 AI는 데이터에 없는 다음 정보를 생성하지 않는다.

- 지원사업
- 지원금액
- 신청기간
- 자격조건
- 정책자금
- 대출금리
- 금융수치

### 5-8. AI 및 데이터 처리 흐름

현재 우선 구조: `[TEAM DECISION]`

`사용자 질문 / 프로필 / 금융 입력`
→ `사용자 조건 파악`
→ `지원사업 Structured / Keyword Retrieval`
→ `비정형 Eligibility Constraint Extraction`
→ `Structured Eligibility`
→ `Deterministic Matching`
→ `재무·리스크 Calculation`
→ `Evidence Validation`
→ `LLM Explanation`
→ `출처 + 근거 + 다음 행동`

### 5-9. Evidence 관리

지원사업 정보에는 가능한 범위에서 다음 metadata를 유지한다.

- `source`
- `source_url`
- `collected_at`
- `effective_date`
- `update_cycle`
- `data_type`

자격조건을 구조화할 경우 구조화된 값만 저장하고 원문을 버리지 않는다.

추출 조건에는 가능한 경우 다음을 함께 관리한다. `[TEAM DECISION]`

- `source_field`
- `evidence_text`
- `extraction_method`
- `validation_status`

Evidence가 부족하면 임의 추론보다 `UNKNOWN`, `NEEDS_REVIEW`, `UNSUPPORTED` 형태로 처리한다.

---

## 7. MVP 기술 구조 및 안정성

### 7-1. 현재 핵심 기술 구조

현재 실제 데이터 검증 결과를 반영한 Backend 논리구조는 다음과 같다. `[TEAM DECISION]`

`Official Data`
→ `Raw Snapshot`
→ `Normalization`
→ `Eligibility Constraint Extraction`
→ `Structured Eligibility`
→ `Deterministic Matching`
→ `Deterministic Calculation`
→ `Evidence Validation`
→ `LLM Explanation`
→ `Final Result + Source`

### 7-2. Backend 주요 책임

- API 요청 검증
- 사용자 프로필 처리
- 지원사업 후보 검색
- 공고 데이터 정규화
- 자격조건 구조화
- 조건별 Matching
- 재무·리스크 계산
- Evidence 구성 및 검증
- LLM 요청 구성
- AI 응답 검증
- `UNKNOWN / NEEDS_REVIEW / UNSUPPORTED` 처리
- Frontend에 Structured Result + AI Explanation 반환

### 7-3. Retrieval 원칙

#### Structured / RDB 우선
- 공고 ID
- 기관
- 분야
- 날짜
- 구조화된 Eligibility
- 숫자
- 명시적 조건

#### Exact / Keyword 우선
- 공고명
- 기관명
- 정책자금명
- 지역·업종 Keyword

#### Semantic / Vector Retrieval
비정형 공고에서 실제 필요성이 검증되는 경우에만 적용을 검토한다.

처음부터 모든 데이터를 Vector DB에 저장하지 않는다.

### 7-4. Matching 원칙

AI가 구조화한 Eligibility를 바로 최종 정답으로 사용하지 않는다.

`Eligibility Extraction`
→ `Evidence 유지`
→ `사용자 조건과 Deterministic Comparison`

방식을 우선한다.

지원사업별로 가능하면 조건별 상태를 반환한다.

예:

- AGE: MATCHED
- REGION: NOT_MATCHED
- BUSINESS_AGE: UNKNOWN

### 7-5. Calculation Engine

금융 및 리스크 계산은 LLM과 분리한다.

현재 계산 후보:

- 월 현금흐름
- 자금 소진 속도
- Runway
- 대출 상환액
- 특정 시점 잔존채무
- 사업 악화 시 재무상태
- 폐업 가정 시 잔존채무

최종 계산식은 금융 도메인 검증 후 확정한다.

동일 입력에 동일 결과가 나오도록 구현하고 테스트를 작성한다.

### 7-6. 데이터 수집 구조

기업마당 API를 사용자 요청 시마다 직접 전량 조회하는 방식보다 다음 구조를 우선 검토한다.

`기업마당 API`
→ `Collector`
→ `Raw Snapshot`
→ `Normalization`
→ `Service DB`

사용자 요청은 Service DB에서 우선 처리해 외부 API 장애와 Latency 영향을 줄이는 방향을 검토한다. `[TEAM DECISION]`

### 7-7. AI 장애 대응

LLM 호출 실패가 전체 서비스 장애로 이어지지 않게 한다.

정상:
`Structured Matching + Evidence + AI Explanation`

LLM 장애:
`Structured Matching + Evidence + Template Explanation`

형태의 Fallback을 우선 검토한다.

### 7-8. 배포·인프라

예선 MVP는 심사자가 별도 설치 없이 Public URL에서 사용할 수 있어야 한다.

배포 단계 우선 확인 항목:

- Public URL
- HTTPS
- Frontend ↔ Backend 연결
- 환경변수 및 Secret 분리
- 외부 API timeout
- LLM timeout
- 예외 처리
- Health Check
- DB 연결
- 서버 재시작 복구
- 잘못된 사용자 입력 처리
- 로그에 API Key 및 민감 금융정보 미노출

### 7-9. 현재 구현 상태

[EXPERIMENT]

2026-08-28 현재 실제 완료:

- 기업마당 지원사업정보 API 공식 Source 확인
- API 사용 신청 및 인증키 발급
- 실제 API GET 호출 성공
- HTTP 200 확인
- 창업 분야 20건 JSON Sample 확보
- Raw JSON 저장
- 실제 Response Schema 확인
- 기업마당 데이터의 정형/비정형 Eligibility 구조 확인
- Backend Ground Truth / MVP Scope / Data Sources / Architecture / Development Status 문서 작성
- FinBridge UI/Backend 디자인 핸드오프 Draft 작성

아직 구현되지 않음:

- Backend Application Framework
- Database
- Collector 자동화
- Normalizer
- Eligibility Extractor
- Matching Engine
- Calculation Engine
- LLM Integration
- Frontend API 연동
- 배포

---

## 현재 확정되지 않은 기술 항목

- [ ] Backend Framework
- [ ] Database / ORM
- [ ] 실제 생성형 AI Provider 및 Model
- [ ] Vector Retrieval 사용 여부
- [ ] 최종 Program Schema
- [ ] 최종 Eligibility Schema
- [ ] 사용자 Profile 최소 입력값
- [ ] 정책자금 공식 Data Source
- [ ] 재무·리스크 계산식
- [ ] CSV / Excel 실제 업로드·분석 지원 범위 (UI 진입점 및 Demo Fallback 원칙은 확정)
- [ ] 사용자 금융 데이터 저장 방식
- [ ] Backend Hosting
- [ ] Database Hosting
- [ ] 최종 API Contract

---

## 다음 구현·검증 순서

[RECOMMENDATION — 2026-08-29]

2026-09-03~04 내부 완료 목표를 기준으로 다음 순서를 권장한다.

1. UI/Backend Handoff 기준 최소 API Contract Freeze
2. Focus Profile 최소 Schema 확정
3. Eligibility 최소 Schema 확정
4. 리스크 계산식 확정
5. Backend Framework / DB / Hosting 결정
6. Backend Scaffold + Health Check
7. 기업마당 Retrieval / Normalization
8. Deterministic Matching + Evidence
9. Risk Calculation
10. AI Chat Integration + Fallback
11. 지원사업 상세 ↔ Chat Context
12. 소득 안정성 간이 분석
13. 매출장표 실제 분석 가능 여부 판단 / Demo Fallback 준비
14. Frontend Integration
15. Public Deployment
16. QA / Evaluation

K-Startup·상권·Vector DB 등은 Core 사용자 흐름 완성 이후 시간이 남을 때만 검토한다.

## 본인 담당 구현 범위 요약

### AI
- 자연어 의도 파악
- 비정형 Eligibility 조건 구조화
- 근거 기반 설명
- 검색·Matching·계산 결과 종합
- 근거 부족 및 Unsupported 대응

### Backend
- API 설계
- 사용자 Profile 처리
- 지원사업 Retrieval
- Eligibility Matching
- Calculation Engine
- Evidence Validation
- AI 호출 및 Structured Response 반환

### Data
- 공식 지원사업 Source 수집
- Raw Evidence 유지
- Schema Normalization
- Eligibility Dataset 구성
- 기준일·출처 관리
- 데이터 품질 검증

### Infra
- Backend / DB 배포
- 환경변수·Secret 관리
- Health Check
- 외부 API / LLM 장애 대응
- Public URL 안정성 확보
