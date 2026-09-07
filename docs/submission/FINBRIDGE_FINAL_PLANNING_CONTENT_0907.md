# FinBridge Final Planning Content

> 공식 기획서 작성용 내용팩. 현재 구현과 향후 확장을 분리하며, 수치·상태는 `FINBRIDGE_FINAL_SUBMISSION_FACTS_0907.md`를 따른다.

## 1. 서비스 명칭

**FinBridge**

팀명: `start`

## 2. 아이디어 기획 핵심내용(요약)

FinBridge는 예비창업자·소상공인·프리랜서가 자신의 상황에 맞는 자금지원 정보를 찾고 실제 행동으로 옮길 수 있도록 돕는 Evidence 기반 금융 의사결정 지원 서비스다. 중소벤처기업부 기업마당의 실제 지원사업 데이터를 Snapshot으로 확보하고, 공고문 속 비정형 Eligibility를 구조화한 뒤 사용자 조건과 deterministic하게 비교한다. 결과에는 일치·불일치·추가 확인 필요 상태와 원문 Evidence, 신청기간 상태, 공식 출처를 함께 제공한다.

지원사업 탐색 이후에는 입력값을 기반으로 원리금·현금흐름·Runway·잔존채무를 계산하는 Risk Calculator, 최근 6개월 소득 통계, 실제 CSV/XLSX 매출 분석을 연결한다. 생성형 AI는 지원사업이나 금융수치를 만들어내는 판정기가 아니라, Backend가 검증한 검색·매칭·계산 결과를 자연어로 설명하고 추가 확인사항과 다음 행동을 제안하는 계층으로 사용한다.

핵심 흐름:

```text
사용자 상황
→ 기업마당 실제 지원사업 탐색
→ 비정형 Eligibility 구조화
→ Deterministic Matching / 지역·날짜 판단
→ Evidence
→ Risk·Income·Sales 계산
→ AI Explanation
→ 공식 출처
→ 다음 행동
```

## 3. 문제 정의 및 제안 배경

지원사업 정보가 공개돼 있어도 사용자는 “내가 지금 신청할 수 있는가”를 판단하기 어렵다. 자격조건은 공고의 요약문, 신청대상 문장, 공고문·별첨에 흩어져 있고, 지역·나이·업력·사업자등록 상태가 자연어 AND/OR/예외 구조로 표현된다. 검색 결과의 키워드 관련성만으로는 실제 자격 적합성을 설명할 수 없으며, 신청기간도 고정 마감·예산 소진·추후 공지처럼 표현 방식이 다양하다.

일반 검색은 관련 공고를 찾는 데는 유용하지만 조건 충족 여부와 근거를 연결하기 어렵다. 반대로 단순 생성형 AI 챗봇에 검색·자격판정·날짜·금융계산을 모두 맡기면 존재하지 않는 정보 생성, 지역 오매칭, 날짜 판단 불일치, 계산 재현성 저하, Provider 장애 시 전체 흐름 중단 위험이 생긴다.

FinBridge는 이 문제를 세 층으로 분리한다.

1. 공식 데이터와 Raw Evidence를 보존한다.
2. 구조화 가능한 자격·지역·날짜·금융수치는 deterministic Backend가 처리한다.
3. 생성형 AI는 검증된 결과를 사용자 언어로 설명한다.

근거가 부족한 경우 결과를 억지로 확정하지 않고 `NEEDS_REVIEW`, `UNKNOWN`, `NEEDS_CONFIRMATION`으로 남겨 사용자가 공식 공고에서 확인할 항목을 분명히 한다.

## 4. 서비스 컨셉 및 차별성

### 4-1. 단순 검색 챗봇이 아닌 의사결정 흐름

FinBridge의 결과는 추천 문장 하나가 아니다. 실제 공고, 사용자 조건, 매칭 상태, Evidence, 신청기간, 공식 출처, 준비사항, 재무 영향까지 한 흐름에서 연결한다.

### 4-2. 실제 데이터와 공식 출처

현재 Main Source는 중소벤처기업부 기업마당 지원사업정보 API다. 검증된 창업 분야 Snapshot 69건을 정규화하여 사용하며, 원문에 없는 지원금·신청기간·자격을 채워 넣지 않는다. 상세 화면과 AI 응답에서 공식 Source URL로 이동할 수 있다.

### 4-3. 비정형 Eligibility 구조화와 deterministic matching

공고의 지역, 나이, 예비창업 여부, 사업자등록 상태, 업력과 안전하게 해석 가능한 OR 경로를 Evidence와 함께 구조화한다. 사용자 입력 부족과 실제 불일치를 구분하고, Evidence가 부족한 조건을 지원 가능으로 단정하지 않는다. Retrieval score도 자격 확률로 사용하지 않는다.

