"""Explicit operator review boundary for unresolved retailer observations."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.catalog.association_storage import FilesystemCanonicalListingAssociationRegistry
from app.product_intelligence.catalog.resolution import (
    CanonicalListingAssociation,
    DeterministicCanonicalListingResolver,
    ListingResolutionStatus,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.types import CatalogValidationError
from app.product_intelligence.models import Product, ProductVariant


class OperatorObservationDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str
    platform: str
    retailer_product_id: str | None
    retailer_product_url: str | None
    title: str | None
    brand: str | None
    quantity_text: str | None
    price: dict[str, object] | None
    availability: str | None
    provenance: dict[str, object]


class OperatorReviewAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str
    operator_id: str
    decision: str
    timestamp: datetime
    canonical_product_id: str | None = None
    canonical_variant_id: str | None = None
    resolver_status: str
    rationale: tuple[str, ...] = ()
    association: CanonicalListingAssociation | None = None


class OperatorReviewService:
    """Review existing observations without changing their historical facts."""

    def __init__(self, *, observation_registry, catalog: FilesystemAuthoritativeCatalog,
                 resolver: DeterministicCanonicalListingResolver,
                 association_registry: FilesystemCanonicalListingAssociationRegistry,
                 audit_path: Path | None = None) -> None:
        self.observation_registry = observation_registry
        self.catalog = catalog
        self.resolver = resolver
        self.association_registry = association_registry
        self.audit_path = audit_path

    def inspect(self, observation_id: str) -> OperatorObservationDetail:
        observation: NormalizedObservation | None = self.observation_registry.get(observation_id)
        if observation is None:
            raise ValueError("observation was not found")
        identifiers = dict(observation.platform_identifiers)
        artifact = observation.raw_artifact_reference
        return OperatorObservationDetail(
            observation_id=observation.observation_id,
            platform=observation.platform.value,
            retailer_product_id=identifiers.get("retailer_product_id"),
            retailer_product_url=identifiers.get("retailer_product_url"),
            title=observation.normalized_name,
            brand=identifiers.get("brand"),
            quantity_text=observation.normalized_quantity,
            price=observation.observed_selling_price.model_dump(mode="json") if observation.observed_selling_price else None,
            availability=observation.availability_signal,
            provenance={
                "source_reference": artifact.source_reference if artifact else None,
                "artifact_id": artifact.artifact_id if artifact else None,
                "content_digest": artifact.content_digest if artifact else None,
                "capture_timestamp": artifact.capture_timestamp.isoformat() if artifact else None,
                "provider_id": getattr(artifact, "provider_id", None) if artifact else None,
                "location_scope": getattr(artifact, "location_scope", None) if artifact else None,
                "provider_request_id": getattr(artifact, "provider_request_id", None) if artifact else None,
            },
        )

    def commit_existing(self, *, observation_id: str, product: Product, variant: ProductVariant,
                        operator_id: str, notes: str | None = None) -> OperatorReviewAudit:
        observation = self.observation_registry.get(observation_id)
        if observation is None:
            raise ValueError("observation was not found")
        if hasattr(self.catalog, "get_product") and hasattr(self.catalog, "get_variant"):
            persisted_product = self.catalog.get_product(product.canonical_product_id)
            persisted_variant = self.catalog.get_variant(variant.canonical_variant_id)
            if persisted_product != product or persisted_variant != variant:
                raise CatalogValidationError(
                    "operator review requires the selected Product and Variant to be persisted catalog records"
                )
        evidence = self.resolver._retailer_identity_adapters[observation.platform.value].adapt(observation)
        comparison = self.resolver.compare_identity(evidence, product, variant)
        if comparison.state != "EXACT_MATCH":
            audit = OperatorReviewAudit(
                observation_id=observation_id, operator_id=operator_id, decision="rejected",
                timestamp=datetime.now(timezone.utc), canonical_product_id=product.canonical_product_id,
                canonical_variant_id=variant.canonical_variant_id, resolver_status=comparison.state,
                rationale=(comparison.reason,),
            )
            self._audit(audit)
            return audit
        association = CanonicalListingAssociation(
            observation_id=observation_id, platform=observation.platform.value,
            platform_listing_id=observation.source_record_id,
            canonical_product_id=product.canonical_product_id,
            canonical_variant_id=variant.canonical_variant_id,
        )
        persisted = self.association_registry.register(association)
        audit = OperatorReviewAudit(
            observation_id=observation_id, operator_id=operator_id, decision="associated",
            timestamp=datetime.now(timezone.utc), canonical_product_id=product.canonical_product_id,
            canonical_variant_id=variant.canonical_variant_id, resolver_status=ListingResolutionStatus.mapped.value,
            rationale=(comparison.reason,), association=persisted,
        )
        self._audit(audit)
        return audit

    def _audit(self, audit: OperatorReviewAudit) -> None:
        if self.audit_path is None:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        records = []
        if self.audit_path.exists():
            records = json.loads(self.audit_path.read_text(encoding="utf-8"))
        records.append(audit.model_dump(mode="json"))
        temporary = self.audit_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(records, sort_keys=True, indent=2), encoding="utf-8")
        os.replace(temporary, self.audit_path)
