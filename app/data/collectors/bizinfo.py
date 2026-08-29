from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.data.program_repository import ProgramRepository
from app.data.snapshot_manager import (
    SnapshotStorageError,
    publish_service_ready_snapshot,
    write_bytes_atomically,
    write_json_atomically,
)


BIZINFO_ENDPOINT = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
STARTUP_CATEGORY_CODE = "06"
STARTUP_CATEGORY_NAME = "창업"
DEFAULT_SEARCH_COUNT = 100
DEFAULT_TIMEOUT_SECONDS = 30.0


class BizinfoRefreshError(RuntimeError):
    """A refresh failure safe to print without credentials or request URLs."""


class MissingAPIKeyError(BizinfoRefreshError):
    pass


class BizinfoTimeoutError(BizinfoRefreshError):
    pass


class BizinfoHTTPError(BizinfoRefreshError):
    pass


class BizinfoNetworkError(BizinfoRefreshError):
    pass


class BizinfoJSONError(BizinfoRefreshError):
    pass


class BizinfoValidationError(BizinfoRefreshError):
    pass


class BizinfoDuplicateIDError(BizinfoValidationError):
    pass


class BizinfoPipelineError(BizinfoRefreshError):
    pass


class BizinfoStorageError(BizinfoRefreshError):
    pass


class BizinfoTransport(Protocol):
    def fetch(self, request: Request, timeout_seconds: float) -> tuple[int, bytes]: ...


class UrllibBizinfoTransport:
    def fetch(self, request: Request, timeout_seconds: float) -> tuple[int, bytes]:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.getcode(), response.read()


@dataclass(frozen=True)
class BizinfoRefreshSettings:
    api_key: str | None = field(repr=False)
    collected_dir: Path
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    search_count: int = DEFAULT_SEARCH_COUNT
    category_code: str = STARTUP_CATEGORY_CODE
    category_name: str = STARTUP_CATEGORY_NAME


@dataclass(frozen=True)
class ValidatedBizinfoResponse:
    payload: dict[str, Any]
    items: list[dict[str, Any]]
    unique_program_count: int
    duplicate_count: int
    tot_cnt: Any | None


@dataclass(frozen=True)
class BizinfoRefreshResult:
    collected_at: datetime
    http_status: int
    record_count: int
    unique_program_count: int
    duplicate_count: int
    tot_cnt: Any | None
    snapshot_path: Path
    metadata_path: Path
    manifest_path: Path
    normalized_program_count: int
    service_ready: bool


