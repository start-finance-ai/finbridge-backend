# FinBridge Final Function Specification Content

> 공식 기능명세서 작성용 내용팩. 최신 실제 코드·테스트·DEV_STATUS·Public QA에서 구현·검증된 범위만 포함한다.

## 1. MVP 구현 범위

최종 Public Frontend `https://finbridge-start.vercel.app`와 Backend `https://backend-production-1620.up.railway.app`를 통해 다음 흐름을 제공한다.

```text
일반모드 또는 집중모드 진입
→ 기업마당 실제 지원사업 검색
→ 구조화 가능한 Eligibility 비교
→ 지역/신청기간 deterministic 판단
→ Evidence·공식 출처·다음 행동 확인
→ 지원사업 상세와 program_id 기반 AI 질문
→ 사용자 유형별 Risk / Sales / Income 분석
```

현재 데이터는 기업마당 창업 분야 검증 Snapshot 69건이다. Database, Auth backend, Vector/Graph DB, Multi-Agent, K-Startup·상권·정책자금 API는 구현 범위가 아니다.

## 2. 주요 기능 목록

| 기능명 | 기능 설명 | 관련 화면 | API | 구현/검증 상태 |
|---|---|---|---|---|
| 서비스 상태 확인 | Backend 기동 상태 반환 | 직접 API/Swagger | `GET /health` | 구현; 2026-09-07 Public 200 |
| 실제 지원사업 조회 | BIZINFO Snapshot에서 검색·필터·정렬·Top-N | 홈, 지원사업/카테고리, 검색 결과 | `GET /programs` | 구현; Public verified; 2026-09-07 sanity 200 |
| 지원사업 상세 | 공고명·기관·대상·요약·기간·신청방법·문의·공식 URL 표시 | 지원사업 상세 | `GET /programs/{program_id}` | 구현; Public verified |
| Eligibility Matching | Evidence가 있는 구조화 조건과 사용자 profile 비교 | 집중모드 Chat, Backend API | `POST /programs/match`; `/chat` 내부 재사용 | 구현; tests verified |
| 지역 기반 Ranking | 동일 지역·전국·예외 타지역·미상 tier 적용, 타지역 전용 제외 | 검색/AI 결과 | `/programs`, `/chat` 내부 | 구현; Public verified |
| 신청기간 상태 판단 | Asia/Seoul 기준 OPEN/UPCOMING/CLOSED/NEEDS_CONFIRMATION, 현재 신청 가능 필터·마감 정렬 | 공고 카드/AI 답변 | `/programs`, `/chat` 내부 | 구현; Public verified |
| 일반모드 | 폼 없이 자연어 질문, 명시 프로필 제한 추출, 집중모드 제안 | AI모드 | `POST /chat` mode `GENERAL` | 구현; Public verified |
| 집중모드 | 7개 항목 입력 후 deterministic matcher 기반 상담 | AI모드 | `POST /chat` mode `FOCUS` + `focus_profile` | 구현; Public verified |
| AI Chat | 검증된 프로그램·매칭·근거를 OpenAI가 설명 | AI모드 | `POST /chat` | 구현; Public verified |
| `program_id` Context | 상세 화면의 공고를 Chat에 정확한 Context로 전달 | 지원사업 상세 → AI모드 | `POST /chat` + `program_id` | 구현; Public verified |
| Template Fallback | LLM 실패 시 structured 결과로 후보·조건·기간·출처·준비사항 생성 | AI모드 상태 배너/답변 | `/chat` 내부 | 구현; regression verified |
| Evidence / 공식 Source | 조건 원문, BIZINFO 출처, 공식 URL 제공 | 상세/AI 결과 | 프로그램·매칭·채팅 응답 | 구현; Public verified |
| Risk Calculation | 월 원리금·현금흐름·burn·runway·잔존채무 계산 | 마이페이지, 예비창업자 | `POST /risk/calculate` | 구현; Public verified |
| Income Stability | 정확히 6개월 소득의 평균·표준편차·CV·최소·최대 | 마이페이지, 프리랜서 | `POST /income-stability/calculate` | 구현; Public verified |
| Sales CSV/XLSX Analysis | 실제 업로드 파일의 월별 매출·trend·CV·MoM·품질 계산 | 마이페이지, 소상공인 | `POST /sales-analysis/analyze` | 실제 구현; `is_demo=false`; Public verified |
| 사용자 유형별 분석 화면 | 유형에 따라 Risk/Sales/Income 도구 표시 | 마이페이지 | 위 3개 API | 구현; Public verified |

