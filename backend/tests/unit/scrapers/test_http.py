from __future__ import annotations

import httpx
import pytest

from app.scrapers.base.exceptions import ScraperRequestError
from app.scrapers.utils.http import AsyncHttpClient


class _FakeAsyncClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.calls = 0

    async def request(self, **kwargs):
        self.calls += 1
        return self.response


@pytest.mark.asyncio
async def test_http_403_is_not_retried() -> None:
    client = AsyncHttpClient(max_retries=3, retry_backoff_seconds=0)
    fake = _FakeAsyncClient(
        httpx.Response(403, request=httpx.Request("GET", "https://blinkit.com/s/"))
    )
    client._client = fake  # type: ignore[assignment]

    with pytest.raises(ScraperRequestError) as error:
        await client.request(method="GET", url="https://blinkit.com/s/")

    assert fake.calls == 1
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_transient_http_failure_uses_retry_budget() -> None:
    client = AsyncHttpClient(max_retries=2, retry_backoff_seconds=0)
    fake = _FakeAsyncClient(
        httpx.Response(503, request=httpx.Request("GET", "https://blinkit.com/s/"))
    )
    client._client = fake  # type: ignore[assignment]

    with pytest.raises(ScraperRequestError) as error:
        await client.request(method="GET", url="https://blinkit.com/s/")

    assert fake.calls == 2
    assert error.value.status_code == 503
