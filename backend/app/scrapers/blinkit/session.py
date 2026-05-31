from pathlib import Path

from playwright.async_api import Browser, BrowserContext
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.scrapers.base.exceptions import ScraperRequestError
from app.scrapers.utils.storage import persist_debug_artifact


class BlinkitBrowserSession:
    """Creates and maintains a reusable Blinkit delivery-location browser session."""

    def __init__(self, *, headers: dict[str, str], timeout_seconds: float) -> None:
        self.settings: Settings = get_settings()
        self.headers = headers
        self.timeout_ms = int(timeout_seconds * 1000)
        self.logger = get_logger(__name__)

    @property
    def state_path(self) -> Path:
        return self.settings.blinkit_session_state_path

    async def new_context(self, browser: Browser) -> BrowserContext:
        kwargs = {
            "user_agent": self.headers["user-agent"],
            "extra_http_headers": {
                key: value for key, value in self.headers.items() if key != "user-agent"
            },
            "viewport": {"width": 1366, "height": 768},
            "locale": "en-IN",
            "timezone_id": "Asia/Kolkata",
            "geolocation": {
                "latitude": self.settings.blinkit_delivery_latitude,
                "longitude": self.settings.blinkit_delivery_longitude,
                "accuracy": self.settings.blinkit_geolocation_accuracy,
            },
            "permissions": ["geolocation"],
        }
        if self.state_path.exists():
            kwargs["storage_state"] = str(self.state_path)
            self.logger.info("blinkit_session_state_loaded path=%s", str(self.state_path))

        context = await browser.new_context(**kwargs)
        context.set_default_timeout(self.timeout_ms)
        context.set_default_navigation_timeout(self.timeout_ms)
        return context

    async def ensure_delivery_location(self, *, page: Page, query: str) -> None:
        self.logger.info(
            "blinkit_location_session_start query=%s location=%s lat=%s lon=%s",
            query,
            self.settings.blinkit_delivery_location_name,
            self.settings.blinkit_delivery_latitude,
            self.settings.blinkit_delivery_longitude,
        )

        if await self._has_product_results(page):
            self.logger.info("blinkit_location_products_already_visible query=%s", query)
            return

        if await self._click_detect_location(page, query):
            if await self._wait_for_product_results(page, query):
                return

        if await self._search_location_input(page, query):
            if await self._wait_for_product_results(page, query):
                return

        await self.capture_failure_artifacts(page=page, query=query, reason="location")
        self.logger.warning("blinkit_location_unresolved query=%s", query)
        raise ScraperRequestError(
            f"Blinkit delivery location could not be established for query={query!r}"
        )

    async def persist_state(self, context: BrowserContext) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(self.state_path))
        self.logger.info("blinkit_session_state_persisted path=%s", str(self.state_path))

    async def capture_failure_artifacts(
        self,
        *,
        page: Page,
        query: str,
        reason: str,
    ) -> None:
        try:
            partial_html = await page.content()
            if partial_html.strip():
                persist_debug_artifact(
                    platform="blinkit",
                    query=query,
                    suffix=f"{reason}.partial.html",
                    content=partial_html.encode("utf-8"),
                )
        except PlaywrightError:
            self.logger.warning(
                "blinkit_debug_partial_html_failed query=%s reason=%s",
                query,
                reason,
            )

        try:
            screenshot = await page.screenshot(full_page=True)
            persist_debug_artifact(
                platform="blinkit",
                query=query,
                suffix=f"{reason}.failure.png",
                content=screenshot,
            )
        except PlaywrightError:
            self.logger.warning(
                "blinkit_debug_screenshot_failed query=%s reason=%s",
                query,
                reason,
            )

    async def _click_detect_location(self, page: Page, query: str) -> bool:
        button = page.get_by_role("button", name="Detect my location")
        try:
            if await button.count() == 0:
                self.logger.info("blinkit_detect_location_button_absent query=%s", query)
                return False
            self.logger.info("blinkit_detect_location_click_start query=%s", query)
            await button.first.click(timeout=5000)
            self.logger.info("blinkit_detect_location_click_complete query=%s", query)
            return True
        except PlaywrightError as exc:
            self.logger.warning(
                "blinkit_detect_location_click_failed query=%s error=%s",
                query,
                exc.__class__.__name__,
            )
            return False

    async def _search_location_input(self, page: Page, query: str) -> bool:
        location = self.settings.blinkit_delivery_location_name
        input_locator = page.get_by_placeholder("search delivery location")
        try:
            if await input_locator.count() == 0:
                self.logger.info("blinkit_location_input_absent query=%s", query)
                return False

            self.logger.info(
                "blinkit_location_input_fill_start query=%s location=%s",
                query,
                location,
            )
            await input_locator.first.fill(location, timeout=5000)
            await page.wait_for_timeout(2000)

            suggestion = page.get_by_text(location, exact=False).first
            await suggestion.click(timeout=5000)
            self.logger.info("blinkit_location_suggestion_selected query=%s", query)
            return True
        except PlaywrightError as exc:
            self.logger.warning(
                "blinkit_location_input_failed query=%s error=%s",
                query,
                exc.__class__.__name__,
            )
            return False

    async def _wait_for_product_results(self, page: Page, query: str) -> bool:
        try:
            await page.wait_for_function(self._product_results_predicate(), timeout=10000)
            self.logger.info("blinkit_product_results_ready query=%s", query)
            return True
        except PlaywrightTimeoutError:
            self.logger.warning("blinkit_product_results_timeout query=%s", query)
            return False

    async def _has_product_results(self, page: Page) -> bool:
        try:
            return await page.evaluate(self._product_results_predicate())
        except PlaywrightError:
            return False

    def _product_results_predicate(self) -> str:
        return """
        () => {
            const text = document.body?.innerText || "";
            const hasAddAction = /\\bADD\\b/i.test(text);
            const hasPrice = /(?:\\u20B9|Rs\\.?|MRP)\\s*\\d/.test(text);
            return hasAddAction && hasPrice;
        }
        """
