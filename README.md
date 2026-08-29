# FinBridge Backend

2026 금융 AI Challenge 팀 `start`의 Backend 저장소입니다.

현재 Core Backend baseline은 검증된 기업마당 Raw Snapshot을 읽어 Program을
정규화하고, Eligibility Schema v0.1 기반의 deterministic matching API를
제공합니다. 실제 Raw 20건에는 명시적인 숫자 연령·업력·지역·사업 상태만
Evidence와 함께 구조화하는 보수적인 Regex baseline을 적용합니다. 공고문·별첨
참조나 지원하지 않는 조건이 남으면 `MATCH`로 올리지 않습니다.

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
* `POST /risk/calculate`
* OpenAPI: `GET /docs`

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
