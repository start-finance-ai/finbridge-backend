from __future__ import annotations

from enum import Enum
from typing import Any

from app.schemas.eligibility import (
    Condition,
    ConditionType,
    ExtractionStatus,
    Operator,
    ProgramEligibility,
    ProgramExtractionStatus,
    Subject,
    Unit,
    enum_or_value,
)
from app.schemas.matching import (
    BusinessStatus,
    ConditionEvidence,
    ConditionResult,
    MatchEvaluation,
    MatchStatus,
    UserProfile,
    UserType,
)


_MISSING = object()


class EligibilityMatcher:
    def match(
        self, eligibility: ProgramEligibility, profile: UserProfile
    ) -> MatchEvaluation:
        exclusion_results = [
            self._evaluate_condition(condition, profile, is_exclusion=True)
            for condition in eligibility.global_exclusions
        ]
        common_results = [
            self._evaluate_condition(condition, profile, is_exclusion=False)
            for condition in eligibility.common_conditions
        ]
        group_results = [
            [
                self._evaluate_condition(condition, profile, is_exclusion=False)
                for condition in group.conditions
            ]
            for group in eligibility.eligibility_groups
        ]

        condition_results = [
            *exclusion_results,
            *common_results,
            *(result for group in group_results for result in group),
        ]
        evidence = [result.evidence for result in condition_results]

        if any(result.status is MatchStatus.MATCH for result in exclusion_results):
            return MatchEvaluation(
                match_status=MatchStatus.NO_MATCH,
                condition_results=condition_results,
                evidence=evidence,
                reason="GLOBAL_EXCLUSION_TRIGGERED",
            )

        if any(result.status is MatchStatus.NO_MATCH for result in common_results):
            return MatchEvaluation(
                match_status=MatchStatus.NO_MATCH,
                condition_results=condition_results,
                evidence=evidence,
                reason="COMMON_CONDITION_NOT_MET",
            )

        if group_results:
            group_satisfied = any(
                all(result.status is MatchStatus.MATCH for result in group)
                for group in group_results
            )
            all_groups_failed = all(
                any(result.status is MatchStatus.NO_MATCH for result in group)
                for group in group_results
            )
        else:
            group_satisfied = True
            all_groups_failed = False

        if not group_satisfied and all_groups_failed:
            return MatchEvaluation(
                match_status=MatchStatus.NO_MATCH,
                condition_results=condition_results,
                evidence=evidence,
                reason="ALL_ELIGIBILITY_GROUPS_FAILED",
            )

        program_gate = self._program_gate_status(
            eligibility.eligibility_extraction_status
        )
        if program_gate is not None:
            return MatchEvaluation(
                match_status=program_gate,
                condition_results=condition_results,
                evidence=evidence,
                reason=f"PROGRAM_ELIGIBILITY_{eligibility.eligibility_extraction_status.value}",
            )

        unresolved_common_results = [
            result
            for result in common_results
            if result.status in {MatchStatus.NEEDS_REVIEW, MatchStatus.UNKNOWN}
        ]
        if unresolved_common_results:
            unresolved_status = (
                MatchStatus.UNKNOWN
                if any(
                    result.status is MatchStatus.UNKNOWN
                    for result in unresolved_common_results
                )
                else MatchStatus.NEEDS_REVIEW
            )
            return MatchEvaluation(
                match_status=unresolved_status,
                condition_results=condition_results,
                evidence=evidence,
                reason="CONDITION_COMPARISON_INCOMPLETE",
            )

        if group_satisfied:
            return MatchEvaluation(
                match_status=MatchStatus.MATCH,
                condition_results=condition_results,
                evidence=evidence,
                reason="ELIGIBILITY_PATH_SATISFIED",
            )

        unresolved_group_results = [
            result
            for group in group_results
            for result in group
            if result.status in {MatchStatus.NEEDS_REVIEW, MatchStatus.UNKNOWN}
        ]
        if unresolved_group_results:
            unresolved_status = (
                MatchStatus.UNKNOWN
                if any(
                    result.status is MatchStatus.UNKNOWN
                    for result in unresolved_group_results
                )
                else MatchStatus.NEEDS_REVIEW
            )
            return MatchEvaluation(
                match_status=unresolved_status,
                condition_results=condition_results,
                evidence=evidence,
                reason="CONDITION_COMPARISON_INCOMPLETE",
            )

        return MatchEvaluation(
            match_status=MatchStatus.NEEDS_REVIEW,
            condition_results=condition_results,
            evidence=evidence,
            reason="ELIGIBILITY_REVIEW_REQUIRED",
        )

    @staticmethod
    def _program_gate_status(
        status: ProgramExtractionStatus,
    ) -> MatchStatus | None:
        if status is ProgramExtractionStatus.SUPPORTED:
            return None
        if status is ProgramExtractionStatus.UNKNOWN:
            return MatchStatus.UNKNOWN
        return MatchStatus.NEEDS_REVIEW

    def _evaluate_condition(
        self,
        condition: Condition,
        profile: UserProfile,
        *,
        is_exclusion: bool,
    ) -> ConditionResult:
        evidence = ConditionEvidence(
            condition_id=condition.condition_id,
            condition_type=condition.condition_type,
            source_field=condition.source_field,
            evidence_text=condition.evidence_text,
        )

        if condition.extraction_status is ExtractionStatus.UNKNOWN:
            return self._result(
                condition,
                MatchStatus.UNKNOWN,
                is_exclusion,
                None,
                "SOURCE_CONDITION_UNKNOWN",
                evidence,
            )
        if condition.extraction_status is not ExtractionStatus.SUPPORTED:
            return self._result(
                condition,
                MatchStatus.NEEDS_REVIEW,
                is_exclusion,
                None,
                "CONDITION_NOT_SUPPORTED_FOR_AUTOMATIC_MATCHING",
                evidence,
            )

        actual_value = self._profile_value(condition, profile)
        if actual_value is _MISSING:
            return self._result(
                condition,
                MatchStatus.NEEDS_REVIEW,
                is_exclusion,
                None,
                "REQUIRED_USER_VALUE_MISSING",
                evidence,
            )

        predicate_result = self._evaluate_predicate(condition, actual_value)
        return self._result(
            condition,
            MatchStatus.MATCH if predicate_result else MatchStatus.NO_MATCH,
            is_exclusion,
            actual_value,
            "PREDICATE_TRUE" if predicate_result else "PREDICATE_FALSE",
            evidence,
        )

    @staticmethod
    def _result(
        condition: Condition,
        status: MatchStatus,
        is_exclusion: bool,
        actual_value: Any,
        reason: str,
        evidence: ConditionEvidence,
    ) -> ConditionResult:
        return ConditionResult(
            condition_id=condition.condition_id,
            condition_type=condition.condition_type,
            status=status,
            is_exclusion=is_exclusion,
            actual_value=enum_or_value(actual_value),
            raw_expected_value=condition.raw_value,
            reason=reason,
            evidence=evidence,
        )

    def _profile_value(self, condition: Condition, profile: UserProfile) -> Any:
        condition_type = condition.condition_type
        if condition_type is ConditionType.REGION_OR_LOCATION:
            if condition.subject is Subject.BUSINESS:
                return profile.business_region or profile.region or _MISSING
            return profile.region or _MISSING
        if condition_type is ConditionType.AGE:
            return profile.age if profile.age is not None else _MISSING
        if condition_type is ConditionType.PRE_FOUNDER:
            if profile.pre_founder is not None:
                return profile.pre_founder
            if profile.user_type is UserType.PRE_FOUNDER:
                return True
            if profile.business_status is BusinessStatus.PRE_FOUNDER:
                return True
            return _MISSING
        if condition_type is ConditionType.BUSINESS_REGISTRATION_STATUS:
            return profile.business_status or _MISSING
        if condition_type is ConditionType.BUSINESS_AGE:
            if profile.business_age is None:
                return _MISSING
            if condition.unit not in {Unit.YEAR, Unit.MONTH}:
                return _MISSING
            months = profile.business_age * (
                12 if profile.business_age_unit is Unit.YEAR else 1
            )
            return months / 12 if condition.unit is Unit.YEAR else months
        if condition_type is ConditionType.INDUSTRY:
            return profile.industry or _MISSING
        if condition_type is ConditionType.BUSINESS_TYPE:
            return profile.business_entity_type or _MISSING
        if condition_type is ConditionType.SALES_OR_INCOME:
            return (
                profile.sales_or_income
                if profile.sales_or_income is not None
                else _MISSING
            )
        if condition_type is ConditionType.EMPLOYEE_COUNT:
            return (
                profile.employee_count
                if profile.employee_count is not None
                else _MISSING
            )
        if condition_type is ConditionType.GENDER:
            return profile.gender or _MISSING
        if condition_type is ConditionType.QUALIFICATION_OR_CERTIFICATION:
            return (
                profile.certifications
                if profile.certifications is not None
                else _MISSING
            )
        if condition_type is ConditionType.EDUCATION_COMPLETION:
            return (
                profile.completed_education
                if profile.completed_education is not None
                else _MISSING
            )
        return _MISSING

    def _evaluate_predicate(self, condition: Condition, actual_value: Any) -> bool:
        actual_value = enum_or_value(actual_value)
        if condition.operator is Operator.EXISTS:
            if isinstance(actual_value, (list, tuple, set, dict, str)):
                return len(actual_value) > 0
            return actual_value is not None

        if condition.operator is Operator.EQ:
            return self._equals(actual_value, condition.value)
        if condition.operator is Operator.IN:
            assert condition.values is not None
            if isinstance(actual_value, (list, tuple, set)):
                return any(
                    self._equals(item, expected)
                    for item in actual_value
                    for expected in condition.values
                )
            return any(
                self._equals(actual_value, expected) for expected in condition.values
            )

        if isinstance(actual_value, bool) or not isinstance(actual_value, (int, float)):
            return False
        numeric_actual = float(actual_value)
        if condition.operator is Operator.BETWEEN:
            assert condition.min_value is not None
            assert condition.max_value is not None
            return condition.min_value <= numeric_actual <= condition.max_value

        expected = condition.value
        if isinstance(expected, bool) or not isinstance(expected, (int, float)):
            return False
        numeric_expected = float(expected)
        if condition.operator is Operator.GT:
            return numeric_actual > numeric_expected
        if condition.operator is Operator.GTE:
            return numeric_actual >= numeric_expected
        if condition.operator is Operator.LT:
            return numeric_actual < numeric_expected
        if condition.operator is Operator.LTE:
            return numeric_actual <= numeric_expected
        return False

    @staticmethod
    def _equals(actual: Any, expected: Any) -> bool:
        actual = actual.value if isinstance(actual, Enum) else actual
        expected = expected.value if isinstance(expected, Enum) else expected
        if isinstance(actual, (list, tuple, set)):
            return any(EligibilityMatcher._equals(item, expected) for item in actual)
        if isinstance(actual, str) and isinstance(expected, str):
            return actual.strip().casefold() == expected.strip().casefold()
        return actual == expected