참고: Frontend의 찜과 대화 목록은 현재 브라우저 실행 중 React state다. 서버 DB에 영속 저장되는 회원 기능으로 표현하지 않는다.

## 3. 사용자 이용 흐름

### 3-1. 빠른 상담 — 일반모드

1. 접속 시 AI모드 화면으로 진입한다.
2. `일반 모드`를 고르거나 입력창에 바로 질문하면 `GENERAL`로 시작한다.
3. Backend가 지원사업 의도와 명시된 지역·나이·예비창업/사업자 상태 등을 제한적으로 구조화한다.
4. 실제 Snapshot에서 후보를 검색하고 지역·신청기간을 deterministic하게 정렬한다.
5. AI 답변과 함께 후보 공고, 공식 출처, 추가 확인사항, 다음 행동을 확인한다.
6. 조건 입력이 더 필요하면 `집중모드로 전환` 배너를 선택해 기존 화면 흐름에서 이어간다.

### 3-2. 정밀 확인 — 집중모드

1. AI모드에서 `집중 모드`를 선택한다.
2. 사용자 유형, 지역, 나이, 사업 단계, 업종, 자본, 필요사항의 7개 항목을 입력한다.
3. `분석 시작하기`를 누르면 Frontend가 `focus_profile`을 구성해 `/chat`에 보낸다.
4. Backend가 Eligibility를 deterministic하게 비교하고 Evidence가 부족하면 추가 확인 필요로 유지한다.
5. 결과 공고 버튼을 선택해 상세 화면으로 이동한다.

### 3-3. 지원사업 탐색과 상세

1. 상단 `지원사업` 메뉴 또는 홈/검색을 이용한다.
2. 실제 API 결과 카드에서 공고명·기관·기간·상태를 확인한다.
3. 상세 화면에서 지원 대상, 신청 방법, 문의처, 데이터 기준을 확인한다.
4. `공식 공고 확인`으로 BIZINFO 원문을 연다.
5. `AI에게 이 공고 물어보기`를 누르면 해당 `program_id`와 자동 질문이 AI모드로 전달된다.

### 3-4. 사용자 유형별 금융 분석

1. `마이페이지`에서 사용자 유형을 선택/수정한다.
2. 예비창업자는 Risk Calculator, 소상공인은 매출장표 분석, 프리랜서는 소득 안정성 분석을 사용한다.
3. 각 결과는 Backend가 계산하며 disclaimer와 한계를 함께 표시한다.

별도 로그인이나 테스트 계정은 필요하지 않다. Auth/Login/Signup Public flow는 현재 제출 범위에서 제거됐다.

## 4. AI 및 데이터 처리 방식

### 4-1. 사용 데이터

- 중소벤처기업부 기업마당 지원사업정보 API
- 검증된 창업 분야 Bootstrap/Snapshot 69건
- 사용자 입력: 자연어 질문, 집중모드 profile, Risk/Income 수치, Sales 파일
- K-Startup·상권·정책자금 공식 데이터는 사용하지 않는다.

### 4-2. 지원사업 처리

```text
기업마당 API 수동 refresh
→ Raw 검증
→ Snapshot/Bootstrap
→ Program normalization
→ Eligibility extraction
→ in-memory repository
→ structured/exact/keyword retrieval
→ deterministic ranking/matching
→ Evidence/Source
```

