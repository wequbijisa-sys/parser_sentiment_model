from __future__ import annotations

import structlog

from text_ingestion.api import ModelAPIClient
from text_ingestion.rate_limit import SourceRateLimiters
from text_ingestion.storage import MinIORawStore

logger = structlog.get_logger(__name__)


async def run_replay(
    store: MinIORawStore,
    model_client: ModelAPIClient,
    limiters: SourceRateLimiters,
    prefix: str = "",
    max_items: int | None = None,
) -> int:
    count = 0
    for item in store.iter_items(prefix=prefix):
        if max_items is not None and count >= max_items:
            break
        await limiters.acquire(item.source_name)
        response = await model_client.send_item(item)
        logger.info(
            "replayed_item_sent",
            source_name=item.source_name,
            source_item_id=item.source_item_id,
            correlation_id=response.correlation_id,
            status_code=response.status_code,
        )
        count += 1
    logger.info("replay_completed", total_items=count, prefix=prefix)
    return count
