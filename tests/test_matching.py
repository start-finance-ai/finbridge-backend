from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.eligibility.matcher import EligibilityMatcher
from app.schemas.eligibility import (
    Condition,
    ConditionRole,
    ConditionType,
    EligibilityGroup,
    ExtractionMethod,
    ExtractionStatus,
    Operator,
    Polarity,
    ProgramEligibility,
    ProgramExtractionStatus,
    Subject,
    Unit,
)
from app.schemas.matching import BusinessEntityType, MatchStatus, UserProfile


def condition(
    condition_id: str,
    condition_type: ConditionType,
    *,
    operator: Operator = Operator.EQ,
    value=None,
    values=None,
    unit: Unit = Unit.NONE,
    polarity: Polarity = Polarity.INCLUDE,
    subject: Subject = Subject.BUSINESS,
    role: ConditionRole = ConditionRole.ELIGIBILITY_REQUIRED,
    evidence_text: str = "검증된 조건 원문",
) -> Condition:
    return Condition(
        condition_id=condition_id,
        condition_type=condition_type,
        subject=subject,
        operator=operator,
        raw_value=evidence_text,
        value=value,
        values=values,
        min_value=None,
        max_value=None,
        unit=unit,
        polarity=polarity,
        condition_role=role,
        evidence_text=evidence_text,
        source_field="bsnsSumryCn",
        evidence_start=None,
        evidence_end=None,
        extraction_method=ExtractionMethod.HUMAN,
        extraction_status=ExtractionStatus.SUPPORTED,
    )


def eligibility(
    *,
    status: ProgramExtractionStatus = ProgramExtractionStatus.SUPPORTED,
    common: list[Condition] | None = None,
    groups: list[EligibilityGroup] | None = None,
    exclusions: list[Condition] | None = None,
) -> ProgramEligibility:
    return ProgramEligibility(
        program_id="PBLN_TEST",
        source_url="https://example.invalid/program",
        eligibility_extraction_status=status,
        common_conditions=common or [],
        eligibility_groups=groups or [],
        global_exclusions=exclusions or [],
    )


def business_age_condition() -> Condition:
    return condition(
        "business-age",
        ConditionType.BUSINESS_AGE,
        operator=Operator.LTE,
        value=7,
        unit=Unit.YEAR,
    )


def test_case_1_business_age_three_years_is_match() -> None:
    result = EligibilityMatcher().match(
        eligibility(common=[business_age_condition()]),
        UserProfile(business_age=3),
    )

    assert result.match_status is MatchStatus.MATCH


def test_case_2_business_age_nine_years_is_no_match() -> None:
    result = EligibilityMatcher().match(
        eligibility(common=[business_age_condition()]),
        UserProfile(business_age=9),
    )

    assert result.match_status is MatchStatus.NO_MATCH


def test_case_3_missing_business_age_needs_review_not_no_match() -> None:
    result = EligibilityMatcher().match(
        eligibility(common=[business_age_condition()]), UserProfile()
    )

    assert result.match_status is MatchStatus.NEEDS_REVIEW


def test_business_age_year_and_month_units_compare_without_rounding() -> None:
    result = EligibilityMatcher().match(
        eligibility(
            common=[
                condition(
                    "business-age-months",
                    ConditionType.BUSINESS_AGE,
                    operator=Operator.GTE,
                    value=18,
                    unit=Unit.MONTH,
                )
            ]
        ),
        UserProfile(business_age=1.5, business_age_unit=Unit.YEAR),
    )

    assert result.match_status is MatchStatus.MATCH


def test_case_4_absent_region_condition_does_not_create_unknown() -> None:
    result = EligibilityMatcher().match(eligibility(), UserProfile())

    assert result.match_status is MatchStatus.MATCH
    assert result.condition_results == []


def test_broad_region_needs_review_for_district_requirement() -> None:
    region = condition(
        "region",
        ConditionType.REGION_OR_LOCATION,
        value="대구 서구",
    )

    result = EligibilityMatcher().match(
        eligibility(common=[region]),
        UserProfile(region="대구", business_region="대구"),
    )

    assert result.match_status is MatchStatus.NEEDS_REVIEW
    assert result.condition_results[0].reason == "REGION_DETAIL_REQUIRED"


