# FinBridge Final Submission Facts — 2026-09-07

> 목적: 최종 기획서·기능명세서 작성에 사용할 사실 기준 문서.
> 판단 우선순위: 실제 코드·테스트·Public 확인 → `FINANCE_AI_DEV_STATUS.md` → QA 기록 → Ground Truth/Architecture/Data Sources/MVP Scope → 과거 기획·디자인 문서.
> 검증 시각: 2026-09-07 KST. 별도 표기가 없는 `PUBLIC VERIFIED`는 최신 DEV_STATUS와 2026-09-01~05 Public QA 기록을 뜻한다.

## 1. Project Identity

- 팀명: `start`
- 서비스명: `FinBridge`
- 대상: 예비창업자, 소상공인, 프리랜서
- 형태: 모바일 웹 중심 Public Web Service
- 핵심 정의: 실제 지원사업 탐색부터 비정형 자격조건 구조화, 결정론적 매칭, 근거 확인, 금융·리스크 계산, AI 설명, 공식 출처와 다음 행동까지 연결하는 금융 의사결정 지원 서비스
- 현재 단계: Submission Candidate / Code Freeze. 신규 기능보다 최종 Public E2E 확인과 제출 문서 정리가 우선이다.

## 2. Final Public URLs

| 구분 | URL | 최종 상태 | 근거 |
|---|---|---|---|
| Frontend | https://finbridge-start.vercel.app | PUBLIC VERIFIED; 2026-09-07 HTTP 200 재확인 | 최신 DEV_STATUS, `frontend_v2` API 연동 코드, 직접 HTTP 확인 |
| Backend | https://backend-production-1620.up.railway.app | PUBLIC VERIFIED | 최신 DEV_STATUS |
| Health | https://backend-production-1620.up.railway.app/health | 2026-09-07 HTTP 200, `{"status":"ok","service":"FinBridge"}` | 직접 HTTP 확인 |
| Swagger | https://backend-production-1620.up.railway.app/docs | 2026-09-07 HTTP 200 | 직접 HTTP 확인 |
| Programs sanity check | https://backend-production-1620.up.railway.app/programs?limit=1 | 2026-09-07 HTTP 200, 실제 BIZINFO 결과 반환 | 직접 HTTP 확인 |

Frontend는 `frontend_v2/src/api/client.ts`에서 위 Railway URL을 기본 API 주소로 사용한다. 최신 DEV_STATUS는 지원사업 목록·상세, 채팅, 세 분석 도구의 Frontend ↔ Backend 연동을 `PUBLIC VERIFIED`로 기록한다.

## 3. Final Technology Stack

### Frontend

- Repository: `frontend_v2`
- React 19, React DOM 19
- Vite 8.0.5 계열
- TypeScript 5.7 계열
- Tailwind CSS 4 계열
- `react-markdown` 10.1 계열
- pnpm
- Hosting: Vercel
- 2026-09-07 `pnpm build` 재검증 성공: 185 modules transformed

### Backend / AI / Data

- Python 3.14.3
- FastAPI 0.141.1
- Pydantic 2.13.4
- Uvicorn 0.52.1
- pytest 9.1.1
- OpenAI Python SDK 3.6.0
- OpenAI Responses API
- 기본/검증 모델: `gpt-5.6-luna`, reasoning effort `low`
- Hosting: Railway Hobby, Southeast Asia / Singapore
- 데이터 계층: 기업마당 Raw/Bootstrap Snapshot → Normalization → in-memory Repository → Retrieval/Eligibility/Matching
- Database/ORM: MVP에서 의도적으로 사용하지 않음

참고: 코드 기본값의 `OPENAI_MAX_OUTPUT_TOKENS`는 1200이며, 최신 Public P0 검증 당시 production 환경값은 DEV_STATUS/QA 기록상 2000이다. 배포 환경변수의 현재 실값은 코드만으로 열람할 수 없다.

## 4. Final Data Status

