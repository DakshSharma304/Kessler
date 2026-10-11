from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient

from app.data import parse_gp_json
from app.main import app
from app.models import Frame
from app.orbital import propagate_object


def test_compact_window_matches_scientific_positions_and_preserves_errors():
    with TestClient(app) as client:
        object_id = client.get("/api/objects?limit=1").json()["items"][0]["catalog_id"]
        start = "2026-10-11T00:00:00Z"
        response = client.post("/api/visualization/window", json={"object_ids": [object_id, "missing"], "start": start})
        assert response.status_code == 200
        window = response.json()
        assert window["display_only"] is True and window["frame"] == "ITRS"
        assert "not for scientific" in window["interpolation"]
        assert len(window["timestamps"]) == 5
        assert window["catalog_version"] == client.get("/api/objects?limit=1").json()["catalog_version"]
        assert len(window["tracks"]) == 1
        assert any("missing:" in error for error in window["errors"])
        exact = client.post("/api/positions", json={"object_ids": [object_id], "timestamps": window["timestamps"], "frame": "ITRS"}).json()[0]
        assert window["tracks"][0]["positions_m"] == [state["position_m"] for state in exact["states"]]
        assert window["tracks"][0]["velocities_m_s"] == [state["velocity_m_s"] for state in exact["states"]]
        assert window["tracks"][0]["metadata"] == exact["states"][0]["metadata"]


def test_window_rejects_naive_time_and_excessive_catalog():
    with TestClient(app) as client:
        assert client.post("/api/visualization/window", json={"object_ids": ["5"], "start": "2026-10-11T00:00:00"}).status_code == 422
        assert client.post("/api/visualization/window", json={"object_ids": ["5"] * 20_001, "start": "2026-10-11T00:00:00Z"}).status_code == 422


def test_window_reports_incomplete_tracks_instead_of_bridging_failed_samples(monkeypatch):
    from app import main
    original_positions = main.positions

    async def incomplete(request):
        results = await original_positions(request)
        results[0].states.pop()
        return results

    with TestClient(app) as client:
        object_id = client.get("/api/objects?limit=1").json()["items"][0]["catalog_id"]
        monkeypatch.setattr(main, "positions", incomplete)
        response = client.post("/api/visualization/window", json={"object_ids": [object_id], "start": "2026-10-11T00:00:00Z"})
        assert response.status_code == 200
        assert response.json()["tracks"] == []
        assert "Incomplete animation samples" in response.json()["errors"][0]


def test_window_rejects_catalog_replacement_during_computation(monkeypatch):
    from app import main
    with TestClient(app) as client:
        object_id = client.get("/api/objects?limit=1").json()["items"][0]["catalog_id"]
        versions = iter(["before", "after"])
        monkeypatch.setattr(main.catalog_loader, "status", lambda: SimpleNamespace(catalog_version=next(versions)))
        response = client.post("/api/visualization/window", json={"object_ids": [object_id], "start": "2026-10-11T00:00:00Z"})
        assert response.status_code == 409
        assert "Catalog changed" in response.json()["detail"]


def test_display_hermite_error_against_real_sgp4_fixture():
    # Fixture-specific display accuracy check, not a general scientific error bound.
    path = Path(__file__).parents[2] / "data/fixtures/gp_active_sample.json"
    objects, errors = parse_gp_json(path.read_bytes(), active_group=True)
    assert not errors
    start = datetime(2026, 10, 10, 23, tzinfo=UTC)
    maximum_error = 0
    for obj in objects:
        endpoints, errors = propagate_object(obj, [start, start + timedelta(seconds=300)], Frame.ITRS)
        assert not errors
        p0, p1 = [np.array(state.position_m) for state in endpoints]
        v0, v1 = [np.array(state.velocity_m_s) for state in endpoints]
        for fraction in (.25, .5, .75):
            exact, errors = propagate_object(obj, [start + timedelta(seconds=300 * fraction)], Frame.ITRS)
            assert not errors
            u = fraction
            interpolated = (2*u**3 - 3*u*u + 1)*p0 + (u**3 - 2*u*u + u)*300*v0 + (-2*u**3 + 3*u*u)*p1 + (u**3 - u*u)*300*v1
            maximum_error = max(maximum_error, np.linalg.norm(interpolated - exact[0].position_m))
    assert maximum_error < 5_000, f"Fixture display error {maximum_error:.3f} m"
