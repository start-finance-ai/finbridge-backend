# FinBridge Backend

2026 금융 AI Challenge 팀 `start`의 Backend 저장소입니다.

FinBridge는 예비창업자·소상공인·프리랜서가 지원사업을 탐색하고,
자신의 조건과 재무 상황을 확인할 수 있도록 돕는 서비스입니다.
이 저장소는 지원사업 검색·조건 매칭, 재무 계산, 근거 기반 AI 설명을 제공하는
FastAPI 백엔드를 담당합니다.

## 주요 기능

| 기능 | 구현 방식 |
| --- | --- |
| 지원사업 검색 | 기업마당 Snapshot을 정규화하고 조건 필터·정확 일치·키워드로 검색 |
| 지원 조건 매칭 | 명시적인 연령·업력·지역·사업 상태를 규칙으로 비교하고 근거 반환 |
| AI 채팅 | 검색·매칭 결과를 OpenAI Responses API에 전달해 설명 생성 |
| 창업 리스크 계산 | 입력한 비용·매출·자본·대출 조건으로 현금흐름과 상환 부담 계산 |
| 소득 안정성 계산 | 월별 소득 입력을 바탕으로 변동성 지표 계산 |
| 매출장표 분석 | 지원하는 CSV/XLSX 형식의 업로드 파일을 검증하고 매출 지표 계산 |

**판정과 계산은 코드가 수행하고, LLM은 결과를 설명합니다.**
지원 조건 추출은 보수적인 Regex baseline으로 동작합니다. 공고문·별첨 참조나
지원하지 않는 조건이 남으면 `MATCH`로 올리지 않습니다. LLM 장애나 API Key
미설정 시에도 구조화 결과를 유지하고 `TEMPLATE_FALLBACK` 응답을 반환합니다.

기술 구성: Python · FastAPI · Pydantic · OpenAI Responses API · pytest.
데이터는 파일 기반 Snapshot으로 읽으며 런타임 DB를 사용하지 않습니다.

## 로컬 실행

저장소 루트에서 실행합니다. Python 버전은 `.python-version`의 `3.14.3`을
기준으로 합니다.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