- Main Source: 중소벤처기업부 기업마당 지원사업정보 API
- 공식 API endpoint: `https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do`
- 창업 분야 검증 Snapshot/Bootstrap: 69 records, unique ID 69, duplicate 0
- 2026-09-07 로컬 Bootstrap 재확인: `jsonArray` 69건, 고유 `pblancId` 69건, 각 레코드의 `totCnt=69`
- 운영 방식: 사용자 요청마다 외부 API를 호출하지 않고, 수동/일회성 refresh 후 검증 Snapshot을 사용한다.
- fallback 순서: 명시적 `FINBRIDGE_BIZINFO_SNAPSHOT` → 정상 runtime service-ready snapshot → Git 추적 Bootstrap
- 현재 데이터 범위는 기업마당 창업 분야 Snapshot이며, 전체 기업마당 분야 coverage가 아니다.
- Eligibility extraction baseline: `SUPPORTED 22 / NEEDS_REVIEW 46 / UNSUPPORTED 1`
- K-Startup, 상권정보, 정책자금 공식 데이터는 현재 서비스 데이터 소스로 연동하지 않았다.

## 5. Final Implemented Features

| 기능 | Endpoint | 구현 상태 | Public 검증 | 근거 |
|---|---|---|---|---|
| Health Check | `GET /health` | 구현 | 2026-09-07 HTTP 200 | `app/api/health.py`, 직접 확인 |
| 실제 지원사업 조회 | `GET /programs` | 구현 | PUBLIC VERIFIED; 2026-09-07 HTTP 200 sanity check | `app/api/programs.py`, `program_retrieval.py`, DEV_STATUS |
| 지원사업 상세 | `GET /programs/{program_id}` | 구현 | PUBLIC VERIFIED | API/Frontend 상세 코드, DEV_STATUS |
| Eligibility 단건 매칭 | `POST /programs/match` | 구현 | VERIFIED | `matcher.py`, API 및 tests |
| 일반/집중 AI Chat | `POST /chat` | 구현 | PUBLIC VERIFIED | `chat_service.py`, QA, DEV_STATUS |
| `program_id` Chat Context | `POST /chat` | 구현 | PUBLIC VERIFIED | 상세→AI UI, chat tests, DEV_STATUS |
| Template Fallback | `POST /chat` 내부 | 구현 | VERIFIED; Public 회귀에서 LLM 정상 응답도 확인 | provider/fallback/chat tests, QA |
| Risk Calculation | `POST /risk/calculate` | 구현 | PUBLIC VERIFIED | calculation/API/tests, DEV_STATUS |
| Income Stability | `POST /income-stability/calculate` | 구현 | PUBLIC VERIFIED | calculation/API/tests, DEV_STATUS |
| Sales CSV/XLSX Analysis | `POST /sales-analysis/analyze` | 실제 분석 구현, Demo 아님 | PUBLIC VERIFIED | upload/calculation/API/tests, DEV_STATUS |
| Regional Ranking | `/programs`, `/chat` 내부 | 구현 | PUBLIC VERIFIED | retrieval code/tests, QA |
| Application Status / Date Logic | `/programs`, `/chat` 내부 | 구현 | PUBLIC VERIFIED | date parser/retrieval/tests, QA |
| Evidence / Official Source | 프로그램·매칭·채팅 응답 | 구현 | PUBLIC VERIFIED | schemas/services/Frontend, QA |
| Frontend API Integration | 위 API 호출 | 구현 | PUBLIC VERIFIED | `frontend_v2/src/api/client.ts`, DEV_STATUS |

`POST /programs/match`는 Backend에 구현되어 있으나 현재 `frontend_v2`가 별도 화면에서 직접 호출하지는 않는다. 집중모드 `/chat` 내부가 같은 deterministic matcher를 재사용한다.

## 6. AI / Deterministic Role Separation

### AI가 담당하는 역할

- 자연어 질문의 의도와 명시적 사용자 조건 이해 보조
- 검증된 지원사업·매칭·Evidence 결과 설명
- 복잡한 공고 내용을 사용자가 이해하기 쉬운 문장으로 요약
- 추가 확인사항과 다음 행동 설명

### Deterministic Backend가 담당하는 역할

