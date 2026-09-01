# FinBridge — QA 이후 Backend / AI Troubleshooting 기록

Last Updated: 2026-09-01

목적:

- 2026 금융 AI Challenge 제출 기획서에서 **“QA를 통해 어떤 문제를 발견했고, 어떻게 실제 서비스 수준으로 개선했는가”**를 설명하기 위한 근거 문서
- 개인 포트폴리오에서 **AI / Backend / Data / Infra 문제 해결 경험**을 구체적인 수치와 의사결정으로 설명하기 위한 기록

이 문서는 QA 담당자의 1차 검증 이후 실제로 발견·수정·재배포·Public 재검증한 내용만 중심으로 정리한다.

---

# 1. 한 줄 요약

FinBridge는 QA 과정에서 **LLM 응답 절단·Fallback, 자연어 프로필 추출 누락, 지역 부적합 공고 랭킹, 신청 가능 상태 판단, OR 자격조건 처리** 문제를 발견했고, 이를 LLM 재프롬프트만으로 해결하지 않고 **deterministic query understanding / regional ranking / date logic / eligibility logic + provider hardening**으로 분리해 수정했다. 이후 전체 Backend regression `222 passed`와 Railway Public 재검증을 통해 핵심 P0를 종료했다.

---

# 2. QA 시작 시점의 문제

QA 담당자가 실제 API를 테스트하면서 다음 문제가 확인됐다.

## P0

1. AI 답변이 중간 문장에서 끊기는 현상
2. `TEMPLATE_FALLBACK`, `model=null` 반복
3. 사용자가 요청한 “지금 준비해야 할 것 1순위·2순위·3순위”가 답변에 없음
4. 대구 사용자의 조건을 입력했는데 울산·전남 등 다른 지역 공고가 높은 순위에 노출
5. “지금 신청 가능한 지원사업” 질문에서 현재 날짜 기준 필터와 마감일 정렬이 충분하지 않음

## P1 / P2

- Sales CSV에서 exact duplicate row를 별도 warning하지 않음
- positive cashflow 상황에서 Runway 의미가 UI에서 오해될 가능성
- 소득 안정성 CV / 표준편차의 설명 방식 및 임의 threshold 사용 위험
- error code 한글화, 0과 blank 구분 등 UX 보완 필요

P0는 심사자가 3~5분 데모에서 직접 체감할 핵심 흐름이므로 우선 수정했다.

---

# 3. Troubleshooting 1 — AI 답변 절단과 `TEMPLATE_FALLBACK`

## 증상

긴 복합 질문에서 정상적인 structured retrieval / matching 결과가 존재하는데도:

```text
reply_source = TEMPLATE_FALLBACK
model = null
```

이 발생하거나 AI 답변이 문장 중간에서 끊겼다.

Railway 로그에서 실제 원인이 분리됐다.

```text
AIProviderTimeoutError         reason=TIMEOUT
AIProviderMaxOutputTokensError reason=MAX_OUTPUT_TOKENS
```

## 원인

단순히 OpenAI 장애가 아니었다.

- LLM prompt에 program 전체 데이터, HTML summary, 중복 evidence / source 정보가 과도하게 포함
- 한 요청에서 후보 5건을 모두 상세 설명하도록 해 input/output 부담 증가
- Responses API의 incomplete 상태를 충분히 엄격하게 처리하지 않으면 partial answer가 노출될 가능성
- `max_output_tokens=1200` 안에 visible text뿐 아니라 reasoning 사용량도 포함될 수 있어 긴 답변에서 한도 초과
- 초기 timeout 10초는 Public 환경에서 안정성이 부족

## 수정

### Provider hardening

- Responses API `status` / `incomplete_details` 검사
- `max_output_tokens` incomplete이면 partial output을 버리고 fallback 사용
- transient timeout / rate limit / server error는 최대 1회 retry
- auth / quota / config / incomplete는 불필요한 retry를 하지 않음
- 안전 로그에는 error class와 reason만 기록

### Prompt context 축소

LLM에게 필요한 최소 정보만 전달하도록 context를 분리했다.

