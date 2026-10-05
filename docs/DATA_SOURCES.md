# FINANCE AI — Data Sources

## 공개본의 데이터 구분

기본 입력 `data/demo/finbridge_demo.json`은 직접 작성한 합성 예제 6건이며
`source=DEMO`로 구분한다. 실제 공고, 모집기관, 신청 링크, 문의처를 제공하지 않는다.
기업마당 수집·정규화 코드는 유지하되 응답 원문, 20건 실데이터 fixture,
48행 Human Review Pack은 공개본에 포함하지 않는다. 실데이터는 제공기관의
이용조건을 확인한 후 비공개 파일로 지정해 사용한다.

아래의 수집·검증 상태는 당시 MVP의 실데이터 작업 기록이다. 합성 예제로
해당 실데이터 평가 성능을 재현했다고 해석하지 않는다.

Last Updated: 2026-08-29

이 문서는 2026 금융 AI Challenge MVP에서 실제로 사용할 외부 데이터와 사용자 입력 데이터의 검증 상태를 관리한다.

데이터는 이름이나 설명만 보고 사용 가능하다고 판단하지 않는다.

각 외부 데이터는 가능한 범위에서 다음을 확인한다.

* 공식 제공기관
* 실제 접근 가능 여부
* 데이터 형식
* 실제 Response Schema
* 주요 필드
* 이용조건
* 갱신주기
* 기준일
* MVP 활용 목적
* 실제 API 호출 또는 파일 다운로드 성공 여부

검증되지 않은 데이터를 실제 서비스 데이터인 것처럼 사용하지 않는다.

데이터에 존재하지 않는 값은 LLM 또는 임의 규칙으로 생성하여 채우지 않는다.

# 1. Status Definition

## VERIFIED

실제 API 호출 또는 파일 접근을 완료하고 Response 및 필요한 주요 필드까지 확인한 상태.

## OFFICIAL_FOUND

공식 데이터와 명세의 존재는 확인했지만 실제 API 호출 또는 파일 검증은 아직 완료하지 않은 상태.

## INVESTIGATING

후보 데이터이나 실제 접근성, 이용조건, Schema 또는 MVP 활용 가능성을 추가 조사해야 하는 상태.

## PARTIALLY_COVERED

다른 공식 Source에서 일부 범위가 이미 제공되어 별도 Source 추가 필요성을 검토하는 상태.

## PLANNED

사용자 입력 또는 내부 데이터 구조처럼 구현 예정이나 최종 Schema가 아직 확정되지 않은 상태.

## OPTIONAL

MVP 핵심 범위는 아니며 MUST 기능이 완료된 이후 일정에 따라 구현할 수 있는 상태.

## REJECTED

접근성, 이용조건, 데이터 품질, 필요한 필드 부재 또는 MVP 적합성 문제로 제외한 상태.

# 2. DS-001 기업마당 지원사업정보 API

Status: VERIFIED

## Provider

중소벤처기업부 기업마당

## Source

기업마당 정책정보 개방 — 지원사업정보 API

## Purpose

MVP의 핵심 지원사업 Main Data Source.

다음 사용자에게 관련된 지원사업 탐색에 활용한다.

* 예비창업자
* 소상공인
* 프리랜서 중 개별 공고의 지원조건에 해당하는 사용자

## Official API

Method:

GET

지원 데이터 형식:

* JSON
* XML

서비스 인증키가 필요하다.

인증키는 환경변수 등 Secret 관리 방식으로만 사용하고 Git에 저장하지 않는다.

## Officially Confirmed Request Parameters

공식 명세에서 다음 요청 Parameter가 확인되었다.

* `crtfcKey`: 서비스 인증키
* `dataType`: 데이터 형식
* `searchCnt`: 조회건수
* `searchLclasId`: 지원분야
* `hashtags`: 해시태그
* `pageUnit`: 페이지당 데이터 개수
* `pageIndex`: 페이지번호

### 지원분야 코드

* 01: 금융
* 02: 기술
* 03: 인력
* 04: 수출
* 05: 내수
* 06: 창업
* 07: 경영
* 09: 기타

### 공식 해시태그 예

분야:

* 금융
* 기술
* 인력
* 수출
* 내수
* 창업
* 경영
* 기타

지역:

* 서울
* 부산
* 대구
* 인천
* 전남광주
* 대전
* 울산
* 세종
* 경기
* 강원
* 충북
* 충남
* 전북
* 경북
* 경남
* 제주

주의:

해시태그가 특정 지역을 포함한다는 이유만으로 해당 지역 사용자가 최종 신청 가능하다고 판정하지 않는다.

해시태그는 후보 검색 또는 Recall 향상을 위한 정보로 활용하고 최종 자격 Evidence로 단독 사용하지 않는다.

## Verification Result — 2026-08-28

[EXPERIMENT]

기업마당 지원사업정보 API의 실제 호출 및 JSON 구조 검증을 완료했다.

### API Call Result

* HTTP Status: 200
* `dataType`: json
* `searchLclasId`: 06
* 조회 분야: 창업
* `searchCnt`: 20
* 실제 Response Item: 20건
* Sample Response 기준 `totCnt`: 71
* Raw JSON 저장 완료

