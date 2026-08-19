"""Explicit retailer and checkout-group enrichment for discovered candidates.

This boundary consumes upstream-supplied identity/context. It never derives
retailer or checkout-group values from discovery fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from app.cart_optimization.types import CandidateItemAllocation, CandidateListingProvenance
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    PersistedCandidateReadiness,
    PersistedListingCandidate,
)


class CandidateAllocationEnrichment(BaseModel):
    """Authoritative context supplied for one discovered candidate."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_product_id: str
    canonical_variant_id: str
    quantity: int
    retailer_id: str
    checkout_group_id: str

    @model_validator(mode="after")
    def _validate_identity_fields(self) -> "CandidateAllocationEnrichment":
        if any(
            not value.strip()
            for value in (
                self.item_id,
                self.canonical_product_id,
                self.canonical_variant_id,
                self.retailer_id,
                self.checkout_group_id,
            )
        ):
            raise ValueError("candidate enrichment identity fields are required")
        if self.quantity <= 0:
            raise ValueError("candidate enrichment quantity must be positive")
        return self


class EnrichedCandidateAllocation(BaseModel):
    """A discovered candidate paired with its explicit upstream context."""

    model_config = ConfigDict(frozen=True)

    candidate: PersistedListingCandidate
    enrichment: CandidateAllocationEnrichment
    allocation: CandidateItemAllocation


class CandidateAllocationEnrichmentService:
    """Validate supplied context and preserve discovered candidate evidence."""

    def enrich(
        self,
        discovery_item: CartCandidateDiscoveryItem,
        candidate: PersistedListingCandidate,
        enrichment: CandidateAllocationEnrichment,
    ) -> EnrichedCandidateAllocation:
        if candidate.readiness is not PersistedCandidateReadiness.ready_for_allocation:
            raise ValueError("candidate is not ready for allocation")
        if candidate not in discovery_item.candidates:
            raise ValueError("candidate is not part of the discovery item")
        expected = (
            candidate.canonical_product_id,
            candidate.canonical_variant_id,
            candidate.observation.observed_selling_price,
        )
        if (
            enrichment.item_id != discovery_item.item_id
            or enrichment.quantity != discovery_item.quantity
            or enrichment.canonical_product_id != candidate.canonical_product_id
            or enrichment.canonical_product_id != discovery_item.canonical_product_id
            or enrichment.canonical_variant_id != candidate.canonical_variant_id
            or enrichment.canonical_variant_id != discovery_item.canonical_variant_id
        ):
            raise ValueError("candidate identity or quantity does not match discovery")
        if candidate.observation.observed_selling_price is None:
            raise ValueError("candidate has no typed observed selling price")
        if expected[2] is None:
            raise ValueError("candidate has no typed observed selling price")
        allocation = CandidateItemAllocation(
            item_id=enrichment.item_id,
            canonical_variant_id=enrichment.canonical_variant_id,
            quantity=enrichment.quantity,
            retailer_id=enrichment.retailer_id,
            checkout_group_id=enrichment.checkout_group_id,
            listing_provenance=CandidateListingProvenance(
                platform=candidate.platform,
                platform_listing_id=candidate.platform_listing_id,
                observation_id=candidate.observation_id,
                observed_selling_price=candidate.observation.observed_selling_price,
            ),
        )
        return EnrichedCandidateAllocation(
            candidate=candidate,
            enrichment=enrichment,
            allocation=allocation,
        )

    def enrich_many(
        self,
        candidates: tuple[
            tuple[CartCandidateDiscoveryItem, PersistedListingCandidate, CandidateAllocationEnrichment], ...
        ],
    ) -> tuple[EnrichedCandidateAllocation, ...]:
        enriched = tuple(
            self.enrich(discovery_item, candidate, context)
            for discovery_item, candidate, context in candidates
        )
        return tuple(
            sorted(
                enriched,
                key=lambda item: item.candidate.model_dump_json(
                    exclude_none=False, warnings=False
                ),
            )
        )
