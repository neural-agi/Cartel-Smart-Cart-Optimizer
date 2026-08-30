"""Export acquired observations for manual canonical catalog review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.data_ingestion.observation_registry import FilesystemObservationRegistry
from app.product_intelligence.catalog import (
    FilesystemAuthoritativeCatalog,
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
    GovernedCatalogPopulationService,
)
from app.product_intelligence.catalog.storage import CatalogFilesystemStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Export observations requiring catalog approval")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = get_settings()
    root = settings.data_dir / "product_intelligence" / "catalog"
    service = GovernedCatalogPopulationService(
        catalog=FilesystemAuthoritativeCatalog(store=CatalogFilesystemStore(root_dir=root)),
        association_registry=FilesystemCanonicalListingAssociationRegistry(
            store=FilesystemCanonicalListingAssociationStore(root_dir=root)
        ),
        observation_registry=FilesystemObservationRegistry(
            root_dir=settings.data_dir / "product_intelligence" / "observations"
        ),
    )
    queue = service.build_review_queue()
    service.save_review_queue(queue, args.output)
    print(json.dumps({"status": "exported", "observations": len(queue.observations), "path": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