Raw Data:

`data/raw/bizinfo/bizinfo_startup_sample.json`

Raw 데이터는 가공 전 원본 Snapshot으로 유지한다.

## Service Snapshot Refresh Verification — 2026-08-29

[EXPERIMENT / IMPLEMENTED]

MVP 서비스가 사용할 최신 기업마당 Snapshot을 운영자가 안전하게 갱신하는 수동
Collector를 구현하고 실제 호출 1회로 검증했다.

### Request and Result

* Method: GET
* Endpoint: `https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do`
* `dataType`: json
* `searchLclasId`: 06 (창업)
* `searchCnt`: 100
* HTTP Status: 200
* 실제 Raw Item: 69건
* 고유 `pblancId`: 69건
* 중복 `pblancId`: 0건
* Response `totCnt`: 69
* Collector 종료 코드: 0
* 수집 시각: `2026-08-29T09:40:30.949819+00:00`

Raw Evidence:

`data/raw/bizinfo/collected/bizinfo_startup_20260829T094030949819Z.json`

서버 응답 bytes는 재직렬화하지 않고 timestamp 파일에 그대로 저장했다. 기존 20건
baseline은 변경하지 않았다. 인증키와 인증키가 포함된 전체 URL은 로그·metadata에
기록하지 않았고, runtime 수집 산출물은 `data/raw/` ignore 규칙 적용을 확인했다.
현재 baseline 역시 `data/raw/` 규칙으로 Git에서 추적되지 않는 로컬 Evidence이므로,
새 배포 환경을 위해 아래의 별도 Bootstrap artifact를 사용한다.

### Service-ready Validation

* 최상위 object / non-empty `jsonArray`: 통과
* `pblancId` / `pblancNm` 필수값: 통과
* 중복 ID 검사: 통과
* 기존 Loader: 69건 로딩 성공
* Program Normalization: 69건 성공
* service-ready manifest 게시: 성공
* 기본 Snapshot resolver가 신규 Snapshot 선택: 확인

동일 Snapshot에 현재 Eligibility Extractor를 적용한 상태 분포는
`SUPPORTED` 22건, `NEEDS_REVIEW` 46건, `UNSUPPORTED` 1건이다. 이는 수집 또는
Normalization 실패가 아니라 현재 보수적 Extractor의 지원 범위를 나타낸다.
`청년` keyword retrieval은 9건을 반환하고 모두 `BIZINFO` Source임을 확인했다.

이 검증은 2026-08-29 시점 창업 분야의 단일 Snapshot에 한정된다. 기업마당 전체
분야 Coverage, 실시간 동기화, 자동 갱신, Eligibility 완전성을 의미하지 않는다.
응답 69건은 `searchCnt=100`보다 작지만 `totCnt=69`이므로 정상 결과로 처리했다.

### Tracked Bootstrap Snapshot — 2026-08-29

[IMPLEMENTED / VERIFIED]

위 service-ready Raw Snapshot과 byte-identical한 배포용 artifact를 다음 경로로
분리했다.

`data/bootstrap/bizinfo_startup_bootstrap.json`

* Record: 69건
* 고유 `pblancId`: 69건
* Duplicate: 0건
* SHA-256: `c82b3bf76c78a7daec5ac6a0bb1f16a824a5daf5b98f85a150899d1463b25bd4`
* Loader / Normalization: 69건 성공
* API Key·인증 Parameter·Authorization 값: 없음
* 사용자 입력 또는 민감 금융정보: 없음

공식 공고 원문 필드인 `refrncNm`에는 공개된 사업 문의 전화번호·이메일이 포함될 수
있다. 이는 사용자 Profile이나 비공개 개인정보가 아니라 기업마당이 공개한 공고
연락처이며, Bootstrap은 원본 Evidence 보존을 위해 이를 변경하지 않는다.

Runtime timestamp Snapshot·metadata·manifest는 계속 Git에서 제외한다. Bootstrap은
자동 최신화나 전체 Coverage를 의미하지 않으며, 운영자가 수동 Refresh를 검증한 뒤
별도 변경으로 갱신해야 한다.

## Confirmed JSON Structure

실제 응답은 다음 구조로 확인되었다.

```text
jsonArray
└─ 지원사업 Object
   ├─ trgetNm
   ├─ updtPnttm
   ├─ hashtags
   ├─ inqireCo
   ├─ creatPnttm
   ├─ pblancNm
   ├─ pblancId
   ├─ printFlpthNm
   ├─ refrncNm
   ├─ pblancUrl
   ├─ jrsdInsttNm
   ├─ excInsttNm
   ├─ totCnt
   ├─ reqstMthPapersCn
   ├─ pldirSportRealmLclasCodeNm
   ├─ reqstBeginEndDe
   ├─ bsnsSumryCn
   ├─ pldirSportRealmMlsfcCodeNm
   └─ printFileNm
```

## Confirmed Response Fields

### Identity / Basic Information

