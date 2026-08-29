from __future__ import annotations

from tests.conftest import ASGITestClient


VALID_PROGRAM_ID = "PBLN_000000000125864"


def test_get_valid_program_detail(client: ASGITestClient) -> None:
    response = client.get(f"/programs/{VALID_PROGRAM_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["program_id"] == VALID_PROGRAM_ID
    assert payload["source"] == "BIZINFO"
    assert payload["raw_source"]["pblancId"] == VALID_PROGRAM_ID


def test_get_invalid_program_detail_returns_404(client: ASGITestClient) -> None:
    response = client.get("/programs/PBLN_NOT_FOUND")

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "PROGRAM_NOT_FOUND"


def test_match_actual_raw_program_is_unknown_not_fabricated(
    client: ASGITestClient,
) -> None:
    response = client.post(
        "/programs/match",
        json={
            "program_id": VALID_PROGRAM_ID,
            "profile": {"user_type": "PRE_FOUNDER", "region": "강원특별자치도"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["program"]["program_id"] == VALID_PROGRAM_ID
    assert payload["match_status"] == "UNKNOWN"
    assert payload["condition_results"] == []
    assert payload["evidence"] == []
    assert payload["source"]["source"] == "BIZINFO"


def test_match_rejects_invalid_enum(client: ASGITestClient) -> None:
    response = client.post(
        "/programs/match",
        json={"program_id": VALID_PROGRAM_ID, "profile": {"user_type": "INVALID"}},
    )

    assert response.status_code == 422


def test_match_rejects_invalid_numeric_range(client: ASGITestClient) -> None:
    response = client.post(
        "/programs/match",
        json={"program_id": VALID_PROGRAM_ID, "profile": {"age": -1}},
    )

    assert response.status_code == 422


def test_program_api_returns_503_when_snapshot_is_missing(
    monkeypatch, tmp_path
) -> None:
    from app.main import create_app

    monkeypatch.setenv("FINBRIDGE_BIZINFO_SNAPSHOT", str(tmp_path / "missing.json"))
    missing_snapshot_client = ASGITestClient(create_app())
    assert missing_snapshot_client.get("/health").status_code == 200
    response = missing_snapshot_client.get(f"/programs/{VALID_PROGRAM_ID}")

    assert response.status_code == 503
    assert response.json()["error_code"] == "BIZINFO_SNAPSHOT_NOT_FOUND"
