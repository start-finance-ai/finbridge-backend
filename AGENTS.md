# 2026 금융 AI Challenge — Backend Development Instructions

## 0. Project Context

이 저장소는 2026 금융 AI Challenge 출품작의 Backend / AI / Data / Infra 구현을 담당한다.

목표는 단순한 금융 챗봇이나 금융상품 검색 서비스를 만드는 것이 아니다.

예비창업자·소상공인·프리랜서가 자신의 상황을 입력하면,

사용자 상황 분석
→ 지원사업 탐색 및 조건 매칭
→ 재무·리스크 계산
→ Evidence 검증
→ 생성형 AI 설명
→ 출처·근거·다음 행동 제시

까지 실제 웹서비스에서 동작하도록 구현하는 것이 목표다.

예선 제출용 MVP는 실제 Public URL에서 핵심 기능이 작동해야 한다.


## 0.1 Current Project Lock — 2026-08-29

현재 확정된 운영 기준:

- 팀명: `start`
- 공식 서비스명: `FinBridge`
- Backend 구축·배포, 디자인, QA 내부 완료 목표: `2026-09-03~04`
- 팀 공유 제출 일정: `2026-09-07 오전` — 최종 제출 전 공식 공지 재확인

현재 UX Contract:

```text
AI모드
├─ 일반모드: 자연어 중심, 미선택 후 바로 입력하면 자동 진입
└─ 집중모드: 첫 대화 전 구조화 입력, 이후 자연어 대화
```

AI 답변은 GPT/Claude형 대화 UI를 사용하되 Backend의 structured matching/evidence를 근거로 한다.

매출장표 분석은 Public URL에서 진입 가능해야 한다. 실제 분석이 일정 내 미완성일 경우 `DEMO SAMPLE`임을 명확히 표시하고 실제 분석으로 표현하지 않는다.

프리랜서 소득 안정성은 간이 deterministic 지표로 구현하고 UI에 결과 한계 안내를 둔다.

## 1. Source of Truth Priority

개발 판단이 충돌할 경우 다음 순서를 따른다.

1. 대회 공식 규정 및 공식 양식
2. `docs/FINANCE_AI_GROUND_TRUTH.md`
3. `docs/FINANCE_AI_MVP_SCOPE.md`
4. `docs/DATA_SOURCES.md`
5. `docs/FINANCE_AI_ARCHITECTURE.md`
6. `docs/FINANCE_AI_DEV_STATUS.md`
7. `docs/planning/` 내부 기획 초안
8. 코드 내 기존 구현

`docs/planning/`은 참고용 초안이며 확정 Ground Truth가 아니다.

기획서에 `[TEAM DECISION]`, TODO, 미정 등으로 표시된 내용은
임의로 확정하지 않는다.


## 2. Core Engineering Principle

LLM 하나에 모든 일을 맡기지 않는다.

다음 항목은 가능한 한 deterministic code 또는 structured query로 처리한다.

- 금융수치 계산
- 대출 원리금 계산
- 현금흐름 계산
- 잔존 채무 계산
- 버틸 수 있는 기간 계산
- 날짜 비교
- 신청 마감 여부
- 지원사업 명시적 자격 조건
- 정렬
- Top-N
- 집계
- 명확한 조건 필터

LLM은 다음 역할에 우선 사용한다.

- 자연어 질문 의도 파악
- 사용자 조건 추출
- 복잡한 질문 분해
- 비정형 문서 의미 해석
- 검색 결과 설명
- 계산 결과 설명
- 여러 Evidence 종합
- 사용자에게 이해하기 쉬운 표현 생성


## 3. Preferred Processing Flow

기본 처리 구조는 다음 방향을 우선한다.

Question / User Profile / Financial Input

→ Intent & Constraint Parsing

→ Query Planning

→ Structured Retrieval

→ Optional Document Retrieval

→ Deterministic Calculation

→ Evidence Validation

→ LLM Explanation

→ Final Response + Evidence + Source


## 3.1 UI / Backend Contract

Frontend 또는 Backend를 구현하기 전에 다음 Handoff를 함께 확인한다.

```text
docs/design/0829_FinBridge_UI_Backend_연동_디자인핸드오프_v1.md
```

이 Handoff는 Ground Truth / MVP Scope / Data Sources / Architecture보다 우선하지 않는다.

충돌 시 상위 Source of Truth가 우선한다.

주요 구현 규칙:

- 기존 디자이너 UI의 전체 톤앤매너와 구조를 불필요하게 갈아엎지 않는다.
- Backend가 필요한 필드·상태·CTA만 최소 추가한다.
- 지원사업 카드의 공고 이미지는 UI asset이며 사실 검증 Evidence가 아니다.
- 지원사업 상세에서 AI 채팅으로 이동할 때 가능하면 `program_id`를 context로 전달한다.
- Backend는 자연어 reply 외에 structured program/match/evidence/action을 함께 반환한다.

## 4. Retrieval Rules

모든 검색 문제를 Vector DB로 해결하지 않는다.

### Structured / RDB 우선

다음은 structured query 또는 deterministic computation을 우선한다.

