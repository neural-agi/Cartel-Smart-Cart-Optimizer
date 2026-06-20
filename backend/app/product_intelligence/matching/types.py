from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.product_intelligence.models import (
    EvidenceReference,
    ListingObservation,
    PlatformListing,
    Product,
    ProductVariant,
)


class MatchOutcome(StrEnum):
    """High-level outcome of a matching decision."""

    mapped = "mapped"
    unresolved = "unresolved"
    ambiguous = "ambiguous"
    conflicting = "conflicting"
    rejected = "rejected"


class ProductMatchRequest(BaseModel):
    """Input for product-level matching."""

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    product_candidates: list[Product] = Field(default_factory=list)


class ProductMatchResponse(BaseModel):
    """Output of product-level matching."""

    outcome: MatchOutcome
    selected_product: Product | None = None
    rationale: list[str] = Field(default_factory=list)


class VariantMatchRequest(BaseModel):
    """Input for variant-level matching."""

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    product: Product | None = None
    variant_candidates: list[ProductVariant] = Field(default_factory=list)


class VariantMatchResponse(BaseModel):
    """Output of variant-level matching."""

    outcome: MatchOutcome
    selected_variant: ProductVariant | None = None
    rationale: list[str] = Field(default_factory=list)

