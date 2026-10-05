from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.data.bizinfo_loader import (
    BizinfoSnapshotLoader,
    BizinfoStructureError,
)
from app.schemas.program import Program
from app.utils.date_parser import parse_application_period


class ProgramRepository:
    def __init__(self, snapshot_path: Path) -> None:
        self._loader = BizinfoSnapshotLoader(snapshot_path)
        self._programs: dict[str, Program] | None = None

    def list(self) -> list[Program]:
        return list(self._load().values())

    def get(self, program_id: str) -> Program | None:
        return self._load().get(program_id)

    def _load(self) -> dict[str, Program]:
        if self._programs is not None:
            return self._programs

        payload = self._loader.load_payload()
        metadata = payload.get("finbridge_dataset")
        is_demo = isinstance(metadata, dict) and metadata.get("kind") == "synthetic_demo"
        programs: dict[str, Program] = {}
        for item in payload["jsonArray"]:
            program = normalize_bizinfo_program(item, is_demo=is_demo)
            if program.program_id in programs:
                raise BizinfoStructureError(
                    f"Duplicate Bizinfo pblancId: {program.program_id}"
                )
            programs[program.program_id] = program
        self._programs = programs
        return programs


def normalize_bizinfo_program(item: dict[str, Any], *, is_demo: bool = False) -> Program:
    program_id = _required_string(item, "pblancId")
    program_name = _required_string(item, "pblancNm")
    period = parse_application_period(_optional_string(item.get("reqstBeginEndDe")))

    try:
        return Program(
            program_id=program_id,
            program_name=program_name,
            provider=_optional_string(item.get("jrsdInsttNm")),
            executing_organization=_optional_string(item.get("excInsttNm")),
            category=_optional_string(item.get("pldirSportRealmLclasCodeNm")),
            subcategory=_optional_string(item.get("pldirSportRealmMlsfcCodeNm")),
            target_type_raw=_optional_string(item.get("trgetNm")),
            hashtags_raw=_optional_string(item.get("hashtags")),
            summary_raw=_optional_string(item.get("bsnsSumryCn")),
            application_method_raw=_optional_string(item.get("reqstMthPapersCn")),
            contact_raw=_optional_string(item.get("refrncNm")),
            apply_start=period.start,
            apply_end=period.end,
            apply_period_text=period.raw_text,
            deadline_type=period.deadline_type,
            source="DEMO" if is_demo else "BIZINFO",
            source_url=_optional_string(item.get("pblancUrl")),
            document_url=_optional_string(
                item.get("printFlpthNm") or item.get("flpthNm")
            ),
            document_name=_optional_string(
                item.get("printFileNm") or item.get("fileNm")
            ),
            source_created_at=_parse_source_datetime(item.get("creatPnttm")),
            source_updated_at=_parse_source_datetime(item.get("updtPnttm")),
            collected_at=None,
            raw_source=dict(item),
        )
    except ValueError as exc:
        raise BizinfoStructureError(
            f"Bizinfo item {program_id} cannot be normalized"
        ) from exc


def _required_string(item: dict[str, Any], field_name: str) -> str:
    value = _optional_string(item.get(field_name))
    if value is None:
        raise BizinfoStructureError(f"Bizinfo item is missing {field_name}")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    normalized = value.strip()
    return normalized or None


def _parse_source_datetime(value: Any) -> datetime | None:
    text = _optional_string(value)
    if text is None:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