* `pblancId`: 공고 ID
* `pblancNm`: 공고명
* `jrsdInsttNm`: 소관기관
* `excInsttNm`: 수행기관

### Classification

* `pldirSportRealmLclasCodeNm`: 지원분야 대분류
* `pldirSportRealmMlsfcCodeNm`: 지원분야 중분류
* `trgetNm`: 지원대상 대분류
* `hashtags`: 해시태그

### Date / Update

* `creatPnttm`: 등록일
* `updtPnttm`: 수정일
* `reqstBeginEndDe`: 신청기간

### Description / Eligibility Candidate

* `bsnsSumryCn`: 사업개요 및 주요 지원대상·지원내용
* `reqstMthPapersCn`: 신청방법
* `refrncNm`: 문의처

### Evidence / Source

* `pblancUrl`: 기업마당 상세공고 URL
* `printFlpthNm`: 본문 또는 공고문 파일 경로
* `printFileNm`: 본문 또는 공고문 파일명

### Other

* `inqireCo`: 조회수
* `totCnt`: 조회 결과 전체 건수

## Important Finding 1 — Structured Fields

다음 정보는 비교적 명확하게 구조화되어 있어 RDB 또는 Structured Retrieval에 직접 활용하기 적합하다.

* 공고 ID
* 공고명
* 소관기관
* 수행기관
* 지원분야 대분류
* 지원분야 중분류
* 등록일
* 수정일
* 상세공고 URL
* 공고문 파일 경로
* 공고문 파일명

## Important Finding 2 — `trgetNm`의 한계

`trgetNm`은 실제 Sample에서 다음과 같은 비교적 큰 범주로 제공되었다.

예:

* 창업벤처
* 여성기업

따라서 `trgetNm` 하나만으로 사용자의 세부 지원자격을 판정할 수 없다.

세부 자격조건은 `bsnsSumryCn` 또는 원문 공고에서 추가 확인해야 한다.

## Important Finding 3 — `hashtags`의 한계

`hashtags`에는 분야, 지역, 기관, 연도, 사용자 유형, 창업 업력 등 다양한 Keyword가 혼합되어 있다.

따라서 다음과 같은 처리를 금지한다.

```text
hashtags에 "경기" 포함
→ 경기도 거주자는 지원 가능
```

해시태그는 다음 용도로만 우선 활용한다.

* 후보 지원사업 검색
* Keyword Search
* Recall 향상
* 공고 분류 보조

최종 Eligibility 판정의 단독 Evidence로 사용하지 않는다.

## Important Finding 4 — 세부 지원자격은 비정형 문장에 존재

실제 Sample의 `bsnsSumryCn`에서 다음과 같은 조건이 확인되었다.

* 특정 시·군 거주
* 선정 이후 일정 기간 내 주소 이전
* 최소·최대 연령
* 예비창업자 여부
* 사업자등록 여부
* 창업 업력
* 여성 여부
* 사업장 소재지
* 업종
* 기술 분야
* 특정 신고증 보유
* 교육 이수 여부
* 특정 기관 추천 여부
* 사업 형태
* 기타 복합 조건

예를 들어 하나의 공고 안에서도 다음과 같은 여러 조건이 함께 존재할 수 있다.

```text
지역
+
연령
+
예비창업 여부
+
창업 업력
+
사업자등록 조건
```

따라서 지원 자격 판단은 단순 Keyword Matching으로 구현하지 않는다.

## Important Finding 5 — 신청기간 표현 방식

`reqstBeginEndDe`는 항상 동일한 날짜 형식으로 제공되지 않는다.

실제 확인된 예:

```text
2026-10-08 ~ 2026-10-12
```

```text
2026-08-17 ~ 2026-09-11
```

```text
예산 소진시까지
```

따라서 신청기간을 단순히

```text
apply_start DATE
apply_end DATE
```

두 필드만으로 표현하지 않는다.

권장 Draft:

* `apply_start`
* `apply_end`
* `apply_period_text`
* `deadline_type`

예:

`deadline_type`

* FIXED_DATE
* UNTIL_BUDGET_EXHAUSTED
* UNKNOWN

정확한 Enum은 Backend Schema 설계 단계에서 확정한다.

## Important Finding 6 — 지원금액

지원금액도 별도 정형 필드로 일관되게 제공되지 않고 `bsnsSumryCn` 안에 자연어로 포함되는 사례가 확인되었다.

실제 Sample에서 다음 형태가 존재한다.

* 최대 금액
* 정액 지원
* 평균 지원금액
* 총 상금
* 분야별 다른 최대 지원액
* 사업화 자금

따라서 지원금액을 단일 숫자 컬럼 하나로 단순화하지 않는다.

Draft 후보:

* `support_amount_min`
* `support_amount_max`
* `support_amount_text`
* `support_amount_unit`
* `support_type`

금액을 구조화할 경우 원문 Evidence를 반드시 유지한다.

## Data Processing Decision

기업마당 데이터는 다음과 같이 나누어 처리하는 방향을 우선한다.

### A. Structured

Backend에서 직접 저장·조회 가능한 데이터:

