from __future__ import annotations

import html
import re
from dataclasses import dataclass

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
from app.schemas.program import Program


_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

_REFERENCE_MARKERS = re.compile(
    r"(?:자세한|세부)\s*(?:지원대상|신청자격|요건|지원내용)?\s*"
    r"(?:은|는|의)?\s*(?:공고문|별첨)\s*(?:참조|확인)|"
    r"신청자격\s*상이|지원요건을\s*충족|신청자격\s*및\s*요건"
)
_UNSUPPORTED_STUDENT = re.compile(r"대학\s*소속\s*대학\(원\)생|대학생")
_REVIEW_ONLY_MARKERS = re.compile(
    r"여성|교육\s*\d*\s*시간|교육\s*(?:이수|수료)|추천을\s*받은|"
    r"추천\s*기업|신고증을\s*보유|청년후계농|농업경영체|"
    r"중소기업|소상공인|법인|"
    r"(?:AI|ICT|바이오|콘텐츠|제조|신산업|GovTech|물안전|물환경|물이용)"
)

_REGION_PATTERN = re.compile(
    r"(?P<value>"
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종)(?:광역시|특별자치시)?"
    r"(?:\s+[가-힣]{1,8}(?:시|군|구))?|"
    r"(?:경기|강원|충북|충남|전북|전남|경북|경남|제주)(?:특별자치도|도|지역)?"
    r"(?:\s+[가-힣]{1,8}(?:시|군|구))?|"
    r"[가-힣]{1,8}(?:시|군|구)|대덕연구개발특구"
    r")\s*(?:에\s*)?"
    r"(?:관내|도내|지역\s*내|內|내|소재|주민등록상\s*주소|민)"
)
_REGION_AFTER_LOCATION_PATTERN = re.compile(
    r"(?:소재지가|주소지가|사업장이)\s*"
    r"(?P<value>경기|강원|충북|충남|전북|전남|경북|경남|제주)"
)
_REGION_GENDER_PATTERN = re.compile(
    r"(?P<value>서울|부산|대구|인천|광주|대전|울산|세종|"
    r"경기|강원|충북|충남|전북|전남|경북|경남|제주)"
    r"지역\s*여성\s*중"
)
_AGE_RANGE_PATTERN = re.compile(
    r"(?:만\s*)?(?P<minimum>\d{1,3})\s*세?\s*"
    r"(?:이상\s*)?(?:~|～|-)\s*(?:만\s*)?"
    r"(?P<maximum>\d{1,3})\s*세(?:\s*이하)?"
    r"|(?:만\s*)?(?P<minimum_words>\d{1,3})\s*세\s*이상\s*"
    r"(?:만\s*)?(?P<maximum_words>\d{1,3})\s*세\s*이하"
)
_AGE_BOUND_PATTERN = re.compile(
    r"(?:만\s*)?(?P<value>\d{1,3})\s*세\s*(?P<bound>이상|이하|미만|초과)"
)
_BUSINESS_AGE_RANGE_PATTERN = re.compile(
    r"(?P<minimum>\d{1,2})\s*년\s*초과\s*"
    r"(?P<maximum>\d{1,2})\s*년\s*(?:이내|이하)"
)
_BUSINESS_AGE_PATTERN = re.compile(
    r"(?:업력|사업\s*경력|창업(?:\s*후)?|창업\s*연차)\s*"
    r"(?P<value>\d{1,2})\s*(?P<unit>년|개월)\s*"
    r"(?P<bound>이내|이하|미만|이상|초과)|"
    r"(?P<leading_value>\d{1,2})\s*(?P<leading_unit>년|개월)\s*"
    r"(?P<leading_bound>이내|이하|미만|이상|초과)\s*"
    r"(?:기\s*창업자|창업기업|초기창업기업|스타트업)"
)
_PRE_FOUNDER_PATTERN = re.compile(
    r"(?:예비|\(예비\))\s*(?:여성\s*)?창업(?:자|가)"
)
_EXISTING_BUSINESS_PATTERN = re.compile(
    r"기\s*창업자|초기창업자|초기창업기업|창업기업|스타트업|사업자등록증상"
)
_COMPLETE_ALTERNATIVE_PATTERN = re.compile(
    r"예비.{0,12}창업.{0,100}(?:또는|/|,).{0,100}"
    r"(?:업력|\d{1,2}\s*년\s*(?:이내|이하|미만).{0,20}(?:기\s*창업자|창업기업))"
    r"|\(예비창업가\).{0,300}\(기창업자\)"
)
_INCOMPLETE_ALTERNATIVE_PATTERN = re.compile(
    r"예비.{0,12}창업.{0,80}(?:또는|/).{0,80}(?:초기창업|창업기업)"
)
_BRANCH_SPECIFIC_PATTERN = re.compile(r"\(아이디어\s*부문\)|\(사업화\s*부문\)")
_CONDITIONAL_REGION_ALTERNATIVE = re.compile(
    r"(?:주소지|거주지).{0,40}(?:또는|OR).{0,80}(?:주소\s*이전|전입)"
)


