from __future__ import annotations

import json

import pytest

from app.data.bizinfo_loader import (
    BizinfoJSONError,
    BizinfoSnapshotNotFoundError,
    BizinfoStructureError,
)
from app.data.program_repository import ProgramRepository
from app.utils.date_parser import DeadlineType, parse_application_period


def test_loads_and_normalizes_actual_twenty_program_snapshot(snapshot_path) -> None:
    repository = ProgramRepository(snapshot_path)

    programs = repository.list()

    assert len(programs) == 20
    assert len({program.program_id for program in programs}) == 20
    first = programs[0]
    assert first.program_id.startswith("PBLN_")
    assert first.program_name
    assert first.source == "BIZINFO"
    assert first.raw_source["pblancId"] == first.program_id


def test_fixed_date_period_is_parsed_without_guessing() -> None:
    period = parse_application_period("2026-08-17 ~ 2026-09-11")

    assert period.deadline_type is DeadlineType.FIXED_DATE
    assert period.start.isoformat() == "2026-08-17"
    assert period.end.isoformat() == "2026-09-11"


def test_budget_exhaustion_and_unknown_periods_are_explicit() -> None:
    budget = parse_application_period("예산 소진시까지")
    unknown = parse_application_period("접수 일정은 추후 확인")

    assert budget.deadline_type is DeadlineType.UNTIL_BUDGET_EXHAUSTED
    assert budget.end is None
    assert unknown.deadline_type is DeadlineType.UNKNOWN
    assert unknown.start is None
    assert unknown.end is None


def test_missing_snapshot_is_reported_without_import_failure(tmp_path) -> None:
    repository = ProgramRepository(tmp_path / "missing.json")

    with pytest.raises(BizinfoSnapshotNotFoundError):
        repository.list()


def test_invalid_json_is_reported(tmp_path) -> None:
    snapshot = tmp_path / "invalid.json"
    snapshot.write_text("{invalid", encoding="utf-8")
    repository = ProgramRepository(snapshot)

    with pytest.raises(BizinfoJSONError):
        repository.list()


def test_invalid_json_array_structure_is_reported(tmp_path) -> None:
    snapshot = tmp_path / "invalid-structure.json"
    snapshot.write_text('{"jsonArray": {}}', encoding="utf-8")
    repository = ProgramRepository(snapshot)

    with pytest.raises(BizinfoStructureError):
        repository.list()


def test_raw_snapshot_is_not_rewritten(snapshot_path) -> None:
    before = snapshot_path.read_bytes()
    ProgramRepository(snapshot_path).list()
    after = snapshot_path.read_bytes()

    assert before == after
    assert isinstance(json.loads(after)["jsonArray"], list)
