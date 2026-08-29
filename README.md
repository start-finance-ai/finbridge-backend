# FinBridge Backend

2026 금융 AI Challenge 팀 `start`의 Backend 저장소입니다.

현재 Core Backend baseline은 검증된 기업마당 Raw Snapshot을 읽어 Program을
정규화하고, Eligibility Schema v0.1 기반의 deterministic matching API를
제공합니다. Eligibility Extractor는 명시적인 숫자 연령·업력·지역·사업 상태만
Evidence와 함께 구조화하는 보수적인 Regex baseline을 적용합니다. 공고문·별첨
참조나 지원하지 않는 조건이 남으면 `MATCH`로 올리지 않습니다.

`POST /chat`은 이 구조화된 Program·Matching·Evidence를 OpenAI Responses API에
전달해 설명 문장을 생성합니다. LLM은 자격 판정이나 금융 계산을 수행하지 않으며,
Provider 장애 시에도 구조화 결과를 유지하고 deterministic template을 반환합니다.
GENERAL 지원사업 탐색 질문은 선택된 Snapshot에 대해 Structured / Exact /
Keyword Retrieval을 먼저 수행하고 Top-5만 Chat context로 전달합니다.

## 로컬 실행

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

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

## API

* `GET /health`
* `GET /programs`
* `GET /programs/{program_id}`
* `POST /programs/match`
* `POST /risk/calculate`
* `POST /chat`
* OpenAPI: `GET /docs`

`GET /programs`는 선택적인 `query`, `region`, `business_status`, `user_type`,
`category`, `provider`, `industry`, `limit`을 받습니다. `limit` 기본값은 5,
최대값은 20입니다. 반환되는 `retrieval_score`는 deterministic 검색 순위용
정수이며 Eligibility 확률이나 신청 가능 확률이 아닙니다.

`/chat`은 `mode`(기본 `GENERAL`), `message`, 선택적 `focus_profile`,
`program_id`, `session_id`를 받습니다. 현재는 stateless이며 `session_id`를
저장하지 않습니다. GENERAL의 지원사업 탐색 intent는 위 Retrieval baseline에
연결되며, Semantic Retrieval이나 자유로운 의미 검색은 아직 지원하지 않습니다.

Eligibility baseline 감사:

```powershell
.venv\Scripts\python.exe scripts\audit_bizinfo_eligibility_baseline.py
```

Risk Calculator는 사용자가 입력한 금리와 원리금균등상환 가정만 사용하는 단순
시뮬레이션입니다. 신용평가나 대출 승인 예측이 아닙니다.

## 테스트

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```
