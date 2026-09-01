from __future__ import annotations

from collections import Counter

from app.data.program_repository import ProgramRepository
from app.eligibility.extractor import EligibilityExtractor
from app.eligibility.matcher import EligibilityMatcher
from app.schemas.eligibility import (
    ConditionType,
    Operator,
    ProgramExtractionStatus,
    Unit,
)
from app.schemas.matching import MatchStatus, UserProfile
from app.schemas.program import Program
from app.services.program_service import ProgramService
from app.utils.date_parser import DeadlineType


def program(summary: str, program_id: str = "PBLN_TEST") -> Program:
    return Program(
        program_id=program_id,
        program_name="테스트 공고",
        summary_raw=summary,
        deadline_type=DeadlineType.UNKNOWN,
        raw_source={"pblancId": program_id, "bsnsSumryCn": summary},
    )


def conditions(extracted):
    return [
        *extracted.common_conditions,
        *(
            condition
            for group in extracted.eligibility_groups
            for condition in group.conditions
        ),
        *extracted.global_exclusions,
    ]


def test_extracts_numeric_age_upper_bound() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 공고일 기준 만 39세 이하 예비창업자 ☞ 지원내용")
    )

    age = next(
        condition
        for condition in conditions(extracted)
        if condition.condition_type is ConditionType.AGE
    )
    assert age.operator is Operator.LTE
    assert age.value == 39
    assert age.unit is Unit.YEAR


def test_extracts_numeric_age_range() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 만 18세 이상 만 45세 이하 청년 ☞ 지원내용")
    )

    age = conditions(extracted)[0]
    assert age.operator is Operator.BETWEEN
    assert age.min_value == 18
    assert age.max_value == 45


def test_does_not_guess_numeric_age_from_youth_label() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 지역 청년 창업자 ☞ 지원내용")
    )

    assert all(
        condition.condition_type is not ConditionType.AGE
        for condition in conditions(extracted)
    )


def test_extracts_business_age_year_patterns() -> None:
    seven_years = EligibilityExtractor().extract(
        program("안내 ☞ 창업 7년 이내 기업 ☞ 지원내용")
    )
    three_years = EligibilityExtractor().extract(
        program("안내 ☞ 업력 3년 이하 기업 ☞ 지원내용", "PBLN_THREE")
    )

    seven = next(
        condition
        for condition in conditions(seven_years)
        if condition.condition_type is ConditionType.BUSINESS_AGE
    )
    three = next(
        condition
        for condition in conditions(three_years)
        if condition.condition_type is ConditionType.BUSINESS_AGE
    )
    assert (seven.operator, seven.value, seven.unit) == (
        Operator.LTE,
        7,
        Unit.YEAR,
    )
    assert (three.operator, three.value, three.unit) == (
        Operator.LTE,
        3,
        Unit.YEAR,
    )


def test_preserves_explicit_business_age_month_unit_without_conversion() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 사업경력 2개월 이상인 사업자 ☞ 지원내용")
    )

    business_age = next(
        condition
        for condition in conditions(extracted)
        if condition.condition_type is ConditionType.BUSINESS_AGE
    )
    assert business_age.operator is Operator.GTE
    assert business_age.value == 2
    assert business_age.unit is Unit.MONTH


def test_business_age_extraction_integrates_with_matcher() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 업력 3년 이하 기업 ☞ 지원내용")
    )

    matched = EligibilityMatcher().match(extracted, UserProfile(business_age=2))
    rejected = EligibilityMatcher().match(extracted, UserProfile(business_age=4))

    assert matched.match_status is MatchStatus.MATCH
    assert rejected.match_status is MatchStatus.NO_MATCH


def test_extracts_explicit_region_but_not_nationwide() -> None:
    local = EligibilityExtractor().extract(
        program("안내 ☞ 서울특별시 소재 창업기업 ☞ 지원내용")
    )
    nationwide = EligibilityExtractor().extract(
        program("안내 ☞ 전국 소재 창업기업 ☞ 지원내용", "PBLN_NATIONWIDE")
    )

    region = next(
        condition
        for condition in conditions(local)
        if condition.condition_type is ConditionType.REGION_OR_LOCATION
    )
    assert region.value == "서울특별시"
    assert all(
        condition.condition_type is not ConditionType.REGION_OR_LOCATION
        for condition in conditions(nationwide)
    )


def test_conditional_move_region_path_is_not_made_a_common_requirement() -> None:
    extracted = EligibilityExtractor().extract(
        program(
            "안내 ☞ 영월군 관내에 주소지를 둔 자 또는 선정 후 영월군에 "
            "주소 이전 가능한 자 ※ 자세한 지원대상 공고문 참조 ☞ 지원내용"
        )
    )

    assert all(
        condition.condition_type is not ConditionType.REGION_OR_LOCATION
        for condition in conditions(extracted)
    )
    result = EligibilityMatcher().match(
        extracted, UserProfile(region="서울특별시")
    )
    assert result.match_status is MatchStatus.NEEDS_REVIEW


