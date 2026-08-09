from datetime import timezone

import pytest

from app.scrapers.base.types import RawHttpResponse
from app.scrapers.blinkit.acquisition import BlinkitAcquisitionAdapter


class FakeBlinkitScraper:
    async def acquire_search(self, query: str) -> RawHttpResponse:
        return RawHttpResponse(
            url=f"https://blinkit.com/s/?q={query}",
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=b"\x00blinkit-html",
            content_type=None,
        )


class MissingContentTypeScraper:
    async def acquire_search(self, query: str) -> RawHttpResponse:
        return RawHttpResponse(url="https://blinkit.com/s/?q=milk", status_code=200, headers={}, body=b"html", content_type=None)


@pytest.mark.asyncio
async def test_acquisition_result_preserves_real_response_facts() -> None:
    result = await BlinkitAcquisitionAdapter(FakeBlinkitScraper()).acquire_search(query="milk", evaluation_scope="search:milk:blr")
    assert result.payload == b"\x00blinkit-html"
    assert result.source_reference == "https://blinkit.com/s/?q=milk"
    assert result.content_type == "text/html"
    assert result.capture_timestamp.tzinfo is not None
    assert result.capture_timestamp.tzinfo == timezone.utc
    assert result.evaluation_scope == "search:milk:blr"
    assert result.pages_evaluated == 1
    assert result.pagination_complete is None
    assert result.capture_coverage.pagination_complete is None
    assert "\\" not in result.source_reference
    assert ":\\" not in result.source_reference


@pytest.mark.asyncio
async def test_missing_content_type_fails_closed() -> None:
    with pytest.raises(ValueError, match="content type"):
        await BlinkitAcquisitionAdapter(MissingContentTypeScraper()).acquire_search(query="milk", evaluation_scope="search:milk")
