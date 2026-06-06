from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx

from text_ingestion.collectors.base import SourceCollector
from text_ingestion.models import TextItem


class ReviewsAPICollector(SourceCollector):
    """Generic public reviews API adapter.

    The target API should return a JSON object with an `items` list, or a JSON list directly.
    Field names can be adapted later by subclassing `_to_item`.
    """

    source_name = "reviews"

    def __init__(
        self,
        api_url: str | None,
        api_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.api_url = api_url
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds

    async def collect(self, max_items: int | None = None) -> AsyncIterator[TextItem]:
        if not self.api_url:
            raise RuntimeError("REVIEWS_API_URL is required to use ReviewsAPICollector")
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.api_url, headers=headers, params={"limit": max_items}
            )
            response.raise_for_status()
            payload = response.json()
        records = (
            payload.get("items", payload) if isinstance(payload, dict) else payload
        )
        for index, record in enumerate(records):
            if max_items is not None and index >= max_items:
                return
            yield self._to_item(record)

    def _to_item(self, record: dict[str, Any]) -> TextItem:
        text = (
            record.get("text")
            or record.get("body")
            or record.get("review")
            or record.get("content")
        )
        if not text:
            raise ValueError(
                "Review record does not contain a text/body/review/content field"
            )
        created_at = (
            record.get("created_at") or record.get("date") or record.get("published_at")
        )
        return TextItem(
            source_name=self.source_name,
            source_item_id=str(
                record.get("id") or record.get("review_id") or hash(str(record))
            ),
            title=record.get("title"),
            text=str(text),
            url=record.get("url"),
            created_at=datetime.fromisoformat(created_at) if created_at else None,
            raw_payload=record,
            metadata={
                "rating": record.get("rating"),
                "product_id": record.get("product_id"),
                "provider": record.get("provider"),
            },
        )