사용자 요청마다 기업마당 API를 호출하지 않는다. 결측값은 0·평균·임의 값으로 보정하지 않으며, 원문에 없는 사실을 만들지 않는다.

### 4-3. AI 역할

- Provider/API/Model: OpenAI Responses API, `gpt-5.6-luna`
- 자연어 질문 의도 이해 보조
- 검증된 공고·매칭·Evidence·계산 결과 설명
- 추가 확인사항·준비사항·다음 행동 안내

AI는 지원사업 존재, 지원금, 신청기간, 자격상태, 금융수치를 생성하거나 최종 계산하지 않는다.

### 4-4. Deterministic Backend 역할

- Program 검색·filter·ranking·Top-N
- GENERAL의 명시적 profile 추출
- Eligibility 조건/OR 경로/전역 제외 비교
- 지역 tier와 신청기간 상태 계산
- Risk: 원리금균등·현금흐름·runway·잔존채무
- Income: 6개월 평균·모집단 표준편차·CV
- Sales: 파일 validation·월별 집계·trend·CV·MoM

### 4-5. 입력 / 출력

- Program: query/지역/사업 상태/유형/분류/기관/업종/limit → 정렬된 프로그램과 source
- Chat: mode/message/optional profile/optional program_id → reply와 programs/matches/evidence/sources/actions
- Risk: 7개 비음수 수치 → 계산 6개 항목, assumptions, disclaimer
- Income: 정확히 6개 비음수 월소득 → 평균·표준편차·CV·최소·최대, disclaimer
- Sales: CSV/XLSX multipart → 월별 series, summary, trend, variability, MoM, data quality, warnings

### 4-6. 개인정보 / 금융입력

- 현재 서버 Auth, 회원 DB, profile/session persistence가 없다.
- Chat은 stateless 계약이며 Frontend가 `session_id=null`을 보낸다.
- Secret은 환경변수/배포 Secret으로 관리한다.
- 매출 업로드 파일을 영구 저장하지 않는다.
- 로그에 사용자 전체 prompt·민감 profile·금융입력이나 API key를 남기지 않는 것이 원칙이다.

### 4-7. 오류 / Fallback

- 잘못된 program ID: 404; LLM이 가짜 공고를 만들지 않는다.
- Snapshot 없음/손상: 구조화된 503; 검증된 fallback chain 사용
- 입력 Schema 오류: 422 또는 Sales 전용 구조화 error code
- LLM timeout/rate/server error: 최대 1회 retry 후 Template Fallback
- LLM incomplete/max output: partial 답변 차단 후 Fallback
- Evidence 부족: 안전한 MATCH 대신 NEEDS_REVIEW/UNKNOWN
- 날짜 불확실: NEEDS_CONFIRMATION, 임의 D-day 금지
- Frontend: Fallback, 추가 확인, 결과 없음, API error를 서로 다른 상태 배너로 구분

## 5. MVP 검증 방법

### 검증 1 — 일반모드 지원사업 탐색

진입 화면: Public Frontend 접속 후 AI모드

입력 예시: `대구에서 창업을 준비 중인데 지금 신청 가능한 지원사업을 알려줘`

실행 방법: 모드를 따로 고르지 않아도 입력창에 질문하고 전송하거나 `일반 모드`를 선택한 뒤 전송한다.

예상 결과: 일반모드 Chat이 시작되고 실제 지원사업 후보와 신청기간/상태, 공식 출처, 추가 확인사항이 표시된다. 지역 명시 시 대구/전국 후보가 명백한 타지역 전용 후보보다 우선한다.

확인 포인트: `GENERAL`, 실제 공고명, 공식 URL, `OPEN/NEEDS_CONFIRMATION` 등 상태, 집중모드 전환 제안 가능 여부. 검색 순위를 자격 보장으로 해석하지 않는다.

### 검증 2 — 집중모드 Eligibility Matching

진입 화면: AI모드 → 집중 모드