* program ID
* program name
* provider
* executing organization
* category
* subcategory
* created time
* updated time
* source URL
* document URL
* document name

### B. Semi-Structured

Parsing 또는 Validation이 필요한 데이터:

* application period
* target category
* hashtags
* application method
* contact information

### C. Unstructured

자격조건 추출 또는 문서 해석이 필요한 데이터:

* 상세 지원 대상
* 지역 조건
* 연령 조건
* 창업 업력
* 사업자등록 조건
* 업종 조건
* 특정 자격조건
* 지원금액
* 지원 내용
* 예외 조건

## Eligibility Processing Direction

현재 데이터 실측 결과를 바탕으로 다음 구조를 우선 검토한다.

```text
기업마당 공고
→ Raw Data 저장
→ Basic Normalization
→ Eligibility Constraint Extraction
→ Structured Eligibility Schema
→ User Profile과 Deterministic Matching
→ Evidence Validation
→ LLM Explanation
```

중요:

LLM이 공고문을 읽은 뒤 직접 최종 지원 가능 여부를 확정하지 않는다.

LLM 또는 Parser가 비정형 조건을 구조화하더라도 최종 Matching은 가능한 범위에서 Deterministic Logic으로 수행한다.

## Potential Eligibility Schema — Draft

실제 Sample을 기준으로 다음 필드가 필요할 가능성이 확인되었다.

* `region`
* `region_condition_text`
* `age_min`
* `age_max`
* `business_status`
* `business_age_min`
* `business_age_max`
* `business_location`
* `industry`
* `gender_condition`
* `required_certificate`
* `required_education`
* `required_recommendation`
* `eligibility_text`

아직 최종 Schema가 아니다.

공고별 조건 표현을 추가 분석한 뒤 최소 공통 Schema로 확정한다.

## Verification Checklist

* [x] API 사용 신청
* [x] 인증키 발급
* [x] 실제 API 호출 성공
* [x] HTTP 200 확인
* [x] JSON Response 저장
* [x] 실제 20건 Sample 확보
* [x] Response 전체 필드 확인
* [x] 공고 시작/마감 관련 정보 확인
* [x] 기관 정보 확인
* [x] 상세공고 URL 확인
* [x] 지원 대상 관련 정보 확인
* [x] Raw JSON Snapshot 저장
* [ ] 창업 분야 Sample 100건 이상 추가 검증
* [ ] 금융 분야 Sample 검증
* [ ] 경영 분야 Sample 검증
* [ ] 업종 조건 구조화 가능성 정량 검증
* [ ] 지역 조건 구조화 정확도 검증
* [ ] Eligibility Extraction Schema 확정
* [ ] API 호출 제한 확인
* [ ] 자료 이용조건 및 저작권 최종 확인

## MVP Priority

P0 — Main Source

# 3. DS-002 K-Startup 창업지원사업 Open API

Status: OFFICIAL_FOUND

## Provider

창업진흥원 / K-Startup

## Purpose

예비창업자 및 창업기업 관련 지원사업을 기업마당 데이터와 보완적으로 활용할 수 있는 후보.

기업마당 데이터에서 세부 구조화가 어려운

* 지원지역
* 사업업력
* 신청대상
* 연령
* 모집상태

등이 더 명확한 정형 필드로 제공되는지 확인하는 것이 핵심 검증 목적이다.

## Officially Confirmed Data

현재 공식 Open API 안내에서 다음 데이터 항목 후보가 확인된 상태다.

* 통합공고 여부
* 통합공고 사업명
* 사업공고명
* 지원사업 분류
* 공고 접수 시작일
* 신청대상 내용
* 지원지역
* 신청대상
* 사업업력
* 사업대상연령
* 우대사항
* 모집 진행 여부

통합공고 지원사업 정보 후보:

* 사업 카테고리
* 지원사업 제목
* 지원대상
* 지원예산
* 지원내용
* 사업특징
* 사업소개
* 사업연도
* 상세페이지 URL

## Potential MVP Usage

기업마당의 비정형 조건을 보완할 수 있는 정형 Source인지 검증한다.

특히 다음 조건을 우선 확인한다.

* 예비창업자 여부
* 창업 업력
* 지원지역
* 연령
* 모집 상태

## Required Verification

* [ ] API 이용 방법 확인
* [ ] 인증 방식 확인
* [ ] 실제 API 호출 성공
* [ ] Raw Response 저장
* [ ] 전체 Response Schema 확인
* [ ] 현재 모집 중 공고 조회 테스트
* [ ] 기업마당과 동일 공고 Mapping 테스트
* [ ] 기업마당과 중복되는 공고 비율 확인
* [ ] 지원지역 정형화 수준 확인
* [ ] 창업 업력 정형화 수준 확인
* [ ] 연령 조건 정형화 수준 확인
* [ ] Eligibility 보완 효과 확인
* [ ] 이용조건 확인

## Adoption Rule

K-Startup을 추가했을 때

* Eligibility Matching 정확도
* 구조화 가능성
* 데이터 Coverage

중 하나 이상의 실질적인 개선이 확인되는 경우 사용한다.

