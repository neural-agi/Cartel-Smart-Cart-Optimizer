from datetime import timezone

import pytest

from app.core.config import Settings
from app.scrapers.base.types import RawHttpResponse
from app.scrapers.base.exceptions import ScraperUnavailableError
from app.scrapers.blinkit.acquisition import BlinkitAcquisitionAdapter
from app.scrapers.blinkit.scraper import BlinkitScraper


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


def test_blinkit_scraper_uses_injected_settings_and_preserves_zero_retries(
    tmp_path,
) -> None:
    settings = Settings(
        _env_file=None,
        scraper_user_agent="Cartel-Test-Agent",
        scraper_timeout_seconds=7.0,
        scraper_max_retries=4,
        scraper_retry_backoff_seconds=0.25,
        blinkit_session_state_path=tmp_path / "blinkit-state.json",
    )

    scraper = BlinkitScraper(settings=settings, max_retries=0)

    assert scraper.settings is settings
    assert scraper.default_headers["user-agent"] == "Cartel-Test-Agent"
    assert scraper.timeout_seconds == 7.0
    assert scraper.max_retries == 0


def test_unavailable_error_exposes_stable_reason_code() -> None:
    error = ScraperUnavailableError("blocked", reason_code="browser_fallback_failed")
    assert error.reason_code == "browser_fallback_failed"


def test_request_error_preserves_http_status_for_diagnostics() -> None:
    from app.scrapers.base.exceptions import ScraperRequestError

    error = ScraperRequestError("forbidden", status_code=403)
    assert error.status_code == 403


def test_browser_executable_override_is_optional() -> None:
    settings = Settings(_env_file=None)
    assert settings.blinkit_browser_executable_path is None
    configured = Settings(_env_file=None, blinkit_browser_executable_path="/usr/bin/google-chrome")
    assert str(configured.blinkit_browser_executable_path) == "/usr/bin/google-chrome"
