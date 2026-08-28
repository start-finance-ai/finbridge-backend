#!/usr/bin/env python3
"""Profile local Bizinfo samples without modifying the raw evidence.

The text-pattern results produced by this script are review candidates, not
eligibility labels. Hashtags are intentionally excluded from all eligibility
and amount pattern searches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SampleSource:
    key: str
    name: str
    path: Path


SOURCES = (
    SampleSource(
        "finance",
        "금융",
        Path("data/raw/bizinfo/bizinfo_finance_sample.json"),
    ),
    SampleSource(
        "startup",
        "창업",
        Path("data/raw/bizinfo/bizinfo_startup_sample_100.json"),
    ),
    SampleSource(
        "management",
        "경영",
        Path("data/raw/bizinfo/bizinfo_management_sample.json"),
    ),
)

ELIGIBILITY_TEXT_FIELDS = (
    "pblancNm",
    "trgetNm",
    "bsnsSumryCn",
    "reqstMthPapersCn",
)
AMOUNT_TEXT_FIELDS = (
    "pblancNm",
    "bsnsSumryCn",
    "reqstMthPapersCn",
)
VALUE_DISTRIBUTION_FIELDS = (
    "trgetNm",
    "pldirSportRealmLclasCodeNm",
    "pldirSportRealmMlsfcCodeNm",
)

NUMBER_PATTERN = r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
MONEY_UNIT_PATTERN = r"(?:조|억|천만|백만|십만|만|천|백)?\s*원"
MONEY_PATTERN = rf"{NUMBER_PATTERN}\s*{MONEY_UNIT_PATTERN}"


@dataclass(frozen=True)
class PatternDefinition:
    key: str
    label: str
    patterns: tuple[str, ...]
    fields: tuple[str, ...] = ELIGIBILITY_TEXT_FIELDS
    false_positive_note: str = ""

    def compile(self) -> re.Pattern[str]:
        return re.compile("|".join(f"(?:{pattern})" for pattern in self.patterns), re.I)


CONDITION_DEFINITIONS = (
    PatternDefinition(
        "region_or_location",
        "지역 / 소재지",
        (
            r"서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주",
            r"소재지|소재|거주|주소지|관내|관외|사업장\s*위치|지역\s*(?:내|기업|소재)",
        ),
        false_positive_note=(
            "지역명이 사업명·기관명·지원 범위를 설명할 수 있어 실제 신청지역 제한과 동일하지 않다."
        ),
    ),
    PatternDefinition(
        "age",
        "연령",
        (
            r"(?:만\s*)?\d{1,2}\s*세",
            r"\d{1,2}\s*[~～\-]\s*\d{1,2}\s*세",
            r"연령|나이|출생",
            r"청년|중장년|고령자|시니어",
        ),
        false_positive_note=(
            "청년·중장년 등의 표현은 대상을 시사하지만 정확한 연령 경계값을 제공하지 않을 수 있다."
        ),
    ),
    PatternDefinition(
        "explicit_numeric_age",
        "명시적 숫자 연령",
        (
            r"(?:만\s*)?\d{1,2}\s*세",
            r"\d{1,2}\s*[~～\-]\s*\d{1,2}\s*세",
            r"\d{2,4}\s*년(?:생|\s*출생)",
        ),
        false_positive_note="생년 또는 연령 숫자가 신청자격이 아닌 설명 문맥에 있을 수 있다.",
    ),
    PatternDefinition(
        "pre_founder",
        "예비창업 여부",
        (
            r"예비\s*창업|창업\s*예정",
            r"사업자\s*등록.{0,30}(?:없|전|미등록)",
        ),
        false_positive_note="예비창업자가 지원대상이 아니라 교육·행사의 일반 독자일 수 있다.",
    ),
    PatternDefinition(
        "business_registration_status",
        "사업자 여부",
        (
            r"사업자\s*등록(?:증)?|사업자등록(?:증)?",
            r"개인\s*사업자|법인\s*사업자|기\s*창업|기창업|창업\s*기업",
            r"휴업|폐업",
        ),
        false_positive_note="사업자등록이 제출서류나 지원내용 문맥에만 등장할 수 있다.",
    ),
    PatternDefinition(
        "business_age",
        "사업 업력",
        (
            r"업력",
            r"(?:창업|설립|개업).{0,15}\d+\s*년",
            r"\d+\s*년\s*(?:이내|미만|이상|초과).{0,15}(?:기업|사업자|창업)",
        ),
        false_positive_note="지원사업 운영기간이나 경력연수가 업력으로 오탐될 수 있다.",
    ),
    PatternDefinition(
        "industry",
        "업종",
        (
            r"업종|영위|산업\s*분류|제외\s*업종",
            r"제조업|서비스업|관광업|농업|어업|수산업",
            r"콘텐츠\s*(?:기업|산업)|ICT\s*(?:기업|산업)",
        ),
        false_positive_note="지원 프로그램의 산업 주제나 지원내용일 수 있어 자격 업종 제한과 구분해야 한다.",
    ),
    PatternDefinition(
        "business_type",
        "사업자 유형",
        (
            r"중소\s*기업|소상공인|중견\s*기업|대기업",
            r"사회적\s*기업|벤처\s*기업|여성\s*기업|장애인\s*기업",
            r"개인\s*사업자|법인\s*(?:사업자|기업)|협동\s*조합",
        ),
        false_positive_note="기관명·사업명 또는 포괄적 정책대상 설명일 수 있다.",
    ),
    PatternDefinition(
        "sales_or_income",
        "매출 / 소득",
        (r"매출(?:액|규모)?|연\s*소득|소득\s*금액|수입\s*금액",),
        false_positive_note="성과목표나 지원효과의 매출 증가 표현일 수 있다.",
    ),
    PatternDefinition(
        "employee_count",
        "직원 수",
        (
            r"(?:상시\s*)?(?:근로자|종업원|직원)\s*(?:수|수는|수의)?\s*\d+\s*명",
            r"\d+\s*명\s*(?:미만|이하|이상|초과)?(?:의)?\s*(?:근로자|종업원|직원)",
            r"상시\s*근로자\s*(?:수)?|고용\s*인원",
            r"(?:업종|제조업|서비스업|운수업).{0,80}\d+\s*(?:명|인)\s*(?:미만|이하|이상|초과)",
        ),
        false_positive_note="신규 채용 목표나 지원 규모가 기존 직원 수 조건으로 오탐될 수 있다.",
    ),
    PatternDefinition(
        "gender",
        "성별",
        (
            r"여성|남성",
            r"(?<![가-힣])(?:여자|남자)(?![가-힣])",
        ),
        false_positive_note="여성기업·행사명 등의 분류 표현일 수 있고 개인 성별 조건과 동일하지 않다.",
    ),
    PatternDefinition(
        "qualification_or_certification",
        "특정 자격 / 인증",
        (
            r"자격증|면허증|허가증|신고증",
            r"(?:자격|인증|지정).{0,15}(?:보유|취득|기업|업체|요건)",
            r"(?:보유|취득).{0,15}(?:자격|인증|면허)",
        ),
        false_positive_note="제품 인증 취득 지원 등 지원내용이 신청자 보유요건으로 오탐될 수 있다.",
    ),
    PatternDefinition(
        "education_completion",
        "교육 이수",
        (
            r"교육.{0,20}(?:이수|수료)",
            r"(?:이수|수료).{0,20}교육",
            r"교육생|수료생|졸업(?:자|예정)",
        ),
        false_positive_note="선정 후 제공하는 교육·수료 지원이 사전 자격요건으로 오탐될 수 있다.",
    ),
    PatternDefinition(
        "recommendation_selection_evaluation",
        "추천 / 선정 / 평가 조건",
        (
            r"(?:기관|정부|지자체|학교|대학|협회).{0,20}추천",
            r"추천(?:을)?\s*받|추천\s*기업",
            r"선정\s*(?:기업|업체|대상|자)",
            r"(?:평가|심사).{0,25}(?:선정|통과)",
        ),
        false_positive_note="일반적인 선발·심사 절차가 신청 전제조건으로 오탐될 가능성이 높다.",
    ),
    PatternDefinition(
        "application_period",
        "신청기간",
        (r".+",),
        fields=("reqstBeginEndDe",),
        false_positive_note="값의 존재만 집계하며 날짜 해석은 별도 신청기간 분류 결과를 사용한다.",
    ),
    PatternDefinition(
        "support_amount_or_limit",
        "지원금액 / 융자한도 / 보조금액",
        (
            MONEY_PATTERN,
            r"융자\s*한도|대출\s*한도|보증\s*한도",
            r"보조금|지원금|지원액|상금|사업화\s*자금",
        ),
        fields=AMOUNT_TEXT_FIELDS,
        false_positive_note="금액이 총사업비·상금·비용 예시일 수 있어 개인별 실제 지원액과 동일하지 않다.",
    ),
)


AMOUNT_DEFINITIONS = (
    PatternDefinition(
        "explicit_won_amount",
        "원 단위 명시 금액",
        (MONEY_PATTERN,),
        fields=AMOUNT_TEXT_FIELDS,
    ),
    PatternDefinition(
        "maximum_amount",
        "최대 / 한도 / 이내 금액",
        (
            rf"(?:최대|한도)\s*(?:약\s*)?{MONEY_PATTERN}",
            rf"{MONEY_PATTERN}\s*(?:이내|이하|한도)",
            rf"(?:업체|기업|개인|건)당\s*(?:최대\s*)?{MONEY_PATTERN}",
        ),
        fields=AMOUNT_TEXT_FIELDS,
    ),
    PatternDefinition(
        "manwon_expression",
        "N만원 계열",
        (rf"{NUMBER_PATTERN}\s*(?:천만|백만|십만|만)\s*원",),
        fields=AMOUNT_TEXT_FIELDS,
    ),
    PatternDefinition(
        "eokwon_expression",
        "N억원 계열",
        (rf"{NUMBER_PATTERN}\s*(?:조|억)\s*원",),
        fields=AMOUNT_TEXT_FIELDS,
    ),
    PatternDefinition(
        "amount_range",
        "금액 범위",
        (
            rf"{MONEY_PATTERN}.{{0,20}}(?:~|～|부터|이상).{{0,20}}{MONEY_PATTERN}",
            rf"{MONEY_PATTERN}.{{0,20}}(?:이하|미만|초과)",
        ),
        fields=AMOUNT_TEXT_FIELDS,
    ),
    PatternDefinition(
        "ratio_support",
        "비율 지원",
        (
            rf"{NUMBER_PATTERN}\s*%|퍼센트|지원\s*비율|총\s*사업비의|자부담|전액\s*지원",
        ),
        fields=AMOUNT_TEXT_FIELDS,
    ),
    PatternDefinition(
        "loan_or_guarantee_limit",
        "융자 / 대출 / 보증 한도",
        (
            rf"(?:융자|대출|보증).{{0,60}}(?:한도|최대|이내|{MONEY_PATTERN})",
            rf"(?:한도|최대).{{0,60}}(?:융자|대출|보증)",
        ),
        fields=AMOUNT_TEXT_FIELDS,
    ),
    PatternDefinition(
        "grant_or_subsidy_amount",
        "보조금 / 지원금 / 사업화자금 금액",
        (
            rf"(?:보조금|지원금|지원액|상금|사업화\s*자금|사업비).{{0,80}}{MONEY_PATTERN}",
            rf"{MONEY_PATTERN}.{{0,80}}(?:보조금|지원금|지원액|상금|사업화\s*자금|사업비)",
        ),
        fields=AMOUNT_TEXT_FIELDS,
    ),
)


FIXED_DATE_RANGE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s*~\s*\d{4}-\d{2}-\d{2}$"
)
PERIOD_CLASSIFIERS = (
    ("fixed_date_range", "명확한 시작일 / 종료일", FIXED_DATE_RANGE_PATTERN),
    (
        "until_budget_exhausted",
        "예산 소진 시까지",
        re.compile(r"예산\s*소진\s*시\s*까지"),
    ),
    ("always_open", "상시 / 수시", re.compile(r"상시\s*접수|수시\s*(?:접수|모집)")),
    (
        "separate_notice_or_reference",
        "별도 문의 / 공지 / 공고문 참고",
        re.compile(r"추후\s*공지|별도\s*(?:문의|공지)|공고문\s*참고"),
    ),
    (
        "varies_by_subprogram",
        "차수 / 분야 / 세부사업별 상이",
        re.compile(r"상이"),
    ),
)

SUPPORT_CONTEXT_PATTERN = re.compile(
    r"지원|융자|대출|보증|보조금|지원금|상금|사업화\s*자금|사업비|한도|"
    r"이차보전|임차료|지급",
    re.I,
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def text_value(value: Any) -> str:
    if value is None:
        return ""
    raw_text = str(value)
    if "<" not in raw_text and "&" not in raw_text:
        return " ".join(raw_text.split())

    parser = TextExtractor()
    try:
        parser.feed(raw_text)
        parser.close()
    except Exception:
        return " ".join(raw_text.split())
    return " ".join(" ".join(parser.parts).split())


def is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def percentage(numerator: int, denominator: int) -> float:
    return round(numerator * 100 / denominator, 2) if denominator else 0.0


def load_samples() -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    by_category: dict[str, list[dict[str, Any]]] = {}
    source_metadata: dict[str, Any] = {}

    for source in SOURCES:
        path = REPOSITORY_ROOT / source.path
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes)
        if not isinstance(payload, dict) or not isinstance(payload.get("jsonArray"), list):
            raise ValueError(f"Invalid top-level jsonArray structure: {source.path}")
        if any(not isinstance(item, dict) for item in payload["jsonArray"]):
            raise ValueError(f"Non-object jsonArray item: {source.path}")

        items = payload["jsonArray"]
        by_category[source.key] = items
        source_metadata[source.key] = {
            "category_name": source.name,
            "path": source.path.as_posix(),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "item_count": len(items),
            "tot_cnt_values": sorted(
                {item["totCnt"] for item in items if "totCnt" in item},
                key=str,
            ),
        }

    return by_category, source_metadata


def iter_rows(
    by_category: dict[str, list[dict[str, Any]]],
) -> Iterable[tuple[str, dict[str, Any]]]:
    for source in SOURCES:
        for item in by_category[source.key]:
            yield source.key, item


def profile_rows(rows: Sequence[dict[str, Any]], all_fields: Sequence[str]) -> dict[str, Any]:
    total = len(rows)
    field_results: dict[str, Any] = {}
    for field in all_fields:
        present = sum(field in item for item in rows)
        non_empty = sum(field in item and is_non_empty(item[field]) for item in rows)
        field_results[field] = {
            "present_count": present,
            "non_empty_count": non_empty,
            "missing_or_empty_count": total - non_empty,
            "presence_rate_pct": percentage(present, total),
            "non_empty_rate_pct": percentage(non_empty, total),
        }
    return {"total_items": total, "fields": field_results}


def build_field_profiles(
    by_category: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    all_rows = [item for _, item in iter_rows(by_category)]
    all_fields = sorted({field for item in all_rows for field in item})

    def value_counts(rows: Sequence[dict[str, Any]], field: str) -> dict[str, int]:
        counts = Counter(
            text_value(item.get(field))
            for item in rows
            if is_non_empty(item.get(field))
        )
        return dict(sorted(counts.items(), key=lambda value: (-value[1], value[0])))

    return {
        "definitions": {
            "present_count": "해당 key가 존재하는 item 수",
            "non_empty_count": "값이 null 또는 빈 문자열/빈 collection이 아닌 item 수",
            "missing_or_empty_count": "전체 item 수 - non_empty_count",
            "presence_rate_pct": "present_count / 전체 item 수",
        },
        "field_count": len(all_fields),
        "overall": profile_rows(all_rows, all_fields),
        "by_category": {
            source.key: profile_rows(by_category[source.key], all_fields)
            for source in SOURCES
        },
        "selected_value_distributions": {
            field: {
                "overall": value_counts(all_rows, field),
                "by_category": {
                    source.key: value_counts(by_category[source.key], field)
                    for source in SOURCES
                },
            }
            for field in VALUE_DISTRIBUTION_FIELDS
        },
    }


def make_snippet(text: str, match: re.Match[str], radius: int = 90) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    prefix = "…" if start else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def split_text_chunks(text: str) -> list[str]:
    """Split summary text into local contexts without changing source data."""
    return [
        chunk.strip()
        for chunk in re.split(r"[☞※]|(?<=[.!?])\s+|\s+-\s+", text)
        if chunk.strip()
    ]


def matched_fields(
    item: dict[str, Any], definition: PatternDefinition, pattern: re.Pattern[str]
) -> list[tuple[str, re.Match[str], str]]:
    matches: list[tuple[str, re.Match[str], str]] = []
    for field in definition.fields:
        normalized = text_value(item.get(field))
        match = pattern.search(normalized)
        if match:
            matches.append((field, match, normalized))
    return matches


def choose_representatives(
    candidates: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for source in SOURCES:
        for candidate in candidates:
            if candidate["category"] != source.key:
                continue
            program_id = candidate["program_id"]
            if program_id not in seen_ids:
                selected.append(candidate)
                seen_ids.add(program_id)
                break
        if len(selected) >= limit:
            return selected

    for candidate in candidates:
        program_id = candidate["program_id"]
        if program_id in seen_ids:
            continue
        selected.append(candidate)
        seen_ids.add(program_id)
        if len(selected) >= limit:
            break
    return selected


def analyze_definitions(
    by_category: dict[str, list[dict[str, Any]]],
    definitions: Sequence[PatternDefinition],
    representative_limit: int,
) -> dict[str, Any]:
    total_items = sum(len(items) for items in by_category.values())
    results: dict[str, Any] = {}

    for definition in definitions:
        pattern = definition.compile()
        category_counts: Counter[str] = Counter()
        source_field_counts: Counter[str] = Counter()
        only_source_field_counts: Counter[str] = Counter()
        candidates: list[dict[str, Any]] = []

        for category, item in iter_rows(by_category):
            field_matches = matched_fields(item, definition, pattern)
            if not field_matches:
                continue

            category_counts[category] += 1
            for field, _, _ in field_matches:
                source_field_counts[field] += 1
            if len(field_matches) == 1:
                only_source_field_counts[field_matches[0][0]] += 1

            preferred = sorted(
                field_matches,
                key=lambda match: (
                    0 if match[0] == "bsnsSumryCn" else 1,
                    definition.fields.index(match[0]),
                ),
            )[0]
            field, match, normalized = preferred
            candidates.append(
                {
                    "category": category,
                    "program_id": item.get("pblancId"),
                    "program_name": item.get("pblancNm"),
                    "source_field": field,
                    "matched_text": match.group(0),
                    "snippet": make_snippet(normalized, match),
                }
            )

        program_count = sum(category_counts.values())
        results[definition.key] = {
            "label": definition.label,
            "program_count": program_count,
            "candidate_rate_pct": percentage(program_count, total_items),
            "by_category": {
                source.key: {
                    "count": category_counts[source.key],
                    "rate_pct": percentage(
                        category_counts[source.key], len(by_category[source.key])
                    ),
                }
                for source in SOURCES
            },
            "source_field_counts": dict(sorted(source_field_counts.items())),
            "only_source_field_counts": dict(
                sorted(only_source_field_counts.items())
            ),
            "false_positive_note": definition.false_positive_note,
            "representatives": choose_representatives(candidates, representative_limit),
        }
    return results


def classify_period(value: Any) -> str:
    normalized = text_value(value)
    if not normalized:
        return "missing"
    for key, _, pattern in PERIOD_CLASSIFIERS:
        if pattern.search(normalized):
            return key
    return "other_unstructured"


def analyze_periods(
    by_category: dict[str, list[dict[str, Any]]], representative_limit: int
) -> dict[str, Any]:
    labels = {key: label for key, label, _ in PERIOD_CLASSIFIERS}
    labels.update(
        {
            "other_unstructured": "기타 비정형",
            "missing": "결측",
        }
    )
    total_items = sum(len(items) for items in by_category.values())
    overall_counts: Counter[str] = Counter()
    category_counts: dict[str, Counter[str]] = {
        source.key: Counter() for source in SOURCES
    }
    examples: dict[str, list[dict[str, Any]]] = {key: [] for key in labels}

    for category, item in iter_rows(by_category):
        value = item.get("reqstBeginEndDe")
        classification = classify_period(value)
        overall_counts[classification] += 1
        category_counts[category][classification] += 1
        if len(examples[classification]) < representative_limit:
            examples[classification].append(
                {
                    "category": category,
                    "program_id": item.get("pblancId"),
                    "program_name": item.get("pblancNm"),
                    "raw_value": value,
                }
            )

    return {
        "method": (
            "reqstBeginEndDe 원문을 정규식으로 분류하며 날짜를 보정하거나 추정하지 않음"
        ),
        "overall": {
            key: {
                "label": label,
                "count": overall_counts[key],
                "rate_pct": percentage(overall_counts[key], total_items),
                "representatives": examples[key],
            }
            for key, label in labels.items()
        },
        "by_category": {
            source.key: {
                key: {
                    "count": category_counts[source.key][key],
                    "rate_pct": percentage(
                        category_counts[source.key][key],
                        len(by_category[source.key]),
                    ),
                }
                for key in labels
            }
            for source in SOURCES
        },
    }


def analyze_amounts(
    by_category: dict[str, list[dict[str, Any]]], representative_limit: int
) -> dict[str, Any]:
    raw_expression_results = analyze_definitions(
        by_category, AMOUNT_DEFINITIONS, representative_limit
    )
    support_context_results = analyze_amount_support_context(
        by_category, representative_limit
    )
    total_items = sum(len(items) for items in by_category.values())

    raw_explicit = raw_expression_results["explicit_won_amount"]
    raw_explicit_by_category = {
        key: value["count"] for key, value in raw_explicit["by_category"].items()
    }
    raw_expression_results["no_explicit_won_amount"] = {
        "label": "원 단위 금액 미표기",
        "program_count": total_items - raw_explicit["program_count"],
        "candidate_rate_pct": percentage(
            total_items - raw_explicit["program_count"], total_items
        ),
        "by_category": {
            source.key: {
                "count": len(by_category[source.key])
                - raw_explicit_by_category[source.key],
                "rate_pct": percentage(
                    len(by_category[source.key])
                    - raw_explicit_by_category[source.key],
                    len(by_category[source.key]),
                ),
            }
            for source in SOURCES
        },
        "source_field_counts": {},
        "only_source_field_counts": {},
        "false_positive_note": (
            "정규식이 한글 수사 또는 원 단위가 없는 금액 표현을 놓칠 수 있으므로 실제 금액 부재 확정이 아님"
        ),
        "representatives": [],
    }

    support_explicit = support_context_results["explicit_won_amount"]
    support_explicit_by_category = {
        key: value["count"]
        for key, value in support_explicit["by_category"].items()
    }
    support_context_results["no_detected_support_context_won_amount"] = {
        "label": "지원 문맥 내 원 단위 금액 미탐지",
        "program_count": total_items - support_explicit["program_count"],
        "candidate_rate_pct": percentage(
            total_items - support_explicit["program_count"], total_items
        ),
        "by_category": {
            source.key: {
                "count": len(by_category[source.key])
                - support_explicit_by_category[source.key],
                "rate_pct": percentage(
                    len(by_category[source.key])
                    - support_explicit_by_category[source.key],
                    len(by_category[source.key]),
                ),
            }
            for source in SOURCES
        },
        "source_field_counts": {},
        "only_source_field_counts": {},
        "false_positive_note": (
            "지원 문맥 휴리스틱의 미탐지 가능성이 있으므로 실제 지원금액 부재 확정이 아님"
        ),
        "representatives": [],
    }

    return {
        "method": (
            "pblancNm, bsnsSumryCn, reqstMthPapersCn에서 원문 표현을 탐지하며 "
            "숫자·단위 환산이나 지원액 정규화를 수행하지 않음"
        ),
        "raw_money_expression_patterns": raw_expression_results,
        "support_context_method": (
            "동일 text chunk 안에 금액 패턴과 지원·융자·대출·보증·보조금·한도 등 "
            "문맥 표지가 함께 있는 후보만 별도 집계; Eligibility 금액과의 혼동 및 "
            "false negative 가능성이 있어 확정 지원금액으로 사용하지 않음"
        ),
        "support_context_patterns": support_context_results,
    }


def analyze_amount_support_context(
    by_category: dict[str, list[dict[str, Any]]], representative_limit: int
) -> dict[str, Any]:
    total_items = sum(len(items) for items in by_category.values())
    results: dict[str, Any] = {}

    for definition in AMOUNT_DEFINITIONS:
        pattern = definition.compile()
        category_counts: Counter[str] = Counter()
        source_field_counts: Counter[str] = Counter()
        only_source_field_counts: Counter[str] = Counter()
        candidates: list[dict[str, Any]] = []

        for category, item in iter_rows(by_category):
            field_matches: list[tuple[str, re.Match[str], str]] = []
            for field in definition.fields:
                for chunk in split_text_chunks(text_value(item.get(field))):
                    match = pattern.search(chunk)
                    if match and SUPPORT_CONTEXT_PATTERN.search(chunk):
                        field_matches.append((field, match, chunk))
                        break

            if not field_matches:
                continue

            category_counts[category] += 1
            for field, _, _ in field_matches:
                source_field_counts[field] += 1
            if len(field_matches) == 1:
                only_source_field_counts[field_matches[0][0]] += 1

            field, match, chunk = sorted(
                field_matches,
                key=lambda value: (
                    0 if value[0] == "bsnsSumryCn" else 1,
                    definition.fields.index(value[0]),
                ),
            )[0]
            candidates.append(
                {
                    "category": category,
                    "program_id": item.get("pblancId"),
                    "program_name": item.get("pblancNm"),
                    "source_field": field,
                    "matched_text": match.group(0),
                    "snippet": make_snippet(chunk, match),
                }
            )

        program_count = sum(category_counts.values())
        results[definition.key] = {
            "label": definition.label,
            "program_count": program_count,
            "candidate_rate_pct": percentage(program_count, total_items),
            "by_category": {
                source.key: {
                    "count": category_counts[source.key],
                    "rate_pct": percentage(
                        category_counts[source.key], len(by_category[source.key])
                    ),
                }
                for source in SOURCES
            },
            "source_field_counts": dict(sorted(source_field_counts.items())),
            "only_source_field_counts": dict(
                sorted(only_source_field_counts.items())
            ),
            "false_positive_note": (
                "동일 문맥 내 표지 기반 후보이며 실제 수혜 금액·한도 확정값이 아님"
            ),
            "representatives": choose_representatives(candidates, representative_limit),
        }

    return results


def build_report(representative_limit: int) -> dict[str, Any]:
    by_category, source_metadata = load_samples()
    all_rows = list(iter_rows(by_category))
    program_ids = [item.get("pblancId") for _, item in all_rows]
    id_counts = Counter(program_ids)

    return {
        "analysis_scope": {
            "source_metadata": source_metadata,
            "total_items": len(all_rows),
            "unique_pblanc_ids": len(id_counts),
            "duplicate_pblanc_id_count": sum(
                count > 1 for count in id_counts.values()
            ),
            "network_or_llm_used": False,
            "raw_files_modified": False,
        },
        "methodology": {
            "eligibility_text_fields": list(ELIGIBILITY_TEXT_FIELDS),
            "amount_text_fields": list(AMOUNT_TEXT_FIELDS),
            "hashtags_as_eligibility_evidence": False,
            "trgetNm_interpretation": (
                "coarse target description; keyword hit is not final eligibility evidence"
            ),
            "pattern_result_interpretation": (
                "deterministic keyword/regex review candidates, not eligibility labels"
            ),
            "source_field_count_note": (
                "한 공고가 여러 field에서 탐지되면 source_field_counts 합계가 program_count보다 클 수 있음"
            ),
        },
        "field_profiles": build_field_profiles(by_category),
        "eligibility_candidates": analyze_definitions(
            by_category, CONDITION_DEFINITIONS, representative_limit
        ),
        "application_period_patterns": analyze_periods(
            by_category, representative_limit
        ),
        "support_amount_patterns": analyze_amounts(
            by_category, representative_limit
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze the three local Bizinfo raw sample files."
    )
    parser.add_argument(
        "--section",
        choices=("full", "scope", "fields", "eligibility", "periods", "amounts"),
        default="full",
        help="Limit JSON output to one report section.",
    )
    parser.add_argument(
        "--representatives",
        type=int,
        default=3,
        help="Maximum representative programs per detected pattern (default: 3).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.representatives < 0:
        print("--representatives must be zero or greater", file=sys.stderr)
        return 2

    try:
        report = build_report(args.representatives)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        print(f"Analysis failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    section_map = {
        "scope": "analysis_scope",
        "fields": "field_profiles",
        "eligibility": "eligibility_candidates",
        "periods": "application_period_patterns",
        "amounts": "support_amount_patterns",
    }
    output: Any = report
    if args.section != "full":
        output = report[section_map[args.section]]

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
