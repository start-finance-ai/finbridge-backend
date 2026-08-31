from __future__ import annotations

import re

from app.schemas.eligibility import Unit
from app.schemas.matching import BusinessStatus, UserProfile, UserType


_REGION_ALIASES = (
    ("서울특별시", "서울"),
    ("부산광역시", "부산"),
    ("대구광역시", "대구"),
    ("인천광역시", "인천"),
    ("광주광역시", "광주"),
    ("대전광역시", "대전"),
    ("울산광역시", "울산"),
    ("세종특별자치시", "세종"),
    ("경기도", "경기"),
    ("강원특별자치도", "강원"),
    ("강원도", "강원"),
    ("충청북도", "충북"),
    ("충청남도", "충남"),
    ("전북특별자치도", "전북"),
    ("전라북도", "전북"),
    ("전라남도", "전남"),
    ("경상북도", "경북"),
    ("경상남도", "경남"),
    ("제주특별자치도", "제주"),
    ("제주도", "제주"),
    *(
        (name, name)
        for name in (
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
    ),
)
_AGE = re.compile(r"(?<!\d)(?:만\s*)?(?P<value>\d{1,3})\s*세(?!기)")
_BUSINESS_AGE = re.compile(
    r"(?:업력|사업\s*경력)\s*(?P<value>\d{1,2}(?:\.\d+)?)\s*"
    r"(?P<unit>년|개월)"
)
_UNREGISTERED = re.compile(
    r"사업자\s*(?:등록)?\s*미등록|사업자등록(?:이|은)?\s*없는|미등록\s*사업자"
)
_PRE_FOUNDER = re.compile(r"예비\s*창업(?:자|가)?|창업\s*준비\s*중")
_EXISTING_BUSINESS = re.compile(
    r"기\s*창업자|기창업자|사업자\s*등록(?:을|이|은)?\s*(?:완료|보유|한)|"
    r"등록\s*사업자"
)
_OPEN_NOW = re.compile(
    r"(?:지금|현재|오늘)\s*(?:바로\s*)?(?:신청|접수)\s*(?:이\s*)?가능|"
    r"(?:지금|현재|오늘)\s*신청할\s*수\s*있는"
)
_PAST_NOTICE = re.compile(r"종료(?:된|한)?\s*공고|마감(?:된|한)?\s*공고|과거\s*공고")
_DEADLINE_SORT = re.compile(
    r"마감(?:일)?\s*(?:이\s*)?가까운|마감\s*임박|마감일?\s*순"
)


def extract_explicit_profile(message: str) -> UserProfile | None:
    values: dict[str, object] = {}

    for alias, canonical in _REGION_ALIASES:
        if alias in message:
            values["region"] = canonical
            values["business_region"] = canonical
            break

    age_match = _AGE.search(message)
    if age_match:
        age = int(age_match.group("value"))
        if age <= 100:
            values["age"] = age

    business_age_match = _BUSINESS_AGE.search(message)
    if business_age_match:
        values["business_age"] = float(business_age_match.group("value"))
        values["business_age_unit"] = (
            Unit.YEAR if business_age_match.group("unit") == "년" else Unit.MONTH
        )
        values["pre_founder"] = False
        values["business_status"] = BusinessStatus.EXISTING_BUSINESS

    is_pre_founder = bool(_PRE_FOUNDER.search(message))
    if is_pre_founder:
        values["pre_founder"] = True
        values["user_type"] = UserType.PRE_FOUNDER

    if _UNREGISTERED.search(message):
        values["business_status"] = BusinessStatus.UNREGISTERED
    elif _EXISTING_BUSINESS.search(message):
        values["pre_founder"] = False
        values["business_status"] = BusinessStatus.REGISTERED

    if "소상공인" in message:
        values["user_type"] = UserType.SMALL_BUSINESS_OWNER
        values.setdefault("pre_founder", False)
    elif "프리랜서" in message:
        values["user_type"] = UserType.FREELANCER

    return UserProfile(**values) if values else None


def merge_profiles(
    inferred: UserProfile | None, provided: UserProfile | None
) -> UserProfile | None:
    if inferred is None:
        return provided
    if provided is None:
        return inferred
    merged = inferred.model_dump()
    for field_name in provided.model_fields_set:
        merged[field_name] = getattr(provided, field_name)
    return UserProfile(**merged)


def requests_currently_open_programs(message: str) -> bool:
    return bool(_OPEN_NOW.search(message)) and not _PAST_NOTICE.search(message)


def requests_deadline_sort(message: str) -> bool:
    return bool(_DEADLINE_SORT.search(message))