@dataclass(frozen=True)
class _ConditionDraft:
    condition_type: ConditionType
    subject: Subject
    operator: Operator
    raw_value: str
    evidence_text: str
    value: str | int | float | bool | None = None
    values: list[str | int | float | bool] | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: Unit = Unit.NONE


class EligibilityExtractor:
    """Conservative regex baseline over explicit Bizinfo eligibility text."""

    def extract(self, program: Program) -> ProgramEligibility:
        summary = _plain_text(program.summary_raw)
        target_text = _target_section(summary)
        if not target_text:
            return self._program(program, ProgramExtractionStatus.UNKNOWN)

        common_drafts: list[_ConditionDraft] = []
        group_drafts: list[list[_ConditionDraft]] = []

        region = (
            None
            if _CONDITIONAL_REGION_ALTERNATIVE.search(target_text)
            else _extract_region(target_text)
        )
        if region is not None:
            common_drafts.append(region)

        age_drafts = [] if _BRANCH_SPECIFIC_PATTERN.search(target_text) else _extract_age(target_text)
        common_drafts.extend(age_drafts)

        pre_founder = _extract_pre_founder(target_text)
        business_age = _extract_business_age(target_text)
        has_branch_specific_structure = bool(
            _BRANCH_SPECIFIC_PATTERN.search(target_text)
        )
        has_complete_alternative = bool(
            pre_founder
            and business_age
            and _COMPLETE_ALTERNATIVE_PATTERN.search(target_text)
            and not has_branch_specific_structure
        )
        has_incomplete_alternative = bool(
            pre_founder
            and not business_age
            and _INCOMPLETE_ALTERNATIVE_PATTERN.search(target_text)
        )

        if has_complete_alternative:
            group_drafts = [[pre_founder], business_age]
        elif not has_incomplete_alternative and not has_branch_specific_structure:
            if pre_founder is not None:
                common_drafts.append(pre_founder)
            common_drafts.extend(business_age)

        if not has_complete_alternative and pre_founder is None:
            existing_business = _extract_existing_business(target_text)
            if existing_business is not None:
                common_drafts.append(existing_business)

        status = self._program_status(
            target_text,
            has_conditions=bool(common_drafts or group_drafts),
            has_incomplete_alternative=has_incomplete_alternative,
        )
        return self._program(
            program,
            status,
            common_drafts=common_drafts,
            group_drafts=group_drafts,
        )

    @staticmethod
    def _program_status(
        target_text: str,
        *,
        has_conditions: bool,
        has_incomplete_alternative: bool,
    ) -> ProgramExtractionStatus:
        if _UNSUPPORTED_STUDENT.search(target_text):
            return ProgramExtractionStatus.UNSUPPORTED
        if not has_conditions:
            if _REFERENCE_MARKERS.search(target_text) or target_text:
                return ProgramExtractionStatus.NEEDS_REVIEW
            return ProgramExtractionStatus.UNKNOWN
        if (
            _REFERENCE_MARKERS.search(target_text)
            or _REVIEW_ONLY_MARKERS.search(target_text)
            or has_incomplete_alternative
            or _BRANCH_SPECIFIC_PATTERN.search(target_text)
        ):
            return ProgramExtractionStatus.NEEDS_REVIEW
        return ProgramExtractionStatus.SUPPORTED

    @staticmethod
    def _program(
        program: Program,
        status: ProgramExtractionStatus,
        *,
        common_drafts: list[_ConditionDraft] | None = None,
        group_drafts: list[list[_ConditionDraft]] | None = None,
    ) -> ProgramEligibility:
        sequence = 0

        def materialize(draft: _ConditionDraft) -> Condition:
            nonlocal sequence
            sequence += 1
            return Condition(
                condition_id=f"{program.program_id}:regex:{sequence}",
                condition_type=draft.condition_type,
                subject=draft.subject,
                operator=draft.operator,
                raw_value=draft.raw_value,
                value=draft.value,
                values=draft.values,
                min_value=draft.min_value,
                max_value=draft.max_value,
                unit=draft.unit,
                polarity=Polarity.INCLUDE,
                condition_role=ConditionRole.ELIGIBILITY_REQUIRED,
                evidence_text=draft.evidence_text,
                source_field="bsnsSumryCn",
                evidence_start=None,
                evidence_end=None,
                extraction_method=ExtractionMethod.REGEX,
                extraction_status=ExtractionStatus.SUPPORTED,
            )

        common = [materialize(draft) for draft in common_drafts or []]
        groups = [
            EligibilityGroup(
                group_id=f"{program.program_id}:group:{index}",
                conditions=[materialize(draft) for draft in drafts],
            )
            for index, drafts in enumerate(group_drafts or [], start=1)
        ]
        return ProgramEligibility(
            program_id=program.program_id,
            source_url=program.source_url,
            eligibility_extraction_status=status,
            common_conditions=common,
            eligibility_groups=groups,
        )


def _plain_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = _HTML_TAG.sub(" ", html.unescape(value))
    return _WHITESPACE.sub(" ", without_tags).strip()


