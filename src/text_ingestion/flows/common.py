from __future__ import annotations

import structlog

from text_ingestion.api import ModelAPIClient
from text_ingestion.collectors import SourceCollector
from text_ingestion.metrics import MetricsRecorder
from text_ingestion.rate_limit import SourceRateLimiters
from text_ingestion.storage import MinIORawStore

logger = structlog.get_logger(__name__)


async def process_collector_once(
    collector: SourceCollector,
    store: MinIORawStore,
    model_client: ModelAPIClient,
    limiters: SourceRateLimiters,
    max_items: int | None,
    metrics: MetricsRecorder | None = None,
) -> int:
    count = 0
    async for item in collector.collect(max_items=max_items):
        key = store.write_item(item)
        logger.info(
            "raw_item_stored",
            source_name=item.source_name,
            source_item_id=item.source_item_id,
            object_key=key,
        )
        await limiters.acquire(item.source_name)
        response = await model_client.send_item(item)
        logger.info(
            "item_sent_to_model",
            source_name=item.source_name,
            source_item_id=item.source_item_id,
            correlation_id=response.correlation_id,
            status_code=response.status_code,
        )
        if metrics:
            metrics.increment("items_processed")
        count += 1
    return count
