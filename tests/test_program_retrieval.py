from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.ai.provider import AIExplanation, AIProviderUnavailableError
from app.data.program_repository import ProgramRepository
from app.main import create_app
from app.retrieval.program_retrieval import (
    ProgramRetrievalService,
    normalize_text,
)
from app.retrieval.query_understanding import extract_explicit_profile
from app.schemas.eligibility import ConditionType, ExtractionStatus
from app.schemas.matching import BusinessStatus, UserProfile
from app.schemas.retrieval import ProgramSearchRequest
from app.services.program_service import ProgramService
from tests.conftest import ASGITestClient


WATER_PROGRAM_ID = "PBLN_000000000125666"
DAEGU_PRE_FOUNDER_PROGRAM_ID = "PBLN_000000000125612"
SHORT_DAEGU_PROFILE_QUERY = (
    "대구 28세 예비창업자 사업자 미등록 지원사업 알려줘"
)
LONG_DAEGU_PROFILE_QUERY = """대구에 거주하는 28세 예비창업자이고 아직 사업자등록은 하지 않았습니다.
제가 지원할 수 있는 사업의 조건 충족 여부와 부족한 정보,
그리고 지금 준비해야 할 것을 1순위, 2순위, 3순위로 알려주세요.
신청기간과 공식 공고도 같이 알려주세요."""


class StubProvider:
    def __init__(self, text: str = "구조화된 검색 결과를 안내합니다.") -> None:
        self.text = text
        self.calls: list[str] = []

    def explain(self, *, instructions: str, input_text: str) -> AIExplanation:
        del instructions
        self.calls.append(input_text)
        return AIExplanation(text=self.text, model="test-model")


class UnavailableProvider:
    def explain(self, *, instructions: str, input_text: str) -> AIExplanation:
        del instructions, input_text
        raise AIProviderUnavailableError("provider unavailable")


@pytest.fixture
def client(private_client: ASGITestClient) -> ASGITestClient:
    return private_client


@pytest.fixture
def program_service(snapshot_path: Path) -> ProgramService:
    return ProgramService(ProgramRepository(snapshot_path))


@pytest.fixture
def retrieval_service(program_service: ProgramService) -> ProgramRetrievalService:
    return ProgramRetrievalService(program_service)


def test_program_name_exact_search_ranks_exact_program_first(
    retrieval_service: ProgramRetrievalService,
    program_service: ProgramService,
) -> None:
    program = program_service.get_program(WATER_PROGRAM_ID)

    response = retrieval_service.search(
        ProgramSearchRequest(query=program.program_name, limit=5)
    )

    assert response.results[0].program.program_id == WATER_PROGRAM_ID
    assert "program_name" in response.results[0].matched_fields


def test_provider_keyword_search(retrieval_service: ProgramRetrievalService) -> None:
    response = retrieval_service.search(
        ProgramSearchRequest(query="중소벤처기업부", limit=20)
    )

    assert response.result_count == 3
    assert all("provider" in item.matched_fields for item in response.results)


def test_category_keyword_search(retrieval_service: ProgramRetrievalService) -> None:
    response = retrieval_service.search(
        ProgramSearchRequest(query="예비창업자지원", limit=20)
    )

    assert response.result_count == 2
    assert all("subcategory" in item.matched_fields for item in response.results)


def test_summary_keyword_search(retrieval_service: ProgramRetrievalService) -> None:
    response = retrieval_service.search(
        ProgramSearchRequest(query="물산업", limit=5)
    )

    assert [item.program.program_id for item in response.results] == [WATER_PROGRAM_ID]
    assert "summary" in response.results[0].matched_fields


def test_structured_region_filter_keeps_unknown_and_excludes_known_mismatch(
    retrieval_service: ProgramRetrievalService,
) -> None:
    response = retrieval_service.search(
        ProgramSearchRequest(region="대구", limit=20)
    )
    by_id = {item.program.program_id: item for item in response.results}

    assert DAEGU_PRE_FOUNDER_PROGRAM_ID in by_id
    assert "region" in by_id[DAEGU_PRE_FOUNDER_PROGRAM_ID].matched_fields
    assert "structured.region" in by_id["PBLN_000000000125755"].matched_fields
    assert "PBLN_000000000125622" not in by_id
    assert any(not item.matched_fields for item in response.results)


