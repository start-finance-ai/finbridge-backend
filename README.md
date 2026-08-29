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
