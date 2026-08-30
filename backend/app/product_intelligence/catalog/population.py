"""Operator-governed catalog review and import boundaries."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.types import CatalogConflictError, CatalogValidationError
from app.product_intelligence.models import Product, ProductVariant


class CatalogReviewItem(BaseModel):
    """Non-authoritative observation facts presented for operator review."""

    model_config = ConfigDict(frozen=True)

    observation_id: str
    platform: str
    platform_listing_id: str
    normalized_name: str | None = None
    normalized_category: str | None = None
    normalized_quantity: str | None = None
    displayed_price: dict[str, object] | None = None
    availability_signal: str | None = None
    source_reference: str | None = None
    resolution_state: str = "unresolved"


class CatalogReviewQueue(BaseModel):
    model_config = ConfigDict(frozen=True)

    observations: tuple[CatalogReviewItem, ...] = Field(default_factory=tuple)


class CatalogPopulationManifest(BaseModel):
    """Explicit operator-supplied canonical entities and associations."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    products: tuple[Product, ...] = Field(default_factory=tuple)
    variants: tuple[ProductVariant, ...] = Field(default_factory=tuple)
    associations: tuple[CanonicalListingAssociation, ...] = Field(default_factory=tuple)


class GovernedCatalogPopulationService:
    """Populate catalog state only from explicit, already-authoritative input."""

    def __init__(
        self,
        *,
        catalog: FilesystemAuthoritativeCatalog,
        association_registry: FilesystemCanonicalListingAssociationRegistry,
        observation_registry: ObservationRegistry,
    ) -> None:
        self.catalog = catalog
        self.association_registry = association_registry
        self.observation_registry = observation_registry

    def build_review_queue(self) -> CatalogReviewQueue:
        items = [self._review_item(observation) for observation in self.observation_registry.list_all()]
        return CatalogReviewQueue(observations=tuple(sorted(items, key=lambda item: item.observation_id)))

    def import_manifest(self, manifest: CatalogPopulationManifest) -> CatalogPopulationManifest:
        self._validate_manifest(manifest)
        for product in sorted(manifest.products, key=lambda item: item.canonical_product_id):
            self.catalog.register_product(product)
        for variant in sorted(manifest.variants, key=lambda item: item.canonical_variant_id):
            self.catalog.register_variant(variant)
        for association in sorted(
            manifest.associations,
            key=lambda item: (item.platform, item.platform_listing_id, item.observation_id),
        ):
            self.association_registry.register(association)
        return manifest

    @staticmethod
    def load_manifest(path: Path) -> CatalogPopulationManifest:
        return CatalogPopulationManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def save_review_queue(queue: CatalogReviewQueue, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(queue.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _validate_manifest(self, manifest: CatalogPopulationManifest) -> None:
        product_ids = [item.canonical_product_id for item in manifest.products]
        variant_ids = [item.canonical_variant_id for item in manifest.variants]
        if len(product_ids) != len(set(product_ids)):
            raise CatalogConflictError("manifest contains duplicate canonical_product_id values")
        if len(variant_ids) != len(set(variant_ids)):
            raise CatalogConflictError("manifest contains duplicate canonical_variant_id values")

        existing = self.catalog.load_state()
        product_map = {item.canonical_product_id: item for item in existing.products}
        product_map.update({item.canonical_product_id: item for item in manifest.products})
        variant_map = {item.canonical_variant_id: item for item in existing.variants}
        variant_map.update({item.canonical_variant_id: item for item in manifest.variants})
        for product in manifest.products:
            self.catalog._validate_product(product)
        for variant in manifest.variants:
            self.catalog._validate_variant(variant)
            if variant.canonical_product_id not in product_map:
                raise CatalogValidationError(
                    f"manifest variant parent Product missing: {variant.canonical_product_id}"
                )
        seen_observations: set[str] = set()
        for association in manifest.associations:
            if association.observation_id in seen_observations:
                raise CatalogConflictError("manifest contains duplicate observation associations")
            seen_observations.add(association.observation_id)
            observation = self.observation_registry.get(association.observation_id)
            if observation is None:
                raise CatalogValidationError(
                    f"association observation not found: {association.observation_id}"
                )
            if observation.platform.value != association.platform:
                raise CatalogValidationError("association platform does not match observation")
            if observation.source_record_id != association.platform_listing_id:
                raise CatalogValidationError("association listing ID does not match observation")
            if association.canonical_product_id not in product_map:
                raise CatalogValidationError("association Product is not in the manifest or catalog")
            variant = variant_map.get(association.canonical_variant_id)
            if variant is None:
                raise CatalogValidationError("association Variant is not in the manifest or catalog")
            if variant.canonical_product_id != association.canonical_product_id:
                raise CatalogValidationError("association Variant belongs to another Product")

    @staticmethod
    def _review_item(observation: NormalizedObservation) -> CatalogReviewItem:
        artifact = observation.raw_artifact_reference
        return CatalogReviewItem(
            observation_id=observation.observation_id,
            platform=observation.platform.value,
            platform_listing_id=observation.source_record_id,
            normalized_name=observation.normalized_name,
            normalized_category=observation.normalized_category,
            normalized_quantity=observation.normalized_quantity,
            displayed_price=(
                observation.observed_selling_price.model_dump(mode="json")
                if observation.observed_selling_price is not None
                else None
            ),
            availability_signal=observation.availability_signal,
            source_reference=artifact.source_reference if artifact is not None else None,
        )
