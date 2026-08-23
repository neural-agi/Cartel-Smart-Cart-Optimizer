"""Validate the configured Blinkit browser session without exposing secrets."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from urllib.parse import urlencode

from app.core.config import get_settings
from app.scrapers.blinkit.session import BlinkitBrowserSession


async def validate(query: str, *, headed: bool = False) -> dict[str, object]:
    settings = get_settings()
    state_path = settings.blinkit_session_state_path
    result: dict[str, object] = {
        "state_exists": state_path.exists(),
        "state_path": str(state_path),
        "location": settings.blinkit_delivery_location_name,
        "query": query,
    }
    if not state_path.exists():
        result.update(status="unavailable", reason="session_state_missing")
        return result
    session = BlinkitBrowserSession(
        headers={"user-agent": settings.scraper_user_agent, "referer": "https://blinkit.com"},
        timeout_seconds=settings.scraper_timeout_seconds,
        settings=settings,
    )
    from playwright.async_api import async_playwright

    browser = None
    context = None
    try:
        async with async_playwright() as playwright:
            launch_kwargs: dict[str, object] = {
                "headless": not headed,
                "timeout": int(settings.scraper_timeout_seconds * 1000),
            }
            if settings.blinkit_browser_executable_path is not None:
                launch_kwargs["executable_path"] = str(settings.blinkit_browser_executable_path)
            browser = await playwright.chromium.launch(**launch_kwargs)
            result["browser_launched"] = True
            context = await session.new_context(browser)
            result["context_loaded"] = True
            page = await context.new_page()
            response = await page.goto(
                "https://blinkit.com/s/?" + urlencode({"q": query}),
                wait_until="domcontentloaded",
                timeout=int(settings.scraper_timeout_seconds * 1000),
            )
            result["navigation_status"] = response.status if response is not None else None
            result["final_url"] = page.url
            result["product_cards_visible"] = await session.wait_for_product_results(
                page=page,
                query=query,
            )
            result["location_metadata"] = await session.safe_location_metadata(page=page)
            result["status"] = "usable" if result["product_cards_visible"] else "unavailable"
            if result["status"] == "unavailable":
                result["reason"] = "location_or_product_results_unavailable"
    except Exception as exc:
        result.update(status="unavailable", error_type=exc.__class__.__name__, reason="browser_or_navigation_failed")
    finally:
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the configured Blinkit session")
    parser.add_argument("--query", default="milk")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(validate(args.query, headed=args.headed))
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "usable" else 2


if __name__ == "__main__":
    sys.exit(main())
