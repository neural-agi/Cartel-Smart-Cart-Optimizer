"""Projection from adapter evidence into governed Product Intelligence models.

This bridge does not create canonical products and does not change matching
semantics. It only converts one retailer-native observation into the existing
``PlatformListing``, ``ListingObservation``, ``EvidenceBundle``, and pipeline
request structures, refusing to project evidence without a raw artifact
reference or a coherent location scope.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.product_intelligence.evidence.types import EvidenceBundle
from app.product_intelligence.models import (
    EvidenceReference,
    ListingObservation,
    PlatformListing,
)
from app.product_intelligence.orchestrator.service import (
    ProductIntelligencePipelineRequest,
)
from app.retailer_adapters.contracts import (
    AvailabilityObservation,
    PriceObservation,
    RetailerLocationContext,
    RetailerProduct,
    SourceProvenance,
)


class AdapterIngestionError(Exception):
    """Base class for adapter-to-ingestion projection failures."""


class InvalidAdapterEvidence(AdapterIngestionError):
    """The adapter observation is not admissible as governed evidence."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid adapter evidence: {code}")


class AdapterListingProjection(BaseModel):
    """One retailer observation projected into existing governed models."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_bundle: EvidenceBundle
    pipeline_request: ProductIntelligencePipelineRequest
    source_provenance: SourceProvenance
    location: RetailerLocationContext
    price: PriceObservation | None = None
    availability: AvailabilityObservation | None = None


class RetailerAdapterIngestionBridge:
    """Pure, deterministic projection boundary. No I/O and no persistence."""

    def project(
        self,
        product: RetailerProduct,
        *,
        price: PriceObservation | None = None,
        availability: AvailabilityObservation | None = None,
        parser_version: str | None = None,
    ) -> AdapterListingProjection:
        if product.raw_payload_reference is None:
            raise InvalidAdapterEvidence("raw_payload_reference_required")
        self._check_observation(product, price, availability)
        provenance_version = (
            parser_version
            or f"retailer-adapter:{product.provenance.adapter_id}:v1"
        )

        listing = PlatformListing(
            platform=product.retailer_id,
            platform_listing_id=product.retailer_product_id,
            raw_title=product.title,
            raw_quantity_text=product.quantity_text,
            raw_category_text=product.category_text,
            listing_url=product.product_url,
        )
        observation = ListingObservation(
            platform_listing_id=product.retailer_product_id,
            displayed_price=None if price is None else price.display_text,
            reference_price=None if price is None else price.reference_display_text,
            availability_signal=None if availability is None else availability.raw_signal,
            capture_timestamp=product.captured_at,
            parser_version=provenance_version,
            source_artifact_reference=product.raw_payload_reference,
            capture_context_reference=product.location.scope.scope_id,
        )
        evidence_reference = EvidenceReference(
            source_type="retailer_adapter_observation",
            source_id=product.raw_payload_reference,
            capture_timestamp=product.captured_at,
            note=self._evidence_note(product, price, availability),
        )
        evidence_bundle = EvidenceBundle(
            platform=product.retailer_id,
            source_artifact_reference=product.raw_payload_reference,
            capture_timestamp=product.captured_at,
            evidence_references=[evidence_reference],
            parser_version=provenance_version,
            capture_context_reference=product.location.scope.scope_id,
        )
        pipeline_request = ProductIntelligencePipelineRequest(
            platform_listing=listing,
            listing_observation=observation,
            evidence_bundles=[evidence_bundle],
        )
        return AdapterListingProjection(
            platform_listing=listing,
            listing_observation=observation,
            evidence_bundle=evidence_bundle,
            pipeline_request=pipeline_request,
            source_provenance=product.provenance,
            location=product.location,
            price=price,
            availability=availability,
        )

    @staticmethod
    def _check_observation(
        product: RetailerProduct,
        price: PriceObservation | None,
        availability: AvailabilityObservation | None,
    ) -> None:
        for observation in (price, availability):
            if observation is None:
                continue
            if observation.retailer_id != product.retailer_id:
                raise InvalidAdapterEvidence("retailer_mismatch")
            if observation.retailer_product_id != product.retailer_product_id:
                raise InvalidAdapterEvidence("retailer_product_id_mismatch")
            if observation.location.scope.scope_id != product.location.scope.scope_id:
                raise InvalidAdapterEvidence("location_scope_mismatch")

    @staticmethod
    def _evidence_note(
        product: RetailerProduct,
        price: PriceObservation | None,
        availability: AvailabilityObservation | None,
    ) -> str:
        parts = [
            f"adapter={product.provenance.adapter_id}",
            f"retailer={product.retailer_id}",
            f"location_scope={product.location.scope.scope_id}",
            f"location_kind={product.location.kind.value}",
        ]
        if price is not None:
            parts.append(f"price_semantics={price.price_semantics.value}")
            parts.append(f"price_currency={price.effective_currency or 'unknown'}")
        if availability is not None:
            parts.append(f"availability={availability.status.value}")
        return "; ".join(parts)


__all__ = [
    "AdapterIngestionError",
    "AdapterListingProjection",
    "InvalidAdapterEvidence",
    "RetailerAdapterIngestionBridge",
]
