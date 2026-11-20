"""Small in-process TTL cache shared by the forecast and AI adapters."""

from __future__ import annotations

import asyncio
import time


class TTLCache[V]:
    """Bounded cache whose entries expire after `ttl` seconds; the oldest entry is evicted first."""

    def __init__(self, ttl: float, limit: int) -> None:
        self.ttl = ttl
        self.limit = limit
        self._items: dict[str, tuple[float, V]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> V | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            expires, value = entry
            if expires < time.monotonic():
                del self._items[key]
                return None
            return value

    async def put(self, key: str, value: V) -> None:
        async with self._lock:
            if key not in self._items and len(self._items) >= self.limit:
                oldest = min(self._items, key=lambda k: self._items[k][0])
                del self._items[oldest]
            self._items[key] = (time.monotonic() + self.ttl, value)

    def clear(self) -> None:
        self._items.clear()
