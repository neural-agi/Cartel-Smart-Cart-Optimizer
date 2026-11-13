from __future__ import annotations

import httpx
import pytest

from app.product_intelligence.canonical_source.providers import (
    CanonicalSourceUnavailable,
    OpenFoodFactsProvider,
)


def _transport(payload: object, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload, request=request)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_open_food_facts_provider_fetches_and_normalizes_source_record():
    async with httpx.AsyncClient(transport=_transport({"status": 1, "product": {"code": "8901000000000", "product_name": "Milk", "brands": "Brand", "quantity": "500 ml", "last_modified_t": 4}}) , base_url="https://example.test") as client:
        provider = OpenFoodFactsProvider(client, base_url="https://example.test")
        artifact = await provider.fetch("8901000000000")
    candidate = provider.normalize(artifact)
    assert artifact.source == "open_food_facts"
    assert artifact.content_digest
    assert candidate.source_record_id == "8901000000000"


@pytest.mark.asyncio
async def test_provider_rejects_unavailable_or_malformed_source_records():
    async with httpx.AsyncClient(transport=_transport({"status": 0}), base_url="https://example.test") as client:
        with pytest.raises(CanonicalSourceUnavailable):
            await OpenFoodFactsProvider(client, base_url="https://example.test").fetch("8901000000000")

    async with httpx.AsyncClient(transport=_transport({"status": 1, "product": {"code": "8901000000000", "product_name": "Milk", "brands": "Brand", "quantity": "unknown"}}), base_url="https://example.test") as client:
        provider = OpenFoodFactsProvider(client, base_url="https://example.test")
        artifact = await provider.fetch("8901000000000")
        with pytest.raises(ValueError, match="quantity"):
            provider.normalize(artifact)
