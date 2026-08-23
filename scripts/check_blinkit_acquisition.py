"""Probe Blinkit acquisition availability for operators.

This command performs one real search using configured settings. It does not
write catalog or observation state; successful raw responses are only reported
as metadata so the probe cannot create downstream facts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.core.config import get_settings
from app.scrapers.base.exceptions import ScraperUnavailableError
from app.scrapers.blinkit.acquisition import BlinkitAcquisitionAdapter


async def probe(query: str) -> int:
    settings = get_settings()
    adapter = BlinkitAcquisitionAdapter(settings=settings)
    try:
        result = await adapter.acquire_search(
            query=query,
            evaluation_scope=f"operator-probe:{query.strip().casefold()}",
        )
    except ScraperUnavailableError as exc:
        print(json.dumps({"status": "unavailable", "reason_code": exc.reason_code, "detail": str(exc)}))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": exc.__class__.__name__, "detail": str(exc)}))
        return 2

    print(json.dumps({
        "status": "acquired",
        "source_reference": result.source_reference,
        "status_code": "captured",
        "content_type": result.content_type,
        "payload_bytes": len(result.payload),
        "location": settings.blinkit_delivery_location_name,
        "evaluation_scope": result.evaluation_scope,
    }))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check configured Blinkit acquisition availability")
    parser.add_argument("query", help="one product search query, for example milk")
    args = parser.parse_args()
    return asyncio.run(probe(args.query))


if __name__ == "__main__":
    sys.exit(main())