```text
program_id
program_name
provider
핵심 eligibility evidence
deterministic match result
apply period / status
축약된 application method
source_url
```

Structured API response 자체는 유지했다.

실측:

```text
Context JSON
10,786 chars / 14,854 bytes
→ 2,982 chars / 4,178 bytes

약 72% 감소
```

LLM 상세 설명 후보는 최대 3건으로 제한했지만 API의 structured `programs`는 5건을 유지했다.

### Output 제어

- 답변 목표: 약 700~900 visible token
- 후보마다 현재 조건 / 추가 확인 / 신청기간 / 공식 출처 위주
- 장문의 지원내용 / 신청방법 원문 반복 금지
- 답변 마지막에 준비사항 1/2/3을 유지

### Production config

```text
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_OUTPUT_TOKENS=2000
```

1200 → 2000 변경은 답변을 장문화하려는 목적이 아니라 reasoning + visible output을 위한 안전 여유를 확보하기 위한 조치다.

## 결과

최종 Public 복합 회귀에서:

```text
reply_source = LLM
model = gpt-5.6-luna
문장 절단 없음
```

으로 확인했다.

### 포트폴리오 포인트

“LLM이 느리다”를 단순 timeout 증가로 처리하지 않고, **실제 provider error reason을 관측 → context budget 축소 → incomplete safety → production token budget 조정**의 순서로 해결했다.

---

# 4. Troubleshooting 2 — Fallback도 사용자에게 쓸 수 있게 만들기

## 문제

AI Provider 실패 시 초기 fallback은 짧은 안내 수준이라 FinBridge의 핵심 가치인:

```text
근거 있는 후보
→ 조건 확인
→ 공식 출처
→ 다음 행동
```

을 충분히 전달하지 못했다.

## 수정

Provider 실패 시에도 deterministic 결과만으로 다음 구조를 생성하도록 개선했다.

- 후보 프로그램
- 현재 확인된 조건
- 추가 확인할 조건
- 신청기간 / 상태
- 신청방법(확보된 경우만)
- 공식 출처
- 준비사항 1순위 / 2순위 / 3순위

## 의미

LLM 장애가 곧 FinBridge 전체 기능 장애가 되지 않는다.

```text
Retrieval / Matching / Evidence / Calculation
= Backend deterministic 결과 유지

LLM
= 설명 품질을 높이는 계층
```

이 구조는 금융·지원사업 서비스에서 “AI가 실패하면 아무것도 못 하는 구조”를 피하기 위한 설계다.

---

# 5. Troubleshooting 3 — 일반모드 자연어에서 사용자 조건이 빠지는 문제

## 증상

사용자가 일반모드에서 자연어로:

```text
대구 거주 28세
예비창업자
사업자등록 없음
```

이라고 적어도 일부 필드가 structured matching에 전달되지 않았다.

특히 긴 문장의:

```text
사업자등록은 하지 않았습니다
```

가 `UNREGISTERED`로 추출되지 않는 사례가 있었다.

## 원인

GENERAL mode 검색이 keyword 중심이고, 제한적인 자연어 profile extraction이 충분하지 않았다.

## 수정

`query_understanding.py`를 추가/보완해 명시적으로 표현된 최소 프로필만 deterministic하게 추출했다.

- region
- age
- pre-founder / existing business
- business age
- business registration status

긴 질문과 짧은 질문이 동일 의미를 가지면 동일 structured profile을 생성하는 regression test를 추가했다.

## 결과

짧은 질문과 긴 종합 질문 모두:

```text
region = 대구
age = 28
pre_founder = true
business_registration_status = UNREGISTERED
```

로 일관되게 해석하도록 보정했다.

### 포트폴리오 포인트

LLM에 사용자 프로필 추출을 전부 위임하지 않고, MVP에 필요한 명시적 패턴은 **deterministic query understanding**으로 처리해 재현성을 높였다.

---

# 6. Troubleshooting 4 — 대구 사용자에게 타지역 공고가 상위 노출

## 증상

초기 Public QA에서 대구 사용자에게:

- 영월
- 울산
- 전남
- 안산

등 타지역 공고가 대구 공고보다 앞서 노출됐다.

긴 질문에서는 “조건 충족 여부”, “준비사항” 같은 추가 keyword가 retrieval score에 영향을 주면서 순위가 더 흔들렸다.

## 원인

keyword relevance score가 지역 적합성보다 강하게 작동했다.

또한 일부 공고의 지역 조건이 extraction되지 않으면 업력·예비창업자 같은 다른 조건만 MATCH되어 지역적으로 부적합한 공고가 높은 평가를 받을 수 있었다.

## 수정

지역이 명시된 검색에서는 일반 keyword score보다 먼저 deterministic region tier를 적용했다.

```text
1. SAME_REGION
2. NATIONWIDE
3. OTHER_REGION_WITH_EXPLICIT_EXCEPTION
4. REGION_UNKNOWN
5. EXPLICIT_OTHER_REGION_ONLY → exclude
```

세부 정책:

- 대구 → 대구 동구/서구는 같은 광역지역으로 보되 구 정보가 없으면 `REGION_DETAIL_REQUIRED`
- 전국 대상 공고는 유지
- 영월 “선정 후 주소 이전 가능”, 울산 “타지역민 별도 자격”, 전남 “타지역민 예외”처럼 Evidence가 있으면 무조건 삭제하지 않음
- 단, 이런 예외 타지역 공고가 SAME_REGION / NATIONWIDE보다 앞서지 않도록 함
- 명백한 타지역 전용 공고는 제외

## 결과

최종 Public 복합 질문에서:

```text
1. 대구 공고
2. 대구 공고
3. 전국 대상 공고
```

순으로 노출되는 것을 확인했다.

### 포트폴리오 포인트

검색 점수를 “자격 가능성”으로 오해하지 않고, **retrieval relevance와 eligibility / geographic compatibility를 분리**해 deterministic ranking policy를 설계했다.

---

# 7. Troubleshooting 5 — “지금 신청 가능한”을 LLM에게 맡기지 않기

## 문제

사용자가:

```text
지금 신청 가능한 지원사업을 마감일 가까운 순으로 알려주세요
```

라고 요청해도 현재 날짜 기준 상태와 정렬이 충분히 deterministic하지 않았다.

## 수정

Backend 날짜 로직을 추가했다.

```text
OPEN
UPCOMING
CLOSED
NEEDS_CONFIRMATION
```

정책:

- `Asia/Seoul` 기준 현재 날짜
- 신청 가능 요청에서는 CLOSED / UPCOMING 제외
- OPEN + 고정 마감일은 마감일 오름차순 정렬
- `예산 소진시까지`는 D-day 생성 금지
- 예산 소진 여부가 확인되지 않으면 `NEEDS_CONFIRMATION`

## 결과

Public QA에서 현재 신청 가능 상태와 마감일 정렬이 정상 동작했다.

### 포트폴리오 포인트

시간·금융·자격 같은 검증 가능한 값은 LLM이 아니라 Backend deterministic logic으로 이동했다.

---

# 8. Troubleshooting 6 — “예비창업자 OR 업력 N년”에서 불필요한 질문

## 증상

공고 조건이:

```text
예비창업자 OR 업력 3년 이내 창업자
```

인데 사용자가 이미 예비창업자라고 명시해도 `업력`을 추가 정보로 다시 요구하는 경우가 있었다.

## 원인

추출된 개별 condition을 그대로 나열하면 OR 대안 경로 중 사용하지 않는 branch의 `REQUIRED_USER_VALUE_MISSING`도 사용자에게 노출될 수 있었다.

## 수정

- OR group 표현과 역순 표현 보존
- 하나의 대안 경로가 충족되면 다른 OR branch의 missing value를 LLM context / fallback 준비사항에서 불필요하게 요구하지 않도록 보정
- 공통 AND 조건은 완화하지 않음

## 현재 주의점

