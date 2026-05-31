import asyncio
from collections.abc import Mapping
from urllib.parse import urlencode

from app.scrapers.base.exceptions import ScraperRequestError
from app.scrapers.base.scraper import BaseScraper
from app.scrapers.base.types import RawHttpResponse
from app.scrapers.blinkit.session import BlinkitBrowserSession


class BlinkitScraper(BaseScraper):
    """Blinkit scraper scaffold for raw search-response collection."""

    platform = "blinkit"
    base_url = "https://blinkit.com"
    search_path = "/s/"
    browser_ready_selector = "body"

    def __init__(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        blinkit_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "referer": self.base_url,
        }
        if headers:
            blinkit_headers.update(headers)
        super().__init__(
            headers=blinkit_headers,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    async def search_products(self, query: str) -> bytes:
        try:
            response = await self.fetch_raw(
                method="GET",
                url=f"{self.base_url}{self.search_path}",
                params={"q": query},
            )
        except ScraperRequestError:
            self.logger.warning(
                "blinkit_http_blocked query=%s falling_back=playwright",
                query,
            )
            response = await self._fetch_via_browser(query)
        self.save_raw_response(query=query, response=response, extension="html")
        return response.body

    async def _fetch_via_browser(self, query: str) -> RawHttpResponse:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright

        search_url = f"{self.base_url}{self.search_path}?{urlencode({'q': query})}"
        browser = None
        context = None
        page = None
        response_status = 0
        response_headers: dict[str, str] = {}
        session = BlinkitBrowserSession(
            headers=self.default_headers,
            timeout_seconds=self.timeout_seconds,
        )

        try:
            self.logger.info("blinkit_browser_start query=%s", query)
            async with async_playwright() as playwright:
                self.logger.info("blinkit_browser_launch_start query=%s", query)
                browser = await playwright.chromium.launch(
                    headless=True,
                    timeout=int(self.timeout_seconds * 1000),
                )
                self.logger.info("blinkit_browser_launch_complete query=%s", query)

                context = await session.new_context(browser)
                page = await context.new_page()

                self.logger.info(
                    "blinkit_browser_navigation_start query=%s url=%s",
                    query,
                    search_url,
                )
                response = await page.goto(
                    search_url,
                    wait_until="commit",
                    timeout=int(self.timeout_seconds * 1000),
                )
                if response is not None:
                    response_status = response.status
                    response_headers = dict(response.headers)
                self.logger.info(
                    "blinkit_browser_navigation_complete query=%s status_code=%s",
                    query,
                    response_status,
                )

                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    self.logger.info(
                        "blinkit_browser_domcontentloaded query=%s",
                        query,
                    )
                except PlaywrightTimeoutError:
                    self.logger.warning(
                        "blinkit_browser_domcontentloaded_timeout query=%s",
                        query,
                    )

                try:
                    await page.wait_for_selector(
                        self.browser_ready_selector,
                        state="attached",
                        timeout=5000,
                    )
                    self.logger.info("blinkit_browser_body_ready query=%s", query)
                except PlaywrightTimeoutError:
                    self.logger.warning("blinkit_browser_body_timeout query=%s", query)

                await session.ensure_delivery_location(page=page, query=query)
                content = await page.content()
                if not content.strip():
                    raise ScraperRequestError(
                        f"Blinkit browser returned empty HTML for query={query!r}"
                    )
                await session.persist_state(context)

        except (PlaywrightError, ScraperRequestError) as exc:
            self.logger.exception(
                "blinkit_browser_failed query=%s error=%s",
                query,
                exc.__class__.__name__,
            )
            if page is not None:
                await session.capture_failure_artifacts(
                    page=page,
                    query=query,
                    reason="browser",
                )
            raise
        finally:
            if context is not None:
                self.logger.info("blinkit_context_close_start query=%s", query)
                try:
                    await asyncio.wait_for(context.close(), timeout=10)
                    self.logger.info("blinkit_context_close_complete query=%s", query)
                except (TimeoutError, PlaywrightError) as exc:
                    if exc.__class__.__name__ == "TargetClosedError":
                        self.logger.info("blinkit_context_already_closed query=%s", query)
                    else:
                        self.logger.warning(
                            "blinkit_context_close_failed query=%s error=%s",
                            query,
                            exc.__class__.__name__,
                        )
            if browser is not None:
                self.logger.info("blinkit_browser_close_start query=%s", query)
                try:
                    await asyncio.wait_for(browser.close(), timeout=10)
                    self.logger.info("blinkit_browser_close_complete query=%s", query)
                except (TimeoutError, PlaywrightError) as exc:
                    self.logger.warning(
                        "blinkit_browser_close_failed query=%s error=%s",
                        query,
                        exc.__class__.__name__,
                    )

        return RawHttpResponse(
            url=search_url,
            status_code=response_status or 200,
            headers=response_headers,
            body=content.encode("utf-8"),
            content_type="text/html",
        )
