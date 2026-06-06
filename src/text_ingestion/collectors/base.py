from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from text_ingestion.models import TextItem


class SourceCollector(ABC):
    """Plugin contract for all text sources."""

    source_name: str

    @abstractmethod
    async def collect(self, max_items: int | None = None) -> AsyncIterator[TextItem]:
        """Yield collected items once for batch-style execution."""

    async def poll(self, max_items: int | None = None) -> AsyncIterator[TextItem]:
        """Default polling behavior; adapters may override for cursor-aware APIs."""
        async for item in self.collect(max_items=max_items):
            yield item
