from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import UTC, datetime

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from text_ingestion.models import TextItem


class MinIORawStore:
    """Store and retrieve raw text items in S3-compatible MinIO object storage."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        secure: bool = False,
        client: BaseClient | None = None,
    ) -> None:
        self.bucket = bucket
        self.client = client or boto3.client(
            "s3",
            endpoint_url=(
                endpoint_url
                if endpoint_url.startswith("http")
                else self._endpoint(endpoint_url, secure)
            ),
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        existing = [
            bucket["Name"] for bucket in self.client.list_buckets().get("Buckets", [])
        ]
        if self.bucket not in existing:
            self.client.create_bucket(Bucket=self.bucket)

    def write_item(self, item: TextItem) -> str:
        key = self.object_key(item)
        body = item.model_dump_json(mode="json").encode("utf-8")
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
            Metadata={
                "source_name": item.source_name,
                "source_item_id": item.source_item_id,
                "content_hash": item.content_hash or "",
            },
        )
        return key

    def write_items_jsonl(self, items: Iterable[TextItem], prefix: str) -> str:
        now = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        key = f"{prefix.rstrip('/')}/batch-{now}.jsonl"
        body = "\n".join(item.model_dump_json(mode="json") for item in items).encode(
            "utf-8"
        )
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType="application/x-ndjson",
        )
        return key

    def read_item(self, key: str) -> TextItem:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        data = response["Body"].read().decode("utf-8")
        return TextItem.model_validate_json(data)

    def iter_items(self, prefix: str = "") -> Iterator[TextItem]:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for entry in page.get("Contents", []):
                key = entry["Key"]
                if key.endswith(".jsonl"):
                    yield from self._iter_jsonl(key)
                elif key.endswith(".json"):
                    yield self.read_item(key)

    def _iter_jsonl(self, key: str) -> Iterator[TextItem]:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        for line in response["Body"].read().decode("utf-8").splitlines():
            if line.strip():
                yield TextItem.model_validate_json(line)

    @staticmethod
    def object_key(item: TextItem) -> str:
        partition_date = item.collected_at.astimezone(UTC)
        return (
            f"source={item.source_name}/"
            f"year={partition_date:%Y}/month={partition_date:%m}/day={partition_date:%d}/"
            f"{item.dedupe_id}.json"
        )

    @staticmethod
    def _endpoint(endpoint: str, secure: bool) -> str:
        scheme = "https" if secure else "http"
        return f"{scheme}://{endpoint}"


class InMemoryRawStore:
    """Test-friendly storage implementation with the same core API as MinIORawStore."""

    def __init__(self) -> None:
        self.objects: dict[str, str] = {}

    def ensure_bucket(self) -> None:
        return None

    def write_item(self, item: TextItem) -> str:
        key = MinIORawStore.object_key(item)
        self.objects[key] = item.model_dump_json(mode="json")
        return key

    def read_item(self, key: str) -> TextItem:
        return TextItem.model_validate_json(self.objects[key])

    def iter_items(self, prefix: str = "") -> Iterator[TextItem]:
        for key, value in self.objects.items():
            if key.startswith(prefix):
                yield TextItem.model_validate_json(value)

    def write_items_jsonl(self, items: Iterable[TextItem], prefix: str) -> str:
        key = f"{prefix.rstrip('/')}/batch.jsonl"
        self.objects[key] = "\n".join(
            item.model_dump_json(mode="json") for item in items
        )
        return key
