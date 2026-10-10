from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_available() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Kessler API"


def test_archived_real_fixture_and_methods_are_exposed() -> None:
    with TestClient(app) as client:
        objects = client.get("/api/objects")
        methods = client.get("/api/methods")
        references = client.get("/api/reference-encounters")
    assert objects.status_code == 200
    assert objects.json()["items"][0]["name"] == "VANGUARD 1"
    assert methods.status_code == 200
    assert references.status_code == 200
    assert references.json()[0]["mode"] == "historical_validation"


def test_api_validation_is_structured() -> None:
    with TestClient(app) as client:
        response = client.post("/api/trajectories", json={
            "object_id": "5", "start": "2026-01-02T00:00:00Z",
            "end": "2026-01-01T00:00:00Z", "samples": 20, "frame": "TEME",
        })
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
