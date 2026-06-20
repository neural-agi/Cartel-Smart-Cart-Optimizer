from __future__ import annotations

from pydantic import BaseModel, Field

from app.product_intelligence.models import (
    EvidenceReference,
    Product,
    ProductVariant,
)


class AssertionUpdateRequest(BaseModel):
    """Input for applying canonical assertion updates."""

    product: Product | None = None
    variant: ProductVariant | None = None
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    decision_references: list[str] = Field(default_factory=list)


class AssertionUpdateResponse(BaseModel):
    """Result of applying a canonical assertion update."""

    product: Product | None = None
    variant: ProductVariant | None = None
    assertion_reference: str | None = None