기업마당 데이터와 대부분 중복되고 추가 가치가 작다면 MVP에서는 Source 수를 늘리지 않는다.

## MVP Priority

P1 — 기업마당 보완 후보

# 4. DS-003 중소벤처기업부 중소기업지원사업 목록

Status: OFFICIAL_FOUND

## Provider

중소벤처기업부 / 공공데이터포털

## Description

공공데이터포털에서 중소기업·소상공인 관련 지원사업 공식 파일 데이터가 제공되는 것을 확인한 상태다.

기업마당 지원사업 공고 데이터를 기반으로 하는 Snapshot 성격의 Source 후보로 본다.

## Potential MVP Usage

기업마당 API의 주 데이터 역할을 대체하기보다는 다음 용도로 검토한다.

* 초기 DB 구축
* Local Development Dataset
* Schema 분석
* 개발용 Snapshot
* 외부 API 장애 시 Fallback 후보
* Evaluation용 고정 데이터셋

## Limitation

파일 데이터는 API보다 최신성이 낮을 수 있다.

또한 원천 데이터 수집 상황에 따라 공란이 존재할 가능성이 있으므로 실제 파일 검증 없이 사용할 수 있다고 판단하지 않는다.

## Required Verification

* [ ] 최신 파일 다운로드
* [ ] 파일 기준일 확인
* [ ] 전체 Column 확인
* [ ] 전체 Row 확인
* [ ] 결측률 확인
* [ ] 기업마당 API와 동일 공고 비교
* [ ] 기업마당 API와 Schema 비교
* [ ] Local Snapshot으로 사용할 가치 확인
* [ ] 이용조건 확인

## MVP Priority

P2 — Snapshot / Fallback 후보

# 5. DS-004 소상공인시장진흥공단 상가(상권)정보 API

Status: OFFICIAL_FOUND

## Provider

소상공인시장진흥공단 / 공공데이터포털

## Officially Confirmed Data

전국 영업 중 상가업소 관련 데이터 제공 Source 후보.

현재 확인된 주요 항목 후보:

* 상가업소번호
* 상호명
* 주소
* 상권업종명
* 표준산업분류명
* 경도
* 위도

## Potential MVP Usage

지원사업 Matching의 Main Source는 아니다.

예비창업자의 실제 지역 또는 상권 조건을 활용한 리스크 분석 기능이 MVP에 포함될 경우 보조 데이터로 검토한다.

## Important Decision

현재 MVP에서는 상권 데이터가 반드시 필요한 것으로 확정되지 않았다.

지원사업 Matching과 핵심 리스크 계산을 상권 데이터 없이 구현할 수 있다면 P0 또는 P1 개발 범위에 포함하지 않는다.

상권 데이터를 추가한다는 이유만으로 서비스 차별성이 생긴다고 판단하지 않는다.

## Required Verification

* [ ] 상권 데이터를 실제 MVP에 사용할지 팀 결정
* [ ] 사용 목적 명확화
* [ ] API 활용신청
* [ ] 실제 호출 테스트
* [ ] Raw Response 저장
* [ ] 업종 Code Mapping 검토
* [ ] 위치 데이터 활용 방식 검토
* [ ] 리스크 계산에 실제로 기여하는지 검증

## MVP Priority

P3 — 선택적 확장

# 6. DS-005 정책자금 대출 데이터

Status: INVESTIGATING

## Purpose

현재 서비스 기획에는 정부지원사업뿐 아니라 정책자금 대출 정보 활용이 포함되어 있다.

특히 다음 기능과 관련된다.

* 사용자에게 적합한 정책자금 탐색
* 리스크 계산의 대출조건 입력 보조
* 창업 이후 잔존 채무 계산

## Current Limitation

MVP에서 사용할 수 있는 정형화된 공식 정책자금 데이터 Source와 실제 제공 Schema를 아직 확정하지 않았다.

따라서 현 단계에서는 다음 값을 임의 데이터로 구축하지 않는다.

* 금리
* 대출한도
* 상환기간
* 거치기간
* 신청자격
* 우대조건
* 지원대상

## Required Verification

* [ ] 소상공인시장진흥공단 정책자금 공식 Source 조사
* [ ] 중소벤처기업진흥공단 정책자금 공식 Source 조사
* [ ] 공공데이터포털 관련 Source 조사
* [ ] API 존재 여부 확인
* [ ] 파일 데이터 존재 여부 확인
* [ ] 실제 금리 데이터 확보 가능성 확인
* [ ] 대출한도 데이터 확보 가능성 확인
* [ ] 상환조건 데이터 확보 가능성 확인
* [ ] 지원대상 조건 확보 가능성 확인
* [ ] 데이터 기준일 확인
* [ ] 갱신주기 확인
* [ ] 이용조건 확인
* [ ] MVP 사용 여부 확정

## MVP Priority

P1

# 7. 지자체 지원사업 Coverage

Status: PARTIALLY_COVERED

기업마당 API Sample에서 실제 지자체 및 지역 기관 지원사업이 포함되는 것을 확인했다.

실제 Sample에는 지역 기반 공고가 존재했다.

