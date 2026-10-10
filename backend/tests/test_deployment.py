from fastapi import FastAPI
from fastapi.testclient import TestClient
import asyncio
import pytest

from app.deployment import persist_source_data


@pytest.mark.asyncio
async def test_background_and_request_commits_are_serialized() -> None:
    active = 0
    maximum = 0

    async def commit():
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(.01)
        active -= 1

    app = persist_source_data(FastAPI(), commit)
    await asyncio.gather(*(app.state.commit_source_data() for _ in range(3)))
    assert maximum == 1


def test_volume_commit_happens_after_refresh_and_on_lifecycle_boundaries() -> None:
    events = []
    app = FastAPI()

    async def commit() -> None:
        events.append("committed")

    @app.post("/api/data/refresh")
    async def refresh() -> dict:
        events.append("data_written")
        return {"status": "cached"}

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    with TestClient(persist_source_data(app, commit)) as client:
        assert events == ["committed"]
        assert client.get("/api/health").status_code == 200
        assert events == ["committed"]
        assert client.post("/api/data/refresh").json() == {"status": "cached"}
        assert events == ["committed", "data_written", "committed"]
    assert events[-1] == "committed"
    assert len(events) == 4


def test_volume_commit_failure_is_not_reported_as_successful_refresh() -> None:
    app = FastAPI()
    commits = 0

    async def commit() -> None:
        nonlocal commits
        commits += 1
        if commits == 2:
            raise RuntimeError("durable storage unavailable")

    @app.post("/api/data/refresh")
    async def refresh() -> dict:
        return {"status": "cached"}

    with TestClient(persist_source_data(app, commit), raise_server_exceptions=False) as client:
        assert client.post("/api/data/refresh").status_code == 500
