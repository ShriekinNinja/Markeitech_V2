from fastapi.testclient import TestClient
from markeitech.api import app


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_defaults_to_data_only() -> None:
    client = TestClient(app)

    response = client.get("/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["stage"] == "0"
    assert payload["mode"] == "data_only"
    assert payload["execution_enabled"] is False
