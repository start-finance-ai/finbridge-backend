from __future__ import annotations

import html
import re
from collections.abc import Iterable
from collections.abc import Callable
from datetime import date
from enum import IntEnum

from app.schemas.eligibility import (
    Condition,
    ConditionType,
    ExtractionStatus,
)
from app.schemas.matching import BusinessStatus, MatchStatus, UserType
from app.schemas.program import Program
from app.schemas.retrieval import (
    ProgramSearchProgram,
    ProgramSearchRequest,
    ProgramSearchResponse,
    ProgramSearchResult,
)
from app.services.program_service import ProgramService
from app.utils.date_parser import (
    ApplicationAvailability,
    ApplicationStatus,
    DeadlineType,
    calculate_application_availability,
    seoul_today,
)


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")
_REGION_EXCEPTION_RE = re.compile(
    r"타\s*지역(?:민|주민|거주자|기업)?.{0,100}(?:예외|신청|지원|이전|설립)|"
    r"(?:주소|거주지|사업장|본사|지사|지점).{0,120}"
    r"(?:이전|전입|설립).{0,30}(?:가능|예정)|"
    r"(?:소재|거주).{0,100}(?:또는|or).{0,100}"
    r"(?:이전|전입|설립).{0,30}(?:가능|예정)"
)
_NATIONWIDE_RE = re.compile(r"전국\s*(?:대상|소재|기업|예비|창업|지역)?")
_NATIONWIDE_REGION_MARKERS = (
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
)
_ALIASES = {
    "예비 창업": "예비창업",
    "예비 창업자": "예비창업자",
}
_PARTICLE_SUFFIXES = (
    "에서는",
    "으로부터",
    "에게서",
    "에서",
    "으로",
    "에게",
    "에는",
    "까지",
    "부터",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "과",
    "와",
    "도",
    "만",
)
_QUERY_STOP_WORDS = {
    "공고",
    "관련",
    "궁금해요",
    "사업",
    "신청",
    "알려줘",
    "알려주세요",
    "있나요",
    "있을까요",
    "있는",
    "중인데",
    "준비",
    "준비중",
    "찾아줘",
    "찾아주세요",
    "추천",
    "추천해줘",
    "받을",
    "정책",
    "정책지원",
    "지원",
    "지원금",
    "지원사업",
    "창업지원",
    "수",
}
_SEARCH_INTENT_TERMS = (
    "사업",
    "지원사업",
    "지원 사업",
    "지원금",
    "창업지원",
    "창업 지원",
    "정책지원",
    "정책 지원",
    "공고",
    "신청",
    "받을 수",
)
_NON_SEARCH_INTENT_TERMS = (
    "리스크",
    "위험 계산",
    "상환",
    "현금흐름",
    "원리금",
)
_FIELD_WEIGHTS = {
    "program_name": 50,
    "provider": 35,
    "executing_organization": 30,
    "category": 25,
    "subcategory": 22,
    "target_type": 18,
    "eligibility_evidence": 16,
    "summary": 10,
    "hashtags": 6,
}
_MATCHED_FIELD_ORDER = {
    name: index
    for index, name in enumerate(
        (
            "program_name",
            "provider",
            "executing_organization",
            "category",
            "subcategory",
            "region",
            "structured.region",
            "structured.business_status",
            "structured.age",
            "structured.business_age",
            "user_type",
            "structured.user_type",
            "industry",
            "structured.industry",
            "target_type",
            "eligibility_evidence",
            "summary",
            "hashtags",
        )
    )
}


class _RegionPriority(IntEnum):
    SAME_REGION = 0
    NATIONWIDE = 1
    OTHER_REGION_WITH_EXPLICIT_EXCEPTION = 2
    REGION_UNKNOWN = 3
    EXPLICIT_OTHER_REGION_ONLY = 4


