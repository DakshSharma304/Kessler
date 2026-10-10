"""Optional ASGI integration for a persistent cloud cache."""

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.types import ASGIApp, Message, Receive, Scope, Send

Commit = Callable[[], Awaitable[None]]


class PersistRefreshMiddleware:
    def __init__(self, app: ASGIApp, commit: Commit):
        self.app = app
        self.commit = commit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        refresh = (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"].rstrip("/") == "/api/data/refresh"
        )

        async def send_with_commit(message: Message) -> None:
            if refresh and message["type"] == "http.response.start" and message["status"] < 500:
                # Cache writes and SQLite transactions have finished before the response starts.
                await self.commit()
            await send(message)

        await self.app(scope, receive, send_with_commit)


def persist_source_data(app: FastAPI, commit: Commit) -> FastAPI:
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with original_lifespan(application):
            # Preserve the offline fixture initialized during the application's startup.
            await commit()
            try:
                yield
            finally:
                await commit()

    app.router.lifespan_context = lifespan
    app.add_middleware(PersistRefreshMiddleware, commit=commit)
    return app
