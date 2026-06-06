from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from text_ingestion.collectors.base import SourceCollector
from text_ingestion.models import TextItem


class RedditCollector(SourceCollector):
    """Collect Reddit submissions through Reddit's official API via PRAW."""

    source_name = "reddit"

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        user_agent: str,
        subreddits: list[str],
        limit: int = 25,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.subreddits = subreddits
        self.limit = limit

    async def collect(self, max_items: int | None = None) -> AsyncIterator[TextItem]:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Reddit credentials are required to use RedditCollector")
        try:
            import praw
        except ImportError as exc:
            raise RuntimeError(
                "Install the reddit extra: pip install '.[reddit]'"
            ) from exc

        reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
        )
        emitted = 0
        for subreddit_name in self.subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.new(limit=self.limit):
                if max_items is not None and emitted >= max_items:
                    return
                text = "\n\n".join(
                    part for part in [submission.title, submission.selftext] if part
                )
                if not text.strip():
                    continue
                yield TextItem(
                    source_name=self.source_name,
                    source_item_id=str(submission.id),
                    title=submission.title,
                    text=text,
                    url=getattr(submission, "url", None),
                    created_at=datetime.fromtimestamp(submission.created_utc, tz=UTC),
                    raw_payload=self._submission_payload(submission),
                    metadata={
                        "subreddit": subreddit_name,
                        "author": str(submission.author),
                    },
                )
                emitted += 1

    @staticmethod
    def _submission_payload(submission: Any) -> dict[str, Any]:
        return {
            "id": submission.id,
            "title": submission.title,
            "selftext": submission.selftext,
            "url": getattr(submission, "url", None),
            "permalink": getattr(submission, "permalink", None),
            "created_utc": submission.created_utc,
            "score": getattr(submission, "score", None),
            "num_comments": getattr(submission, "num_comments", None),
        }
