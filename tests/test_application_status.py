from __future__ import annotations

from datetime import date

import pytest

from app.retrieval.program_retrieval import ProgramRetrievalService
from app.schemas.program import Program
from app.schemas.retrieval import ProgramSearchRequest
from app.services.program_service import ProgramService
from app.utils.date_parser import (
    ApplicationStatus,
    DeadlineType,
    calculate_application_availability,
)


@pytest.mark.parametrize(
    ("deadline_type", "start", "end", "expected"),
    [
        (
            DeadlineType.FIXED_DATE,
            date(2026, 8, 1),
            date(2026, 9, 1),
            ApplicationStatus.OPEN,
        ),
        (
            DeadlineType.FIXED_DATE,
            date(2026, 9, 1),
            date(2026, 9, 30),
            ApplicationStatus.UPCOMING,
        ),
        (
            DeadlineType.FIXED_DATE,
            date(2026, 7, 1),
            date(2026, 8, 1),
            ApplicationStatus.CLOSED,
        ),
        (DeadlineType.ALWAYS_OPEN, None, None, ApplicationStatus.OPEN),
        (
            DeadlineType.UNTIL_BUDGET_EXHAUSTED,
            None,
            None,
            ApplicationStatus.NEEDS_CONFIRMATION,
        ),
        (
            DeadlineType.FIXED_DATE,
            None,
            None,
            ApplicationStatus.NEEDS_CONFIRMATION,
        ),
    ],
)
def test_application_status_is_deterministic(
    deadline_type, start, end, expected
) -> None:
    availability = calculate_application_availability(
        deadline_type=deadline_type,
        apply_start=start,
        apply_end=end,
        today=date(2026, 8, 31),
    )

    assert availability.status is expected
    if deadline_type is DeadlineType.UNTIL_BUDGET_EXHAUSTED:
        assert availability.note == "예산 소진 여부는 공식 공고에서 확인 필요"


class InMemoryProgramRepository:
    def __init__(self, programs: list[Program]) -> None:
        self._programs = programs

    def list(self) -> list[Program]:
        return list(self._programs)

    def get(self, program_id: str) -> Program | None:
        return next(
            (item for item in self._programs if item.program_id == program_id),
            None,
        )


def _program(
    program_id: str,
    deadline_type: DeadlineType,
    start: date | None = None,
    end: date | None = None,
) -> Program:
    return Program(
        program_id=program_id,
        program_name=program_id,
        apply_start=start,
        apply_end=end,
        apply_period_text=(
            f"{start.isoformat()} ~ {end.isoformat()}" if start and end else None
        ),
        deadline_type=deadline_type,
        raw_source={"pblancId": program_id},
    )


def test_open_now_filter_excludes_closed_and_sorts_fixed_deadlines_first() -> None:
    programs = [
        _program(
            "closed",
            DeadlineType.FIXED_DATE,
            date(2026, 7, 1),
            date(2026, 8, 1),
        ),
        _program(
            "upcoming",
            DeadlineType.FIXED_DATE,
            date(2026, 9, 2),
            date(2026, 9, 30),
        ),
        _program(
            "open-late",
            DeadlineType.FIXED_DATE,
            date(2026, 8, 1),
            date(2026, 9, 10),
        ),
        _program(
            "open-soon",
            DeadlineType.FIXED_DATE,
            date(2026, 8, 1),
            date(2026, 9, 1),
        ),
        _program("always", DeadlineType.ALWAYS_OPEN),
        _program("budget", DeadlineType.UNTIL_BUDGET_EXHAUSTED),
        _program("incomplete", DeadlineType.FIXED_DATE),
    ]
    service = ProgramRetrievalService(
        ProgramService(InMemoryProgramRepository(programs)),
        today_provider=lambda: date(2026, 8, 31),
    )

    response = service.search(
        ProgramSearchRequest(
            open_now_only=True,
            sort_by_deadline=True,
            limit=10,
        )
    )
    ids = [item.program.program_id for item in response.results]

    assert ids[:3] == ["open-soon", "open-late", "always"]
    assert "closed" not in ids
    assert "upcoming" not in ids
    assert {"budget", "incomplete"}.issubset(ids)
    budget = next(
        item.program for item in response.results if item.program.program_id == "budget"
    )
    assert budget.application_status is ApplicationStatus.NEEDS_CONFIRMATION
    assert budget.application_status_note == "예산 소진 여부는 공식 공고에서 확인 필요"
