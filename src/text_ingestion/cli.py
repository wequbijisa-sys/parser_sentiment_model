from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from text_ingestion.api import ModelAPIClient
from text_ingestion.collectors import (
    RedditCollector,
    ReviewsAPICollector,
    RSSCollector,
    SourceCollector,
)
from text_ingestion.config import Settings, get_settings
from text_ingestion.flows import run_batch_ingestion, run_live_polling, run_replay
from text_ingestion.logging import configure_logging
from text_ingestion.rate_limit import SourceRateLimiters
from text_ingestion.storage import MinIORawStore

app = typer.Typer(
    help="Collect public text data, store it in MinIO, and send it to a model API."
)


def build_collectors(
    settings: Settings, enabled_sources: list[str]
) -> list[SourceCollector]:
    collectors: list[SourceCollector] = []
    requested = {source.strip().lower() for source in enabled_sources}
    if "rss" in requested:
        collectors.append(
            RSSCollector(settings.rss_feed_url_list, settings.model_api_timeout_seconds)
        )
    if "reddit" in requested:
        collectors.append(
            RedditCollector(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
                subreddits=settings.reddit_subreddit_list,
                limit=settings.reddit_limit,
            )
        )
    if "reviews" in requested:
        collectors.append(
            ReviewsAPICollector(
                api_url=settings.reviews_api_url,
                api_token=settings.reviews_api_token,
                timeout_seconds=settings.model_api_timeout_seconds,
            )
        )
    return collectors


def build_store(settings: Settings) -> MinIORawStore:
    store = MinIORawStore(
        endpoint_url=settings.minio_endpoint_url,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        region=settings.minio_region,
        secure=settings.minio_secure,
    )
    store.ensure_bucket()
    return store


def build_model_client(settings: Settings) -> ModelAPIClient:
    return ModelAPIClient(
        endpoint_url=settings.model_api_url,
        auth_token=settings.model_api_auth_token,
        auth_header=settings.model_api_auth_header,
        timeout_seconds=settings.model_api_timeout_seconds,
        max_retries=settings.model_api_max_retries,
    )


def build_limiters(settings: Settings) -> SourceRateLimiters:
    return SourceRateLimiters(
        global_requests_per_minute=settings.global_requests_per_minute,
        per_source_requests_per_minute=settings.per_source_rpm_map,
        burst_size=settings.burst_size,
    )


@app.command()
def batch(
    sources: Annotated[
        list[str] | None,
        typer.Option("--source", "-s", help="Source to enable: rss, reddit, reviews."),
    ] = None,
    max_items: Annotated[int | None, typer.Option(help="Max items per source.")] = None,
) -> None:
    """Run one collection pass and send collected items to the model API."""
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(
        run_batch_ingestion(
            collectors=build_collectors(settings, sources or ["rss"]),
            store=build_store(settings),
            model_client=build_model_client(settings),
            limiters=build_limiters(settings),
            max_items_per_source=max_items or settings.batch_max_items,
        )
    )


@app.command()
def live(
    sources: Annotated[list[str] | None, typer.Option("--source", "-s")] = None,
    max_items_per_poll: Annotated[
        int | None, typer.Option(help="Max items per source per poll.")
    ] = None,
) -> None:
    """Continuously poll configured sources."""
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(
        run_live_polling(
            collectors=build_collectors(settings, sources or ["rss"]),
            store=build_store(settings),
            model_client=build_model_client(settings),
            limiters=build_limiters(settings),
            polling_interval_seconds=settings.polling_interval_seconds,
            max_items_per_poll=max_items_per_poll or settings.batch_max_items,
        )
    )


@app.command()
def replay(
    prefix: Annotated[str, typer.Option(help="MinIO object prefix to replay.")] = "",
    max_items: Annotated[
        int | None, typer.Option(help="Max stored items to replay.")
    ] = None,
) -> None:
    """Replay previously stored raw records from MinIO to the model API."""
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(
        run_replay(
            store=build_store(settings),
            model_client=build_model_client(settings),
            limiters=build_limiters(settings),
            prefix=prefix,
            max_items=max_items,
        )
    )


if __name__ == "__main__":
    app()