Evidence traceability를 위해 structured `condition_results` 내부에는 branch-level `NEEDS_REVIEW`가 남을 수 있다. 중요한 것은 사용자에게 “이미 예비창업 경로를 충족했는데 업력을 필수로 입력하라”고 잘못 안내하지 않는 것이다.

### 포트폴리오 포인트

자연어 공고의 논리구조를 단순 condition list가 아니라 **대안 eligibility path**로 다뤄 잘못된 추가 질문을 줄였다.

---

# 9. Regression Test 확대

QA troubleshooting 과정에서 단순 수동 확인으로 끝내지 않고 회귀 테스트를 단계적으로 추가했다.

```text
189 passed  — QA hardening 전 baseline
215 passed  — incomplete/retry/fallback/general profile/date P0
219 passed  — compact context / regional extraction / OR handling
222 passed  — 긴 질문 profile 일관성 / deterministic regional tier
```

추가된 주요 test 범주:

- Responses API incomplete output 차단
- transient retry / auth·quota no-retry
- safe provider logging
- prompt candidate 3건 제한
- structured fallback
- GENERAL profile extraction
- 지역 scope
- OPEN / UPCOMING / CLOSED / NEEDS_CONFIRMATION
- 신청 가능 filter / deadline sort
- 짧은 질문 vs 긴 질문 profile 동일성
- SAME_REGION / NATIONWIDE / OTHER_REGION_WITH_EXCEPTION ranking
- OR eligibility path

각 단계에서 `git diff --check`도 통과했다.

---

# 10. Public 검증 흐름

Troubleshooting은 로컬 test 통과만으로 종료하지 않았다.

```text
pytest regression
→ Railway 배포 후 Swagger /chat 검증
→ provider timeout / token-limit 로그 확인
```

실제 Public log를 통해:

```text
TIMEOUT
MAX_OUTPUT_TOKENS
```

를 각각 확인했고, 최종 regression 질문에서:

```text
reply_source = LLM
model = gpt-5.6-luna
대구 공고 우선
준비사항 1/2/3
신청기간
공식 출처
문장 절단 없음
```

을 검증했다.

이 과정을 거쳐 AI Chat P0를 `PUBLIC VERIFIED`로 종료했다.

---

# 11. 제출 기획서용 요약 문구

## 버전 A — 짧은 문단

FinBridge는 실제 QA 과정에서 LLM 답변 절단과 fallback, 자연어 사용자 조건 누락, 지역이 다른 지원사업의 잘못된 상위 노출, 신청기간 판단 문제를 발견했다. 이를 단순 프롬프트 수정으로 처리하지 않고, 자연어 프로필 구조화·지역 우선순위·신청상태·자격조건 비교를 Backend의 deterministic logic으로 분리하고 LLM은 검증된 결과의 설명에 집중하도록 개선했다. 또한 LLM 입력 Context를 약 72% 축소하고 incomplete 응답 차단과 fallback을 강화했으며, 222개 회귀 테스트와 Railway Public 재검증을 거쳐 핵심 AI 상담 흐름을 안정화했다.

## 버전 B — 심사자용 핵심 bullet

- 기업마당 실제 공고를 기반으로 사용자 조건을 구조화하고 deterministic matching 수행
- QA에서 발견된 지역 오매칭을 `SAME_REGION → NATIONWIDE → 예외 타지역` 순으로 결정론적 보정
- 신청기간은 한국 시간 기준 `OPEN / UPCOMING / CLOSED / NEEDS_CONFIRMATION`으로 Backend 계산
- LLM Context 약 72% 축소, incomplete / timeout / token-limit 오류에 안전 fallback 적용
- 전체 Backend regression `222 passed`, 핵심 `/chat` 흐름 Railway Public 재검증 완료

## 기획서에서 피할 표현

다음처럼 쓰지 않는다.

```text
AI가 지원 가능 여부를 정확히 판정한다.
모든 지원사업을 완벽하게 매칭한다.
LLM 장애가 발생하지 않는다.
```

대신:

```text
확보된 Evidence와 구조화 가능한 조건을 deterministic하게 비교하고,
근거가 부족한 조건은 추가 확인 필요로 안내한다.
```

