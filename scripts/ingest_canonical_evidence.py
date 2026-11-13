"""Operator CLI for source-isolated canonical evidence ingestion.

This command never admits a catalog entity during ingest. Admission requires a
separate explicit approval and canonical Product/ProductVariant payload.
"""

from __future__ import annotations

import argparse
import asyncio

from app.product_intelligence.canonical_source import (
    CanonicalEvidenceIngestionService,
    OpenFoodFactsProvider,
)
from app.product_intelligence.canonical_source.storage import CanonicalEvidenceFilesystemStore
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog


async def _run(source_record_id: str) -> None:
    service = CanonicalEvidenceIngestionService(
        provider=OpenFoodFactsProvider(),
        store=CanonicalEvidenceFilesystemStore(),
        catalog=FilesystemAuthoritativeCatalog(),
    )
    review = await service.ingest(source_record_id)
    print(f"pending candidate={review.candidate.candidate_id} source={review.candidate.source_record_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one canonical evidence source record for operator review")
    parser.add_argument("source_record_id", help="Open Food Facts barcode/source record ID")
    args = parser.parse_args()
    asyncio.run(_run(args.source_record_id))


if __name__ == "__main__":
    main()
