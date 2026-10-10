import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.catalog import CatalogLoader, validate_catalog
from app.data import GP_URL, CatalogStore, SourceCache, parse_gp_json
from app.models import Availability, DatasetStatus, Frame
from app.orbital import propagate_object, propagate_objects

FIXTURES = Path(__file__).parents[2] / "data" / "fixtures"
ACTIVE_PAYLOAD = (FIXTURES / "gp_active_sample.json").read_bytes()


def mock_source(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs))


@pytest.fixture
def loader(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    archived = parse_gp_json((FIXTURES / "gp_sample.json").read_bytes(), source="Archived test fallback")[0]
    store.upsert_objects(archived)
    store.set_dataset(DatasetStatus(name="gp", source_url=GP_URL, availability=Availability.STALE,
                                   record_count=1, parsing_status="archived_fixture", stale=True))
    return CatalogLoader(store, SourceCache(tmp_path / "cache", store), 7200)


@pytest.mark.asyncio
async def test_initial_load_replaces_archive_and_coalesces_concurrent_refreshes(loader, monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        await asyncio.sleep(.02)
        return httpx.Response(200, content=ACTIVE_PAYLOAD)

    mock_source(monkeypatch, handler)
    task = loader.start(automatic=True)
    assert loader.status().state == "loading"
    first, second = await asyncio.gather(loader.refresh(), loader.refresh())
    await task
    assert len(requests) == 1
    assert first.state == second.state == "ready"
    assert first.record_count == 4
    assert loader.store.object("5") is None
    assert loader.store.object("100981").category == "active"
    assert first.source.checksum_sha256
    assert first.source.dataset_timestamp
    assert first.categories == {"active": 4}
    await loader.refresh()
    assert len(requests) == 1  # The refresh button respects the fresh-cache floor.


@pytest.mark.asyncio
async def test_http_failure_retains_fallback_and_does_not_retry_automatically(loader, monkeypatch):
    requests = []
    mock_source(monkeypatch, lambda request: (requests.append(request), httpx.Response(403))[1])
    await loader.start(automatic=True)
    status = loader.status()
    assert status.state == "degraded"
    assert status.record_count == 1
    assert status.source.parsing_status == "archived_fixture"
    assert "HTTP 403" in status.source.error
    assert status.source.next_retry_at > datetime.now(UTC)
    await loader.refresh()
    await loader.start(automatic=True)
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_payload", [b"<html>blocked</html>", b"[]", b'[{"NORAD_CAT_ID": 42}]'])
async def test_invalid_successful_response_keeps_last_good_bytes_and_catalog(loader, monkeypatch, bad_payload):
    metadata = validate_catalog(ACTIVE_PAYLOAD)
    good = loader.cache.promote("gp", GP_URL, "json", ACTIVE_PAYLOAD, metadata)
    await loader.refresh()
    loader.store.set_dataset(good.model_copy(update={"retrieved_at": datetime.now(UTC) - timedelta(hours=3)}))
    mock_source(monkeypatch, lambda request: httpx.Response(200, content=bad_payload))
    await loader.refresh()
    assert (loader.cache.directory / "gp.json").read_bytes() == ACTIVE_PAYLOAD
    assert loader.store.count("objects") == 4
    assert loader.status().state == "degraded"
    assert loader.status().source.checksum_sha256 == good.checksum_sha256


@pytest.mark.asyncio
async def test_fresh_cache_survives_restart_without_network(loader, monkeypatch):
    loader.cache.promote("gp", GP_URL, "json", ACTIVE_PAYLOAD, validate_catalog(ACTIVE_PAYLOAD))
    await loader.refresh()
    path, directory = loader.store.path, loader.cache.directory
    loader.store.connection.close()
    store = CatalogStore(path)
    restarted = CatalogLoader(store, SourceCache(directory, store), 7200)
    mock_source(monkeypatch, lambda request: pytest.fail("Fresh offline restart must not download"))
    await restarted.start(automatic=True)
    assert restarted.status().state == "ready"
    assert restarted.store.count("objects") == 4
    assert restarted.status().source.checksum_sha256


@pytest.mark.asyncio
async def test_startup_load_commits_background_result(loader, monkeypatch):
    events = []
    mock_source(monkeypatch, lambda request: httpx.Response(200, content=ACTIVE_PAYLOAD))

    async def commit():
        events.append(loader.store.count("objects"))

    loader.persist = commit
    await loader.start(automatic=True)
    assert events == [4]


@pytest.mark.asyncio
async def test_failed_background_commit_is_not_ready(loader, monkeypatch):
    mock_source(monkeypatch, lambda request: httpx.Response(200, content=ACTIVE_PAYLOAD))

    async def commit():
        raise RuntimeError("volume unavailable")

    loader.persist = commit
    await loader.start(automatic=True)
    assert loader.status().state == "degraded"
    assert loader.status().error == "volume unavailable"


def test_real_active_fixture_and_duplicate_latest_epoch():
    records = json.loads(ACTIVE_PAYLOAD)
    old = {**records[0], "EPOCH": "2020-01-01T00:00:00.000000"}
    objects, errors = parse_gp_json(json.dumps([old, *records]).encode(), active_group=True)
    assert not errors
    assert len(objects) == 4
    assert objects[0].elements.epoch.year == 2026
    assert objects[-1].catalog_id == "100981"


@pytest.mark.parametrize("frame", [Frame.TEME, Frame.ITRS])
def test_batch_positions_match_single_object_and_preserve_identity(frame):
    objects, _ = parse_gp_json(ACTIVE_PAYLOAD, active_group=True)
    timestamps = [objects[0].elements.epoch, objects[0].elements.epoch + timedelta(minutes=1)]
    results = propagate_objects(objects, timestamps, frame)
    for obj, result in zip(objects, results):
        single, errors = propagate_object(obj, timestamps, frame)
        assert not errors and not result.errors
        assert result.object_id == obj.catalog_id
        for actual, expected in zip(result.states, single):
            assert actual.timestamp == expected.timestamp
            assert np.allclose(actual.position_m, expected.position_m, rtol=0, atol=.001)
            assert np.allclose(actual.velocity_m_s, expected.velocity_m_s, rtol=0, atol=.00001)


def test_application_starts_background_load_and_exposes_status(loader, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "store", loader.store)
    monkeypatch.setattr(main, "catalog_loader", loader)
    monkeypatch.setattr(main.settings, "auto_refresh_catalog", True)
    mock_source(monkeypatch, lambda request: httpx.Response(200, content=ACTIVE_PAYLOAD))
    with TestClient(main.app) as client:
        status = client.post("/api/catalog/refresh").json()
        assert status["state"] == "ready"
        assert status["record_count"] == 4
        page1 = client.get("/api/objects?limit=2&offset=0").json()
        page2 = client.get("/api/objects?limit=2&offset=2").json()
        assert page1["catalog_version"] == page2["catalog_version"]
        assert len(page1["items"] + page2["items"]) == 4
        assert "raw_omm" not in page1["items"][0]["elements"]
        assert client.get("/api/objects/100981").json()["elements"]["raw_omm"]
        response = client.post("/api/positions", json={"object_ids": ["100981", "missing"],
            "timestamps": ["2026-10-10T10:18:32Z"], "frame": "ITRS"})
        assert response.status_code == 200
        assert len(response.json()[0]["states"]) == 1
        assert response.json()[1]["errors"]
