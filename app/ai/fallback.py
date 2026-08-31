from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.schemas.matching import MatchStatus


_CONDITION_LABELS = {
    "region_or_location": "지역",
    "age": "연령",
    "pre_founder": "예비창업 여부",
    "business_registration_status": "사업자등록 상태",
    "business_age": "업력",
    "industry": "업종",
    "business_type": "사업자 유형",
    "sales_or_income": "매출·소득",
    "employee_count": "종업원 수",
    "gender": "성별",
    "qualification_or_certification": "자격·인증",
    "education_completion": "교육 이수",
}
_STATUS_TEXT = {
    "OPEN": "현재 신청기간 내",
    "UPCOMING": "신청 시작 전",
    "CLOSED": "신청 종료",
    "NEEDS_CONFIRMATION": "공식 공고 확인 필요",
}


def build_template_reply(
    *,
    match_status: MatchStatus | None,
    has_program_context: bool,
    has_profile: bool,
    retrieval_attempted: bool = False,
    retrieval_result_count: int = 0,
    structured_context: Mapping[str, Any] | None = None,
) -> str:
    programs = list((structured_context or {}).get("programs") or [])
    if programs:
        return _build_structured_program_reply(programs, structured_context or {})

    if retrieval_attempted and retrieval_result_count == 0:
        return (
            "현재 확보된 공고 범위에서는 입력한 조건과 검색어에 맞는 후보를 찾지 "
            "못했습니다. 이는 실제 지원사업이 존재하지 않는다는 뜻은 아닙니다. "
            "지역이나 사업 단계를 바꿔 검색하고 기업마당 공식 공고도 확인해 주세요."
        )
    if match_status is MatchStatus.MATCH:
        return (
            "현재 입력하신 정보와 확보된 공고 조건을 비교한 결과, 확인된 조건에서는 "
            "일치하는 부분이 있습니다. 다만 최종 신청 자격을 보장하는 결과는 아니므로 "
            "신청 전 공식 공고를 확인해 주세요."
        )
    if match_status is MatchStatus.NO_MATCH:
        return (
            "현재 입력하신 정보와 확인된 공고 조건 중 일치하지 않는 항목이 있습니다. "
            "아래 근거와 공식 공고를 함께 확인해 주세요."
        )
    if match_status is MatchStatus.NEEDS_REVIEW:
        return (
            "현재 확인된 조건 외에 추가 확인이 필요한 항목이 있습니다. 아래 근거와 "
            "공식 공고를 함께 확인해 주세요."
        )
    if match_status is MatchStatus.UNKNOWN:
        return (
            "현재 확보된 정보만으로는 일부 자격조건을 판단하기 어렵습니다. 공식 공고의 "
            "세부 조건 확인이 필요합니다."
        )
    if retrieval_attempted:
        return (
            f"현재 확보된 공고 범위에서 관련 후보 {retrieval_result_count}건을 "
            "찾았습니다. 검색 순위는 자격 충족 확률이 아니므로 구조화된 결과와 공식 "
            "공고를 함께 확인해 주세요."
        )
    if has_program_context and not has_profile:
        return (
            "선택하신 공고 정보를 확인했습니다. 자격조건을 비교하려면 지역, 연령, "
            "현재 사업 단계 등 필요한 정보를 추가로 입력해 주세요."
        )
    if has_profile:
        return (
            "입력하신 프로필을 확인했습니다. 지원사업에서 공고를 선택하면 확보된 "
            "자격조건과 입력값을 비교해 안내할 수 있습니다."
        )
    return (
        "어떤 지원이 필요한지 확인했습니다. 정확한 조건 비교가 필요하다면 지역과 현재 "
        "사업 단계 등 필요한 정보만 추가로 알려주시거나 집중모드를 이용해 주세요."
    )