### 4-4. 지역·신청기간의 재현 가능한 판단

지역이 명시된 경우 `SAME_REGION → NATIONWIDE → 예외가 있는 타지역 → 지역 미상` 순으로 정렬하고 명시적 타지역 전용 공고는 제외한다. 신청기간은 Asia/Seoul 기준으로 `OPEN / UPCOMING / CLOSED / NEEDS_CONFIRMATION`을 계산하며, “지금 신청 가능한” 요청에서는 종료·예정 공고를 제외한다.

### 4-5. 일반모드와 집중모드

- 일반모드: 별도 폼 없이 질문하면 바로 시작한다. 명시된 지역·나이·예비창업/사업 상태를 제한적으로 구조화하고, 더 정밀한 확인이 필요하면 집중모드 전환을 제안한다.
- 집중모드: 사용자 유형, 지역, 나이, 사업 단계, 업종, 자본, 필요사항 7개 항목을 먼저 입력하고 같은 deterministic matcher로 더 구체적인 조건을 확인한다.

### 4-6. 지원사업 상세와 AI의 연결

사용자가 상세 화면에서 `AI에게 이 공고 물어보기`를 선택하면 해당 `program_id`가 Chat Context로 전달된다. AI는 Repository 안의 정확한 공고와 Evidence를 기준으로 신청 대상과 준비사항을 설명하며, 잘못된 ID에서 가짜 공고를 생성하지 않는다.

### 4-7. 금융·리스크 계산

Risk Calculator는 초기비용·자기자본·월매출·월지출·대출조건으로 월 원리금, 현금흐름, cash burn, runway, 잔존채무를 계산한다. 소득 안정성은 최근 6개월 평균·표준편차·CV를, 매출장표는 실제 CSV/XLSX의 월별 합계·추세·변동성·MoM을 계산한다. 세 기능 모두 LLM이 아닌 Backend 계산이며 금융기관 판정이 아니다.

### 4-8. 실제 QA 기반 신뢰성 개선

Public QA에서 답변 절단, 반복 fallback, 자연어 조건 누락, 타지역 공고 상위 노출, 신청 가능 상태 판단 부족을 확인했다. 원인을 Provider 상태·prompt context·keyword ranking·date logic으로 분리하고 코드와 회귀 테스트를 수정한 뒤 재배포·Public 재검증했다. Backend regression은 QA 전 189개에서 최종 222개로 확대됐으며, 2026-09-07에도 222개 전체가 통과했다.

## 5. 활용 데이터 및 생성형 AI 모델 적용 방안

### 5-1. Bizinfo와 Snapshot

- Source: 중소벤처기업부 기업마당 지원사업정보 API
- 현재 범위: 창업 분야 69건 Bootstrap/Snapshot
- 처리: Raw 보존 → validation → normalization → in-memory repository
- 운영: 수동/일회성 refresh. 사용자 요청 시마다 외부 API를 호출하지 않는다.
- 장애 대응: 새 Snapshot 검증 실패 시 기존 정상 Snapshot을 유지하고 Bootstrap으로 기동할 수 있다.

### 5-2. Normalization, Eligibility, Matching, Evidence

Program ID·공고명·기관·분류·대상·요약·신청기간·신청방법·공식 URL·수집시각을 정규화한다. 비정형 Eligibility는 공고 수준과 조건 수준의 추출 상태를 분리하고 Evidence 원문을 보존한다. deterministic matcher는 AND/OR/전역 제외 구조를 비교하여 `MATCH / NO_MATCH / NEEDS_REVIEW / UNKNOWN`을 반환한다.

### 5-3. 생성형 AI 모델

- Provider: OpenAI
- API: Responses API
- 모델: `gpt-5.6-luna`
- reasoning effort: `low`
- 적용 역할: 자연어 의도 이해 보조, 검증 결과·공고·추가 확인사항·다음 행동 설명
- 비적용 역할: 지원사업 생성, 최종 자격 계산, 날짜 판단, 지원금·금리·공식 URL 생성, 금융계산

### 5-4. Deterministic Backend 역할

- Structured/exact/keyword retrieval, Top-N
- 명시적 일반모드 프로필 추출
- Eligibility 비교와 지역 ranking
- 신청기간 상태와 마감 정렬
- Risk/Income/Sales 수치 계산
- Evidence와 공식 Source 구성

### 5-5. Fallback