def test_other_region_allowed_evidence_stays_needs_review() -> None:
    extracted = EligibilityExtractor().extract(
        program(
            "안내 ☞ 울산시에 주소를 둔 사업자 미등록 예비창업자 "
            "※ 타 지역민도 신청 가능하나 자격조건은 공고문 참조 ☞ 지원내용"
        )
    )

    assert all(
        condition.condition_type is not ConditionType.REGION_OR_LOCATION
        for condition in conditions(extracted)
    )
    assert (
        extracted.eligibility_extraction_status
        is ProgramExtractionStatus.NEEDS_REVIEW
    )
    result = EligibilityMatcher().match(
        extracted, UserProfile(region="대구", pre_founder=True)
    )
    assert result.match_status is MatchStatus.NEEDS_REVIEW


def test_extracts_explicit_pre_founder_status() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 공고일 기준 예비창업자 ☞ 지원내용")
    )

    pre_founder = next(
        condition
        for condition in conditions(extracted)
        if condition.condition_type is ConditionType.PRE_FOUNDER
    )
    assert pre_founder.operator is Operator.EQ
    assert pre_founder.value is True


def test_supported_conditions_always_preserve_evidence_and_source_field() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 대구 동구 소재 만 39세 이하 예비창업자 ☞ 지원내용")
    )

    assert conditions(extracted)
    assert all(condition.evidence_text for condition in conditions(extracted))
    assert all(
        condition.source_field == "bsnsSumryCn"
        for condition in conditions(extracted)
    )


def test_reference_to_unavailable_notice_prevents_match() -> None:
    extracted = EligibilityExtractor().extract(
        program(
            "안내 ☞ 업력 7년 이내 기업 ※ 자세한 지원대상 공고문 참조 ☞ 지원내용"
        )
    )

    result = EligibilityMatcher().match(
        extracted, UserProfile(business_age=3)
    )
    assert extracted.eligibility_extraction_status is ProgramExtractionStatus.NEEDS_REVIEW
    assert result.match_status is MatchStatus.NEEDS_REVIEW


def test_clear_pre_founder_or_business_age_is_stored_as_or_groups() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 예비창업자 또는 업력 3년 이내 창업기업 ☞ 지원내용")
    )

    assert len(extracted.eligibility_groups) == 2
    assert {
        group.conditions[0].condition_type for group in extracted.eligibility_groups
    } == {ConditionType.PRE_FOUNDER, ConditionType.BUSINESS_AGE}


def test_reverse_business_age_or_pre_founder_is_stored_as_or_groups() -> None:
    extracted = EligibilityExtractor().extract(
        program("안내 ☞ 창업 7년 이내 스타트업 또는 예비창업자 ☞ 지원내용")
    )

    assert len(extracted.eligibility_groups) == 2
    result = EligibilityMatcher().match(
        extracted,
        UserProfile(pre_founder=True),
    )
    assert result.match_status is MatchStatus.MATCH
    assert result.reason == "ELIGIBILITY_PATH_SATISFIED"


def test_actual_raw_snapshot_coverage_and_statuses(snapshot_path) -> None:
    programs = ProgramRepository(snapshot_path).list()
    extracted = [EligibilityExtractor().extract(item) for item in programs]
    status_counts = Counter(
        item.eligibility_extraction_status for item in extracted
    )
    type_counts = Counter(
        condition.condition_type
        for item in extracted
        for condition in conditions(item)
    )

    assert len(programs) == 20
    assert sum(bool(conditions(item)) for item in extracted) == 18
    assert status_counts == {
        ProgramExtractionStatus.SUPPORTED: 3,
        ProgramExtractionStatus.NEEDS_REVIEW: 16,
        ProgramExtractionStatus.UNSUPPORTED: 1,
    }
    assert type_counts == {
        ConditionType.REGION_OR_LOCATION: 12,
        ConditionType.AGE: 4,
        ConditionType.PRE_FOUNDER: 5,
        ConditionType.BUSINESS_AGE: 9,
        ConditionType.BUSINESS_REGISTRATION_STATUS: 8,
    }


def test_actual_supported_program_can_match_deterministically(snapshot_path) -> None:
    repository = ProgramRepository(snapshot_path)
    actual = repository.get("PBLN_000000000125612")
    assert actual is not None
    extracted = EligibilityExtractor().extract(actual)

    result = EligibilityMatcher().match(
        extracted,
        UserProfile(
            business_region="동구",
            region="동구",
            age=30,
            pre_founder=True,
        ),
    )

    assert extracted.eligibility_extraction_status is ProgramExtractionStatus.SUPPORTED
    assert result.match_status is MatchStatus.MATCH
    assert len(result.evidence) == 3


def test_extractor_failure_degrades_to_unknown_without_crashing(snapshot_path) -> None:
    class BrokenExtractor:
        def extract(self, item):
            del item
            raise RuntimeError("synthetic extractor failure")

    service = ProgramService(
        ProgramRepository(snapshot_path), extractor=BrokenExtractor()
    )

    response = service.match_program("PBLN_000000000125612", UserProfile())

    assert response.match_status is MatchStatus.UNKNOWN
    assert response.condition_results == []