- Snapshot 내 지원사업 검색, 정렬, Top-N
- 명시적 자연어 프로필 추출과 조건 비교
- Eligibility match 상태 집계
- 지역 tier ranking
- 신청기간 및 `OPEN / UPCOMING / CLOSED / NEEDS_CONFIRMATION` 계산
- 원리금균등 월 상환액, 현금흐름, cash burn, runway, 잔존채무 계산
- 6개월 소득 통계
- CSV/XLSX 매출 수치 검증·집계·통계

LLM이 지원사업의 존재, 지원금, 신청기간, 공식 URL, 자격상태, 대출금리 또는 금융수치를 생성·계산한다고 표현하지 않는다.

## 7. Eligibility / Matching

- 기업마당 비정형 원문에서 AGE, BUSINESS_AGE, REGION, PRE_FOUNDER, BUSINESS_REGISTRATION_STATUS와 안전한 OR 경로를 구조화한다.
- Boolean 구조는 `common_conditions AND (eligibility_group_1 OR ...) AND NOT global_exclusions`다.
- 결과 상태는 `MATCH / NO_MATCH / NEEDS_REVIEW / UNKNOWN`이다.
- 사용자 입력 부족은 곧바로 `NO_MATCH`로 처리하지 않는다.
- Evidence가 부족한 조건은 안전한 `MATCH`로 승격하지 않는다.
- 전체 공고문·별첨의 모든 조건을 완전 구조화한 것은 아니다.
- Retrieval score는 검색 순위 점수이며 자격 확률이나 신청 가능 확률이 아니다.

## 8. Risk Calculation

- 입력: 초기비용, 자기자본, 월매출, 월지출, 대출금액, 연이율, 대출기간(개월)
- 상환 방식: 원리금균등상환 1종
- 출력: 초기 가용 현금, 월 원리금, 월 현금흐름, cash burn, runway, runway 시점 잔존채무
- Decimal 및 `ROUND_HALF_UP`을 사용하며 반올림은 응답 단계에서 적용한다.
- 세금, 수수료, 변동금리, 연체, 추가차입은 계산 범위 밖이다.
- 금융기관 신용평가·대출 승인 예측이 아닌 입력 기반 참고 시뮬레이션이다.

## 9. Income Stability

- 정확히 최근 6개월 소득을 입력한다.
- 평균, 모집단 표준편차, 변동계수(CV), 최솟값, 최댓값을 deterministic하게 계산한다.
- 0은 허용하고 음수·잘못된 타입·5개월/7개월 입력은 거부한다.
- 평균이 0이면 CV는 `null`이다.
- 임의의 안정/불안정 threshold를 만들지 않으며, 금융기관 소득인정·신용평가·상환능력 판정이 아니다.

## 10. Sales CSV/XLSX Analysis

- 실제 CSV/XLSX multipart upload와 Backend 분석이 구현됐다. `is_demo=false` 계약을 사용한다.
- 파일 제한: `.csv` 또는 `.xlsx`, 최대 5MB, 최대 50,000 data rows
- CSV 인코딩: UTF-8/UTF-8-SIG/CP949 지원
- 필수 개념: 거래일자와 매출액. 한글 alias를 지원한다.
- 결과: 월별 매출/거래수, 총매출, 평균 월매출, 최신·최고·최저 월, 최근 3개월 대 이전 3개월 trend, 모집단 표준편차/CV, MoM, data quality, warnings
- 결측 월을 임의로 0으로 채우지 않는다.
- 음수 매출은 환불 모델 미지원으로 오류 처리한다.
- 원본 업로드 파일을 영구 저장하지 않고 LLM을 사용하지 않는다.
- 잔여 P1: 동일 거래의 exact duplicate row warning은 미구현이다.

## 11. Chat / Fallback