따라서 처음부터 전국 지자체별 API를 각각 연결하지 않는다.

우선 기업마당에서 확보 가능한 지역 지원사업 Coverage를 측정한다.

기업마당에서 중요한 지역 공고의 누락이 확인될 경우에만 개별 지자체 Source 추가를 검토한다.

## Required Verification

* [x] 기업마당 Sample에서 지자체 공고 존재 확인
* [x] 지역 기반 지원조건이 `bsnsSumryCn`에 존재함을 확인
* [ ] 주요 지역별 Sample 수집
* [ ] 지역별 Coverage 측정
* [ ] 기업마당 누락 공고 Sample 조사
* [ ] 별도 지자체 API 필요성 판단

## MVP Priority

P1 — 기업마당 Coverage 검증 우선

# 8. User Profile Data

Source:

사용자 직접 입력

Status: PLANNED

현재 기본 후보:

* `user_type`
* `region`
* `industry`
* `capital`

기업마당 Sample 실측 결과 다음 조건도 지원사업 Matching에 필요할 가능성이 확인되었다.

* age
* business_status
* business_age
* business_location
* gender_condition
* certificate
* education_completion

## Profile Design Rule

[TEAM DECISION — 2026-08-29]

모든 정보를 회원가입 또는 첫 화면에서 일괄 요구하지 않는다.

### 일반모드

```text
자연어 질문
→ 현재 문장에서 확보 가능한 조건 추출
→ 후보 지원사업 탐색
→ 부족한 조건만 추가 질문
```

### 집중모드

```text
첫 대화 전 최소 구조화 Profile 입력
→ 후보 지원사업 탐색
→ 필요한 경우 추가 질문
→ 이후 자연어 대화
```

집중모드의 체크·선택 필드는 실제 Eligibility Schema와 MVP 구현량을 기준으로 최소화한다.

사용자에게 불필요한 금융정보나 개인정보를 과도하게 입력받지 않는다.

# 9. User Financial Input

Source:

사용자 직접 입력

Status: PLANNED

현재 리스크 계산 입력 후보:

* `initial_cost`
* `monthly_revenue`
* `monthly_expense`
* `loan_amount`
* `interest_rate`
* `loan_term`

추가 후보:

* own_capital
* fixed_cost
* variable_cost
* repayment_type
* grace_period

위 필드는 최종 확정이 아니다.

## Financial Input Rule

계산식이 확정된 이후 필요한 최소 입력값만 유지한다.

UI 편의를 위해 필요하지 않은 값을 먼저 추가하지 않는다.

금융수치 계산은 LLM이 아니라 Backend Calculation Engine에서 수행한다.

# 10. CSV / Excel Financial Data

Status: OPTIONAL — Backend actual analysis

[TEAM DECISION — 2026-08-29]

소상공인용 매출장표 분석의 **UI 진입점은 Public MVP에서 유지**한다.

다만 실제 CSV/Excel 업로드·분석 Backend는 핵심 Matching/리스크/AI/배포보다 후순위다.

실제 구현할 경우 임의의 모든 회계파일 형식을 지원하려 하지 않는다.

MVP에서는 서비스가 정의한 Sample Schema만 지원하는 방안을 우선한다.

실제 분석이 2026-09-03~04 내부 완료 목표까지 안정적으로 구현되지 않으면:

- 사용자가 업로드한 파일을 분석한 것처럼 가장하지 않는다.
- `DEMO SAMPLE`이라고 명확히 표시한 샘플 데이터·샘플 결과만 UI Fallback으로 사용한다.
- 샘플 데이터는 실제 외부 금융 데이터 또는 실제 사용자 분석 결과로 취급하지 않는다.
- 공식 기능명세서에는 검증 완료된 실제 동작 범위만 기재한다.

## Required Verification

* [ ] Sample Schema 정의
* [ ] CSV 지원 여부
* [ ] Excel 지원 여부
* [ ] 필수 Column 정의
* [ ] 숫자 단위 정의
* [ ] 개인정보 포함 가능성 확인
* [ ] 파일 저장 여부 결정
* [ ] 파일 삭제 정책 결정
* [ ] 잘못된 파일 형식 처리 정의
* [ ] Demo Fallback 사용 시 `DEMO SAMPLE` 라벨 확인

## MVP Priority

P3 — 실제 업로드·분석 Backend

UI 진입점은 MVP 화면 범위에서 유지.

## 10.1 Freelancer Income Stability Input

Source:

사용자 직접 입력

Status: PLANNED

[TEAM DECISION — 2026-08-29]

프리랜서 소득 안정성은 MVP에서 구현 가능한 간이 지표로 제공하는 방향이다.

현재 입력 후보:

* 기간별 소득 금액
* 기간 정보

정확한 기간 단위, 최소 입력 개수, 안정성 계산식은 아직 확정되지 않았다.

원칙:

* 계산은 deterministic code 우선
* 결측값을 임의 보간하지 않음
* 금융기관 신용평가 또는 대출 승인 가능성으로 오인시키지 않음
* UI에 작은 회색 주의사항 표시
* 계산식과 가정을 최종 구현 시 문서화

