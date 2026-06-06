from __future__ import annotations

from text_ingestion.models import TextItem
from text_ingestion.storage import InMemoryRawStore, MinIORawStore


def test_in_memory_store_round_trip() -> None:
    store = InMemoryRawStore()
    item = TextItem(source_name="rss", source_item_id="1", text="hello")

    key = store.write_item(item)
    loaded = store.read_item(key)

    assert loaded == item
    assert key.startswith("source=rss/")
    assert key.endswith(".json")


def test_minio_object_key_is_partitioned() -> None:
    item = TextItem(source_name="reviews", source_item_id="r1", text="great")

    key = MinIORawStore.object_key(item)

    assert "source=reviews/" in key
    assert "year=" in key
    assert item.dedupe_id in key
