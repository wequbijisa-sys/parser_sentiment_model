from __future__ import annotations

import time

import pytest

from text_ingestion.rate_limit import AsyncTokenBucketRateLimiter, SourceRateLimiters


@pytest.mark.asyncio
async def test_rate_limiter_waits_after_burst_is_exhausted() -> None:
    limiter = AsyncTokenBucketRateLimiter(requests_per_minute=120, burst_size=1)

    await limiter.acquire()
    started = time.perf_counter()
    await limiter.acquire()
    elapsed = time.perf_counter() - started

    assert elapsed >= 0.45


@pytest.mark.asyncio
async def test_source_rate_limiters_apply_per_source_limiter() -> None:
    limiters = SourceRateLimiters(
        global_requests_per_minute=1000,
        per_source_requests_per_minute={"rss": 120},
        burst_size=1,
    )

    await limiters.acquire("rss")
    started = time.perf_counter()
    await limiters.acquire("rss")

    assert time.perf_counter() - started >= 0.45