입력 예시: `예비창업자 / 대구 / 28세 / 사업자등록 전 / 카페 / 자기자본 3,000만원 / 지원사업`

실행 방법: 7개 항목을 모두 채우고 `분석 시작하기`를 누른다.

예상 결과: 입력 profile이 적용됐다는 안내 후 조건에 맞는 후보, 현재 확인된 조건, 추가 확인할 조건과 Evidence를 포함한 답변이 표시된다.

확인 포인트: Backend deterministic matcher 사용, 입력 부족과 불일치 구분, `MATCH/NEEDS_REVIEW/UNKNOWN` 의미, 최종 자격 보장 문구가 없는지 확인한다.

### 검증 3 — 지원사업 상세 / 공식 Source

진입 화면: 지원사업 목록·검색 결과 또는 Chat 후보 → 공고 상세

입력 예시: 목록의 실제 공고 1건 선택

실행 방법: 공고 카드를 열고 상세 항목과 `공식 공고 확인`을 선택한다.

예상 결과: API에서 가져온 공고명, 기관, 기간, 지원 대상, 신청 방법, 문의처, 수집일과 BIZINFO 원문 링크가 표시된다. 원문에 없는 값은 `공식 공고에서 확인 필요`로 표시된다.

확인 포인트: `GET /programs/{program_id}`, source=`BIZINFO`, 공식 URL, 임의 이미지·지원금·자격 생성이 없는지 확인한다.

### 검증 4 — AI에게 이 공고 물어보기

진입 화면: 지원사업 상세

입력 예시: 상세의 `AI에게 이 공고 물어보기` 버튼

실행 방법: 버튼을 누른다. 자동 생성된 `“공고명” 공고의 신청 대상과 준비사항을 알려주세요.` 질문이 전송된다.

예상 결과: 선택한 공고의 `program_id`가 Context로 전달되고 해당 공고의 대상·조건·기간·준비사항을 Evidence 기반으로 설명한다.

확인 포인트: `program_context_id`, 선택 공고와 답변 일치, 공식 출처, 다른 공고를 임의 생성하지 않는지 확인한다.

### 검증 5 — Risk Calculator

진입 화면: 마이페이지 → 사용자 유형 `예비창업자` → 리스크 계산기

입력 예시: 초기비용 5,000만원, 자기자본 2,000만원, 월매출 800만원, 월지출 500만원, 대출 3,000만원, 연이율 4.5%, 36개월

실행 방법: 7개 항목을 모두 입력하고 `결과 계산하기`를 누른다.

예상 결과: 초기 가용 현금, 월 원리금 상환액, 월 현금흐름, cash burn, runway, runway 시점 잔존채무와 계산 가정/disclaimer가 표시된다.

확인 포인트: Backend 계산 결과이며 하드코딩/LLM 계산이 아님, 비음수 검증, 대출이 있으면 기간이 1개월 이상 정수인지 확인한다.

### 검증 6 — Income Stability

진입 화면: 마이페이지 → 사용자 유형 `프리랜서` → 소득 안정성 분석

입력 예시: 최근 6개월 `300, 320, 280, 310, 290, 300`만원

실행 방법: 여섯 칸을 모두 입력하고 `분석하기`를 누른다.

예상 결과: 평균 300만원, 표준편차 약 12.91만원, CV 4.3%, 최소 280만원, 최대 320만원, 기간 6개월이 표시된다.

확인 포인트: 정확히 6개월, 0 허용, 음수/빈값 거부, 금융기관 안정성·신용평가 판정이 아니라는 disclaimer를 확인한다.

### 검증 7 — CSV/XLSX Sales Analysis

진입 화면: 마이페이지 → 사용자 유형 `소상공인` → 매출장표 분석

입력 예시: `backend/tests/fixtures/sales_analysis_sample.csv`

실행 방법: CSV 또는 XLSX 파일을 선택하고 `분석하기`를 누른다.

