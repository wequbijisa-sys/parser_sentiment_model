from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="local", alias="ENVIRONMENT")

    minio_endpoint_url: str = Field(
        default="http://localhost:9000", alias="MINIO_ENDPOINT_URL"
    )
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="raw-text-items", alias="MINIO_BUCKET")
    minio_region: str = Field(default="us-east-1", alias="MINIO_REGION")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    model_api_url: str = Field(
        default="http://localhost:8080/predict", alias="MODEL_API_URL"
    )
    model_api_auth_token: str | None = Field(default=None, alias="MODEL_API_AUTH_TOKEN")
    model_api_auth_header: str = Field(
        default="Authorization", alias="MODEL_API_AUTH_HEADER"
    )
    model_api_timeout_seconds: float = Field(
        default=10.0, alias="MODEL_API_TIMEOUT_SECONDS"
    )
    model_api_max_retries: int = Field(default=3, alias="MODEL_API_MAX_RETRIES")

    global_requests_per_minute: int = Field(
        default=60, alias="GLOBAL_REQUESTS_PER_MINUTE"
    )
    per_source_requests_per_minute: str | None = Field(
        default=None, alias="PER_SOURCE_REQUESTS_PER_MINUTE"
    )
    burst_size: int | None = Field(default=None, alias="BURST_SIZE")

    polling_interval_seconds: float = Field(
        default=60.0, alias="POLLING_INTERVAL_SECONDS"
    )
    batch_max_items: int = Field(default=100, alias="BATCH_MAX_ITEMS")

    reddit_client_id: str | None = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = Field(default=None, alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(
        default="streaming-text-ingestion/0.1", alias="REDDIT_USER_AGENT"
    )
    reddit_subreddits: str = Field(
        default="MachineLearning,python", alias="REDDIT_SUBREDDITS"
    )
    reddit_limit: int = Field(default=25, alias="REDDIT_LIMIT")

    rss_feed_urls: str = Field(default="", alias="RSS_FEED_URLS")
    rss_limit: int = Field(default=50, alias="RSS_LIMIT")

    reviews_api_url: str | None = Field(default=None, alias="REVIEWS_API_URL")
    reviews_api_token: str | None = Field(default=None, alias="REVIEWS_API_TOKEN")
    reviews_limit: int = Field(default=50, alias="REVIEWS_LIMIT")

    @field_validator("global_requests_per_minute")
    @classmethod
    def positive_rpm(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("GLOBAL_REQUESTS_PER_MINUTE must be positive")
        return value

    @property
    def reddit_subreddit_list(self) -> list[str]:
        return [
            part.strip() for part in self.reddit_subreddits.split(",") if part.strip()
        ]

    @property
    def rss_feed_url_list(self) -> list[str]:
        return [part.strip() for part in self.rss_feed_urls.split(",") if part.strip()]

    @property
    def per_source_rpm_map(self) -> dict[str, int]:
        if not self.per_source_requests_per_minute:
            return {}
        limits: dict[str, int] = {}
        for pair in self.per_source_requests_per_minute.split(","):
            if not pair.strip():
                continue
            source, rpm = pair.split(":", maxsplit=1)
            limits[source.strip()] = int(rpm.strip())
        return limits


@lru_cache
def get_settings() -> Settings:
    return Settings()
