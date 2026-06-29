"""FastAPI application for the Pulse Dashboard.

Exposes REST snapshot endpoints, an ingest endpoint used by the simulator and a
Server-Sent Events stream that pushes a fresh dashboard snapshot whenever a new
event is recorded. Also serves the single-file frontend.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import database
from app.events import broker

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Pulse Dashboard", version="1.0.0")


class EventIn(BaseModel):
    """Incoming event payload posted by clients or the simulator."""

    kind: str = Field(..., description="Event type, e.g. 'order' or 'booking'.")
    item: str = Field(..., description="Product or service name.")
    amount: float = Field(..., ge=0, description="Monetary value of the event.")


@app.on_event("startup")
def _startup() -> None:
    """Ensure the database schema exists before serving traffic."""
    database.init_db()


@app.get("/")
def index() -> FileResponse:
    """Serve the single-file dashboard UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/snapshot")
def get_snapshot() -> JSONResponse:
    """Return the current dashboard snapshot."""
    return JSONResponse(database.snapshot())


@app.post("/api/events")
async def post_event(event: EventIn) -> JSONResponse:
    """Record a new event and broadcast an updated snapshot to SSE clients.

    Args:
        event: The incoming event payload.

    Returns:
        The stored event as JSON.
    """
    stored = database.insert_event(event.kind, event.item, event.amount)
    await broker.publish({"event": stored, "snapshot": database.snapshot()})
    return JSONResponse(stored, status_code=201)


async def _event_stream(request: Request) -> AsyncIterator[str]:
    """Yield SSE-formatted messages for one connected client.

    Sends an initial snapshot immediately, then forwards every broadcast until
    the client disconnects. Emits periodic comments to keep the connection
    alive through proxies.
    """
    queue = await broker.subscribe()
    try:
        initial = {"event": None, "snapshot": database.snapshot()}
        yield f"data: {json.dumps(initial)}\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(message)}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        await broker.unsubscribe(queue)


@app.get("/api/stream")
async def stream(request: Request) -> StreamingResponse:
    """Open a Server-Sent Events stream of live dashboard updates."""
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers=headers,
    )
