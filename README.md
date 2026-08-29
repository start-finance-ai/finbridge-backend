# FinBridge Backend

2026 금융 AI Challenge 팀 `start`의 Backend 저장소입니다.

현재 Core Backend baseline은 검증된 기업마당 Raw Snapshot을 읽어 Program을
정규화하고, Eligibility Schema v0.1 기반의 deterministic matching API를
제공합니다. 실제 Raw 공고의 Eligibility Extraction은 아직 구현되지 않았으므로
추출되지 않은 공고를 `MATCH`로 만들지 않습니다.

## 로컬 실행

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

기본 Snapshot은
`data/raw/bizinfo/bizinfo_startup_sample.json`입니다. 필요한 경우
`FINBRIDGE_BIZINFO_SNAPSHOT` 환경변수로 경로만 변경할 수 있습니다.

## API

* `GET /health`
* `GET /programs/{program_id}`
* `POST /programs/match`
* OpenAPI: `GET /docs`

## 테스트

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```
