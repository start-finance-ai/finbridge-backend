#!/usr/bin/env python3
"""Manually refresh the service-ready Bizinfo startup snapshot."""

from __future__ import annotations

import sys

from app.config import BIZINFO_COLLECTED_DIR, get_setting
from app.data.collectors.bizinfo import (
    DEFAULT_TIMEOUT_SECONDS,
    BizinfoRefreshError,
    BizinfoRefresher,
    BizinfoRefreshSettings,
)


def _timeout_seconds() -> float:
    configured = get_setting("BIZINFO_TIMEOUT_SECONDS")
    if configured is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(configured)
    except ValueError:
        raise BizinfoRefreshError(
            "BIZINFO_TIMEOUT_SECONDS must be a number"
        ) from None
    if timeout <= 0:
        raise BizinfoRefreshError(
            "BIZINFO_TIMEOUT_SECONDS must be positive"
        )
    return timeout


def main() -> int:
    try:
        settings = BizinfoRefreshSettings(
            api_key=get_setting("BIZINFO_API_KEY"),
            collected_dir=BIZINFO_COLLECTED_DIR,
            timeout_seconds=_timeout_seconds(),
        )
        result = BizinfoRefresher(settings).refresh()
    except BizinfoRefreshError as exc:
        print(f"Bizinfo refresh failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            "Bizinfo refresh failed: unexpected safe failure "
            f"({type(exc).__name__})",
            file=sys.stderr,
        )
        return 1

    print(f"collected_at: {result.collected_at.isoformat()}")
    print(f"HTTP success: {result.http_status == 200}")
    print(f"raw record count: {result.record_count}")
    print(f"unique program count: {result.unique_program_count}")
    print(f"duplicate count: {result.duplicate_count}")
    if result.tot_cnt is not None:
        print(f"totCnt: {result.tot_cnt}")
    print(f"snapshot path: {result.snapshot_path}")
    print(
        "normalization success: "
        f"{result.normalized_program_count == result.unique_program_count}"
    )
    print(f"service-ready: {result.service_ready}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
