from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BizinfoDataError(RuntimeError):
    error_code = "BIZINFO_DATA_ERROR"


class BizinfoSnapshotNotFoundError(BizinfoDataError):
    error_code = "BIZINFO_SNAPSHOT_NOT_FOUND"


class BizinfoJSONError(BizinfoDataError):
    error_code = "BIZINFO_JSON_INVALID"


class BizinfoStructureError(BizinfoDataError):
    error_code = "BIZINFO_STRUCTURE_INVALID"


class BizinfoSnapshotLoader:
    def __init__(self, snapshot_path: Path) -> None:
        self.snapshot_path = snapshot_path

    def load_items(self) -> list[dict[str, Any]]:
        try:
            response_bytes = self.snapshot_path.read_bytes()
        except FileNotFoundError as exc:
            raise BizinfoSnapshotNotFoundError(
                f"Bizinfo snapshot not found: {self.snapshot_path}"
            ) from exc
        except OSError as exc:
            raise BizinfoDataError("Bizinfo snapshot could not be read") from exc

        try:
            payload = json.loads(response_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BizinfoJSONError("Bizinfo snapshot is not valid JSON") from exc

        if not isinstance(payload, dict):
            raise BizinfoStructureError("Bizinfo snapshot root must be an object")
        json_array = payload.get("jsonArray")
        if not isinstance(json_array, list):
            raise BizinfoStructureError("Bizinfo jsonArray must be a list")
        if any(not isinstance(item, dict) for item in json_array):
            raise BizinfoStructureError("Every Bizinfo jsonArray item must be an object")

        return json_array