class ProgramRetrievalService:
    def __init__(
        self,
        program_service: ProgramService,
        *,
        today_provider: Callable[[], date] | None = None,
    ) -> None:
        self._program_service = program_service
        self._today_provider = today_provider or seoul_today

    @staticmethod
    def is_program_search_intent(message: str) -> bool:
        normalized = normalize_text(message)
        has_positive = any(
            normalize_text(term) in normalized for term in _SEARCH_INTENT_TERMS
        )
        if not has_positive:
            return False
        has_non_search = any(
            normalize_text(term) in normalized for term in _NON_SEARCH_INTENT_TERMS
        )
        return not has_non_search

    def search(self, request: ProgramSearchRequest) -> ProgramSearchResponse:
        results: list[ProgramSearchResult] = []
        region_priority_by_id: dict[str, _RegionPriority] = {}
        today = self._today_provider()
        terms = query_terms(request.query) if request.query else []
        generic_intent_only = bool(
            request.query
            and not terms
            and self.is_program_search_intent(request.query)
        )
        for program in self._program_service.list_programs():
            availability = calculate_application_availability(
                deadline_type=program.deadline_type,
                apply_start=program.apply_start,
                apply_end=program.apply_end,
                today=today,
            )
            if request.open_now_only and availability.status in {
                ApplicationStatus.CLOSED,
                ApplicationStatus.UPCOMING,
            }:
                continue
            conditions = self._matching_conditions(program.program_id)
            filtered, structured_score, structured_fields = self._structured_filter(
                program, conditions, request
            )
            if filtered:
                continue

            region_priority = self._region_priority(
                program,
                conditions,
                request.region,
            )
            if region_priority is _RegionPriority.EXPLICIT_OTHER_REGION_ONLY:
                continue

            keyword_score, keyword_fields = self._keyword_score(
                program, conditions, request.query
            )
            if request.query and keyword_score == 0 and not generic_intent_only:
                continue

            matched_fields = sorted(
                {*structured_fields, *keyword_fields},
                key=lambda field: (_MATCHED_FIELD_ORDER.get(field, 999), field),
            )
            results.append(
                ProgramSearchResult(
                    program=self._summary(program, availability),
                    retrieval_score=structured_score + keyword_score,
                    matched_fields=matched_fields,
                    source=program.source,
                    source_url=program.source_url,
                )
            )
            region_priority_by_id[program.program_id] = region_priority

        if request.sort_by_deadline:
            results.sort(key=self._deadline_sort_key)
        else:
            results.sort(
                key=lambda result: (
                    region_priority_by_id[result.program.program_id],
                    -result.retrieval_score,
                    result.program.program_id,
                )
            )
        limited = results[: request.limit]
        return ProgramSearchResponse(
            results=limited,
            result_count=len(limited),
            limit=request.limit,
        )

    def _matching_conditions(self, program_id: str) -> list[Condition]:
        eligibility = self._program_service.get_program_eligibility(program_id)
        return [
            *eligibility.common_conditions,
            *(
                condition
                for group in eligibility.eligibility_groups
                for condition in group.conditions
            ),
            *eligibility.global_exclusions,
        ]

    def _structured_filter(
        self,
        program: Program,
        conditions: list[Condition],
        request: ProgramSearchRequest,
    ) -> tuple[bool, int, set[str]]:
        score = 0
        matched_fields: set[str] = set()

        if request.category:
            if not _matches_any(request.category, program.category, program.subcategory):
                return True, 0, set()
            score += 40
            matched_fields.add("category")

        if request.provider:
            if not _matches_any(
                request.provider, program.provider, program.executing_organization
            ):
                return True, 0, set()
            score += 40
            matched_fields.add(
                "provider"
                if _matches_any(request.provider, program.provider)
                else "executing_organization"
            )

        if request.region:
            region_conditions = _conditions_of(
                conditions, ConditionType.REGION_OR_LOCATION
            )
            condition_region_texts = [
                *(condition.value for condition in region_conditions),
                *(condition.evidence_text for condition in region_conditions),
            ]
            metadata_region_texts = [
                program.program_name,
                program.provider,
                program.executing_organization,
            ]
            if _matches_any(request.region, *condition_region_texts):
                score += 45
                matched_fields.add("structured.region")
            elif _matches_any(request.region, *metadata_region_texts):
                score += 30
                matched_fields.add("region")
            elif _all_supported(region_conditions) and not _has_region_exception(
                program
            ):
                return True, 0, set()

        if request.business_status:
            compatible = self._business_status_compatible(
                request.business_status, conditions
            )
            if compatible is False:
                return True, 0, set()
            if compatible is True:
                score += 40
                matched_fields.add("structured.business_status")

        if request.user_type:
            compatible = self._user_type_compatible(
                request.user_type, program, conditions
            )
            if compatible is False:
                return True, 0, set()
            if compatible is True:
                score += 35
                matched_fields.add(
                    "structured.user_type"
                    if request.user_type is UserType.PRE_FOUNDER
                    else "user_type"
                )

        if request.industry:
            industry_conditions = _conditions_of(conditions, ConditionType.INDUSTRY)
            structured_industry_texts = [
                *(condition.raw_value for condition in industry_conditions),
                *(condition.evidence_text for condition in industry_conditions),
            ]
            program_industry_texts = [
                program.program_name,
                program.summary_raw,
                program.hashtags_raw,
            ]
            if _matches_any(request.industry, *structured_industry_texts):
                score += 35
                matched_fields.add("structured.industry")
            elif _matches_any(request.industry, *program_industry_texts):
                score += 20
                matched_fields.add("industry")
            else:
                return True, 0, set()

        if request.profile is not None:
            filter_profile = request.profile.model_copy(
                update={
                    "region": None,
                    "business_region": None,
                    "industry": None,
                }
            )
            match = self._program_service.match_program(
                program.program_id, filter_profile
            )
            if match.match_status is MatchStatus.NO_MATCH:
                return True, 0, set()
            matched_types = {
                result.condition_type
                for result in match.condition_results
                if result.status is MatchStatus.MATCH and not result.is_exclusion
            }
            if ConditionType.AGE in matched_types:
                score += 35
                matched_fields.add("structured.age")
            if ConditionType.BUSINESS_AGE in matched_types:
                score += 35
                matched_fields.add("structured.business_age")

        return False, score, matched_fields

    @staticmethod
    def _region_priority(
        program: Program,
        conditions: list[Condition],
        requested_region: str | None,
    ) -> _RegionPriority:
        if not requested_region:
            return _RegionPriority.SAME_REGION

        region_conditions = _conditions_of(
            conditions, ConditionType.REGION_OR_LOCATION
        )
        condition_region_texts = [
            *(condition.value for condition in region_conditions),
            *(condition.evidence_text for condition in region_conditions),
        ]
        if _matches_any(requested_region, *condition_region_texts):
            return _RegionPriority.SAME_REGION
        if _matches_any(
            requested_region,
            program.program_name,
            program.provider,
            program.executing_organization,
        ):
            return _RegionPriority.SAME_REGION
        if _has_region_exception(program):
            return _RegionPriority.OTHER_REGION_WITH_EXPLICIT_EXCEPTION
        if _is_nationwide(program):
            return _RegionPriority.NATIONWIDE
        if region_conditions:
            return _RegionPriority.EXPLICIT_OTHER_REGION_ONLY
        return _RegionPriority.REGION_UNKNOWN

    @staticmethod
    def _business_status_compatible(
        requested: BusinessStatus,
        conditions: list[Condition],
    ) -> bool | None:
        pre_founder = _conditions_of(conditions, ConditionType.PRE_FOUNDER)
        registered = _conditions_of(
            conditions, ConditionType.BUSINESS_REGISTRATION_STATUS
        )
        explicit = [*pre_founder, *registered]
        if not explicit:
            return None

        if requested is BusinessStatus.PRE_FOUNDER:
            if pre_founder:
                return True
            return None if not _all_supported(registered) else False

        requested_value = requested.value
        supported_values = {
            str(value)
            for condition in registered
            if condition.extraction_status is ExtractionStatus.SUPPORTED
            for value in (condition.values or [])
        }
        if requested_value in supported_values:
            return True
        if registered and _all_supported(registered):
            return False
        return None

    def _user_type_compatible(
        self,
        requested: UserType,
        program: Program,
        conditions: list[Condition],
    ) -> bool | None:
        if requested is UserType.PRE_FOUNDER:
            return self._business_status_compatible(
                BusinessStatus.PRE_FOUNDER, conditions
            )
        keyword = {
            UserType.SMALL_BUSINESS_OWNER: "소상공인",
            UserType.FREELANCER: "프리랜서",
        }[requested]
        if _matches_any(
            keyword,
            program.program_name,
            program.target_type_raw,
            program.summary_raw,
            program.hashtags_raw,
        ):
            return True
        return None

    @staticmethod
    def _keyword_score(
        program: Program,
        conditions: list[Condition],
        query: str | None,
    ) -> tuple[int, set[str]]:
        if query is None:
            return 0, set()

        normalized_query = normalize_text(query)
        terms = query_terms(query)
        if not normalized_query or not terms:
            return 0, set()

        fields: dict[str, str | None] = {
            "program_name": program.program_name,
            "provider": program.provider,
            "executing_organization": program.executing_organization,
            "category": program.category,
            "subcategory": program.subcategory,
            "target_type": program.target_type_raw,
            "eligibility_evidence": " ".join(
                condition.evidence_text for condition in conditions
            ),
            "summary": program.summary_raw,
            "hashtags": program.hashtags_raw,
        }
        score = 0
        matched_fields: set[str] = set()
        for field_name, raw_text in fields.items():
            if field_name == "hashtags":
                continue
            normalized_field = normalize_text(raw_text or "")
            if not normalized_field:
                continue
            weight = _FIELD_WEIGHTS[field_name]
            if normalized_query == normalized_field:
                score += weight * 4
                matched_fields.add(field_name)
                continue
            if normalized_query in normalized_field:
                score += weight * 2
                matched_fields.add(field_name)
            token_hits = sum(term in normalized_field for term in terms)
            if token_hits:
                score += weight * token_hits
                matched_fields.add(field_name)

        hashtags = normalize_text(program.hashtags_raw or "")
        if matched_fields and hashtags:
            hashtag_hits = sum(term in hashtags for term in terms)
            if hashtag_hits:
                score += _FIELD_WEIGHTS["hashtags"] * hashtag_hits
                matched_fields.add("hashtags")
        return score, matched_fields

    @staticmethod
    def _summary(
        program: Program,
        availability: ApplicationAvailability,
    ) -> ProgramSearchProgram:
        return ProgramSearchProgram(
            program_id=program.program_id,
            program_name=program.program_name,
            provider=program.provider,
            executing_organization=program.executing_organization,
            category=program.category,
            subcategory=program.subcategory,
            target_text=program.target_type_raw,
            summary_text=program.summary_raw,
            apply_start=program.apply_start,
            apply_end=program.apply_end,
            apply_period_text=program.apply_period_text,
            deadline_type=program.deadline_type,
            application_status=availability.status,
            application_status_note=availability.note,
        )

    @staticmethod
    def _deadline_sort_key(result: ProgramSearchResult) -> tuple[object, ...]:
        program = result.program
        if (
            program.application_status is ApplicationStatus.OPEN
            and program.deadline_type is DeadlineType.FIXED_DATE
            and program.apply_end is not None
        ):
            status_rank = 0
            deadline = program.apply_end
        elif program.application_status is ApplicationStatus.OPEN:
            status_rank = 1
            deadline = date.max
        elif program.application_status is ApplicationStatus.NEEDS_CONFIRMATION:
            status_rank = 2
            deadline = date.max
        elif program.application_status is ApplicationStatus.UPCOMING:
            status_rank = 3
            deadline = program.apply_start or date.max
        else:
            status_rank = 4
            deadline = program.apply_end or date.max
        return (
            status_rank,
            deadline,
            -result.retrieval_score,
            program.program_id,
        )


