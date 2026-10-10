"""One coordinated, nonblocking initial GP load and explicit policy-aware refresh."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from app.data import GP_URL, CatalogStore, SourceCache, parse_gp_json
from app.models import Availability, CatalogLoadingStatus
from app.orbital import satrec_from_object


def validate_catalog(payload: bytes) -> dict:
    objects, errors = parse_gp_json(payload, active_group=True)
    if not objects:
        raise ValueError("GP response contains no valid orbital objects; previous catalog retained")
    # Required SGP4 fields and initialization must work before bytes become the good cache.
    for obj in objects:
        satrec_from_object(obj)
    return {
        "record_count": len(objects), "parsing_status": "parsed",
        "dataset_timestamp": min(obj.elements.epoch for obj in objects),
        "error": "; ".join(errors[:5]) or None,
    }


class CatalogLoader:
    def __init__(self, store: CatalogStore, cache: SourceCache, ttl_seconds: int):
        self.store, self.cache, self.ttl_seconds = store, cache, ttl_seconds
        self.task: asyncio.Task | None = None
        self.state = "idle"
        self.error: str | None = None
        self.persist: Callable[[], Awaitable[None]] | None = None

    def status(self) -> CatalogLoadingStatus:
        source = next((item for item in self.store.dataset_statuses() if item.name == "gp"), None)
        if source and source.retrieved_at and datetime.now(UTC) - source.retrieved_at >= timedelta(seconds=self.ttl_seconds):
            source = source.model_copy(update={"availability": Availability.STALE, "stale": True})
        count = self.store.count("objects")
        state = self.state
        if state != "loading":
            state = "ready" if count and source and source.availability == Availability.AVAILABLE else "degraded" if count else "failed"
            if self.error:
                state = "degraded" if count else "failed"
        return CatalogLoadingStatus(
            state=state, record_count=count, source=source, categories=self.store.categories(),
            catalog_version=(source.checksum_sha256 if source else None) or "archived-fixture",
            error=self.error,
        )

    def start(self, *, automatic: bool = False) -> asyncio.Task:
        if not self.task or self.task.done():
            self.state = "loading"
            self.error = None
            self.task = asyncio.create_task(self._load(automatic))
        return self.task

    async def refresh(self) -> CatalogLoadingStatus:
        await asyncio.shield(self.start())
        return self.status()

    async def _load(self, automatic: bool) -> None:
        try:
            payload, source = await self.cache.fetch(
                "gp", GP_URL, self.ttl_seconds, "json", validate=validate_catalog, automatic=automatic,
            )
            if payload is not None:
                try:
                    validate_catalog(payload)
                    objects, _ = parse_gp_json(payload, active_group=True)
                    self.store.replace_objects(objects)
                except (ValueError, KeyError, TypeError) as exc:
                    self.store.set_dataset(source.model_copy(update={
                        "availability": Availability.STALE if self.store.count("objects") else Availability.UNAVAILABLE,
                        "stale": True, "parsing_status": "parse_failed", "error": str(exc),
                    }))
            if self.persist:
                await self.persist()
        except Exception as exc:
            self.error = str(exc)
            logging.getLogger(__name__).exception("Catalog loading failed; retaining existing data")
        finally:
            self.state = "idle"

    async def close(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
        elif self.task:
            # Retrieve exceptions so a failed persistence operation is not hidden.
            self.task.result()