# 11. Data Source Priority

현재 우선순위는 다음과 같다.

## P0

기업마당 지원사업정보 API

역할:

* MVP Main 지원사업 Source
* 실제 지원사업 탐색
* 원문 Evidence
* Eligibility Extraction 대상

## P1

K-Startup Open API 검증

정책자금 공식 Source 검증

기업마당의 지역 지원사업 Coverage 검증

## P2

공공데이터포털 지원사업 Snapshot 검증

역할 후보:

* 개발용 Local Dataset
* Evaluation Dataset
* API Fallback

## P3

상권정보

CSV / Excel 실제 업로드·분석

기타 확장 데이터

# 12. Current Data Architecture

현재 기업마당 실측 결과를 반영한 권장 구조:

```text
기업마당 API
        ↓
Collector
        ↓
Raw JSON Snapshot
        ↓
Basic Validation
        ↓
Normalization
        ↓
┌─────────────────────┐
│ Structured Fields   │
│ ID / 기관 / 분야 등 │
└─────────────────────┘
        +
┌────────────────────────┐
│ Unstructured Evidence  │
│ bsnsSumryCn / 공고문   │
└────────────────────────┘
        ↓
Eligibility Constraint Extraction
        ↓
Structured Eligibility Schema
        ↓
Service DB
        ↓
Structured Retrieval
        ↓
User Profile Matching
        ↓
Evidence Validation
        ↓
LLM Explanation
```

K-Startup 및 다른 Source는 실제 검증 후 필요한 경우 이 Pipeline에 추가한다.

# 13. Normalized Program Schema — Draft v2

기업마당 API 실제 Response를 기준으로 Draft를 수정한다.

## Program Identity

* `program_id`
* `program_name`

## Organization

* `provider`
* `executing_organization`

## Classification

* `category`
* `subcategory`
* `target_type_raw`
* `hashtags_raw`

## Description

* `summary_raw`
* `application_method_raw`

## Application Period

* `apply_start`
* `apply_end`
* `apply_period_text`
* `deadline_type`

## Support

* `support_summary`
* `support_amount_min`
* `support_amount_max`
* `support_amount_text`

## Evidence

* `source`
* `source_url`
* `document_url`
* `document_name`
* `contact_raw`

## Freshness

* `source_created_at`
* `source_updated_at`
* `collected_at`
* `effective_date`

## Data Quality

* `parsing_status`
* `validation_status`

실제 Source에 존재하지 않는 값을 임의로 생성해서 채우지 않는다.

결측치는 NULL 또는 명시적인 UNKNOWN 상태로 유지한다.

# 14. Eligibility Schema — Draft v1

기업마당 Sample 분석 결과 별도 Eligibility 구조가 필요할 가능성이 높다.

초기 후보:

## Region

* `region`
* `region_scope`
* `region_condition_text`

## Age

* `age_min`
* `age_max`

## Business Status

* `business_status`
* `business_age_min`
* `business_age_max`

예:

* PRE_FOUNDER
* EXISTING_BUSINESS
* STARTUP

최종 Enum은 추가 Sample 분석 후 결정한다.

## Business Condition

* `business_location`
* `industry`
* `required_business_registration`

## Personal Condition

* `gender_condition`

## Additional Requirements

* `required_certificate`
* `required_education`
* `required_recommendation`
* `additional_condition_text`

## Evidence

각 추출 조건은 가능하면 다음과 함께 저장한다.

* `evidence_text`
* `source_field`
* `extraction_method`
* `confidence`

단,

Confidence Score만으로 지원 가능 여부를 자동 확정하지 않는다.

# 15. Data Safety Rules

## 15.1 No Fabrication

데이터에 없는 다음 정보를 생성하지 않는다.

* 지원사업
* 지원금액
* 신청기간
* 지원대상
* 지역조건
* 업종조건
* 정책자금 금리
* 대출한도
* 자격조건

## 15.2 Missing Values

결측값을 임의로

* 0
* 평균값
* 가장 흔한 값

등으로 대체하지 않는다.

## 15.3 Raw Evidence

구조화된 값만 저장하고 원문을 버리지 않는다.

Eligibility 또는 지원금액을 추출한 경우 원문 Evidence를 유지한다.

## 15.4 Freshness

지원사업은 최신성이 중요하므로 다음을 구분한다.

* Source 등록일
* Source 수정일
* API 수집일
* 신청기간

과거 공고와 현재 모집 공고를 혼동하지 않는다.

## 15.5 Secret

API Key 등 인증정보는

* 채팅
* Git
* 문서
* Source Code

에 직접 기록하지 않는다.

환경변수 또는 Secret 관리 방식을 사용한다.

# 16. Current Findings for AI Necessity

[EXPERIMENT]

기업마당 실제 데이터 검증 결과, 지원사업의 핵심 자격조건이 하나의 완전한 정형 Schema로 제공되지 않는다는 점을 확인했다.

정형 데이터:

* 공고명
* 기관
* 지원분야
* 등록일
* URL

비정형 또는 반정형 데이터:

