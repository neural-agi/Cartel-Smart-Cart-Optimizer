"""Interactively establish and persist an authorized Blinkit browser session."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from urllib.parse import urlencode

from app.core.config import get_settings
from app.scrapers.blinkit.session import BlinkitBrowserSession


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a Blinkit session through normal headed browser interaction."
    )
    parser.add_argument("--query", default="milk")
    parser.add_argument("--location")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--fresh", action="store_true", help="Do not load the existing state file.")
    return parser.parse_args()


def apply_overrides(args: argparse.Namespace) -> None:
    if args.location:
        os.environ["BLINKIT_DELIVERY_LOCATION_NAME"] = args.location
    if args.lat is not None:
        os.environ["BLINKIT_DELIVERY_LATITUDE"] = str(args.lat)
    if args.lon is not None:
        os.environ["BLINKIT_DELIVERY_LONGITUDE"] = str(args.lon)


async def bootstrap(args: argparse.Namespace) -> dict[str, object]:
    settings = get_settings()
    headers = {
        "user-agent": settings.scraper_user_agent,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "referer": "https://blinkit.com",
    }
    session = BlinkitBrowserSession(
        headers=headers,
        timeout_seconds=settings.scraper_timeout_seconds,
        settings=settings,
    )
    from playwright.async_api import async_playwright

    if args.fresh:
        session.settings.blinkit_session_state_path = session.state_path.with_name(
            f"{session.state_path.stem}.bootstrap-fresh.json"
        )
    browser = None
    context = None
    try:
        async with async_playwright() as playwright:
            launch_kwargs: dict[str, object] = {
                "headless": False,
                "timeout": int(settings.scraper_timeout_seconds * 1000),
            }
            if settings.blinkit_browser_executable_path is not None:
                launch_kwargs["executable_path"] = str(settings.blinkit_browser_executable_path)
            browser = await playwright.chromium.launch(**launch_kwargs)
            context = await session.new_context(browser)
            page = await context.new_page()
            response = await page.goto(
                "https://blinkit.com/s/?" + urlencode({"q": args.query}),
                wait_until="domcontentloaded",
                timeout=int(settings.scraper_timeout_seconds * 1000),
            )
            ready = await session.has_product_results(page=page)
            if not ready:
                print(json.dumps({
                    "status": "operator_action_required",
                    "message": "Select or confirm the delivery location in the open Blinkit window, then press Enter here.",
                    "query": args.query,
                    "location": settings.blinkit_delivery_location_name,
                }, indent=2))
                await asyncio.to_thread(input, "Press Enter after the location and product results are visible: ")
                ready = await session.has_product_results(page=page)
            if not ready:
                raise RuntimeError("Blinkit product cards were not visible after operator interaction")
            metadata = await session.safe_location_metadata(page=page)
            await session.persist_state(context)
            return {
                "status": "usable",
                "query": args.query,
                "state_path": str(session.state_path),
                "location": settings.blinkit_delivery_location_name,
                "location_metadata": metadata,
                "navigation_status": response.status if response is not None else None,
                "session_persisted": session.state_path.exists(),
            }
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


def main() -> int:
    args = parse_args()
    apply_overrides(args)
    try:
        result = asyncio.run(bootstrap(args))
    except Exception as exc:
        print(json.dumps({"status": "unavailable", "error_type": exc.__class__.__name__, "detail": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