OpenAI 응답이 timeout·rate/server error·incomplete 상태이면 partial 답변을 노출하지 않는다. 최대 1회 재시도 후 deterministic Template Fallback으로 후보, 확인 조건, 기간, 출처, 준비사항을 제공한다. LLM 실패가 지원사업 검색·매칭·Evidence·계산 결과의 소실로 이어지지 않도록 설계했다.

### 5-6. Income / Sales 실제 구현 상태

- Income Stability: 정확히 6개월 입력을 검증하고 평균·모집단 표준편차·CV·최소·최대를 계산하는 실제 구현, Public verified
- Sales: CSV/XLSX multipart upload, 5MB/50,000행 제한, 날짜·금액 검증, 월별 통계·trend·CV·MoM을 계산하는 실제 구현, Public verified, `is_demo=false`
- 한계: 범용 회계파일이나 환불/음수 거래 모델은 아니며 exact duplicate warning은 미구현

### 5-7. Security

- Secret/API key는 환경변수와 Railway Secret으로 관리
- `.env`와 runtime collected snapshot은 Git 제외
- exact-origin CORS, wildcard 거부
- 사용자 prompt·전체 프로필·금융입력 및 provider 원문 오류를 안전 로그에 남기지 않음
- 업로드 파일 영구 저장 없음
- MVP에서 DB/Auth backend/서버 영속 세션을 사용하지 않음

## 6. 기대 효과 및 확장 가능성

### 현재 MVP에서 기대하는 효과

- 사용자가 지원사업 목록을 찾는 데서 끝나지 않고 자기 조건과 공고 조건의 차이를 확인할 수 있다.
- Evidence와 공식 출처를 함께 제시해 AI 설명의 검증 경로를 제공한다.
- 지역·날짜·금융계산을 deterministic하게 처리해 같은 입력에 대한 재현성을 높인다.
- 일반모드의 낮은 진입장벽과 집중모드의 구조화 입력을 함께 제공한다.
- 지원사업 선택 이후 자금조달의 현금흐름·소득 변동·매출 추세까지 같은 서비스 안에서 점검할 수 있다.
- LLM 장애 시에도 최소 의사결정 정보를 유지한다.

### 향후 확장 가능성 — 현재 구현으로 표현하지 않음

- 기업마당 다른 분야와 추가 공식 데이터 소스의 라이선스·중복·품질 검증 후 coverage 확대
- 공고문/별첨 수집을 통한 Eligibility 구조화 범위 확대와 human review workflow
- 실제 사용자 동의·보안 설계 이후 Auth, 프로필·찜·대화·분석 이력의 영속 저장
- 환불·중복 거래·더 다양한 회계 Schema 지원
- 세금·수수료·변동금리 등 Risk scenario 확장
- 충분한 평가 근거가 확보된 경우에만 semantic/vector retrieval 검토

K-Startup, 상권정보, 정책자금 자동 연동, DB, Vector DB, Graph DB, Multi-Agent는 현재 MVP 구현 기능이 아니다.

## 7. 자유 타이틀

### 1순위 추천

**“AI에게 판정을 맡기지 않았다: Public QA로 완성한 Evidence 기반 FinBridge”**

문제 발견 → deterministic 역할 분리 → 회귀 테스트 → 재배포 → Public 재검증이라는 프로젝트의 실제 강점을 가장 잘 드러낸다.

### 대안 2

**“189에서 222까지: 실패를 회귀 테스트로 바꾼 금융 AI 서비스”**

### 대안 3

**“검색 결과에서 다음 행동까지: 근거·자격·리스크를 잇는 FinBridge”**

## 8. 추천 도식 / 화면 캡처 위치

최대 4개만 사용한다.

1. **서비스 처리 흐름 도식** — 문제/해결 소개 직후. `Official Data → Snapshot → Eligibility → Matching → Evidence → Calculation → AI Explanation → Action`의 역할 분리를 한눈에 보여준다.
2. **일반모드와 집중모드 화면 캡처** — 서비스 컨셉 부분. 일반모드 자연어 진입과 집중모드 7개 구조화 입력의 차이를 나란히 보여준다.
3. **지원사업 상세 → AI에게 이 공고 물어보기 화면** — 차별성 부분. 실제 공고·공식 출처·`program_id` Context 연결을 보여준다.
4. **QA 개선 전후 요약 도식 또는 분석 도구 화면** — 성과 부분. `문제 → 코드 수정 → 222 tests → Public 재검증`을 중심으로 하고, 공간이 남으면 Risk/Sales/Income 결과를 한 장에 구성한다.

새로운 디자인 시안을 만들 필요는 없으며 최종 Public 화면을 캡처한다.
