"""In-process publish/subscribe broker for Server-Sent Events.

Provides a tiny async broker that fans out JSON-serialisable payloads to every
connected SSE client. Suitable for a single-process demo deployment.
"""

from __future__ import annotations

import asyncio
from typing import Any


class EventBroker:
    """Fans out messages to all subscribed asyncio queues."""

    def __init__(self) -> None:
        """Initialise an empty set of subscriber queues."""
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new subscriber and return its queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue."""
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, message: dict[str, Any]) -> None:
        """Push a message to every current subscriber.

        Args:
            message: A JSON-serialisable payload to broadcast.
        """
        async with self._lock:
            targets = list(self._subscribers)
        for queue in targets:
            await queue.put(message)


broker = EventBroker()
