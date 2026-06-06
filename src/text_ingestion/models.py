from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from text_ingestion.utils.dedupe import stable_hash
from text_ingestion.utils.time import utc_now


class TextItem(BaseModel):
    """Canonical representation for one collected user-generated or public text item."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    title: str | None = None
    text: str = Field(min_length=1)
    url: HttpUrl | None = None
    created_at: datetime | None = None
    collected_at: datetime = Field(default_factory=utc_now)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str | None = None

    @field_validator("text")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text must not be blank")
        return stripped

    @field_validator("source_name", "source_item_id")
    @classmethod
    def non_empty_identifier(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("identifier fields must not be blank")
        return stripped

    def model_post_init(self, __context: Any) -> None:
        if self.content_hash is None:
            self.content_hash = stable_hash(
                {
                    "source_name": self.source_name,
                    "source_item_id": self.source_item_id,
                    "title": self.title,
                    "text": self.text,
                    "url": str(self.url) if self.url else None,
                    "created_at": (
                        self.created_at.isoformat() if self.created_at else None
                    ),
                }
            )

    @property
    def dedupe_id(self) -> str:
        return self.content_hash or self.source_item_id


class ModelRequest(BaseModel):
    """Generic request body for a model endpoint accepting text input."""

    text: str
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    source_name: str
    source_item_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_item(cls, item: TextItem) -> ModelRequest:
        return cls(
            text=item.text,
            source_name=item.source_name,
            source_item_id=item.source_item_id,
            metadata={"content_hash": item.content_hash, **item.metadata},
        )


class ModelResponse(BaseModel):
    """Normalized response envelope returned by the model API client."""

    correlation_id: str
    status_code: int
    body: dict[str, Any] | list[Any] | str | None = None
    elapsed_ms: float