- 지역
- 사용자 유형
- 업종
- 자본금
- 지원 금액
- 신청 기간
- 날짜
- 자격 조건
- 정렬
- 집계
- 숫자 비교

### Keyword / Exact Lookup 우선

다음은 keyword 또는 exact lookup을 우선한다.

- 지원사업명
- 기관명
- 지역명
- 정책자금명

### Vector Retrieval 후보

다음과 같이 비정형 텍스트의 의미 검색이 실제로 필요한 경우에만 사용을 검토한다.

- 지원사업 공고문
- 긴 사업 설명
- 자연어로 표현된 복잡한 조건

Vector DB, Graph DB, Agent Framework 등 새로운 기술은
baseline 대비 정확도 또는 사용자 가치가 증가하는 경우에만 도입한다.


## 5. Financial Safety

다음 정보를 LLM이 임의로 생성해서는 안 된다.

- 존재하지 않는 지원사업
- 존재하지 않는 정책자금
- 존재하지 않는 정부 제도
- 지원 금액
- 대출 금리
- 신청 자격
- 신청 기간
- 금융 계산 결과
- 법·제도 존재 여부

Evidence가 부족하면 추측하지 않는다.

가능하면 다음 상태를 명시적으로 처리한다.

- SUPPORTED
- NEEDS_REVIEW
- UNSUPPORTED

서비스가 사용자의 최종 지원 자격이나 대출 승인을 보장하는 것처럼 표현하지 않는다.


## 6. Evidence First

AI 답변보다 Evidence가 먼저다.

지원사업 또는 데이터에는 가능한 범위에서 다음 metadata를 관리한다.

- source
- source_url
- collected_at
- effective_date
- update_cycle
- data_type

최종 AI 설명은 검색된 Evidence와 Backend 계산 결과를 입력으로 사용해야 한다.

데이터에 없는 사실을 LLM이 보완해서는 안 된다.


## 7. Backend Responsibilities

Backend는 다음 책임을 가진다.

- API request validation
- 사용자 프로필 입력 처리
- 지원사업 데이터 조회
- 지원사업 조건 필터링
- 사용자 조건과 지원사업 조건 매칭
- CSV / Excel 입력 처리
- 재무 지표 계산
- 창업 리스크 계산
- Evidence 생성
- Evidence validation
- LLM request 구성
- LLM response validation
- Unsupported 처리
- Frontend API response 생성


## 8. Data Principles

데이터는 공개·허가·라이선스 범위가 명확한 자료를 우선한다.

외부 데이터 도입 전 반드시 확인한다.

- 실제 접근 가능 여부
- 제공기관
- 이용조건
- 데이터 기준일
- 갱신주기
- 필요한 필드 존재 여부
- MVP 기간 내 재현 가능 여부

결측값을 근거 없이 0, 평균값 또는 임의값으로 대체하지 않는다.

최신성이 필요한 금융 데이터는 기준 시점을 구분한다.

샘플 데이터, Mock 데이터, 실제 데이터를 코드와 문서에서 명확하게 구분한다.


## 9. Privacy & Security

다음을 코드나 Git에 직접 저장하지 않는다.

- API Key
- Secret Key
- Access Token
- Password
- 개인정보
- 민감 금융정보

Secret은 환경변수로 관리한다.

`.env`는 Git에 커밋하지 않는다.

필요한 환경변수 이름만 `.env.example`에 작성한다.

사용자가 업로드하는 매출·소득 데이터는
MVP에서 꼭 필요한 범위만 처리한다.

가능하면 세션 단위 처리를 우선하고
불필요한 개인정보를 장기 저장하지 않는다.

민감정보 원문을 로그에 출력하지 않는다.


## 10. Backend Structure

구현 시 관심사를 분리한다.

권장 구조:

- api/
- services/
- agent/
- retrieval/
- calculation/
- data/
- models/
- schemas/
- evaluation/
- tests/

실제 Framework가 결정된 이후 Framework 관례에 맞게 조정할 수 있다.

다만 다음 로직은 가능한 한 분리한다.

- API
- Retrieval
- Calculation
- Evidence Validation
- LLM
- Data Access


## 11. API Rules

API request / response에는 명시적인 Schema를 사용한다.

사용자 입력을 신뢰하지 않는다.

다음을 검증한다.

- 필수값
- 데이터 타입
- 숫자 범위
- 날짜 형식
- 파일 형식
- 비정상 입력

외부 API에는 timeout을 설정한다.

외부 API 또는 LLM 실패가 전체 Backend 장애로 이어지지 않도록 예외처리한다.


## 12. Calculation Rules

금융 및 재무 계산은 LLM에게 수행시키지 않는다.

Calculation Engine은 가능한 한 동일 입력에 동일 결과를 반환해야 한다.

계산식은 코드에 구현하기 전에 다음을 명확히 한다.

- 입력값
- 단위
- 계산식
- 가정
- 경계값
- 결측 처리
- 출력값

계산 로직에는 테스트를 작성한다.


## 13. AI Rules

LLM Prompt에는 검증된 데이터와 계산 결과를 전달한다.

