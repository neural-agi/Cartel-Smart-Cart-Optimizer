"""Compare Blinkit's existing Playwright runtime with an explicit Chrome path."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import get_settings
from app.scrapers.blinkit.scraper import BlinkitScraper


async def check(scraper: BlinkitScraper, query: str, *, executable: str | None, headless: bool) -> dict[str, object]:
    try:
        response = await scraper._fetch_via_browser(
            query,
            executable_path=executable,
            headless=headless,
        )
        return {
            "status": "succeeded",
            "executable": executable or "playwright-managed",
            "headless": headless,
            "response_status": response.status_code,
            "final_url": response.url,
            "content_type": response.content_type,
            "payload_bytes": len(response.body),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "executable": executable or "playwright-managed",
            "headless": headless,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }


async def main(query: str, chrome_path: str | None, headed: bool) -> None:
    settings = get_settings()
    scraper = BlinkitScraper(settings=settings)
    results = [await check(scraper, query, executable=None, headless=not headed)]
    if chrome_path:
        results.append(await check(scraper, query, executable=chrome_path, headless=not headed))
    print(json.dumps({"query": query, "location": settings.blinkit_delivery_location_name, "results": results}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose Blinkit browser runtime selection")
    parser.add_argument("query", nargs="?", default="milk")
    parser.add_argument("--chrome-path", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.query, str(args.chrome_path) if args.chrome_path else None, args.headed))