- 모드: `GENERAL`, `FOCUS`
- 선택 입력: `focus_profile`, `program_id`, `session_id`; 현재 Frontend는 `session_id=null`을 보내며 대화 서버 영속 저장은 하지 않는다.
- 응답: `reply`, `reply_source`, `model`, `programs`, `matches`, `evidence`, `sources`, `actions`, `suggest_focus_mode`, `program_context_id`
- LLM 성공 시 `reply_source=LLM`, Provider 실패 시 `reply_source=TEMPLATE_FALLBACK`
- Fallback도 후보, 확인 조건, 신청기간/상태, 확보된 신청방법, 공식 출처, 준비사항 1/2/3을 deterministic 결과에서 구성한다.
- incomplete partial output은 사용자에게 노출하지 않는다.
- timeout/rate/server 계열은 최대 1회 재시도하고, auth/quota/config/incomplete는 불필요하게 재시도하지 않는다.
- 최종 Public 복합 회귀에서 `reply_source=LLM`, `model=gpt-5.6-luna`, 문장 절단 없음, 대구 공고 우선, 준비사항·신청기간·공식 출처 출력을 확인했다.

## 12. QA → Code Improvement → Regression

| QA 문제 | 수정 내용 | 재검증 결과 |
|---|---|---|
| 긴 답변 문장 절단, timeout/max token으로 fallback 반복 | Responses API `status/incomplete_details` 검사, partial 차단, retry 정책 분리, production timeout 30초, token budget 조정 | Public 복합 질문에서 LLM 답변·모델 확인, 문장 절단 없음 |
| Prompt가 5개 후보의 전체 HTML·중복 근거를 포함 | LLM 상세 후보 3건, 최소 필드 context로 축소; structured API의 programs 5/sources 5/actions 10은 유지 | Context 10,786→2,982 chars, 약 72% 감소; Public 정상 응답 |
| Fallback이 짧고 행동 가능한 정보 부족 | deterministic 결과로 후보·조건·기간·출처·준비사항 1/2/3 구성 | Provider 장애 시에도 structured 결과와 유용한 안내 유지 |
| 일반모드 긴 문장에서 지역·나이·예비창업·미등록 조건 누락 | 명시적 패턴 기반 `query_understanding.py` 보강 | 짧은/긴 동의 질문이 동일 structured profile을 생성하는 회귀 테스트 통과 |
| 대구 사용자에게 울산·전남·안산 등 타지역 공고가 상위 노출 | `SAME_REGION → NATIONWIDE → 예외 타지역 → 지역 미상` tier, 타지역 전용 제외 | Public에서 대구 2건 후 전국 1건 순 확인 |
| “지금 신청 가능한”의 현재 상태/마감 정렬 부족 | Asia/Seoul 기준 상태 계산, CLOSED/UPCOMING 제외, 고정 마감 OPEN 오름차순 | Public QA와 date/retrieval tests 통과 |
| OR 조건의 충족하지 않아도 되는 branch를 추가 질문 | OR group 보존, 충족 경로가 있으면 다른 branch의 missing value 안내 억제 | 관련 matcher/chat regression 통과 |
| CSV/XLSX 잘못된 입력·결측 처리 위험 | 형식/크기/행/컬럼/날짜/금액 검증, 결측 월 명시, 음수 거부 | 정상 CSV/XLSX와 오류 케이스 tests 및 Public 분석 검증 |

## 13. Test / QA Evidence

- 2026-09-07 로컬 Backend 전체 regression 재실행: `222 passed in 7.25s`
- QA progression: `189 → 215 → 219 → 222 passed`
- 2026-09-07 Frontend production build 재실행: 성공, 185 modules transformed
- 2026-09-07 Public GET 확인: Frontend 200, Backend health 200, programs 200, docs 200
- 최신 문서 기준 Public 검증: Chat, regional ranking, application status, risk, income stability, sales upload/analysis, Frontend ↔ Backend integration
- 이번 작성 과정에서는 Public POST 전체를 다시 실행하지 않았다. 해당 표기의 최신 근거는 2026-09-01~05 QA/DEV_STATUS다.

## 14. Security / Privacy

