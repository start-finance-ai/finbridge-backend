# 설치·실행 및 운영 가이드

[메인 README로 돌아가기](../README.md)

로컬 설치, 데모 호출, 환경변수, 데이터 갱신, 테스트 실행과 재배포 절차를 모았습니다. 기능과 구현 구조는 [메인 README](../README.md)를 참고하세요. 아래 PowerShell 명령은 clone 및 폴더 이동 이후 저장소 루트에서 실행합니다.

## 빠른 시작

### 설치와 실행 — PowerShell

[`.python-version`](../.python-version)에 지정한 Python `3.14.3`을 기준으로 저장소 루트에서 실행합니다.

```powershell
git clone https://github.com/start-finance-ai/finbridge-backend.git
Set-Location finbridge-backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API 문서는 `http://127.0.0.1:8000/docs`, 상태 확인은 `GET /health`입니다. 루트 `/`에는 별도 라우트가 없어 404가 정상입니다. 기본 데모를 사용하면 기업마당·OpenAI Key가 필요하지 않습니다.

### 데모 검색·매칭·설명

서버를 실행한 상태에서 다른 PowerShell 창에 입력합니다.

```powershell
$apiBase = "http://127.0.0.1:8000"
Invoke-RestMethod "$apiBase/health"
Invoke-RestMethod "$apiBase/programs?query=$([uri]::EscapeDataString('창업'))"

$profile = @{ region = "대구"; business_region = "대구"; age = 28; pre_founder = $true }
$matchBody = @{ program_id = "DEMO_002"; profile = $profile } | ConvertTo-Json -Depth 5
Invoke-RestMethod "$apiBase/programs/match" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($matchBody))

$chatBody = @{
    mode = "FOCUS"
    program_id = "DEMO_002"
    focus_profile = $profile
    message = "이 사업의 조건과 확인할 사항을 설명해줘"
} | ConvertTo-Json -Depth 5
Invoke-RestMethod "$apiBase/chat" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($chatBody))
```

매칭 응답의 핵심 값은 다음과 같습니다. 전체 응답에는 사업 정보와 조건별 근거도 포함됩니다.

```json
{
  "match_status": "MATCH",
  "reason": "ELIGIBILITY_PATH_SATISFIED"
}
```

OpenAI Key가 없으면 채팅의 `reply_source`는 `TEMPLATE_FALLBACK`입니다. 실제 설명 생성을 사용하려면 `.env.example`을 `.env`로 복사하고 `OPENAI_API_KEY`를 설정합니다. Key는 Git에 커밋하지 않습니다. 환경변수가 `.env`보다 우선하며, 실제 모델 호출에는 비용이 발생할 수 있습니다.

## 환경변수

| 환경변수 | 기본값·역할 |
| --- | --- |
| `OPENAI_API_KEY` | Secret. 미설정 시 템플릿 폴백 |
| `OPENAI_MODEL` | `gpt-5.6-luna` |
| `OPENAI_TIMEOUT_SECONDS` | `30`; 단일 요청 timeout, 재시도로 총 지연이 늘어날 수 있음 |
| `OPENAI_MAX_OUTPUT_TOKENS` | `1200` |
| `FINBRIDGE_CORS_ORIGINS` | `http://localhost:8443`; 쉼표로 구분한 정확한 Origin, `*` 거부 |
| `FINBRIDGE_BIZINFO_SNAPSHOT` | 선택적 비공개 Snapshot 경로; 프로세스 환경변수로 설정 |
| `BIZINFO_API_KEY` | 수동 수집용 Secret, 서버 기동 필수값 아님 |
| `BIZINFO_TIMEOUT_SECONDS` | `30`; 수집 요청 timeout |

로컬에서는 저장소 루트의 `.env.example`을 `.env`로 복사해 필요한 값을 설정합니다. `FINBRIDGE_BIZINFO_SNAPSHOT`은 프로세스 환경변수로 설정합니다. 배포 시에는 호스팅 서비스의 Variables/Secrets를 사용합니다.

## 데이터 선택과 수동 갱신

