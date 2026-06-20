from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.product_intelligence.matching.types import MatchOutcome
from app.product_intelligence.models import (
    EvidenceReference,
    ListingObservation,
    PlatformListing,
    Product,
    ProductVariant,
)


class ReviewStatus(StrEnum):
    """Lifecycle state for a review case."""

    queued = "queued"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    needs_more_evidence = "needs_more_evidence"
    superseded = "superseded"


class ReviewCase(BaseModel):
    """A reviewable matching decision and its evidence."""

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    product_candidates: list[Product] = Field(default_factory=list)
    variant_candidates: list[ProductVariant] = Field(default_factory=list)
    match_outcome: MatchOutcome
    review_status: ReviewStatus = ReviewStatus.queued


class ReviewDecision(BaseModel):
    """Outcome of a human review action."""

    review_case_id: str
    review_status: ReviewStatus
    rationale: list[str] = Field(default_factory=list)