def _build_structured_program_reply(
    programs: list[Mapping[str, Any]],
    context: Mapping[str, Any],
) -> str:
    matches_by_id = {
        item["program_id"]: item for item in context.get("matches") or []
    }
    evidence_by_id: dict[str, list[Mapping[str, Any]]] = {}
    for item in context.get("evidence") or []:
        evidence_by_id.setdefault(item["program_id"], []).append(item)

    lines = [
        f"현재 확보된 공고 범위에서 후보 {len(programs)}건을 찾았습니다. "
        "검색 순위는 자격 충족 확률이 아니며, 아래 내용은 확보된 구조화 데이터만으로 "
        "정리했습니다."
    ]
    missing_labels: list[str] = []

    for index, program in enumerate(programs[:3], start=1):
        program_id = program["program_id"]
        match = matches_by_id.get(program_id)
        lines.append(f"\n{index}. {program['program_name']}")
        if match:
            condition_results = match.get("condition_results") or []
            confirmed = _expected_conditions(
                condition_results,
                lambda item: item.get("status") == "MATCH"
                and not item.get("is_exclusion"),
            )
            mismatched = _expected_conditions(
                condition_results,
                lambda item: (
                    item.get("status") == "NO_MATCH"
                    and not item.get("is_exclusion")
                )
                or (
                    item.get("status") == "MATCH"
                    and item.get("is_exclusion")
                ),
            )
            uncertain = _condition_names(
                condition_results,
                lambda item: item.get("status") in {"NEEDS_REVIEW", "UNKNOWN"},
            )
            missing = _condition_names(
                condition_results,
                lambda item: item.get("reason") == "REQUIRED_USER_VALUE_MISSING",
            )
            missing_labels.extend(missing)
            if confirmed:
                lines.append(f"현재 확인되는 조건은 {_join(confirmed)}입니다.")
            if mismatched:
                lines.append(f"입력과 맞지 않는 조건은 {_join(mismatched)}입니다.")
            if uncertain:
                lines.append(f"판단하기 어려운 조건은 {_join(uncertain)}입니다.")
            if missing:
                lines.append(f"추가로 필요한 사용자 정보는 {_join(missing)}입니다.")
            if not any((confirmed, mismatched, uncertain, missing)):
                lines.append(
                    "현재 확보된 구조화 조건만으로는 사용자 조건을 비교하기 어려워 "
                    "공식 공고 확인이 필요합니다."
                )
        else:
            evidence = evidence_by_id.get(program_id, [])
            condition_names = _condition_names(evidence, lambda item: True)
            if condition_names:
                lines.append(
                    f"공고에서 현재 구조화해 확인한 조건은 {_join(condition_names)}이며, "
                    "입력값과의 최종 비교는 추가 확인이 필요합니다."
                )
            else:
                lines.append(
                    "현재 확보된 데이터만으로는 자동 비교할 자격조건이 충분하지 않아 "
                    "공식 공고 확인이 필요합니다."
                )

        period = program.get("apply_period_text") or "공식 공고에서 확인 필요"
        status = _STATUS_TEXT.get(
            str(program.get("application_status")), "공식 공고 확인 필요"
        )
        note = program.get("application_status_note")
        lines.append(
            f"신청기간은 {period}이며 현재 상태는 {status}입니다."
            + (f" {note}." if note else "")
        )
        source_url = program.get("source_url")
        if source_url:
            lines.append(f"공식 출처: {source_url}")

    if len(programs) > 3:
        lines.append(
            f"\n나머지 {len(programs) - 3}건은 응답의 structured programs와 "
            "공식 출처에서 추가 후보로 확인할 수 있습니다."
        )

    unique_missing = list(dict.fromkeys(missing_labels))
    first_priority = (
        f"부족한 자격조건 정보({_join(unique_missing)})를 먼저 확인하세요."
        if unique_missing
        else "현재 입력값과 후보별 자격조건을 먼저 대조하세요."
    )
    method = next(
        (
            concise
            for program in programs[:3]
            if (concise := _concise_text(program.get("application_method_text")))
        ),
        None,
    )
    second_priority = "신청기간과 신청방법을 확인하세요."
    if method:
        second_priority += f" 확보된 신청방법 안내는 ‘{method}’입니다."
    lines.extend(
        [
            "\n준비사항 1순위: " + first_priority,
            "준비사항 2순위: " + second_priority,
            "준비사항 3순위: 공식 공고에서 최종 세부요건과 최신 접수 상태를 확인하세요.",
        ]
    )
    return "\n".join(lines)


def _expected_conditions(items, predicate) -> list[str]:
    return list(
        dict.fromkeys(
            text
            for item in items
            if predicate(item)
            if (text := _concise_text(item.get("raw_expected_value")))
        )
    )[:3]


def _condition_names(items, predicate) -> list[str]:
    return list(
        dict.fromkeys(
            _CONDITION_LABELS.get(
                str(item.get("condition_type")), str(item.get("condition_type"))
            )
            for item in items
            if predicate(item)
            if item.get("condition_type")
        )
    )


def _concise_text(value: object, limit: int = 180) -> str | None:
    if not isinstance(value, str):
        return None
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*selected, sentence])
        if len(candidate) > limit:
            break
        selected.append(sentence)
    return " ".join(selected) or None


def _join(values: list[str]) -> str:
    return ", ".join(values)