기본 데이터는 API Key 없이 사용할 수 있는 합성 데모 6건입니다. Snapshot 선택 순서와 검증·게시 방식은 [README의 데이터 처리 구조](../README.md#데이터-처리-구조)를 참고하세요.

허가된 실데이터를 직접 지정하는 예:

```powershell
$env:FINBRIDGE_BIZINFO_SNAPSHOT = "C:\private-data\bizinfo_snapshot.json"
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

런타임 검색·매칭 API는 기업마당 외부 API를 호출하지 않습니다. 이용조건을 확인한 후 수집기로 별도 갱신합니다.

```powershell
# BIZINFO_API_KEY는 로컬 .env 또는 프로세스 환경변수에 설정
.venv\Scripts\python.exe -m scripts.refresh_bizinfo
```

수집 결과는 `data/raw/bizinfo/collected/`에 저장되며 Git에 포함되지 않습니다. 갱신된 Snapshot을 서비스에 반영하려면 애플리케이션을 다시 기동해야 합니다. 명시한 Snapshot이 잘못되면 503을 반환하며 다른 데이터로 대체하지 않습니다.

출처·이용 범위는 [DATA_SOURCES](DATA_SOURCES.md), 데모 구성은 [data/demo/README](../data/demo/README.md)를 확인하세요. 기존 20건 테스트 입력, 69건 Bootstrap, 48행 Review CSV는 공개 저장소에 포함하지 않습니다.

## 테스트와 평가 실행

### 기본 테스트

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

공개 기본 실행에서는 비공개 원본 의존 테스트가 명시적으로 `SKIPPED`이므로 pass/skip 수를 함께 확인합니다. 검증 대상과 과거 결과의 해석 범위는 [README의 테스트와 평가](../README.md#테스트와-평가)를 참고하세요.

### 비공개 입력을 사용하는 회귀 테스트

기존 실데이터 회귀 테스트를 재현하려면 별도로 보관한 입력을 지정합니다.

```powershell
$env:FINBRIDGE_TEST_SNAPSHOT = "C:\private-data\bizinfo_startup_sample_20.json"
$env:FINBRIDGE_TEST_BOOTSTRAP = "C:\private-data\bizinfo_startup_bootstrap.json"
.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

### 조건 추출 점검과 Review Pack 평가

```powershell
.venv\Scripts\python.exe scripts\audit_bizinfo_eligibility_baseline.py
.venv\Scripts\python.exe -m scripts.evaluate_bizinfo_review_pack --input "C:\private-data\bizinfo_eligibility_review_48.csv"
```

Review Pack 평가는 별도로 보관한 48행 입력 CSV가 필요합니다. 조건 추출·표현 범위에 대한 검증과 실제 지원 자격의 정확도는 구분합니다.

## 배포 설정

현재 문서의 재현 기준은 로컬 데모 실행입니다. 기존 Railway/Vercel 배포는 중지되어 있으며, 아래는 새 저장소로 재배포할 때 사용할 설정입니다.

```text
Repository: start-finance-ai/finbridge-backend
Builder: Railpack
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check: /health
Database / Volume / Docker: 사용하지 않음
```

Railway Dashboard에서 저장소 루트·Builder·Start Command·Health Check·Variables를 설정하고 Public Networking Domain을 생성합니다. `PORT`는 Railway가 제공하므로 직접 만들지 않습니다. `.python-version`의 Python 버전에 대한 실제 호스팅 빌드 호환성은 재배포 시 확인합니다.

Frontend의 `VITE_API_BASE_URL`에는 Backend Domain을 설정하고, Backend의 `FINBRIDGE_CORS_ORIGINS`에는 실제 Frontend Origin을 지정합니다. CORS 기본값은 Vite 기본 포트와 다를 수 있으므로 로컬 Frontend의 Origin도 명시적으로 맞춥니다.

배포 후에는 [데모 검색·매칭·설명](#데모-검색매칭설명)의 `$apiBase`를 실제 Domain으로 바꾸어 `/health`, `/programs`, `/programs/match`, `/chat`을 확인합니다. DB/Volume 없는 환경에서 로컬 파일의 영속성을 가정하지 않으며, 재시작·재배포 후 비공개 Snapshot의 존재 여부와 선택 경로를 확인해야 합니다. 외부 Snapshot이 없으면 기본 데모를 사용합니다.
