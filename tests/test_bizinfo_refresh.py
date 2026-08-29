from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError

import pytest

import app.config as config
import app.data.collectors.bizinfo as bizinfo_module
import scripts.refresh_bizinfo as refresh_script
from app.data.collectors.bizinfo import (
    BIZINFO_ENDPOINT,
    BizinfoDuplicateIDError,
    BizinfoHTTPError,
    BizinfoJSONError,
    BizinfoPipelineError,
    BizinfoRefresher,
    BizinfoRefreshSettings,
    BizinfoStorageError,
    BizinfoTimeoutError,
    BizinfoValidationError,
    MissingAPIKeyError,
)
from app.data.program_repository import ProgramRepository
from app.data.snapshot_manager import (
    SERVICE_READY_MANIFEST_NAME,
    SnapshotStorageError,
    publish_service_ready_snapshot,
    resolve_service_ready_snapshot,
    write_json_atomically,
)
from app.retrieval.program_retrieval import ProgramRetrievalService
from app.schemas.retrieval import ProgramSearchRequest
from app.services.program_service import ProgramService


FIXED_NOW = datetime(2026, 8, 29, 1, 2, 3, 456789, tzinfo=timezone.utc)
SECRET = "bizinfo-secret-for-test"


class FakeTransport:
    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"",
        error: Exception | None = None,
    ) -> None:
        self.status = status
        self.body = body
        self.error = error
        self.calls = 0
        self.request_url: str | None = None

    def fetch(self, request, timeout_seconds: float) -> tuple[int, bytes]:
        assert timeout_seconds > 0
        self.calls += 1
        self.request_url = request.full_url
        if self.error is not None:
            raise self.error
        return self.status, self.body


def response_bytes(items: list[dict] | None = None) -> bytes:
    records = items or [
        {
            "pblancId": "PBLN_REFRESH_001",
            "pblancNm": "창업 테스트 지원사업",
            "pldirSportRealmLclasCodeNm": "창업",
            "bsnsSumryCn": "예비창업자를 지원합니다.",
            "totCnt": 2,
        },
        {
            "pblancId": "PBLN_REFRESH_002",
            "pblancNm": "청년 창업 프로그램",
            "pldirSportRealmLclasCodeNm": "창업",
            "bsnsSumryCn": "청년 창업기업을 지원합니다.",
            "totCnt": 2,
        },
    ]
    return json.dumps({"jsonArray": records}, ensure_ascii=False).encode("utf-8")


def refresher(
    collected_dir: Path,
    transport: FakeTransport,
    *,
    api_key: str | None = SECRET,
) -> BizinfoRefresher:
    return BizinfoRefresher(
        BizinfoRefreshSettings(
            api_key=api_key,
            collected_dir=collected_dir,
            timeout_seconds=3,
        ),
        transport=transport,
        now=lambda: FIXED_NOW,
    )


def existing_service_ready(collected_dir: Path) -> tuple[Path, bytes]:
    old_body = response_bytes(
        [{"pblancId": "PBLN_OLD", "pblancNm": "기존 정상 공고"}]
    )
    old_snapshot = collected_dir / "bizinfo_startup_old.json"
    old_snapshot.parent.mkdir(parents=True, exist_ok=True)
    old_snapshot.write_bytes(old_body)
    publish_service_ready_snapshot(
        collected_dir=collected_dir,
        snapshot_path=old_snapshot,
        manifest_payload={"service_ready": True},
    )
    return old_snapshot, (
        collected_dir / SERVICE_READY_MANIFEST_NAME
    ).read_bytes()


def test_valid_response_saves_exact_raw_and_publishes_service_ready(
    tmp_path: Path,
) -> None:
    collected_dir = tmp_path / "collected"
    body = response_bytes()
    transport = FakeTransport(body=body)
    baseline = tmp_path / "bizinfo_startup_sample.json"
    baseline.write_bytes(b"verified-baseline")

    result = refresher(collected_dir, transport).refresh()

    assert transport.calls == 1
    assert result.http_status == 200
    assert result.record_count == 2
    assert result.unique_program_count == 2
    assert result.duplicate_count == 0
    assert result.snapshot_path.read_bytes() == body
    assert result.snapshot_path.name == (
        "bizinfo_startup_20260829T010203456789Z.json"
    )
    assert result.normalized_program_count == 2
    assert result.service_ready is True
    assert resolve_service_ready_snapshot(collected_dir) == result.snapshot_path
    assert baseline.read_bytes() == b"verified-baseline"

    metadata_text = result.metadata_path.read_text(encoding="utf-8")
    assert SECRET not in metadata_text
    assert BIZINFO_ENDPOINT in metadata_text
    assert '"category_code": "06"' in metadata_text


