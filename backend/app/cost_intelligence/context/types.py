"""Immutable Cost Context value objects."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.cost_intelligence.observation.types import CheckoutObservation
from app.product_intelligence.models import EvidenceReference


class CostContext(BaseModel):
    """Canonical immutable input shared by Cost Intelligence evaluators."""

    model_config = ConfigDict(frozen=True)

    context_id: str
    checkout_observation: CheckoutObservation
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)
