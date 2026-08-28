#!/usr/bin/env python3
"""Collect unmodified Bizinfo JSON samples for data verification."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ENDPOINT = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
API_KEY_ENV_NAME = "BIZINFO_API_KEY"
SEARCH_COUNT = 100
REQUEST_TIMEOUT_SECONDS = 30

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Category:
    code: str
    name: str
    relative_output_path: Path


CATEGORIES = (
    Category("01", "금융", Path("data/raw/bizinfo/bizinfo_finance_sample.json")),
    Category("06", "창업", Path("data/raw/bizinfo/bizinfo_startup_sample_100.json")),
    Category("07", "경영", Path("data/raw/bizinfo/bizinfo_management_sample.json")),
)


_TOT_CNT_NOT_FOUND = object()


class CollectionError(Exception):
    """An expected collection failure safe to report without request details."""


class HttpRequestError(CollectionError):
    """The server returned an unsuccessful HTTP status."""


class NetworkError(CollectionError):
    """The request could not be completed due to a network-level failure."""


class JsonParsingError(CollectionError):
    """The response body was not valid JSON."""


class JsonStructureError(CollectionError):
    """The parsed JSON did not have the expected Bizinfo structure."""


class FileSaveError(CollectionError):
    """The validated raw response bytes could not be saved."""


@dataclass(frozen=True)
class CollectionResult:
    category: Category
    http_status: int
    item_count: int
    tot_cnt: Any


def build_request(api_key: str, category_code: str) -> Request:
    """Build a GET request without logging the URL containing the API key."""
    query = urlencode(
        {
            "crtfcKey": api_key,
            "dataType": "json",
            "searchCnt": SEARCH_COUNT,
            "searchLclasId": category_code,
        }
    )
    return Request(
        f"{API_ENDPOINT}?{query}",
        headers={"Accept": "application/json"},
        method="GET",
    )


def fetch_response_bytes(api_key: str, category_code: str) -> tuple[int, bytes]:
    """Fetch one category and return its HTTP status and untouched body bytes."""
    request = build_request(api_key, category_code)

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = response.getcode()
            body = response.read()
    except HTTPError as exc:
        raise HttpRequestError(f"HTTP 오류 (status={exc.code})") from None
    except (URLError, TimeoutError, OSError, HTTPException) as exc:
        raise NetworkError(f"네트워크 오류 ({type(exc).__name__})") from None

    if status != 200:
        status_text = "확인 불가" if status is None else str(status)
        raise HttpRequestError(f"HTTP 오류 (status={status_text})")
    if not isinstance(body, bytes):
        raise NetworkError("네트워크 오류 (응답 body가 bytes가 아님)")

    return status, body


def parse_and_validate_response(body: bytes) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse a separate in-memory view while leaving the raw body unchanged."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise JsonParsingError("JSON parsing 실패") from None

    if not isinstance(payload, dict):
        raise JsonStructureError("최상위 JSON 구조 이상 (object가 아님)")
    if "jsonArray" not in payload:
        raise JsonStructureError("jsonArray가 응답에 없음")

    items = payload["jsonArray"]
    if not isinstance(items, list):
        raise JsonStructureError("jsonArray가 list가 아님")
    if any(not isinstance(item, dict) for item in items):
        raise JsonStructureError("jsonArray item 구조 이상 (object가 아님)")

    return payload, items


def find_tot_cnt(payload: dict[str, Any], items: list[dict[str, Any]]) -> Any:
    """Find totCnt at the root or in the first item that contains it."""
    if "totCnt" in payload:
        return payload["totCnt"]

    for item in items:
        if "totCnt" in item:
            return item["totCnt"]

    return _TOT_CNT_NOT_FOUND


def save_raw_response(output_path: Path, body: bytes) -> None:
    """Atomically save exactly the bytes received from the server."""
    temporary_path: Path | None = None

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(body)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, output_path)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise FileSaveError("파일 저장 실패") from None


def collect_category(api_key: str, category: Category) -> CollectionResult:
    """Fetch, validate, and save one category without transforming its body."""
    http_status, body = fetch_response_bytes(api_key, category.code)
    payload, items = parse_and_validate_response(body)
    tot_cnt = find_tot_cnt(payload, items)
    save_raw_response(REPOSITORY_ROOT / category.relative_output_path, body)

    return CollectionResult(
        category=category,
        http_status=http_status,
        item_count=len(items),
        tot_cnt=tot_cnt,
    )


def format_tot_cnt(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def print_success(result: CollectionResult) -> None:
    print(f"분야 코드: {result.category.code}")
    print(f"분야명: {result.category.name}")
    print(f"HTTP Status: {result.http_status}")
    print(f"jsonArray 실제 item 수: {result.item_count}")
    if result.tot_cnt is not _TOT_CNT_NOT_FOUND:
        print(f"totCnt: {format_tot_cnt(result.tot_cnt)}")
    print(f"저장 경로: {result.category.relative_output_path.as_posix()}")


def main() -> int:
    api_key = os.environ.get(API_KEY_ENV_NAME, "").strip()
    if not api_key:
        print(
            f"오류: {API_KEY_ENV_NAME} 환경변수가 설정되지 않았습니다.",
            file=sys.stderr,
        )
        return 2

    failed = False
    for category in CATEGORIES:
        try:
            result = collect_category(api_key, category)
        except CollectionError as exc:
            print(f"오류 [{category.code} {category.name}]: {exc}", file=sys.stderr)
            failed = True
            continue
        except Exception as exc:
            # Do not print exception details: a request exception may contain the secret URL.
            print(
                f"오류 [{category.code} {category.name}]: 예상하지 못한 오류 "
                f"({type(exc).__name__})",
                file=sys.stderr,
            )
            failed = True
            continue

        print_success(result)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
