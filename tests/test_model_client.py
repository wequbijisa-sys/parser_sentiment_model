from __future__ import annotations

import httpx
import pytest

from text_ingestion.api import ModelAPIClient
from text_ingestion.models import TextItem


@pytest.mark.asyncio
async def test_model_api_client_sends_item_with_auth_and_correlation_id() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        seen["correlation"] = request.headers.get("X-Correlation-ID")
        seen["json"] = request.read().decode()
        return httpx.Response(200, json={"prediction": "positive"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelAPIClient(
            endpoint_url="https://model.example/predict",
            auth_token="secret",
            client=http_client,
        )
        response = await client.send_item(
            TextItem(source_name="rss", source_item_id="1", text="hello")
        )

    assert response.status_code == 200
    assert response.body == {"prediction": "positive"}
    assert seen["auth"] == "Bearer secret"
    assert seen["correlation"]
    assert "hello" in str(seen["json"])