def test_explicit_other_top_level_region_is_no_match() -> None:
    region = condition(
        "region",
        ConditionType.REGION_OR_LOCATION,
        value="울산광역시",
    )

    result = EligibilityMatcher().match(
        eligibility(common=[region]),
        UserProfile(region="대구", business_region="대구"),
    )

    assert result.match_status is MatchStatus.NO_MATCH


def test_specific_user_region_matches_broader_program_region() -> None:
    region = condition(
        "region",
        ConditionType.REGION_OR_LOCATION,
        value="대구광역시",
    )

    result = EligibilityMatcher().match(
        eligibility(common=[region]),
        UserProfile(region="대구 서구", business_region="대구 서구"),
    )

    assert result.match_status is MatchStatus.MATCH


def test_case_5_missing_appendix_program_cannot_match() -> None:
    result = EligibilityMatcher().match(
        eligibility(status=ProgramExtractionStatus.UNKNOWN), UserProfile()
    )

    assert result.match_status is MatchStatus.UNKNOWN


def test_unsupported_program_cannot_create_safe_match() -> None:
    result = EligibilityMatcher().match(
        eligibility(status=ProgramExtractionStatus.UNSUPPORTED), UserProfile()
    )

    assert result.match_status is MatchStatus.NEEDS_REVIEW


def test_case_6_corporation_exclusion_triggers_no_match_once() -> None:
    corporation_exclusion = condition(
        "corporation-exclusion",
        ConditionType.BUSINESS_TYPE,
        value="CORPORATION",
        polarity=Polarity.EXCLUDE,
        evidence_text="법인 제외",
    )
    result = EligibilityMatcher().match(
        eligibility(exclusions=[corporation_exclusion]),
        UserProfile(business_entity_type=BusinessEntityType.CORPORATION),
    )

    assert result.match_status is MatchStatus.NO_MATCH
    assert result.reason == "GLOBAL_EXCLUSION_TRIGGERED"
    assert result.condition_results[0].status is MatchStatus.MATCH


def test_one_or_group_can_satisfy_program() -> None:
    pre_founder = condition(
        "pre-founder",
        ConditionType.PRE_FOUNDER,
        value=True,
        subject=Subject.APPLICANT,
    )
    under_seven = business_age_condition().model_copy(
        update={"condition_id": "under-seven"}
    )
    result = EligibilityMatcher().match(
        eligibility(
            groups=[
                EligibilityGroup(group_id="G1", conditions=[pre_founder]),
                EligibilityGroup(group_id="G2", conditions=[under_seven]),
            ]
        ),
        UserProfile(pre_founder=True),
    )

    assert result.match_status is MatchStatus.MATCH


def test_all_or_groups_can_fail() -> None:
    result = EligibilityMatcher().match(
        eligibility(
            groups=[
                EligibilityGroup(
                    group_id="G1",
                    conditions=[
                        condition(
                            "pre-founder",
                            ConditionType.PRE_FOUNDER,
                            value=True,
                            subject=Subject.APPLICANT,
                        )
                    ],
                ),
                EligibilityGroup(
                    group_id="G2", conditions=[business_age_condition()]
                ),
            ]
        ),
        UserProfile(pre_founder=False, business_age=9),
    )

    assert result.match_status is MatchStatus.NO_MATCH


def test_global_exclusion_has_priority_over_positive_path() -> None:
    exclusion = condition(
        "corporation-exclusion",
        ConditionType.BUSINESS_TYPE,
        value="CORPORATION",
        polarity=Polarity.EXCLUDE,
    )
    result = EligibilityMatcher().match(
        eligibility(common=[business_age_condition()], exclusions=[exclusion]),
        UserProfile(
            business_age=3,
            business_entity_type=BusinessEntityType.CORPORATION,
        ),
    )

    assert result.match_status is MatchStatus.NO_MATCH
    assert result.reason == "GLOBAL_EXCLUSION_TRIGGERED"


def test_supported_condition_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        condition(
            "no-evidence",
            ConditionType.BUSINESS_AGE,
            operator=Operator.LTE,
            value=7,
            unit=Unit.YEAR,
            evidence_text="",
        )


def test_operator_operand_shape_is_validated() -> None:
    with pytest.raises(ValidationError):
        condition("missing-value", ConditionType.BUSINESS_TYPE)
