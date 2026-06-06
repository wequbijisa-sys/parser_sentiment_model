from __future__ import annotations

import asyncio

from text_ingestion.collectors import SourceCollector
from text_ingestion.models import TextItem


class MockCollector(SourceCollector):
    source_name = "mock"

    async def collect(self, max_items: int | None = None):
        for index in range(max_items or 2):
            yield TextItem(
                source_name=self.source_name,
                source_item_id=str(index),
                text=f"text {index}",
            )


def test_mock_source_adapter_respects_max_items() -> None:
    async def collect_items() -> list[TextItem]:
        collector = MockCollector()
        return [item async for item in collector.collect(max_items=3)]

    items = asyncio.run(collect_items())

    assert len(items) == 3
    assert all(item.source_name == "mock" for item in items)
