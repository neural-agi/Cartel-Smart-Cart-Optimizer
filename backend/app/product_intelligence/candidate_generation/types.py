from __future__ import annotations

from pydantic import BaseModel, Field

from app.product_intelligence.models import (
    EvidenceReference,
    ListingObservation,
    PlatformListing,
    Product,
    ProductVariant,
)


class CandidateGenerationRequest(BaseModel):
    """Input required to generate canonical product candidates."""

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_references: list[EvidenceReference] = Field(default_factory=list)


class CandidateGenerationResponse(BaseModel):
    """Candidate sets produced for downstream matching."""

    product_candidates: list[Product] = Field(default_factory=list)
    variant_candidates: list[ProductVariant] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)

