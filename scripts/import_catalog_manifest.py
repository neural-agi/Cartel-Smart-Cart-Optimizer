"""Import explicit operator-approved canonical catalog state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.data_ingestion.observation_registry import FilesystemObservationRegistry
from app.product_intelligence.catalog import (
    CatalogPopulationManifest,
    FilesystemAuthoritativeCatalog,
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
    GovernedCatalogPopulationService,
)
from app.product_intelligence.catalog.storage import CatalogFilesystemStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an explicit approved catalog manifest")
    parser.add_argument("manifest", type=Path)
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
    manifest = CatalogPopulationManifest.model_validate(json.loads(args.manifest.read_text(encoding="utf-8")))
    service.import_manifest(manifest)
    print(json.dumps({"status": "imported", "products": len(manifest.products), "variants": len(manifest.variants), "associations": len(manifest.associations)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
