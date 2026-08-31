from __future__ import annotations

from app.retrieval.query_understanding import (
    extract_explicit_profile,
    requests_currently_open_programs,
    requests_deadline_sort,
)
from app.schemas.matching import BusinessStatus, UserType


def test_extracts_only_explicit_general_mode_profile_fields() -> None:
    profile = extract_explicit_profile(
        "대구 / 28세 / 예비창업자 / 사업자 미등록 지원사업을 알려줘"
    )

    assert profile is not None
    assert profile.region == "대구"
    assert profile.business_region == "대구"
    assert profile.age == 28
    assert profile.user_type is UserType.PRE_FOUNDER
    assert profile.pre_founder is True
    assert profile.business_status is BusinessStatus.UNREGISTERED


def test_extracts_explicit_business_age_as_existing_business() -> None:
    profile = extract_explicit_profile("대구에서 업력 5년 사업자입니다")

    assert profile is not None
    assert profile.business_age == 5
    assert profile.pre_founder is False
    assert profile.business_status is BusinessStatus.EXISTING_BUSINESS


def test_current_open_and_deadline_sort_intents_are_explicit() -> None:
    message = "지금 신청 가능한 대구 창업 지원사업을 마감일 가까운 순서로 알려주세요"

    assert requests_currently_open_programs(message) is True
    assert requests_deadline_sort(message) is True
    assert requests_currently_open_programs("과거 마감된 공고를 알려주세요") is False