def _target_section(summary: str) -> str:
    if "☞" not in summary:
        return ""
    return summary.split("☞", maxsplit=1)[1].split("☞", maxsplit=1)[0].strip()


def _evidence(text: str, match: re.Match[str], radius: int = 110) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return text[start:end].strip(" -")


def _canonical_region(value: str) -> str:
    normalized = _WHITESPACE.sub(" ", value).strip()
    return re.sub(r"(?:지역|도)$", "", normalized) if normalized not in {"제주도"} else normalized


def _extract_region(text: str) -> _ConditionDraft | None:
    matches = list(_REGION_PATTERN.finditer(text))
    matches.extend(_REGION_AFTER_LOCATION_PATTERN.finditer(text))
    matches.extend(_REGION_GENDER_PATTERN.finditer(text))
    for match in sorted(matches, key=lambda candidate: candidate.start()):
        value = _canonical_region(match.group("value"))
        if value == "전국" or value == "지역":
            continue
        return _ConditionDraft(
            condition_type=ConditionType.REGION_OR_LOCATION,
            subject=Subject.BUSINESS,
            operator=Operator.EQ,
            raw_value=match.group(0),
            value=value,
            evidence_text=_evidence(text, match),
        )
    return None


def _extract_age(text: str) -> list[_ConditionDraft]:
    range_match = _AGE_RANGE_PATTERN.search(text)
    if range_match:
        minimum = range_match.group("minimum") or range_match.group("minimum_words")
        maximum = range_match.group("maximum") or range_match.group("maximum_words")
        return [
            _ConditionDraft(
                condition_type=ConditionType.AGE,
                subject=Subject.APPLICANT,
                operator=Operator.BETWEEN,
                raw_value=range_match.group(0),
                min_value=float(minimum),
                max_value=float(maximum),
                unit=Unit.YEAR,
                evidence_text=_evidence(text, range_match),
            )
        ]

    match = _AGE_BOUND_PATTERN.search(text)
    if not match:
        return []
    operator = {
        "이상": Operator.GTE,
        "이하": Operator.LTE,
        "미만": Operator.LT,
        "초과": Operator.GT,
    }[match.group("bound")]
    return [
        _ConditionDraft(
            condition_type=ConditionType.AGE,
            subject=Subject.APPLICANT,
            operator=operator,
            raw_value=match.group(0),
            value=int(match.group("value")),
            unit=Unit.YEAR,
            evidence_text=_evidence(text, match),
        )
    ]


def _extract_business_age(text: str) -> list[_ConditionDraft]:
    range_match = _BUSINESS_AGE_RANGE_PATTERN.search(text)
    if range_match:
        evidence = _evidence(text, range_match)
        return [
            _ConditionDraft(
                condition_type=ConditionType.BUSINESS_AGE,
                subject=Subject.BUSINESS,
                operator=Operator.GT,
                raw_value=f"{range_match.group('minimum')}년 초과",
                value=int(range_match.group("minimum")),
                unit=Unit.YEAR,
                evidence_text=evidence,
            ),
            _ConditionDraft(
                condition_type=ConditionType.BUSINESS_AGE,
                subject=Subject.BUSINESS,
                operator=Operator.LTE,
                raw_value=f"{range_match.group('maximum')}년 이내",
                value=int(range_match.group("maximum")),
                unit=Unit.YEAR,
                evidence_text=evidence,
            ),
        ]

    match = _BUSINESS_AGE_PATTERN.search(text)
    if not match:
        return []
    value = match.group("value") or match.group("leading_value")
    unit_text = match.group("unit") or match.group("leading_unit")
    bound = match.group("bound") or match.group("leading_bound")
    operator = {
        "이내": Operator.LTE,
        "이하": Operator.LTE,
        "미만": Operator.LT,
        "이상": Operator.GTE,
        "초과": Operator.GT,
    }[bound]
    return [
        _ConditionDraft(
            condition_type=ConditionType.BUSINESS_AGE,
            subject=Subject.BUSINESS,
            operator=operator,
            raw_value=match.group(0),
            value=int(value),
            unit=Unit.YEAR if unit_text == "년" else Unit.MONTH,
            evidence_text=_evidence(text, match),
        )
    ]


def _extract_pre_founder(text: str) -> _ConditionDraft | None:
    match = _PRE_FOUNDER_PATTERN.search(text)
    if not match:
        return None
    return _ConditionDraft(
        condition_type=ConditionType.PRE_FOUNDER,
        subject=Subject.APPLICANT,
        operator=Operator.EQ,
        raw_value=match.group(0),
        value=True,
        evidence_text=_evidence(text, match),
    )


def _extract_existing_business(text: str) -> _ConditionDraft | None:
    match = _EXISTING_BUSINESS_PATTERN.search(text)
    if not match:
        return None
    return _ConditionDraft(
        condition_type=ConditionType.BUSINESS_REGISTRATION_STATUS,
        subject=Subject.BUSINESS,
        operator=Operator.IN,
        raw_value=match.group(0),
        values=["REGISTERED", "EXISTING_BUSINESS"],
        evidence_text=_evidence(text, match),
    )
