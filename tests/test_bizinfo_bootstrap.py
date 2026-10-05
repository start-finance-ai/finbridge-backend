from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.config as config
from app.ai.provider import AIExplanation
from app.data.program_repository import ProgramRepository
from app.main import create_app
from app.retrieval.program_retrieval import ProgramRetrievalService
from app.schemas.retrieval import ProgramSearchRequest
from app.services.program_service import ProgramService
from tests.conftest import ASGITestClient


EXPECTED_BOOTSTRAP_RECORDS = 6


class StubProvider:
    def explain(self, *, instructions: str, input_text: str) -> AIExplanation:
        del instructions, input_text
        return AIExplanation(text="검증된 검색 결과입니다.", model="test-model")


def configure_fresh_deployment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("FINBRIDGE_BIZINFO_SNAPSHOT", raising=False)
    monkeypatch.setattr(config, "BIZINFO_COLLECTED_DIR", tmp_path / "collected")


def test_fresh_deployment_selects_tracked_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_fresh_deployment(monkeypatch, tmp_path)

    assert config.get_bizinfo_snapshot_path() == config.BIZINFO_BOOTSTRAP_SNAPSHOT
    assert config.BIZINFO_BOOTSTRAP_SNAPSHOT.is_file()


def test_bootstrap_loads_expected_unique_records() -> None:
    payload = json.loads(config.BIZINFO_BOOTSTRAP_SNAPSHOT.read_bytes())
    items = payload["jsonArray"]
    program_ids = [item["pblancId"] for item in items]

    assert len(items) == EXPECTED_BOOTSTRAP_RECORDS
    assert len(set(program_ids)) == EXPECTED_BOOTSTRAP_RECORDS
    assert len(ProgramRepository(config.BIZINFO_BOOTSTRAP_SNAPSHOT).list()) == (
        EXPECTED_BOOTSTRAP_RECORDS
    )


def test_bootstrap_contains_no_credentials() -> None:
    body = config.BIZINFO_BOOTSTRAP_SNAPSHOT.read_bytes()

    for marker in (
        b"BIZINFO_API_KEY",
        b"OPENAI_API_KEY",
        b"crtfcKey=",
        b"Authorization",
    ):
        assert marker not in body


def test_invalid_explicit_override_is_not_silently_bypassed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing-explicit.json"
    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(missing))
    monkeypatch.setattr(config, "BIZINFO_COLLECTED_DIR", tmp_path / "collected")

    assert config.get_bizinfo_snapshot_path() == missing.resolve()
    response = ASGITestClient(create_app(ai_provider=StubProvider())).get("/programs")
    assert response.status_code == 503


def test_fresh_deployment_health_and_program_search_use_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_fresh_deployment(monkeypatch, tmp_path)
    client = ASGITestClient(create_app(ai_provider=StubProvider()))

    health = client.get("/health")
    programs = client.get("/programs?query=창업")

    assert health.status_code == 200
    assert programs.status_code == 200
    assert programs.json()["result_count"] > 0


def test_fresh_deployment_runs_extraction_and_retrieval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_fresh_deployment(monkeypatch, tmp_path)
    repository = ProgramRepository(config.get_bizinfo_snapshot_path())
    service = ProgramService(repository)
    programs = service.list_programs()
    eligibility = [
        service.get_program_eligibility(program.program_id)
        for program in programs
    ]
    retrieval = ProgramRetrievalService(service).search(
        ProgramSearchRequest(query="창업", limit=20)
    )

    assert len(programs) == EXPECTED_BOOTSTRAP_RECORDS
    assert len(eligibility) == EXPECTED_BOOTSTRAP_RECORDS
    assert retrieval.result_count > 0


def test_fresh_deployment_chat_retrieval_uses_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_fresh_deployment(monkeypatch, tmp_path)
    client = ASGITestClient(create_app(ai_provider=StubProvider()))

    response = client.post(
        "/chat",
        json={"message": "창업 지원사업을 찾아줘"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["programs"]
    assert payload["sources"]
    assert all(source["source"] == "DEMO" for source in payload["sources"])
    assert all(source["source_url"] is None for source in payload["sources"])
    assert payload["reply"].startswith("[데모]")