예상 결과: 테스트 fixture 기준 총매출 750만원, 평균 월매출 125만원, 최신 월매출 150만원, 2026-06 최고/2026-01 최저, 최근 추세 `UP 27.27%`, CV `13.66%`, MoM `7.14%`, `is_demo=false` 결과가 표시된다.

확인 포인트: 최대 5MB, 실제 파일 분석, 월별 data quality, 결측 월 warning, 잘못된 확장자·날짜·금액·음수 거부를 확인한다.

### 검증 계정

테스트 계정은 불필요하다. 로그인·회원가입 Backend/Public flow는 현재 구현 범위가 아니다.

## 6. MVP 제한사항

- 기업마당 창업 분야 Snapshot 69건만 사용하며 실시간 전체 분야 검색이 아니다.
- refresh는 수동/일회성이고 scheduler가 없다.
- 전체 공고문·별첨의 모든 Eligibility를 완전 추출하지 않는다.
- 근거 부족은 NEEDS_REVIEW/UNKNOWN/NEEDS_CONFIRMATION으로 남는다.
- Retrieval score는 자격 확률이 아니다.
- Risk는 원리금균등상환 1종의 참고 시뮬레이션이며 신용평가·승인 예측이 아니다.
- Income 지표에는 임의 안정/불안정 threshold가 없다.
- Sales는 정의된 CSV/XLSX Schema만 지원하고 음수/환불 거래와 exact duplicate warning은 지원하지 않는다.
- DB/Auth/서버 영속 세션이 없어 프로필·대화·찜·분석 이력을 서버에 보존하지 않는다.
- Vector DB/Graph DB/Multi-Agent/Semantic Retrieval을 사용하지 않는다.
- K-Startup/상권/정책자금 공식 데이터 API를 사용하지 않는다.
- LLM/네트워크 일시 실패 가능성이 있으며 이때 Template Fallback을 사용한다.

## 7. QA / Public Verification Evidence

### 자동 검증

- 2026-09-07 Backend 전체: `222 passed in 7.25s`
- 회귀 확대: `189 → 215 → 219 → 222 passed`
- 주요 범주: health/deployment, Bizinfo refresh/bootstrap, normalization, Eligibility extraction/matching, query understanding, regional retrieval, date status, chat/provider/fallback, risk, income, sales
- 2026-09-07 Frontend production build: 성공, 185 modules transformed

### Public 검증

- 2026-09-07: Frontend `/` HTTP 200
- 2026-09-07: Backend `/health`, `/programs?limit=1`, `/docs` HTTP 200
- 최신 DEV_STATUS/QA: Chat, 지역 ranking, 신청상태, Risk, Income, Sales, Frontend API 연동 `PUBLIC VERIFIED`
- 최종 Chat 복합 회귀: `reply_source=LLM`, `model=gpt-5.6-luna`, 대구 공고 우선, 문장 절단 없음, 준비사항 1/2/3·신청기간·공식 출처 확인

### 문제 → 수정 → 재검증 대표 사례

| 문제 | 수정 | 재검증 |
|---|---|---|
| LLM 답변 절단·반복 fallback | incomplete 차단, retry 분리, prompt 72% 축소, production budget 보정 | Public LLM 응답과 완결 문장 확인 |
| 대구 조건인데 타지역 공고 상위 | deterministic region tier와 타지역 전용 제외 | Public 대구→전국 순 확인 |
| “지금 신청 가능한” 판단 부족 | Asia/Seoul 상태 계산과 마감 정렬 | Public 및 date regression 통과 |
| 긴 질문에서 profile 누락 | 명시적 query understanding 보강 | 짧은/긴 질문 동일 profile test 통과 |
| OR 조건의 불필요한 추가 질문 | 대안 경로 보존·충족 branch 처리 | matcher/chat regression 통과 |

이번 문서 작성 시 Public POST 전 기능을 다시 실행한 것은 아니므로, 제출 직전 사람이 일곱 검증 흐름을 브라우저에서 한 번씩 최종 확인하는 것이 안전하다.