처럼 표현한다.

---

# 12. 포트폴리오용 상세 정리

## 프로젝트

**FinBridge — 예비창업자·소상공인·프리랜서를 위한 Evidence 기반 금융 의사결정 지원 서비스**

## 담당 영역

- AI / Backend / Data / Infra
- FastAPI API 설계 및 Railway 배포
- 기업마당 실제 지원사업 데이터 normalization / retrieval
- 비정형 eligibility 구조화 및 deterministic matching
- Risk / Income Stability / Sales Analysis deterministic engine
- OpenAI Responses API orchestration / fallback
- QA 분석 및 production troubleshooting

## 핵심 문제

생성형 AI가 지원사업을 직접 판정하게 하면 지역·업력·신청기간 같은 명확한 조건에서도 일관성이 흔들릴 수 있고, 외부 LLM timeout이나 token limit가 발생하면 전체 사용자 흐름이 무너질 수 있었다.

## 해결 접근

```text
Official Data
→ Snapshot
→ Normalization
→ Eligibility Extraction
→ Deterministic Matching
→ Evidence
→ Deterministic Calculation
→ LLM Explanation
```

LLM을 최종 판정기가 아니라 **검증된 Backend 결과의 설명 계층**으로 제한했다.

## 내가 해결한 production-level 이슈

- Responses API incomplete output 감지 및 partial answer 차단
- timeout / max token 원인을 Railway log로 분리
- LLM prompt context 72% 축소
- retry policy와 deterministic fallback 설계
- 긴 자연어에서도 사용자 region/age/business 상태를 동일하게 추출
- keyword relevance와 지역 자격 적합도를 분리한 deterministic tier ranking
- 한국 시간 기준 신청상태 / 마감일 정렬
- OR eligibility path의 불필요한 추가 질문 제거
- 189 → 222 regression tests 확대
- Local success가 아닌 Railway Public API까지 반복 검증

## 수치로 보여줄 수 있는 결과

```text
Prompt context: 약 72% 감소
Backend tests: 189 → 222 passed
Structured response contract: programs 5 / sources 5 / actions 10 유지
Final Public Chat: reply_source=LLM, gpt-5.6-luna
```

## 포트폴리오 한 문장

> 실제 공공데이터 기반 금융 AI 서비스를 구축하면서 LLM의 검색·판정 의존도를 낮추고, eligibility·지역·날짜·금융계산을 deterministic backend로 분리했으며, Railway production 로그와 222개 회귀 테스트를 기반으로 timeout·token limit·지역 오매칭 문제를 직접 해결했습니다.

---

# 13. 면접에서 설명할 때의 구조

1. **문제**: “로컬 테스트는 통과했지만 Public QA에서 LLM fallback과 지역 오매칭이 발생했습니다.”
2. **관측**: “Railway 로그에서 TIMEOUT과 MAX_OUTPUT_TOKENS를 분리했고, 긴 질문과 짧은 질문의 profile extraction 결과도 비교했습니다.”
3. **설계 판단**: “LLM parameter만 키우지 않고 prompt context를 줄이고, 지역·날짜·자격은 deterministic logic으로 이동했습니다.”
4. **검증**: “회귀 테스트를 189개에서 222개까지 늘리고 매 수정마다 Public API를 재검증했습니다.”
5. **결과**: “최종 복합 질문에서 LLM 응답, 지역 우선순위, Evidence, 다음 행동이 정상 동작했고 P0를 Public Verified로 종료했습니다.”

---

# 14. 아직 남아 있는 개선사항

이 문서는 모든 QA가 종료됐다는 의미가 아니다.

다음은 P1/P2로 유지한다.

- Sales exact duplicate row warning
- Risk positive cashflow / Runway UI 의미 보정
- Income Stability 지표 설명 강화
- 사용자용 error message localization
- Frontend ↔ Backend 실제 연결 후 E2E QA

제출 직전에는 새로운 기술 확장보다 Public URL 안정성, 실제 데이터 연동, 핵심 사용자 흐름 완성도를 우선한다.
