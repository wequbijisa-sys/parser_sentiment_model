from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from text_ingestion.collectors.base import SourceCollector
from text_ingestion.models import TextItem


class RSSCollector(SourceCollector):
    """Collect public RSS/Atom feed entries."""

    source_name = "rss"

    def __init__(self, feed_urls: list[str], timeout_seconds: float = 10.0) -> None:
        self.feed_urls = feed_urls
        self.timeout_seconds = timeout_seconds

    async def collect(self, max_items: int | None = None) -> AsyncIterator[TextItem]:
        emitted = 0
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, follow_redirects=True
        ) as client:
            for feed_url in self.feed_urls:
                response = await client.get(feed_url)
                response.raise_for_status()
                parsed = feedparser.parse(response.text)
                for entry in parsed.entries:
                    if max_items is not None and emitted >= max_items:
                        return
                    text = self._entry_text(entry)
                    if not text:
                        continue
                    item_id = str(
                        entry.get("id")
                        or entry.get("guid")
                        or entry.get("link")
                        or text[:80]
                    )
                    yield TextItem(
                        source_name=self.source_name,
                        source_item_id=item_id,
                        title=entry.get("title"),
                        text=text,
                        url=entry.get("link"),
                        created_at=self._parse_entry_datetime(entry),
                        raw_payload=dict(entry),
                        metadata={
                            "feed_url": feed_url,
                            "feed_title": parsed.feed.get("title"),
                        },
                    )
                    emitted += 1

    @staticmethod
    def _entry_text(entry: dict) -> str:
        for key in ("summary", "description", "title"):
            value = entry.get(key)
            if value:
                return str(value)
        content = entry.get("content")
        if content and isinstance(content, list) and content[0].get("value"):
            return str(content[0]["value"])
        return ""

    @staticmethod
    def _parse_entry_datetime(entry: dict) -> datetime | None:
        for key in ("published", "updated", "created"):
            value = entry.get(key)
            if not value:
                continue
            try:
                parsed = parsedate_to_datetime(str(value))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except (TypeError, ValueError):
                continue
        return None
