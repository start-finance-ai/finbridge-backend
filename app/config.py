from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BIZINFO_BOOTSTRAP_SNAPSHOT = (
    PROJECT_ROOT / "data" / "bootstrap" / "bizinfo_startup_bootstrap.json"
)
# Backward-compatible name for callers that use the default local snapshot constant.
DEFAULT_BIZINFO_SNAPSHOT = BIZINFO_BOOTSTRAP_SNAPSHOT
BIZINFO_COLLECTED_DIR = PROJECT_ROOT / "data" / "raw" / "bizinfo" / "collected"
DEFAULT_CORS_ORIGINS = ("http://localhost:8443",)


def get_bizinfo_snapshot_path() -> Path:
    configured_path = os.getenv("FINBRIDGE_BIZINFO_SNAPSHOT")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    from app.data.snapshot_manager import resolve_service_ready_snapshot

    collected_snapshot = resolve_service_ready_snapshot(BIZINFO_COLLECTED_DIR)
    if collected_snapshot is not None:
        return collected_snapshot
    return BIZINFO_BOOTSTRAP_SNAPSHOT


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str | None = field(repr=False)
    model: str = "gpt-5.6-luna"
    timeout_seconds: float = 30.0
    max_output_tokens: int = 1200


def get_openai_settings() -> OpenAISettings:
    timeout_text = get_setting("OPENAI_TIMEOUT_SECONDS") or "30"
    try:
        timeout_seconds = float(timeout_text)
    except ValueError:
        timeout_seconds = 30.0
    if timeout_seconds <= 0:
        timeout_seconds = 30.0
    max_output_tokens_text = get_setting("OPENAI_MAX_OUTPUT_TOKENS") or "1200"
    try:
        max_output_tokens = int(max_output_tokens_text)
    except ValueError:
        max_output_tokens = 1200
    if max_output_tokens <= 0:
        max_output_tokens = 1200
    return OpenAISettings(
        api_key=get_setting("OPENAI_API_KEY"),
        model=get_setting("OPENAI_MODEL") or "gpt-5.6-luna",
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
    )


def get_cors_origins() -> tuple[str, ...]:
    configured = get_setting("FINBRIDGE_CORS_ORIGINS")
    if configured is None:
        return DEFAULT_CORS_ORIGINS

    origins = tuple(
        dict.fromkeys(
            origin.strip().rstrip("/")
            for origin in configured.split(",")
            if origin.strip()
        )
    )
    if "*" in origins:
        raise ValueError("FINBRIDGE_CORS_ORIGINS must not contain wildcard origins")
    return origins or DEFAULT_CORS_ORIGINS


def get_setting(name: str) -> str | None:
    environment_value = os.getenv(name)
    if environment_value is not None:
        normalized = environment_value.strip()
        return normalized or None

    env_path = PROJECT_ROOT / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", maxsplit=1)
        if key.strip() != name:
            continue
        normalized = value.strip()
        quoted = (
            len(normalized) >= 2
            and normalized[0] == normalized[-1]
            and normalized[0] in {"'", '"'}
        )
        if quoted:
            normalized = normalized[1:-1]
        return normalized or None
    return None
