from __future__ import annotations

import asyncio

import structlog

from text_ingestion.api import ModelAPIClient
from text_ingestion.collectors import SourceCollector
from text_ingestion.flows.common import process_collector_once
from text_ingestion.metrics import MetricsRecorder
from text_ingestion.rate_limit import SourceRateLimiters
from text_ingestion.storage import MinIORawStore

logger = structlog.get_logger(__name__)


async def run_live_polling(
    collectors: list[SourceCollector],
    store: MinIORawStore,
    model_client: ModelAPIClient,
    limiters: SourceRateLimiters,
    polling_interval_seconds: float,
    max_items_per_poll: int | None,
) -> None:
    metrics = MetricsRecorder()
    while True:
        for collector in collectors:
            try:
                await process_collector_once(
                    collector=collector,
                    store=store,
                    model_client=model_client,
                    limiters=limiters,
                    max_items=max_items_per_poll,
                    metrics=metrics,
                )
            except Exception:
                logger.exception(
                    "live_poll_source_failed", source_name=collector.source_name
                )
        logger.info(
            "live_poll_cycle_completed",
            sleep_seconds=polling_interval_seconds,
            metrics=dict(metrics.counters),
        )
        await asyncio.sleep(polling_interval_seconds)
