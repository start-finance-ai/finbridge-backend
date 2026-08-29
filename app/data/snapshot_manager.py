from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


SERVICE_READY_MANIFEST_NAME = "service_ready.json"


class SnapshotStorageError(RuntimeError):
    """A safe storage failure without response data or credentials."""


def resolve_service_ready_snapshot(collected_dir: Path) -> Path | None:
    manifest_path = collected_dir / SERVICE_READY_MANIFEST_NAME
    try:
        payload = json.loads(manifest_path.read_bytes())
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("service_ready") is not True:
        return None

    filename = payload.get("snapshot_filename")
    if not isinstance(filename, str) or not filename:
        return None
    if Path(filename).name != filename or not filename.endswith(".json"):
        return None

    candidate = collected_dir / filename
    try:
        if not candidate.is_file():
            return None
        if candidate.resolve().parent != collected_dir.resolve():
            return None
    except OSError:
        return None
    return candidate.resolve()


def write_bytes_atomically(path: Path, body: bytes, *, overwrite: bool) -> None:
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise SnapshotStorageError("snapshot filename already exists")
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(body)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except SnapshotStorageError:
        raise
    except OSError:
        raise SnapshotStorageError("snapshot storage failed") from None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    body = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    write_bytes_atomically(path, body, overwrite=True)


def publish_service_ready_snapshot(
    *,
    collected_dir: Path,
    snapshot_path: Path,
    manifest_payload: dict[str, Any],
) -> Path:
    try:
        resolved_dir = collected_dir.resolve()
        resolved_snapshot = snapshot_path.resolve()
    except OSError:
        raise SnapshotStorageError("snapshot path resolution failed") from None
    if resolved_snapshot.parent != resolved_dir or not resolved_snapshot.is_file():
        raise SnapshotStorageError("service-ready snapshot is outside collected dir")

    manifest = {
        **manifest_payload,
        "snapshot_filename": resolved_snapshot.name,
    }
    manifest_path = collected_dir / SERVICE_READY_MANIFEST_NAME
    write_json_atomically(manifest_path, manifest)
    return manifest_path
