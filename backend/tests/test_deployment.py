from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deployment import persist_source_data


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
