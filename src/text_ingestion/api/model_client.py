from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from text_ingestion.models import ModelRequest, ModelResponse, TextItem

logger = structlog.get_logger(__name__)


class ModelAPIClient:
    """Generic async client for model inference endpoints accepting text payloads."""

    def __init__(
        self,
        endpoint_url: str,
        auth_token: str | None = None,
        auth_header: str = "Authorization",
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        self.auth_header = auth_header
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._external_client = client

    async def send_item(self, item: TextItem) -> ModelResponse:
        request = ModelRequest.from_item(item)
        return await self.send_request(request)

    async def send_request(self, request: ModelRequest) -> ModelResponse:
        if self._external_client:
            return await self._send_with_retries(self._external_client, request)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await self._send_with_retries(client, request)

    async def _send_with_retries(
        self, client: httpx.AsyncClient, request: ModelRequest
    ) -> ModelResponse:
        retrying_send = retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError)
            ),
        )(self._send_once)
        return await retrying_send(client, request)

    async def _send_once(
        self, client: httpx.AsyncClient, request: ModelRequest
    ) -> ModelResponse:
        headers = self._headers(request.correlation_id)
        payload = request.model_dump(mode="json")
        started = time.perf_counter()
        logger.info(
            "model_request_started",
            correlation_id=request.correlation_id,
            source_name=request.source_name,
            source_item_id=request.source_item_id,
        )
        response = await client.post(self.endpoint_url, json=payload, headers=headers)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        body: dict[str, Any] | list[Any] | str | None
        try:
            body = response.json()
        except ValueError:
            body = response.text
        logger.info(
            "model_request_completed",
            correlation_id=request.correlation_id,
            status_code=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
        )
        return ModelResponse(
            correlation_id=request.correlation_id,
            status_code=response.status_code,
            body=body,
            elapsed_ms=elapsed_ms,
        )

    def _headers(self, correlation_id: str) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Correlation-ID": correlation_id,
        }
        if self.auth_token:
            headers[self.auth_header] = f"Bearer {self.auth_token}"
        return headers
