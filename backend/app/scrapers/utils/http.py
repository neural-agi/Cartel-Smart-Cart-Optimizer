import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.scrapers.base.exceptions import ScraperRequestError
from app.scrapers.base.types import RawHttpResponse


logger = get_logger(__name__)


class AsyncHttpClient:
    """Shared async HTTP client with timeout, retries, and structured logging."""

    def __init__(
        self,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_backoff_seconds: float | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.scraper_timeout_seconds
        self.max_retries = max_retries or settings.scraper_max_retries
        self.retry_backoff_seconds = (
            retry_backoff_seconds or settings.scraper_retry_backoff_seconds
        )
        self.default_headers = dict(default_headers or {})
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncHttpClient":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            headers=self.default_headers,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> RawHttpResponse:
        if self._client is None:
            raise RuntimeError("AsyncHttpClient must be used within an async context.")

        request_headers = dict(self.default_headers)
        if headers:
            request_headers.update(headers)

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "scraper_http_request method=%s url=%s attempt=%s",
                    method.upper(),
                    url,
                    attempt,
                )
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=request_headers,
                )
                response.raise_for_status()
                logger.info(
                    "scraper_http_response method=%s url=%s status_code=%s attempt=%s",
                    method.upper(),
                    str(response.url),
                    response.status_code,
                    attempt,
                )
                return RawHttpResponse(
                    url=str(response.url),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=response.content,
                    content_type=response.headers.get("content-type"),
                )
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                last_error = exc
                logger.warning(
                    "scraper_http_retry method=%s url=%s attempt=%s error=%s",
                    method.upper(),
                    url,
                    attempt,
                    exc.__class__.__name__,
                )
                if attempt == self.max_retries:
                    break
                await asyncio.sleep(self.retry_backoff_seconds * attempt)

        raise ScraperRequestError(
            f"Request failed after {self.max_retries} attempts: {method.upper()} {url}"
        ) from last_error