LLM이 원본 데이터베이스의 사실을 임의로 변경하거나 추가하지 않게 한다.

LLM 답변에는 가능한 경우 다음을 구분한다.

- Fact
- Calculation
- Inference
- Recommendation

모델 또는 API 공급자는 팀에서 확정하기 전 임의로 특정하지 않는다.


## 14. MVP Priority

새로운 기술보다 제출 가능한 상태를 우선한다.

개발 우선순위:

1. 실제 데이터 소스 검증
2. MVP 범위 확정
3. 데이터 Schema 확정
4. DB / Data Layer
5. 지원사업 Structured Retrieval
6. 사용자 조건 Matching
7. Deterministic Calculation
8. Evidence Validation
9. LLM Integration
10. Frontend API Integration
11. Deployment
12. QA / Evaluation

기능 수를 늘리는 것보다 하나의 핵심 사용자 시나리오를 완성한다.


## 15. Do Not Overengineer

다음을 사전 검증 없이 추가하지 않는다.

- Multi-Agent
- Graph DB
- Vector DB
- Knowledge Graph
- 복잡한 Workflow Framework
- 실시간 Streaming Architecture
- 불필요한 Microservice 분리

필요성이 생기면 먼저 단순한 baseline과 비교한다.


## 16. Reliability

MVP 배포 전에 최소한 다음을 확인한다.

- Public 접근
- HTTPS
- Backend 실행
- DB 연결
- 환경변수
- API timeout
- LLM timeout
- 예외처리
- Health Check
- 서버 재시작
- 브라우저 새로고침
- 잘못된 사용자 입력
- 외부 API 장애
- LLM 장애

특정 개발자 PC가 켜져 있어야 서비스가 작동하는 구조는 사용하지 않는다.


## 17. Testing & Evaluation

가능하면 다음 유형의 테스트를 준비한다.

- 정상 입력
- 경계값
- 모호한 질문
- 잘못된 전제
- 데이터에 없는 질문
- 다중 조건 질문
- 계산 질문
- 긴 자연어 질문
- Prompt Injection
- 비정상 입력

가능하면 기록한다.

- Retrieval Accuracy
- Calculation Accuracy
- Unsupported Detection
- Hallucination Rate
- Latency
- API Failure Rate


## 18. Implementation Truthfulness

구현되지 않은 기능을 구현된 것처럼 표현하지 않는다.

Frontend 표시 내용과 Backend 실제 동작이 일치해야 한다.

하드코딩된 데모 결과를 실제 AI 분석 결과처럼 표현하지 않는다.

기획 기능과 구현 완료 기능을 반드시 구분한다.


## 19. Before Coding

새로운 주요 기능을 구현하기 전에 확인한다.

1. `docs/FINANCE_AI_GROUND_TRUTH.md`
2. `docs/FINANCE_AI_MVP_SCOPE.md`
3. `docs/DATA_SOURCES.md`
4. `docs/FINANCE_AI_ARCHITECTURE.md`
5. `docs/FINANCE_AI_DEV_STATUS.md`
6. `docs/design/0829_FinBridge_UI_Backend_연동_디자인핸드오프_v1.md`

문서 간 충돌이 있으면 임의로 판단하지 않는다.

불확실한 내용은 TODO 또는 TEAM DECISION으로 표시한다.


## 20. After Coding

주요 작업 완료 후 반드시 수행한다.

1. 관련 테스트 실행
2. API 동작 검증
3. 오류 확인
4. `docs/FINANCE_AI_DEV_STATUS.md` 최신화
5. 구현 / 미구현 기능 구분
6. 새로운 기술 결정사항 기록
7. 새로운 데이터 소스가 추가되면 `DATA_SOURCES.md` 업데이트


## 21. Current Development Rule

2026-08-29 현재는 문서·데이터 검증만 이어가는 단계가 아니라 **Core Backend 구현으로 전환해야 하는 시점**이다.

이미 확인된 사실:

- 기업마당 지원사업정보 API Main Source 최초 실측 검증 완료
- 공식 서비스명 `FinBridge` 확정
- 일반모드 / 집중모드 UX 확정
- UI/Backend Handoff Draft 작성

아직 빠르게 Freeze해야 하는 항목:

- Backend Framework
- Database / Local Snapshot 방식
- LLM Provider / Model
- Backend Hosting
- 최소 Eligibility Schema
- Focus Profile Schema
- Risk Calculation Formula
- Chat/API Contract

다음 항목은 핵심 사용자 흐름을 지연시키면서까지 선행하지 않는다.

- Vector DB
- Graph DB
- Multi-Agent
- 상권 데이터
- K-Startup 추가 연동
- 범용 CSV / Excel Parser

Core 작업 순서:

```text
Schema/API 최소 Freeze
→ Backend Scaffold
→ 기업마당 Retrieval
→ Deterministic Matching
→ Risk Calculation
→ Evidence
→ AI Chat
→ Frontend Integration
→ Public Deployment
→ QA
```

기능 구현 후에는 반드시 `docs/FINANCE_AI_DEV_STATUS.md`를 실제 코드/테스트 상태에 맞춰 갱신한다.
