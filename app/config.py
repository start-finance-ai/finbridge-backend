from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BIZINFO_SNAPSHOT = (
    PROJECT_ROOT / "data" / "raw" / "bizinfo" / "bizinfo_startup_sample.json"
)


def get_bizinfo_snapshot_path() -> Path:
    configured_path = os.getenv("FINBRIDGE_BIZINFO_SNAPSHOT")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_BIZINFO_SNAPSHOT
