from __future__ import annotations

from datetime import datetime, timezone

from app.product_intelligence.catalog.association_storage import FilesystemCanonicalListingAssociationRegistry
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.types import CatalogValidationError
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.retailer_data.types import AssociationStatus, RetailerObservation


class GovernedRetailerAssociationService:
    """Associate a listing only with an existing governed canonical variant."""

    def __init__(self, *, catalog: FilesystemAuthoritativeCatalog, registry: FilesystemCanonicalListingAssociationRegistry) -> None:
        self.catalog = catalog
        self.registry = registry

    def associate(self, observation: RetailerObservation, *, canonical_variant_id: str, method: str = "operator_supplied") -> CanonicalListingAssociation:
        variant = self.catalog.get_variant(canonical_variant_id)
        if variant is None:
            raise CatalogValidationError("canonical ProductVariant does not exist")
        if variant.canonical_product_id not in {item.canonical_product_id for item in self.catalog.load_state().products}:
            raise CatalogValidationError("canonical Product parent does not exist")
        association = CanonicalListingAssociation(
            observation_id=observation.observation_id,
            platform=observation.provider,
            platform_listing_id=observation.retailer_listing_id,
            canonical_product_id=variant.canonical_product_id,
            canonical_variant_id=variant.canonical_variant_id,
            association_status=AssociationStatus.associated.value,
            association_method=method,
            association_timestamp=datetime.now(timezone.utc),
        )
        return self.registry.register(association)

    def mark_needs_review(self, observation: RetailerObservation, *, reason: str) -> CanonicalListingAssociation:
        return CanonicalListingAssociation(
            observation_id=observation.observation_id,
            platform=observation.provider,
            platform_listing_id=observation.retailer_listing_id,
            canonical_product_id="",
            canonical_variant_id="",
            association_status=AssociationStatus.needs_review.value,
            association_method=reason,
            association_timestamp=datetime.now(timezone.utc),
        )
