from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class DeadlineType(str, Enum):
    FIXED_DATE = "FIXED_DATE"
    UNTIL_BUDGET_EXHAUSTED = "UNTIL_BUDGET_EXHAUSTED"
    ALWAYS_OPEN = "ALWAYS_OPEN"
    SEE_ANNOUNCEMENT = "SEE_ANNOUNCEMENT"
    VARIABLE = "VARIABLE"
    UNKNOWN = "UNKNOWN"


class ApplicationStatus(str, Enum):
    OPEN = "OPEN"
    UPCOMING = "UPCOMING"
    CLOSED = "CLOSED"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"


@dataclass(frozen=True, slots=True)
class ApplicationPeriod:
    raw_text: str | None
    start: date | None
    end: date | None
    deadline_type: DeadlineType


@dataclass(frozen=True, slots=True)
class ApplicationAvailability:
    status: ApplicationStatus
    note: str | None = None


_DATE_RANGE = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2})\s*[~～]\s*(\d{4}-\d{2}-\d{2})\s*$"
)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
try:
    _SEOUL_TIME_ZONE = ZoneInfo("Asia/Seoul")
except ZoneInfoNotFoundError:
    # Some minimal Windows Python distributions do not bundle the IANA tzdb.
    # Korea has no DST, so UTC+09:00 preserves the same calendar-date semantics.
    _SEOUL_TIME_ZONE = timezone(timedelta(hours=9), name="Asia/Seoul")


def seoul_today() -> date:
    return datetime.now(_SEOUL_TIME_ZONE).date()


def calculate_application_availability(
    *,
    deadline_type: DeadlineType,
    apply_start: date | None,
    apply_end: date | None,
    today: date | None = None,
) -> ApplicationAvailability:
    reference_date = today or seoul_today()

    if deadline_type is DeadlineType.ALWAYS_OPEN:
        return ApplicationAvailability(ApplicationStatus.OPEN)
    if deadline_type is DeadlineType.UNTIL_BUDGET_EXHAUSTED:
        return ApplicationAvailability(
            ApplicationStatus.NEEDS_CONFIRMATION,
            "예산 소진 여부는 공식 공고에서 확인 필요",
        )
    if deadline_type is not DeadlineType.FIXED_DATE:
        return ApplicationAvailability(
            ApplicationStatus.NEEDS_CONFIRMATION,
            "신청 가능 여부는 공식 공고에서 확인 필요",
        )
    if apply_start is None or apply_end is None or apply_start > apply_end:
        return ApplicationAvailability(
            ApplicationStatus.NEEDS_CONFIRMATION,
            "신청기간 날짜가 불완전하여 공식 공고에서 확인 필요",
        )
    if reference_date < apply_start:
        return ApplicationAvailability(ApplicationStatus.UPCOMING)
    if reference_date > apply_end:
        return ApplicationAvailability(ApplicationStatus.CLOSED)
    return ApplicationAvailability(ApplicationStatus.OPEN)


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_application_period(raw_text: str | None) -> ApplicationPeriod:
    if raw_text is None or not raw_text.strip():
        return ApplicationPeriod(raw_text, None, None, DeadlineType.UNKNOWN)

    text = raw_text.strip()
    fixed_match = _DATE_RANGE.fullmatch(text)
    if fixed_match:
        start = _parse_date(fixed_match.group(1))
        end = _parse_date(fixed_match.group(2))
        if start is not None and end is not None and start <= end:
            return ApplicationPeriod(text, start, end, DeadlineType.FIXED_DATE)
        return ApplicationPeriod(text, None, None, DeadlineType.UNKNOWN)

    if "예산" in text and re.search(r"소진\s*(?:시|때)?\s*까지", text):
        first_date = _DATE.search(text)
        start = _parse_date(first_date.group(0)) if first_date else None
        return ApplicationPeriod(
            text, start, None, DeadlineType.UNTIL_BUDGET_EXHAUSTED
        )

    if re.search(r"(?:상시|수시)(?:\s*접수|\s*모집|\s*신청)?", text):
        return ApplicationPeriod(text, None, None, DeadlineType.ALWAYS_OPEN)

    if re.search(r"(?:별도\s*(?:공지|문의)|공고문\s*참고|문의\s*필요)", text):
        return ApplicationPeriod(text, None, None, DeadlineType.SEE_ANNOUNCEMENT)

    if "상이" in text and re.search(r"(?:차수|분야|세부사업|사업별)", text):
        return ApplicationPeriod(text, None, None, DeadlineType.VARIABLE)

    return ApplicationPeriod(text, None, None, DeadlineType.UNKNOWN)
