from __future__ import annotations

import structlog

from text_ingestion.api import ModelAPIClient
from text_ingestion.collectors import SourceCollector
from text_ingestion.flows.common import process_collector_once
from text_ingestion.metrics import MetricsRecorder
from text_ingestion.rate_limit import SourceRateLimiters
from text_ingestion.storage import MinIORawStore

logger = structlog.get_logger(__name__)


async def run_batch_ingestion(
    collectors: list[SourceCollector],
    store: MinIORawStore,
    model_client: ModelAPIClient,
    limiters: SourceRateLimiters,
    max_items_per_source: int | None,
) -> int:
    metrics = MetricsRecorder()
    total = 0
    for collector in collectors:
        logger.info("batch_source_started", source_name=collector.source_name)
        total += await process_collector_once(
            collector=collector,
            store=store,
            model_client=model_client,
            limiters=limiters,
            max_items=max_items_per_source,
            metrics=metrics,
        )
    logger.info(
        "batch_ingestion_completed", total_items=total, metrics=dict(metrics.counters)
    )
    return total