* 지역 자격
* 연령
* 창업 업력
* 사업자등록 상태
* 특정 업종
* 교육 이수
* 지원금액
* 추가 조건

따라서 AI 또는 문서 Parsing이 필요한 핵심 이유는

**지원사업을 추천하기 위해서가 아니라, 비정형 공고문에서 검증 가능한 자격조건을 구조화하기 위해서다.**

권장 역할 분리:

```text
LLM / Parser
→ Eligibility 조건 추출

Deterministic Code
→ 사용자 조건과 Eligibility 비교

Evidence Validator
→ 추출 조건과 원문 근거 확인

LLM
→ 최종 결과 설명
```

이 구조는 단순 지원사업 추천 챗봇보다 정확성, 설명가능성 및 금융 안전성을 우선한다.

# 17. Next Data Verification

DS-001의 최초 API 접근 및 Schema 확인은 완료되었다.

따라서 다음 검증 순서는 다음과 같다.

## Step 1 — 기업마당 Sample 확대

목표:

* 창업 분야 100건 이상 Sample 확보
* 금융 분야 Sample 확보
* 경영 분야 Sample 확보
* 다양한 지역 공고 확보
* 다양한 지원대상 공고 확보

확인할 항목:

* Eligibility 조건 종류
* 결측 패턴
* 날짜 표현 방식
* 지원금액 표현 방식
* HTML 제거 필요성
* 중복 공고 존재 여부

## Step 2 — Eligibility Schema 검증

최소 30~50개 공고를 직접 확인하여

* 지역
* 연령
* 업력
* 창업 여부
* 업종
* 추가 조건

을 현재 Draft Schema로 표현할 수 있는지 확인한다.

표현할 수 없는 조건 유형을 기록하고 Schema를 수정한다.

## Step 3 — K-Startup 실제 검증

기업마당과 동일하거나 유사한 공고를 조회해

* 지원지역
* 업력
* 연령
* 모집상태

등이 더 구조화되어 있는지 비교한다.

K-Startup 추가가 Matching 정확도를 실제로 높이는 경우에만 MVP에 포함한다.

## Step 4 — 정책자금 Source 검증

리스크 계산과 실제 금융 의사결정을 위해

* 금리
* 한도
* 상환조건
* 자격조건

을 공식적으로 확보할 수 있는 Source를 조사한다.

## Step 5 — Architecture Freeze

위 데이터 검증 결과를 바탕으로 다음을 확정한다.

* 최종 Program Schema
* Eligibility Schema
* 사용자 Profile Schema
* Matching Logic
* Retrieval 방식
* LLM 역할
* DB 구조
* Backend Framework
* 배포 구조

데이터 구조가 확정되기 전에 과도한 Vector DB, Graph DB 또는 Multi-Agent 구조를 먼저 도입하지 않는다.

# 17.5 2026-08-29 Schedule-Driven Data Rule

[CURRENT DATA DECISION + RECOMMENDATION — 2026-08-29]

- DS-001 기업마당 지원사업정보 API는 이미 `VERIFIED`이며 MVP Main Source로 유지한다.
- [RECOMMENDATION] 2026-09-03~04 내부 개발 완료 목표를 고려해 K-Startup, 상권정보, 추가 지자체 Source 등은 **핵심 구현을 지연시키는 선행조건으로 두지 않는다.**
- 추가 Source는 실제 Matching 정확도 또는 Coverage 개선이 즉시 검증될 때만 포함한다.
- 현재 최우선은 Source 수 확대가 아니라 FinBridge의 한 개 완성된 사용자 흐름이다.

```text
기업마당 실제 데이터
→ 최소 Normalization
→ Eligibility 구조화
→ Deterministic Matching
→ Evidence
→ AI 설명
→ Public URL
```

# 18. Current Data Decision Summary

[TEAM DECISION / CURRENT]

현재 MVP의 데이터 전략은 다음을 우선한다.

### Main Source

기업마당 지원사업정보 API

### Primary Processing

Structured Retrieval + Eligibility Constraint Extraction + Deterministic Matching

### Evidence

기업마당 상세공고 및 원문 데이터

### Secondary Source

K-Startup은 기업마당의 Eligibility 정보를 실질적으로 보완하는지 검증한 후 결정

### Policy Loan Data

별도 공식 Source 검증 필요

### Commercial District Data

핵심 MVP 완료 이후 필요성이 입증될 때만 추가

### CSV / Excel

실제 업로드·분석 Backend는 Optional/P3. 다만 매출장표 분석 UI 진입점은 2026-08-29 팀 결정에 따라 Public MVP에서 유지하며, 미완성 시 `DEMO SAMPLE`을 명확히 표시한다.

### Freelancer Income Stability

사용자 직접 입력 기반 간이 deterministic 분석을 MVP 목표로 하며, 최종 계산식은 구현·검증 후 Freeze한다.

현재 최우선 과제는 데이터 Source 수를 늘리는 것이 아니라

**기업마당 실제 공고를 정확하게 구조화하고 사용자 조건과 안전하게 Matching할 수 있는지를 검증하는 것**이다.