def test_missing_api_key_fails_without_http_or_files(tmp_path: Path) -> None:
    transport = FakeTransport(body=response_bytes())

    with pytest.raises(MissingAPIKeyError):
        refresher(tmp_path / "collected", transport, api_key=None).refresh()

    assert transport.calls == 0
    assert not (tmp_path / "collected").exists()


def test_timeout_preserves_existing_service_ready_snapshot(tmp_path: Path) -> None:
    collected_dir = tmp_path / "collected"
    old_snapshot, old_manifest = existing_service_ready(collected_dir)

    with pytest.raises(BizinfoTimeoutError):
        refresher(
            collected_dir,
            FakeTransport(error=TimeoutError("timed out")),
        ).refresh()

    assert old_snapshot.is_file()
    assert (collected_dir / SERVICE_READY_MANIFEST_NAME).read_bytes() == old_manifest


@pytest.mark.parametrize("status", [400, 503])
def test_http_error_preserves_existing_service_ready_snapshot(
    tmp_path: Path,
    status: int,
) -> None:
    collected_dir = tmp_path / "collected"
    old_snapshot, old_manifest = existing_service_ready(collected_dir)

    with pytest.raises(BizinfoHTTPError, match=f"status={status}"):
        refresher(
            collected_dir,
            FakeTransport(status=status, body=b"error"),
        ).refresh()

    assert old_snapshot.is_file()
    assert (collected_dir / SERVICE_READY_MANIFEST_NAME).read_bytes() == old_manifest


def test_malformed_json_is_not_saved(tmp_path: Path) -> None:
    collected_dir = tmp_path / "collected"

    with pytest.raises(BizinfoJSONError):
        refresher(collected_dir, FakeTransport(body=b"{invalid")).refresh()

    assert not list(collected_dir.glob("bizinfo_startup_*.json"))


def test_empty_records_are_not_saved(tmp_path: Path) -> None:
    collected_dir = tmp_path / "collected"
    body = json.dumps({"jsonArray": []}).encode("utf-8")

    with pytest.raises(BizinfoValidationError, match="must not be empty"):
        refresher(collected_dir, FakeTransport(body=body)).refresh()

    assert not list(collected_dir.glob("bizinfo_startup_*.json"))


def test_duplicate_ids_are_rejected_without_deduplication(tmp_path: Path) -> None:
    collected_dir = tmp_path / "collected"
    duplicate = {"pblancId": "DUPLICATE", "pblancNm": "중복 공고"}

    with pytest.raises(BizinfoDuplicateIDError, match="1 duplicate"):
        refresher(
            collected_dir,
            FakeTransport(body=response_bytes([duplicate, duplicate])),
        ).refresh()

    assert not list(collected_dir.glob("bizinfo_startup_*.json"))


def test_missing_required_id_is_rejected(tmp_path: Path) -> None:
    collected_dir = tmp_path / "collected"

    with pytest.raises(BizinfoValidationError, match="pblancId"):
        refresher(
            collected_dir,
            FakeTransport(body=response_bytes([{"pblancNm": "ID 없음"}])),
        ).refresh()

    assert not list(collected_dir.glob("bizinfo_startup_*.json"))


def test_optional_fields_may_be_missing(tmp_path: Path) -> None:
    result = refresher(
        tmp_path / "collected",
        FakeTransport(
            body=response_bytes(
                [{"pblancId": "PBLN_MINIMAL", "pblancNm": "최소 공고"}]
            )
        ),
    ).refresh()

    programs = ProgramRepository(result.snapshot_path).list()
    assert len(programs) == 1
    assert programs[0].provider is None


def test_existing_timestamped_snapshot_is_never_overwritten(tmp_path: Path) -> None:
    collected_dir = tmp_path / "collected"
    existing = collected_dir / "bizinfo_startup_20260829T010203456789Z.json"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing-evidence")

    with pytest.raises(BizinfoStorageError, match="already exists"):
        refresher(collected_dir, FakeTransport(body=response_bytes())).refresh()

    assert existing.read_bytes() == b"existing-evidence"


def test_disk_write_failure_preserves_old_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collected_dir = tmp_path / "collected"
    _, old_manifest = existing_service_ready(collected_dir)

    def fail_write(path: Path, body: bytes, *, overwrite: bool) -> None:
        del path, body, overwrite
        raise SnapshotStorageError("disk unavailable")

    monkeypatch.setattr(bizinfo_module, "write_bytes_atomically", fail_write)

    with pytest.raises(BizinfoStorageError, match="disk unavailable"):
        refresher(collected_dir, FakeTransport(body=response_bytes())).refresh()

    assert (collected_dir / SERVICE_READY_MANIFEST_NAME).read_bytes() == old_manifest


