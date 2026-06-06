from __future__ import annotations

import asyncio
import time

from text_ingestion.rate_limit import AsyncTokenBucketRateLimiter, SourceRateLimiters


def test_rate_limiter_waits_after_burst_is_exhausted() -> None:
    async def run_check() -> float:
        limiter = AsyncTokenBucketRateLimiter(requests_per_minute=120, burst_size=1)

        await limiter.acquire()
        started = time.perf_counter()
        await limiter.acquire()
        return time.perf_counter() - started

    assert asyncio.run(run_check()) >= 0.45


def test_source_rate_limiters_apply_per_source_limiter() -> None:
    async def run_check() -> float:
        limiters = SourceRateLimiters(
            global_requests_per_minute=1000,
            per_source_requests_per_minute={"rss": 120},
            burst_size=1,
        )

        await limiters.acquire("rss")
        started = time.perf_counter()
        await limiters.acquire("rss")
        return time.perf_counter() - started

    assert asyncio.run(run_check()) >= 0.45
