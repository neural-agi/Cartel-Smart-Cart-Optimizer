"""Run one bounded operator query against an explicitly configured provider.

This command intentionally has no generic HTTP fallback. Until a concrete,
authorized provider adapter is installed, it reports unavailable and performs
no network request. Provider adapters must return the typed retailer-data
contract before they can be registered here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.core.config import Settings
from app.data_ingestion import CaptureContext, CaptureType, DownstreamMode, Platform, RequestParameters, ScrapeJob
from app.retailer_data.contracts import RetailerAcquisitionOutcome
from app.retailer_data.providers import (
    QuickCommerceRetailerDataProvider,
    RetailerAcquisitionRequest,
    UnavailableRetailerDataProvider,
    location_from_job,
)


def _job(location: str, query: str) -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", query),)),
        capture_context=CaptureContext(
            country_code="IN", currency_code="INR", locale="en-IN",
            location_scope=location, session_scope="operator-provider-query",
        ),
        parser_policy_version="blinkit-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="scrape-job-v1",
    )


async def _run(provider_name: str, platform: str, location: str, query: str, latitude: float, longitude: float) -> dict[str, object]:
    if platform != "BlinkIt":
        raise ValueError("this integration supports only platform=BlinkIt")
    settings = Settings()
    provider = QuickCommerceRetailerDataProvider(settings) if provider_name == "quickcommerce" else UnavailableRetailerDataProvider()
    job = _job(location, query)
    request = RetailerAcquisitionRequest(
        retailer=Platform.BLINKIT,
        provider_id=provider_name,
        method=provider.method,
        location=location_from_job(job).model_copy(update={"latitude": latitude, "longitude": longitude}),
        job=job,
    )
    result = await provider.acquire(request)
    return {
        "provider": provider_name,
        "configured_mode": settings.retailer_data_provider_mode,
        "outcome": result.outcome.value,
        "reason_code": result.reason_code,
        "location_scope": result.location.scope_id,
        "query": query,
        "request_state": result.request_state.value,
        "evidence": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Query one explicitly configured retailer-data provider")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--platform", choices=("BlinkIt",), default="BlinkIt")
    parser.add_argument("--location", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    args = parser.parse_args()
    if not args.location.strip() or not args.query.strip():
        parser.error("location and query must be non-empty")
    result = asyncio.run(_run(args.provider, args.platform, args.location, args.query, args.lat, args.lon))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["outcome"] is RetailerAcquisitionOutcome.SUCCESS.value else 2


if __name__ == "__main__":
    sys.exit(main())