def test_normalization_failure_removes_candidate_and_preserves_manifest(
    tmp_path: Path,
) -> None:
    collected_dir = tmp_path / "collected"
    old_snapshot, old_manifest = existing_service_ready(collected_dir)
    invalid_for_normalizer = response_bytes(
        [
            {
                "pblancId": "PBLN_INVALID_URL",
                "pblancNm": "URL 구조 오류 공고",
                "pblancUrl": "not-a-valid-url",
            }
        ]
    )

    with pytest.raises(BizinfoPipelineError, match="pipeline validation failed"):
        refresher(
            collected_dir,
            FakeTransport(body=invalid_for_normalizer),
        ).refresh()

    assert old_snapshot.is_file()
    assert (collected_dir / SERVICE_READY_MANIFEST_NAME).read_bytes() == old_manifest
    assert len(list(collected_dir.glob("bizinfo_startup_*.json"))) == 1


def test_new_snapshot_runs_loader_normalization_extraction_and_retrieval(
    tmp_path: Path,
) -> None:
    result = refresher(
        tmp_path / "collected",
        FakeTransport(body=response_bytes()),
    ).refresh()
    service = ProgramService(ProgramRepository(result.snapshot_path))

    programs = service.list_programs()
    eligibility = [
        service.get_program_eligibility(program.program_id)
        for program in programs
    ]
    retrieval = ProgramRetrievalService(service).search(
        ProgramSearchRequest(query="창업", limit=5)
    )

    assert len(programs) == 2
    assert len(eligibility) == 2
    assert retrieval.result_count == 2


def test_explicit_snapshot_override_has_highest_priority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collected_dir = tmp_path / "collected"
    existing_service_ready(collected_dir)
    explicit = tmp_path / "explicit.json"
    explicit.write_bytes(response_bytes())
    monkeypatch.setattr(config, "BIZINFO_COLLECTED_DIR", collected_dir)
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(explicit))

    assert config.get_bizinfo_snapshot_path() == explicit.resolve()


def test_service_ready_snapshot_is_second_priority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collected_dir = tmp_path / "collected"
    collected, _ = existing_service_ready(collected_dir)
    monkeypatch.setattr(config, "BIZINFO_COLLECTED_DIR", collected_dir)
    monkeypatch.delenv("FINBRIDGE_BIZINFO_SNAPSHOT", raising=False)

    assert config.get_bizinfo_snapshot_path() == collected.resolve()


def test_bootstrap_is_used_when_manifest_is_missing_or_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collected_dir = tmp_path / "collected"
    collected_dir.mkdir()
    write_json_atomically(
        collected_dir / SERVICE_READY_MANIFEST_NAME,
        {"snapshot_filename": "../outside.json"},
    )
    bootstrap = tmp_path / "bootstrap.json"
    monkeypatch.setattr(config, "BIZINFO_COLLECTED_DIR", collected_dir)
    monkeypatch.setattr(config, "BIZINFO_BOOTSTRAP_SNAPSHOT", bootstrap)
    monkeypatch.delenv("FINBRIDGE_BIZINFO_SNAPSHOT", raising=False)

    assert config.get_bizinfo_snapshot_path() == bootstrap


def test_http_error_never_exposes_secret_url(tmp_path: Path) -> None:
    secret_url = f"{BIZINFO_ENDPOINT}?crtfcKey={SECRET}"
    transport = FakeTransport(
        error=HTTPError(secret_url, 401, "unauthorized", None, None)
    )

    with pytest.raises(BizinfoHTTPError) as captured:
        refresher(tmp_path / "collected", transport).refresh()

    assert SECRET not in str(captured.value)
    assert secret_url not in str(captured.value)


def test_cli_failure_log_does_not_expose_secret(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    secret_url = f"{BIZINFO_ENDPOINT}?crtfcKey={SECRET}"
    transport = FakeTransport(
        error=HTTPError(secret_url, 401, "unauthorized", None, None)
    )
    real_refresher = BizinfoRefresher

    monkeypatch.setattr(
        refresh_script,
        "get_setting",
        lambda name: SECRET if name == "BIZINFO_API_KEY" else "3",
    )
    monkeypatch.setattr(refresh_script, "BIZINFO_COLLECTED_DIR", tmp_path)
    monkeypatch.setattr(
        refresh_script,
        "BizinfoRefresher",
        lambda settings: real_refresher(settings, transport=transport),
    )

    assert refresh_script.main() == 1
    output = capsys.readouterr()
    combined = output.out + output.err
    assert SECRET not in combined
    assert secret_url not in combined
