"""Acquire governed Blinkit observations for a fresh MVP deployment.

This uses the production JobExecutionCoordinator and persists only facts that
the existing ingestion and catalog contracts authorize. It never creates
canonical products or approves unresolved listing associations.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from app.core.config import get_settings
from app.data_ingestion import (
    CaptureContext,
    CaptureType,
    DownstreamMode,
    Platform,
    RequestParameters,
    ScrapeJob,
)
from app.workers.bootstrap import build_product_intelligence_runtime


async def acquire(
    queries: tuple[str, ...],
    *,
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> int:
    if location is not None:
        os.environ["BLINKIT_DELIVERY_LOCATION_NAME"] = location
    if latitude is not None:
        os.environ["BLINKIT_DELIVERY_LATITUDE"] = str(latitude)
    if longitude is not None:
        os.environ["BLINKIT_DELIVERY_LONGITUDE"] = str(longitude)
    settings = get_settings()
    coordinator = build_product_intelligence_runtime(settings)
    results = []
    for query in queries:
        job = ScrapeJob(
            platform=Platform.BLINKIT,
            capture_type=CaptureType.SEARCH_RESULTS,
            request_parameters=RequestParameters(values=(("query", query),)),
            capture_context=CaptureContext(
                country_code="IN",
                currency_code="INR",
                locale="en-IN",
                location_scope=settings.blinkit_delivery_location_name,
                session_scope="mvp-operator",
            ),
            parser_policy_version="blinkit-parser-v1",
            normalization_policy_version="normalization-v1",
            downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
            job_contract_version="scrape-job-v1",
        )
        result = await coordinator.execute(job)
        results.append({
            "query": query,
            "job_id": result.job_id,
            "status": result.status,
            "rationale": list(result.rationale),
            "observations": [
                {
                    "observation_id": observation.observation_id,
                    "status": observation.status,
                    "rationale": list(observation.rationale),
                    "association": (
                        observation.association.model_dump(mode="json")
                        if observation.association is not None
                        else None
                    ),
                }
                for observation in result.observations
            ],
        })

    print(json.dumps({"location": settings.blinkit_delivery_location_name, "jobs": results}, indent=2))
    return 0 if all(item["status"] != "ingestion_failed" for item in results) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire current governed Blinkit observations")
    parser.add_argument("query", nargs="+", help="one or more Blinkit search queries")
    parser.add_argument("--location", help="explicit delivery location label/address")
    parser.add_argument("--lat", type=float, help="explicit delivery latitude")
    parser.add_argument("--lon", type=float, help="explicit delivery longitude")
    args = parser.parse_args()
    return asyncio.run(
        acquire(
            tuple(args.query),
            location=args.location,
            latitude=args.lat,
            longitude=args.lon,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
