from __future__ import annotations

import pytest

from tests.conftest import ASGITestClient


VALID_PROGRAM_ID = "PBLN_000000000125864"


@pytest.fixture
def client(private_client: ASGITestClient) -> ASGITestClient:
    return private_client


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


def test_match_actual_raw_program_with_reference_stays_needs_review(
    client: ASGITestClient,
) -> None:
    response = client.post(
        "/programs/match",
        json={
            "program_id": VALID_PROGRAM_ID,
            "profile": {
                "user_type": "PRE_FOUNDER",
                "region": "영월군",
                "business_region": "영월군",
                "age": 30,
                "pre_founder": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["program"]["program_id"] == VALID_PROGRAM_ID
    assert payload["match_status"] == "NEEDS_REVIEW"
    assert payload["condition_results"]
    assert payload["evidence"]
    assert payload["source"]["source"] == "BIZINFO"


def test_match_actual_supported_raw_program(client: ASGITestClient) -> None:
    response = client.post(
        "/programs/match",
        json={
            "program_id": "PBLN_000000000125612",
            "profile": {
                "region": "동구",
                "business_region": "동구",
                "age": 30,
                "pre_founder": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["match_status"] == "MATCH"
    assert len(payload["condition_results"]) == 3
    assert len(payload["evidence"]) == 3


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
