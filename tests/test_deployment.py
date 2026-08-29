from __future__ import annotations

from pathlib import Path

import pytest

import app.config as config
from app.main import app, create_app
from tests.conftest import ASGITestClient


LOCAL_ORIGIN = "http://localhost:8443"
VERCEL_ORIGIN = "https://finbridge-example.vercel.app"


def clean_deployment_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> ASGITestClient:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("BIZINFO_API_KEY", "")
    monkeypatch.delenv("FINBRIDGE_BIZINFO_SNAPSHOT", raising=False)
    monkeypatch.setattr(config, "BIZINFO_COLLECTED_DIR", tmp_path / "collected")
    return ASGITestClient(create_app())


def preflight(client: ASGITestClient, origin: str) -> object:
    return client.request(
        "OPTIONS",
        "/chat",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_python_runtime_pin_and_app_import_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]

    assert (project_root / ".python-version").read_text(encoding="utf-8").strip() == (
        "3.14.3"
    )
    assert app.title == "FinBridge Backend"


def test_cors_origin_parser_strips_whitespace_and_empty_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FINBRIDGE_CORS_ORIGINS",
        f" {LOCAL_ORIGIN},, {VERCEL_ORIGIN}/, {LOCAL_ORIGIN} ",
    )

    assert config.get_cors_origins() == (LOCAL_ORIGIN, VERCEL_ORIGIN)


def test_cors_wildcard_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINBRIDGE_CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="wildcard"):
        config.get_cors_origins()


def test_default_cors_allows_local_frontend_and_rejects_other_origin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("FINBRIDGE_CORS_ORIGINS", raising=False)
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    client = ASGITestClient(create_app())

    allowed = preflight(client, LOCAL_ORIGIN)
    disallowed = preflight(client, "https://not-allowed.example")

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == LOCAL_ORIGIN
    assert disallowed.status_code == 400
    assert "access-control-allow-origin" not in disallowed.headers


def test_cors_env_adds_vercel_origin_without_code_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FINBRIDGE_CORS_ORIGINS", VERCEL_ORIGIN)
    client = ASGITestClient(create_app())

    response = preflight(client, VERCEL_ORIGIN)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == VERCEL_ORIGIN


def test_startup_and_core_apis_work_without_secrets_or_runtime_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = clean_deployment_client(monkeypatch, tmp_path)

    health = client.get("/health")
    programs = client.get("/programs?query=창업")
    chat = client.post("/chat", json={"message": "창업 지원사업을 찾아줘"})
    risk = client.post(
        "/risk/calculate",
        json={
            "initial_cost": 30_000_000,
            "own_capital": 20_000_000,
            "monthly_revenue": 6_000_000,
            "monthly_expense": 5_000_000,
            "loan_amount": 20_000_000,
            "annual_interest_rate": 4.5,
            "loan_term_months": 60,
        },
    )

    assert health.status_code == 200
    assert programs.status_code == 200
    assert programs.json()["result_count"] > 0
    assert chat.status_code == 200
    assert chat.json()["reply_source"] == "TEMPLATE_FALLBACK"
    assert chat.json()["programs"]
    assert chat.json()["sources"]
    assert risk.status_code == 200
