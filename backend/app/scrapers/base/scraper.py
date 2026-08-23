from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.scrapers.base.types import RawHttpResponse
from app.scrapers.utils.http import AsyncHttpClient
from app.scrapers.utils.storage import persist_raw_response


class BaseScraper(ABC):
    """Reusable foundation for platform scrapers."""

    platform: str

    def __init__(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.logger = get_logger(f"{__name__}.{self.platform}")
        self.default_headers = self.build_headers(headers)
        self.timeout_seconds = self.settings.scraper_timeout_seconds if timeout_seconds is None else timeout_seconds
        self.max_retries = self.settings.scraper_max_retries if max_retries is None else max_retries
        self.retry_backoff_seconds = self.settings.scraper_retry_backoff_seconds

    def build_headers(
        self,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        base_headers = {
            "user-agent": self.settings.scraper_user_agent,
            "accept": "*/*",
            "accept-language": "en-IN,en;q=0.9",
        }
        if headers:
            base_headers.update(headers)
        return base_headers

    async def fetch_raw(
        self,
        *,
        method: str,
        url: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> RawHttpResponse:
        async with AsyncHttpClient(
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            retry_backoff_seconds=self.retry_backoff_seconds,
            default_headers=self.default_headers,
            settings=self.settings,
        ) as client:
            return await client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
            )

    def save_raw_response(
        self,
        *,
        query: str,
        response: RawHttpResponse,
        extension: str,
    ) -> Path:
        return persist_raw_response(
            platform=self.platform,
            query=query,
            response=response,
            extension=extension,
        )

    @abstractmethod
    async def search_products(self, query: str) -> bytes:
        """Fetch raw unmodified product search data for a query."""
