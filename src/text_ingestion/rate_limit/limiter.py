from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class AsyncTokenBucketRateLimiter:
    """Concurrency-safe async token-bucket limiter configured in requests per minute."""

    def __init__(self, requests_per_minute: int, burst_size: int | None = None) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self.requests_per_minute = requests_per_minute
        self.capacity = max(1, burst_size or requests_per_minute)
        self._tokens = float(self.capacity)
        self._refill_per_second = requests_per_minute / 60.0
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                missing = 1.0 - self._tokens
                wait_seconds = missing / self._refill_per_second
            await asyncio.sleep(wait_seconds)

    @asynccontextmanager
    async def limit(self) -> AsyncIterator[None]:
        await self.acquire()
        yield

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = max(0.0, now - self._updated_at)
        self._updated_at = now
        self._tokens = min(
            self.capacity, self._tokens + elapsed * self._refill_per_second
        )


class SourceRateLimiters:
    """Composes a required global limiter with optional per-source limiters."""

    def __init__(
        self,
        global_requests_per_minute: int,
        per_source_requests_per_minute: dict[str, int] | None = None,
        burst_size: int | None = None,
    ) -> None:
        self.global_limiter = AsyncTokenBucketRateLimiter(
            global_requests_per_minute, burst_size
        )
        self.source_limiters = {
            source: AsyncTokenBucketRateLimiter(rpm, burst_size)
            for source, rpm in (per_source_requests_per_minute or {}).items()
        }

    async def acquire(self, source_name: str) -> None:
        await self.global_limiter.acquire()
        limiter = self.source_limiters.get(source_name)
        if limiter:
            await limiter.acquire()
