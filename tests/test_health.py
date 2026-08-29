from tests.conftest import ASGITestClient


def test_health(client: ASGITestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "FinBridge"}
