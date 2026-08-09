"""Blinkit acquisition adapter for the immutable ingestion boundary."""

from __future__ import annotations

from datetime import datetime, timezone

from app.data_ingestion import AcquisitionResult, CaptureCoverage, CaptureType
from app.scrapers.base.types import RawHttpResponse
from app.scrapers.blinkit.scraper import BlinkitScraper


class BlinkitAcquisitionAdapter:
    """Adapt concrete Blinkit response facts without storing or parsing them."""

    def __init__(self, scraper: BlinkitScraper | None = None) -> None:
        self._scraper = scraper or BlinkitScraper()

    async def acquire_search(self, *, query: str, evaluation_scope: str) -> AcquisitionResult:
        response = await self._scraper.acquire_search(query)
        return self._to_result(response, evaluation_scope=evaluation_scope)

    @staticmethod
    def _to_result(response: RawHttpResponse, *, evaluation_scope: str) -> AcquisitionResult:
        content_type = response.content_type
        if content_type is None:
            content_type = response.headers.get("content-type")
        if content_type is None or not content_type.strip():
            raise ValueError("Blinkit acquisition did not provide content type")

        coverage = CaptureCoverage(
            evaluation_scope=evaluation_scope,
            pages_evaluated=1,
            pagination_complete=None,
            termination_reason="pagination_completion_unknown",
        )
        return AcquisitionResult(
            payload=response.body,
            source_reference=response.url,
            content_type=content_type.split(";", 1)[0].strip(),
            capture_timestamp=datetime.now(timezone.utc),
            evaluation_scope=evaluation_scope,
            pages_evaluated=1,
            pagination_complete=None,
            termination_reason=coverage.termination_reason,
            capture_type=CaptureType.SEARCH_RESULTS,
            warnings=tuple(),
            capture_coverage=coverage,
        )