- OpenAI/Bizinfo API key는 환경변수와 배포 Secret으로 관리하며 `.env`는 Git에서 제외한다.
- Secret literal을 소스·문서에 기록하지 않는다.
- CORS는 exact origin 목록을 사용하고 wildcard `*`를 거부한다. credentialed CORS는 사용하지 않는다.
- Provider 안전 로그에는 error class/reason만 남기며 사용자 prompt나 provider message 전체를 기록하지 않는다.
- 업로드 매출 파일은 영구 저장하지 않는다.
- 사용자 프로필·대화·금융입력을 위한 DB 영속 저장과 Auth backend는 구현하지 않았다.

## 15. Not Implemented / Do Not Claim

- Database/ORM/PostgreSQL, 서버 영속 세션
- Auth/Login/Signup backend 및 Public flow
- Vector DB, Graph DB, Embedding/Semantic Retrieval, Multi-Agent
- K-Startup 추가 API, 상권정보 API, 정책자금 공식 데이터 자동 연동
- Scheduler/Cron/Celery 기반 자동 refresh
- 전체 기업마당 분야와 전체 공고·별첨 Eligibility의 완전 구조화
- 범용 회계파일 parser, 환불/음수 매출 모델, exact duplicate warning
- 실제 지원사업 신청/자동 제출, 실제 대출 신청, 대출 승인 예측, 금융기관 신용평가
- 장기 대화/프로필/찜의 서버 저장

## 16. Submission-safe Wording

권장:

- “기업마당 실제 지원사업 Snapshot을 기반으로 검색·매칭한다.”
- “확보된 Evidence와 구조화 가능한 조건을 deterministic하게 비교하고, 부족한 근거는 추가 확인 필요로 안내한다.”
- “LLM은 검증된 결과를 설명하며, 자격·날짜·금융수치는 Backend가 처리한다.”
- “Risk Calculator는 사용자 입력을 바탕으로 한 참고용 재무 시뮬레이션이다.”
- “CSV/XLSX 파일을 Backend가 직접 검증·집계하며 업로드 파일은 영구 저장하지 않는다.”

금지:

- “AI가 모든 지원사업을 완벽하게 추천하고 자격을 보장한다.”
- “대출 승인 가능성 또는 신용도를 판정한다.”
- “K-Startup·상권·정책자금·DB·Vector DB·Graph DB·Multi-Agent를 사용한다.”
- “전체 기업마당 데이터를 실시간 자동 갱신한다.”
- “LLM이 지원금·신청기간·금융수치를 계산하거나 생성한다.”

## 17. Facts Needing Final Human Check

1. 공식 Challenge 공지의 최종 제출 마감시각과 제출 양식 최신본.
2. 제출 직전 브라우저에서 일반/집중 Chat, 상세→AI, Risk, Income, CSV/XLSX까지 한 번씩 최종 Public E2E 확인.
3. Railway production 환경의 실제 `OPENAI_MODEL`, token/timeout, CORS origin 값이 제출 후보 설정과 같은지 확인.
4. 2026-08-29 기준 69건 Bootstrap을 그대로 제출할지, 안전한 수동 refresh 후 최신 Snapshot으로 교체할지 팀 결정.
5. 요청 우선순위에 적힌 “Backend QA Developer Handoff”와 “Frontend API QA Handoff” 파일은 현재 세 저장소에서 발견되지 않았으므로, 외부 공유본이 있다면 마지막 대조 필요.

### 핵심 Source 경로

- `backend/docs/FINANCE_AI_DEV_STATUS.md`
- `backend/docs/FinBridge_QA_TROUBLESHOOTING_2026-09-01.md`
- `backend/app/`, `backend/tests/`, `backend/data/bootstrap/bizinfo_startup_bootstrap.json`
- `frontend_v2/src/`, `frontend_v2/package.json`
- `backend/docs/FINANCE_AI_GROUND_TRUTH.md`
- `backend/docs/FINANCE_AI_ARCHITECTURE.md`
- `backend/docs/DATA_SOURCES.md`
- `backend/docs/FINANCE_AI_MVP_SCOPE.md`
- Git HEAD에만 존재하고 작업트리에서는 삭제 상태인 `backend/docs/design/0829_FinBridge_UI_Backend_연동_디자인핸드오프_v1.md`