def normalize_text(value: str) -> str:
    normalized = html.unescape(_HTML_TAG_RE.sub(" ", value)).casefold().strip()
    normalized = _PUNCTUATION_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    for source, target in _ALIASES.items():
        normalized = normalized.replace(source, target)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for token in normalize_text(query).split():
        stripped = _strip_particle(token)
        if len(stripped) < 2 or stripped in _QUERY_STOP_WORDS:
            continue
        if stripped not in terms:
            terms.append(stripped)
    return terms


def _strip_particle(token: str) -> str:
    for suffix in _PARTICLE_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 1:
            return token[: -len(suffix)]
    return token


def _matches_any(expected: str, *values: object | None) -> bool:
    normalized_expected = normalize_text(expected)
    return bool(normalized_expected) and any(
        normalized_expected in normalize_text(str(value))
        for value in values
        if value is not None
    )


def _conditions_of(
    conditions: Iterable[Condition], condition_type: ConditionType
) -> list[Condition]:
    return [
        condition
        for condition in conditions
        if condition.condition_type is condition_type
    ]


def _all_supported(conditions: list[Condition]) -> bool:
    return bool(conditions) and all(
        condition.extraction_status is ExtractionStatus.SUPPORTED
        for condition in conditions
    )


def _has_region_exception(program: Program) -> bool:
    summary = normalize_text(program.summary_raw or "")
    return bool(_REGION_EXCEPTION_RE.search(summary))


def _is_nationwide(program: Program) -> bool:
    searchable_text = normalize_text(
        " ".join(
            value
            for value in (
                program.program_name,
                program.target_type_raw,
                program.summary_raw,
            )
            if value
        )
    )
    if _NATIONWIDE_RE.search(searchable_text):
        return True
    hashtags = normalize_text(program.hashtags_raw or "")
    marker_count = sum(
        marker in hashtags for marker in _NATIONWIDE_REGION_MARKERS
    )
    return marker_count >= 8