class BizinfoRefresher:
    def __init__(
        self,
        settings: BizinfoRefreshSettings,
        transport: BizinfoTransport | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport or UrllibBizinfoTransport()
        self._now = now or (lambda: datetime.now(timezone.utc))

    def refresh(self) -> BizinfoRefreshResult:
        api_key = (self._settings.api_key or "").strip()
        if not api_key:
            raise MissingAPIKeyError("BIZINFO_API_KEY is not configured")
        if self._settings.timeout_seconds <= 0:
            raise BizinfoRefreshError("BIZINFO_TIMEOUT_SECONDS must be positive")
        if self._settings.search_count <= 0:
            raise BizinfoRefreshError("Bizinfo search_count must be positive")

        request = self._build_request(api_key)
        status, body = self._fetch(request)
        validated = validate_bizinfo_response(body)
        collected_at = self._utc_now()
        timestamp = collected_at.strftime("%Y%m%dT%H%M%S%fZ")
        snapshot_path = (
            self._settings.collected_dir
            / f"bizinfo_startup_{timestamp}.json"
        )
        metadata_path = snapshot_path.with_suffix(".metadata.json")

        snapshot_created = False
        metadata_created = False
        try:
            write_bytes_atomically(snapshot_path, body, overwrite=False)
            snapshot_created = True
            normalized_programs = ProgramRepository(snapshot_path).list()
            if len(normalized_programs) != validated.unique_program_count:
                raise BizinfoPipelineError(
                    "normalized program count does not match validated records"
                )

            metadata = self._metadata(
                collected_at=collected_at,
                validated=validated,
                normalized_count=len(normalized_programs),
            )
            write_json_atomically(metadata_path, metadata)
            metadata_created = True
            manifest_path = publish_service_ready_snapshot(
                collected_dir=self._settings.collected_dir,
                snapshot_path=snapshot_path,
                manifest_payload=metadata,
            )
        except BizinfoPipelineError:
            self._cleanup_candidate(
                snapshot_path if snapshot_created else None,
                metadata_path if metadata_created else None,
            )
            raise
        except Exception as exc:
            self._cleanup_candidate(
                snapshot_path if snapshot_created else None,
                metadata_path if metadata_created else None,
            )
            if isinstance(exc, SnapshotStorageError):
                raise BizinfoStorageError(str(exc)) from None
            raise BizinfoPipelineError(
                f"snapshot pipeline validation failed ({type(exc).__name__})"
            ) from None

        return BizinfoRefreshResult(
            collected_at=collected_at,
            http_status=status,
            record_count=len(validated.items),
            unique_program_count=validated.unique_program_count,
            duplicate_count=validated.duplicate_count,
            tot_cnt=validated.tot_cnt,
            snapshot_path=snapshot_path,
            metadata_path=metadata_path,
            manifest_path=manifest_path,
            normalized_program_count=len(normalized_programs),
            service_ready=True,
        )

    def _build_request(self, api_key: str) -> Request:
        query = urlencode(
            {
                "crtfcKey": api_key,
                "dataType": "json",
                "searchCnt": self._settings.search_count,
                "searchLclasId": self._settings.category_code,
            }
        )
        return Request(
            f"{BIZINFO_ENDPOINT}?{query}",
            headers={"Accept": "application/json"},
            method="GET",
        )

    def _fetch(self, request: Request) -> tuple[int, bytes]:
        try:
            status, body = self._transport.fetch(
                request,
                self._settings.timeout_seconds,
            )
        except HTTPError as exc:
            raise BizinfoHTTPError(f"Bizinfo HTTP error (status={exc.code})") from None
        except (TimeoutError,):
            raise BizinfoTimeoutError("Bizinfo request timed out") from None
        except (URLError, OSError, HTTPException) as exc:
            if isinstance(getattr(exc, "reason", None), TimeoutError):
                raise BizinfoTimeoutError("Bizinfo request timed out") from None
            raise BizinfoNetworkError(
                f"Bizinfo network error ({type(exc).__name__})"
            ) from None

        if status != 200:
            raise BizinfoHTTPError(f"Bizinfo HTTP error (status={status})")
        if not isinstance(body, bytes):
            raise BizinfoNetworkError("Bizinfo response body is not bytes")
        return status, body

    def _utc_now(self) -> datetime:
        current = self._now()
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc)

    def _metadata(
        self,
        *,
        collected_at: datetime,
        validated: ValidatedBizinfoResponse,
        normalized_count: int,
    ) -> dict[str, Any]:
        return {
            "source": "BIZINFO",
            "source_endpoint": BIZINFO_ENDPOINT,
            "collected_at": collected_at.isoformat(),
            "record_count": len(validated.items),
            "unique_program_count": validated.unique_program_count,
            "duplicate_count": validated.duplicate_count,
            "normalized_program_count": normalized_count,
            "tot_cnt": validated.tot_cnt,
            "request_scope": {
                "category_code": self._settings.category_code,
                "category_name": self._settings.category_name,
                "search_count": self._settings.search_count,
                "data_type": "json",
            },
            "service_ready": True,
        }

    @staticmethod
    def _cleanup_candidate(*paths: Path | None) -> None:
        for path in paths:
            if path is None:
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def validate_bizinfo_response(body: bytes) -> ValidatedBizinfoResponse:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BizinfoJSONError("Bizinfo response is not valid JSON") from None
    if not isinstance(payload, dict):
        raise BizinfoValidationError("Bizinfo response root must be an object")

    items = payload.get("jsonArray")
    if not isinstance(items, list):
        raise BizinfoValidationError("Bizinfo jsonArray must be a list")
    if not items:
        raise BizinfoValidationError("Bizinfo jsonArray must not be empty")

    program_ids: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise BizinfoValidationError(
                f"Bizinfo record at index {index} must be an object"
            )
        program_id = _required_string(item, "pblancId", index)
        _required_string(item, "pblancNm", index)
        program_ids.append(program_id)

    unique_ids = set(program_ids)
    duplicate_count = len(program_ids) - len(unique_ids)
    if duplicate_count:
        raise BizinfoDuplicateIDError(
            f"Bizinfo response contains {duplicate_count} duplicate pblancId"
        )

    return ValidatedBizinfoResponse(
        payload=payload,
        items=items,
        unique_program_count=len(unique_ids),
        duplicate_count=duplicate_count,
        tot_cnt=_find_tot_cnt(payload, items),
    )


def _required_string(item: dict[str, Any], field_name: str, index: int) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise BizinfoValidationError(
            f"Bizinfo record at index {index} is missing {field_name}"
        )
    return value.strip()


def _find_tot_cnt(payload: dict[str, Any], items: list[dict[str, Any]]) -> Any | None:
    if "totCnt" in payload:
        return payload["totCnt"]
    for item in items:
        if "totCnt" in item:
            return item["totCnt"]
    return None
