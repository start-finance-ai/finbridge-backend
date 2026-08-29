from __future__ import annotations

from app.schemas.matching import MatchStatus


def build_template_reply(
    *,
    match_status: MatchStatus | None,
    has_program_context: bool,
    has_profile: bool,
    retrieval_attempted: bool = False,
    retrieval_result_count: int = 0,
) -> str:
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
    if retrieval_attempted and retrieval_result_count == 0:
        return (
            "현재 확보된 공고 범위에서는 조건에 맞는 후보를 찾지 못했습니다. "
            "검색어 또는 조건을 바꿔 다시 확인해 주세요."
        )
    if retrieval_attempted:
        return (
            f"현재 확보된 공고 범위에서 관련 후보 {retrieval_result_count}건을 "
            "찾았습니다. 검색 순위는 자격 충족 확률이 아니므로 아래 조건과 공식 "
            "공고를 함께 확인해 주세요."
        )
    if has_program_context and not has_profile:
        return (
            "선택하신 공고 정보를 확인했습니다. 자격조건을 비교하려면 지역, 연령, "
            "현재 사업 단계 등 필요한 정보를 추가로 입력해 주세요."
        )
    if has_profile:
        return (
            "입력하신 프로필을 확인했습니다. 현재 채팅 baseline은 특정 공고를 선택한 "
            "경우에만 자격조건을 비교할 수 있습니다. 지원사업에서 공고를 선택해 주세요."
        )
    return (
        "어떤 지원이 필요한지 확인했습니다. 정확한 조건 비교가 필요하다면 지역과 현재 "
        "사업 단계 등 필요한 정보만 추가로 알려주시거나 집중모드를 이용해 주세요."
    )
