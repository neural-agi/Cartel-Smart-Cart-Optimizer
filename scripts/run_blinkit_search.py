import argparse
import asyncio
import os
import sys
import warnings
from pathlib import Path

if sys.platform.startswith("win"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scrapers.blinkit import BlinkitScraper
from app.core.config import get_settings
from app.core.logging import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch raw Blinkit search HTML.")
    parser.add_argument("query", nargs="?", default="milk")
    parser.add_argument("--location", help="Blinkit delivery location label/address.")
    parser.add_argument("--lat", type=float, help="Delivery latitude.")
    parser.add_argument("--lon", type=float, help="Delivery longitude.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.location:
        os.environ["BLINKIT_DELIVERY_LOCATION_NAME"] = args.location
    if args.lat is not None:
        os.environ["BLINKIT_DELIVERY_LATITUDE"] = str(args.lat)
    if args.lon is not None:
        os.environ["BLINKIT_DELIVERY_LONGITUDE"] = str(args.lon)

    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_logs=settings.log_json)
    scraper = BlinkitScraper()
    raw_body = await scraper.search_products(args.query)
    print(f"Fetched {len(raw_body)} bytes for query={args.query!r}")


if __name__ == "__main__":
    asyncio.run(main())