def test_business_status_filter_uses_explicit_conditions(
    retrieval_service: ProgramRetrievalService,
) -> None:
    response = retrieval_service.search(
        ProgramSearchRequest(
            business_status=BusinessStatus.PRE_FOUNDER,
            limit=20,
        )
    )
    by_id = {item.program.program_id: item for item in response.results}

    assert DAEGU_PRE_FOUNDER_PROGRAM_ID in by_id
    assert "structured.business_status" in by_id[DAEGU_PRE_FOUNDER_PROGRAM_ID].matched_fields
    assert "PBLN_000000000125755" not in by_id


def test_query_normalization_handles_case_spacing_punctuation_and_alias(
    retrieval_service: ProgramRetrievalService,
) -> None:
    assert normalize_text("  STARTUP,   Water  ") == "startup water"
    assert normalize_text("예비,   창업") == "예비창업"

    response = retrieval_service.search(
        ProgramSearchRequest(query="  예비,   창업  ", limit=5)
    )
    assert response.results[0].program.program_id == DAEGU_PRE_FOUNDER_PROGRAM_ID


def test_ranking_is_deterministic(retrieval_service: ProgramRetrievalService) -> None:
    request = ProgramSearchRequest(query="창업", limit=10)

    first = retrieval_service.search(request)
    second = retrieval_service.search(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_limit_and_maximum_validation(
    retrieval_service: ProgramRetrievalService,
    client: ASGITestClient,
) -> None:
    response = retrieval_service.search(ProgramSearchRequest(query="창업", limit=2))
    assert response.result_count == 2
    assert len(response.results) == 2

    invalid = client.get("/programs?query=창업&limit=21")
    assert invalid.status_code == 422


def test_no_result_does_not_create_program(
    retrieval_service: ProgramRetrievalService,
    program_service: ProgramService,
) -> None:
    response = retrieval_service.search(
        ProgramSearchRequest(query="절대없는검색어", limit=20)
    )
    repository_ids = {
        program.program_id for program in program_service.list_programs()
    }

    assert response.result_count == 0
    assert response.results == []
    assert all(
        item.program.program_id in repository_ids for item in response.results
    )


def test_retrieval_score_does_not_promote_match_status(
    retrieval_service: ProgramRetrievalService,
    program_service: ProgramService,
) -> None:
    result = retrieval_service.search(
        ProgramSearchRequest(query="창업", limit=1)
    ).results[0]
    match = program_service.match_program(
        result.program.program_id,
        UserProfile(),
    )

    assert result.retrieval_score > 0
    assert match.match_status.value == "NEEDS_REVIEW"


def test_search_api_returns_structured_result(client: ASGITestClient) -> None:
    response = client.get("/programs?query=물산업&limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_count"] == 1
    assert payload["results"][0]["program"]["program_id"] == WATER_PROGRAM_ID
    assert payload["results"][0]["source"] == "BIZINFO"
    assert payload["results"][0]["source_url"]
    assert payload["results"][0]["program"]["application_status"] in {
        "OPEN",
        "UPCOMING",
        "CLOSED",
        "NEEDS_CONFIRMATION",
    }
    assert payload["score_semantics"] == "DETERMINISTIC_RANKING_ONLY"


def test_general_chat_retrieves_top_n_with_evidence_and_sources(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    provider = StubProvider()
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=provider))

    response = client.post(
        "/chat",
        json={"message": "대구에서 창업 준비 중인데 지원사업 찾아줘"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert 1 <= len(payload["programs"]) <= 5
    assert len(payload["sources"]) == len(payload["programs"])
    assert payload["evidence"]
    assert payload["program_context_id"] is None
    assert '"retrieval_score"' not in provider.calls[0]
    assert '"eligibility_evidence"' in provider.calls[0]
    assert '"raw_source"' not in provider.calls[0]


def test_general_message_explicit_profile_drives_matching_and_region_ranking(
    retrieval_service: ProgramRetrievalService,
    program_service: ProgramService,
) -> None:
    message = "대구 28세 예비창업자 사업자 미등록 지원사업 알려줘"
    profile = extract_explicit_profile(message)
    assert profile is not None

    response = retrieval_service.search(
        ProgramSearchRequest(
            query=message,
            region=profile.region,
            business_status=profile.business_status,
            user_type=profile.user_type,
            profile=profile,
            limit=10,
        )
    )

    assert response.results
    assert all(
        "대구" in item.program.program_name
        for item in response.results[:2]
    )
    kept_unknown_region = False
    for item in response.results:
        eligibility = program_service.get_program_eligibility(
            item.program.program_id
        )
        region_conditions = [
            condition
            for condition in [
                *eligibility.common_conditions,
                *(
                    condition
                    for group in eligibility.eligibility_groups
                    for condition in group.conditions
                ),
            ]
            if condition.condition_type is ConditionType.REGION_OR_LOCATION
            and condition.extraction_status is ExtractionStatus.SUPPORTED
        ]
        if not region_conditions:
            kept_unknown_region = True
        assert (
            not region_conditions
            or "대구" in item.program.program_name
            or any("대구" in str(condition.value) for condition in region_conditions)
        )
    assert kept_unknown_region is True


def test_private_snapshot_daegu_profile_excludes_explicit_other_local_only(real_bootstrap_path: Path) -> None:
    service = ProgramService(ProgramRepository(real_bootstrap_path))
    retrieval = ProgramRetrievalService(service)
    message = "대구 28세 예비창업자 사업자 미등록 지원사업 알려줘"
    profile = extract_explicit_profile(message)
    assert profile is not None

    response = retrieval.search(
        ProgramSearchRequest(
            query=message,
            region=profile.region,
            business_status=profile.business_status,
            user_type=profile.user_type,
            profile=profile,
            limit=20,
        )
    )
    result_ids = {item.program.program_id for item in response.results}

    assert {
        "PBLN_000000000125900",  # 경기 안산시 관내
        "PBLN_000000000123753",  # 경기 안산시 관내
        "PBLN_000000000120031",  # 경기 안산시 관내
        "PBLN_000000000125622",  # 울산 울주군민
        "PBLN_000000000121148",  # 울산 소재 사업장
    }.isdisjoint(result_ids)
    assert "PBLN_000000000116904" in result_ids  # 전국 통합 공고 유지


def test_short_and_long_daegu_queries_extract_the_same_structured_profile() -> None:
    short_profile = extract_explicit_profile(SHORT_DAEGU_PROFILE_QUERY)
    long_profile = extract_explicit_profile(LONG_DAEGU_PROFILE_QUERY)

    assert short_profile is not None
    assert long_profile is not None
    assert short_profile == long_profile
    assert short_profile.region == "대구"
    assert short_profile.business_region == "대구"
    assert short_profile.age == 28
    assert short_profile.pre_founder is True
    assert short_profile.business_status is BusinessStatus.UNREGISTERED


@pytest.mark.parametrize(
    "message",
    [SHORT_DAEGU_PROFILE_QUERY, LONG_DAEGU_PROFILE_QUERY],
    ids=["short", "long"],
)
def test_daegu_region_tiers_are_stable_across_query_length(message: str, real_bootstrap_path: Path) -> None:
    service = ProgramService(ProgramRepository(real_bootstrap_path))
    retrieval = ProgramRetrievalService(service)
    profile = extract_explicit_profile(message)
    assert profile is not None

    response = retrieval.search(
        ProgramSearchRequest(
            query=message,
            region=profile.region,
            business_status=profile.business_status,
            user_type=profile.user_type,
            profile=profile,
            limit=20,
        )
    )
    positions = {
        item.program.program_id: index
        for index, item in enumerate(response.results)
    }
    same_region_ids = {
        "PBLN_000000000125941",  # 대구 동구
        "PBLN_000000000125748",  # 대구 여성창업
    }
    exception_ids = {
        "PBLN_000000000125864",  # 영월 주소 이전 가능
        "PBLN_000000000118665",  # 울산 타 지역민 별도조건
        "PBLN_000000000119107",  # 전남 타 지역민 예외조건
    }
    explicit_other_only_ids = {
        "PBLN_000000000125900",  # 경기 안산시 관내
        "PBLN_000000000123753",  # 경기 안산시 관내
        "PBLN_000000000125622",  # 울산 울주군민
    }

    assert same_region_ids <= positions.keys()
    assert exception_ids <= positions.keys()
    assert "PBLN_000000000116904" in positions  # 전국 통합 공고
    assert max(positions[item] for item in same_region_ids) < min(
        positions[item] for item in exception_ids
    )
    assert positions["PBLN_000000000116904"] < min(
        positions[item] for item in exception_ids
    )
    assert explicit_other_only_ids.isdisjoint(positions)


def test_general_message_explicit_profile_is_reused_by_chat_matcher(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=StubProvider()))

    response = client.post(
        "/chat",
        json={
            "message": "대구 28세 예비창업자이고 사업자 미등록 상태입니다. 지원사업 알려줘"
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["programs"]
    assert len(payload["matches"]) == len(payload["programs"])
    assert all(
        "대구" in item["program_name"] for item in payload["programs"][:2]
    )


def test_structured_fallback_includes_conditions_priorities_period_and_sources(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=UnavailableProvider()))

    response = client.post(
        "/chat",
        json={"message": "대구 업력 5년 사업자 지원사업과 준비사항을 알려줘"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["reply_source"] == "TEMPLATE_FALLBACK"
    assert "현재 확보된 공고 범위에서 후보" in payload["reply"]
    assert "현재 확인되는 조건" in payload["reply"]
    assert "준비사항 1순위" in payload["reply"]
    assert "준비사항 2순위" in payload["reply"]
    assert "준비사항 3순위" in payload["reply"]
    assert "신청기간" in payload["reply"]
    assert "공식 출처" in payload["reply"]
    assert payload["programs"]
    assert payload["matches"]
    assert payload["evidence"]
    assert payload["sources"]
    assert payload["actions"]


def test_currently_open_chat_filters_closed_and_sorts_open_fixed_deadlines(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    monkeypatch.setattr(
        "app.retrieval.program_retrieval.seoul_today",
        lambda: date(2026, 8, 31),
    )
    monkeypatch.setattr(
        "app.services.chat_service.seoul_today",
        lambda: date(2026, 8, 31),
    )
    client = ASGITestClient(create_app(ai_provider=UnavailableProvider()))

    response = client.post(
        "/chat",
        json={
            "message": "지금 신청 가능한 대구 창업 지원사업을 마감일 가까운 순서로 알려주세요"
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["programs"]
    assert all(
        item["application_status"] in {"OPEN", "NEEDS_CONFIRMATION"}
        for item in payload["programs"]
    )
    fixed_open_ends = [
        item["apply_end"]
        for item in payload["programs"]
        if item["application_status"] == "OPEN"
        and item["deadline_type"] == "FIXED_DATE"
    ]
    assert fixed_open_ends == sorted(fixed_open_ends)
    assert "신청 종료" not in payload["reply"]


def test_general_chat_with_profile_runs_matcher_without_score_promotion(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=StubProvider()))

    response = client.post(
        "/chat",
        json={
            "message": "대구에서 창업 지원사업 찾아줘",
            "focus_profile": {
                "region": "동구",
                "business_region": "동구",
                "age": 30,
                "pre_founder": True,
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["matches"]) == len(payload["programs"])
    assert all(
        item["match_status"] in {"MATCH", "NO_MATCH", "NEEDS_REVIEW", "UNKNOWN"}
        for item in payload["matches"]
    )


def test_general_chat_no_result_keeps_structured_programs_empty(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    provider = StubProvider("가상의 지원사업을 추천합니다.")
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=provider))

    response = client.post(
        "/chat",
        json={"message": "절대없는검색어 지원사업 찾아줘"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["programs"] == []
    assert payload["matches"] == []
    assert payload["evidence"] == []
    assert payload["sources"] == []


def test_general_chat_no_result_uses_snapshot_scoped_fallback(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=UnavailableProvider()))

    response = client.post(
        "/chat",
        json={"message": "절대없는검색어 지원사업 찾아줘"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["reply_source"] == "TEMPLATE_FALLBACK"
    assert "현재 확보된 공고 범위" in payload["reply"]
    assert payload["programs"] == []


def test_general_risk_message_does_not_run_program_retrieval(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    provider = StubProvider()
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=provider))

    response = client.post(
        "/chat",
        json={"message": "사업 리스크와 대출 상환을 설명해줘"},
    )

    assert response.status_code == 200
    assert response.json()["programs"] == []
    context_text = provider.calls[0].split(
        "Structured Context(JSON):\n", maxsplit=1
    )[1]
    assert json.loads(context_text)["programs"] == []


def test_focus_mode_does_not_implicitly_run_general_retrieval(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_path,
) -> None:
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(snapshot_path))
    client = ASGITestClient(create_app(ai_provider=StubProvider()))

    response = client.post(
        "/chat",
        json={"mode": "FOCUS", "message": "지원사업 찾아줘"},
    )

    assert response.status_code == 200
    assert response.json()["programs"] == []