서버 실행 후 [API 문서](http://127.0.0.1:8000/docs)에서 요청·응답 Schema와
각 API를 확인할 수 있습니다. 기동 확인은 `GET /health`로 합니다.

OpenAI 설명 기능을 사용하려면 `.env.example`을 참고해 `.env`를 만들거나
서버 환경변수를 설정합니다. 실제 API Key는 Git에 커밋하지 않습니다.
API Key 없이도 기본 Snapshot 검색과 계산, 템플릿 채팅을 사용할 수 있습니다.

## API

| Method | 경로 | 역할 |
| --- | --- | --- |
| GET | `/health` | 서버 상태 확인 |
| GET | `/programs` | 지원사업 검색·필터 |
| GET | `/programs/{program_id}` | 지원사업 상세 조회 |
| POST | `/programs/match` | 사용자 조건과 지원 조건 매칭 |
| POST | `/chat` | 지원사업 탐색·근거 기반 설명 |
| POST | `/risk/calculate` | 창업 리스크 시뮬레이션 |
| POST | `/income-stability/calculate` | 소득 안정성 지표 계산 |
| POST | `/sales-analysis/analyze` | CSV/XLSX 매출장표 분석 (`file` multipart 업로드) |
| GET | `/docs` | Swagger UI / API Schema |

`GET /programs`는 선택적인 `query`, `region`, `business_status`, `user_type`,
`category`, `provider`, `industry`, `limit`을 받습니다. `limit` 기본값은 5,
최대값은 20입니다. 반환되는 `retrieval_score`는 deterministic 검색 순위용
정수이며 Eligibility 확률이나 신청 가능 확률이 아닙니다.

`/chat`은 `mode`(기본 `GENERAL`), `message`, 선택적 `focus_profile`,
`program_id`, `session_id`를 받습니다. 현재는 stateless이며 `session_id`를
저장하지 않습니다. GENERAL의 지원사업 탐색 intent는 위 Retrieval baseline에
연결되며, Semantic Retrieval이나 자유로운 의미 검색은 아직 지원하지 않습니다.

지원 조건 추출 baseline 평가:

```powershell
.venv\Scripts\python.exe scripts\audit_bizinfo_eligibility_baseline.py
```

Risk Calculator는 사용자가 입력한 금리와 원리금균등상환 가정만 사용하는 단순
시뮬레이션입니다. 신용평가나 대출 승인 예측이 아닙니다.

## 테스트

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

## 구현 범위와 한계

- 검색 결과는 선택된 Snapshot의 수집 시점에 따릅니다. 최신 공고·신청 기간·최종 자격은 원문에서 확인해야 합니다.
- 검색 점수와 조건 매칭은 최종 지원 자격, 선정 또는 대출 승인을 보장하지 않습니다.
- 매출장표 분석은 FinBridge가 지원하는 입력 Schema를 사용합니다. 임의 형식의 모든 장표를 해석하는 기능은 아닙니다.
- 재무·소득 계산은 입력값과 계산 가정에 따른 참고 지표입니다.
- 채팅은 stateless이며 서버에 대화 세션을 저장하지 않습니다. 의미 검색·Vector DB는 구현 범위에 포함되지 않습니다.

## 관련 문서

- [프로젝트 기준과 범위](docs/FINANCE_AI_GROUND_TRUTH.md)
- [MVP 기능 범위](docs/FINANCE_AI_MVP_SCOPE.md)
- [구조와 배포 설계](docs/FINANCE_AI_ARCHITECTURE.md)
- [데이터 출처와 사용 범위](docs/DATA_SOURCES.md)
- [개발 상태와 검증 기록](docs/FINANCE_AI_DEV_STATUS.md)

## Railway 배포

현재 Backend 배포 기준은 Railway Hobby + Railpack이며 DB를 사용하지 않습니다.
Config as Code 파일은 사용하지 않고 Railway Dashboard에서 다음 값을 직접 설정합니다.
`.python-version`은 Python `3.14.3`을 고정합니다.

```text
Builder: Railpack
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check: /health
Public Networking: Generate Domain
Database: 없음
Volume: 없음
Docker: 없음
```

Railway Dashboard 설정:

1. `New Project` → `Deploy from GitHub repo`
2. `start-finance-ai/backend` 선택
3. Root Directory가 필요하면 Backend 저장소 루트로 지정
4. Builder를 `Railpack`으로 설정
5. Start Command를 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`로 설정
6. Health Check Path를 `/health`로 설정
7. Variables 설정
8. Public Networking에서 `Generate Domain`
9. 아래 Public smoke 명령 실행

Railpack은 `.python-version`의 버전을 읽지만 Python `3.14.3`의 실제 Railway build는
Public deployment에서 최종 검증합니다. `MISE_PYTHON_COMPILE=1`은 미리 설정하지 않고,
실제 build 실패가 확인될 때만 대응합니다.

### Railway Variables

Railway가 자동 제공하므로 직접 만들지 않는 값:

```text
PORT
```

Frontend 연결 시 필수 설정:

```text
FINBRIDGE_CORS_ORIGINS=https://<final-vercel-domain>
```

권장 Secret 및 설정:

```text
OPENAI_API_KEY=<Railway Secret>
OPENAI_MODEL=gpt-5.6-luna
OPENAI_TIMEOUT_SECONDS=10
```

선택 설정:

```text
BIZINFO_API_KEY=<Collector를 Railway에서 수동 실행할 때만 필요한 Secret>
BIZINFO_TIMEOUT_SECONDS=30
FINBRIDGE_BIZINFO_SNAPSHOT=<별도 Snapshot 경로가 있을 때만 사용>
```

`OPENAI_API_KEY`가 없으면 `/chat`은 Structured Result를 유지하고
`TEMPLATE_FALLBACK`을 반환합니다. `BIZINFO_API_KEY`와 runtime collected 파일도
서버 기동 필수값이 아니며, 기본 서비스 데이터는 Git에 포함된 69건 Bootstrap입니다.
Railway의 로컬 filesystem은 영속 저장소로 가정하지 않습니다.

### Public Domain Smoke — PowerShell

```powershell
$apiBase = "https://<railway-domain>"

Invoke-RestMethod "$apiBase/health"
Invoke-RestMethod "$apiBase/programs?query=$([uri]::EscapeDataString('창업'))"

$chatBody = @{ message = "창업 지원사업을 찾아줘" } | ConvertTo-Json
Invoke-RestMethod "$apiBase/chat" -Method Post -ContentType "application/json" -Body $chatBody

$riskBody = @{
  initial_cost = 30000000
  own_capital = 20000000
  monthly_revenue = 6000000
  monthly_expense = 5000000
  loan_amount = 20000000
  annual_interest_rate = 4.5
  loan_term_months = 60
} | ConvertTo-Json
Invoke-RestMethod "$apiBase/risk/calculate" -Method Post -ContentType "application/json" -Body $riskBody
```

Backend Domain 생성 후 Frontend에는
`VITE_API_BASE_URL=https://<railway-domain>` 형태로 연결하고, 최종 Vercel Origin을
Railway의 `FINBRIDGE_CORS_ORIGINS`에 설정합니다.

Snapshot 선택 순서는 다음과 같습니다.

1. `FINBRIDGE_BIZINFO_SNAPSHOT`으로 명시한 파일
2. 검증을 모두 통과해 `service_ready.json`에 게시된 최신 수집 Snapshot
3. Git으로 배포되는 검증된 69건 Bootstrap인
   `data/bootstrap/bizinfo_startup_bootstrap.json`

런타임 API는 기업마당 외부 API를 호출하지 않습니다. 최신 Snapshot은 운영자가
다음 명령으로만 수동 갱신합니다.

```powershell
$env:BIZINFO_API_KEY="..."
$env:BIZINFO_TIMEOUT_SECONDS="30"
.venv\Scripts\python.exe -m scripts.refresh_bizinfo
```

수집기는 창업(`searchLclasId=06`) 최대 100건을 한 번 요청하고, 응답 원본 bytes를
`data/raw/bizinfo/collected/`에 timestamp 파일로 보존합니다. Raw 구조·필수 ID·중복·
Loader·Normalization 검증을 모두 통과한 경우에만 service-ready manifest를 마지막에
교체합니다. 실패 시 기존 service-ready Snapshot과 baseline을 보존합니다. 수집 파일과
manifest는 `data/raw/` ignore 규칙으로 Git에 포함되지 않습니다.

Bootstrap은 2026-08-29 실제 수집·검증한 69건 Snapshot의 byte-identical 배포
artifact이며 runtime 수집 경로와 분리해 Git 추적할 수 있습니다. 따라서 fresh
deployment도 외부 API Refresh 없이 Program API를 기동할 수 있습니다.

Chat 환경변수는 `.env.example`을 참고해 서버 환경에 설정합니다. Secret은
`.env`에만 두고 Git에 포함하지 않습니다.

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna
OPENAI_TIMEOUT_SECONDS=10
BIZINFO_API_KEY=
BIZINFO_TIMEOUT_SECONDS=30
```
