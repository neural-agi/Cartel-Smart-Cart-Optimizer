"""Explicit immutable output contracts for Cost Intelligence evaluators."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


class OfferEvaluationResult(BaseModel):
    """Immutable result produced by a future offer evaluator."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: str
    offer_reference: str
    applicable: bool | None = None
    immediate_discount: Money | None = None
    deferred_value: Money | None = None
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)


class FeeEvaluationResult(BaseModel):
    """Immutable result produced by a future fee evaluator."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: str
    fee_reference: str
    applicable: bool | None = None
    fee_amount: Money | None = None
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)


class MembershipEvaluationResult(BaseModel):
    """Immutable result produced by a future membership evaluator."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: str
    membership_reference: str
    eligible: bool | None = None
    benefit_value: Money | None = None
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)


class EffectiveCostEvaluationResult(BaseModel):
    """Immutable result produced by a future effective-cost evaluator."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: str
    context_id: str
    subtotal: Money | None = None
    immediate_discounts: tuple[Money, ...] = Field(default_factory=tuple)
    fees: tuple[Money, ...] = Field(default_factory=tuple)
    effective_cost: Money | None = None
    deferred_value: Money | None = None
    unknown_components: tuple[str, ...] = Field(default_factory=tuple)
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)
