from __future__ import annotations

import pytest
from pydantic import ValidationError

from text_ingestion.models import ModelRequest, TextItem


def test_text_item_generates_content_hash() -> None:
    item = TextItem(source_name="rss", source_item_id="1", text="hello world")

    assert item.content_hash
    assert item.dedupe_id == item.content_hash


def test_text_item_rejects_blank_text() -> None:
    with pytest.raises(ValidationError):
        TextItem(source_name="rss", source_item_id="1", text="   ")


def test_model_request_from_item_includes_source_metadata() -> None:
    item = TextItem(
        source_name="reddit", source_item_id="abc", text="hello", metadata={"x": 1}
    )

    request = ModelRequest.from_item(item)

    assert request.text == "hello"
    assert request.source_name == "reddit"
    assert request.source_item_id == "abc"
    assert request.metadata["x"] == 1
    assert request.metadata["content_hash"] == item.content_hash
