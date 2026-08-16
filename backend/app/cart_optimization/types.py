from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.cart_optimization.enums import (
    ConstraintHardness,
    CoverageState,
    OptimizationOutcome,
    PlanRejectionCode,
    PlanFeasibility,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation
from app.product_intelligence.models import EvidenceReference


class CartItemRequest(BaseModel):
    """One canonical variant demand in an optimization request."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_variant_id: str
    quantity: int


class RetailerAllocation(BaseModel):
    """Retailer assignment for one candidate checkout plan."""

    model_config = ConfigDict(frozen=True)

    retailer_id: str
    checkout_group_id: str


class CandidateListingProvenance(BaseModel):
    """Exact persisted listing and displayed-price source for an allocation."""

    model_config = ConfigDict(frozen=True)

    platform: str
    platform_listing_id: str
    observation_id: str
    observed_selling_price: Money


class ItemAllocation(BaseModel):
    """Fulfillment assignment for one requested cart item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_variant_id: str
    quantity: int
    retailer_id: str
    checkout_group_id: str
    listing_provenance: CandidateListingProvenance | None = None


class CandidateItemAllocation(BaseModel):
    """Candidate allocation retaining listing provenance without cart execution state."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_variant_id: str
    quantity: int
    retailer_id: str
    checkout_group_id: str
    listing_provenance: CandidateListingProvenance

    @classmethod
    def from_comparable_observation(
        cls,
        *,
        item_id: str,
        canonical_variant_id: str,
        quantity: int,
        retailer_id: str,
        checkout_group_id: str,
        observation: ComparableRetailObservation,
    ) -> "CandidateItemAllocation":
        if observation.canonical_variant_id != canonical_variant_id:
            raise ValueError("listing association does not target requested canonical Variant")
        return cls(
            item_id=item_id,
            canonical_variant_id=canonical_variant_id,
            quantity=quantity,
            retailer_id=retailer_id,
            checkout_group_id=checkout_group_id,
            listing_provenance=CandidateListingProvenance(
                platform=observation.platform,
                platform_listing_id=observation.platform_listing_id,
                observation_id=observation.observation_id,
                observed_selling_price=observation.observed_selling_price,
            ),
        )

    def to_item_allocation(self) -> ItemAllocation:
        """Convert to optimizer allocation data without dropping provenance."""
        return ItemAllocation(
            item_id=self.item_id,
            canonical_variant_id=self.canonical_variant_id,
            quantity=self.quantity,
            retailer_id=self.retailer_id,
            checkout_group_id=self.checkout_group_id,
            listing_provenance=self.listing_provenance,
        )


class CheckoutGroup(BaseModel):
    """One retailer checkout represented by a candidate plan."""

    model_config = ConfigDict(frozen=True)

    checkout_group_id: str
    retailer_id: str
    effective_cost_evaluation_id: str


class EffectiveCostEvaluationReference(BaseModel):
    """Immutable identity reference to one effective-cost evaluation."""

    model_config = ConfigDict(frozen=True)

    effective_cost_evaluation_id: str

    @field_validator("effective_cost_evaluation_id")
    @classmethod
    def _require_reference(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("effective-cost evaluation reference is required")
        return value


class OptimizationConstraintReference(BaseModel):
    """Immutable identity reference to one optimization constraint."""

    model_config = ConfigDict(frozen=True)

    optimization_constraint_id: str

    @field_validator("optimization_constraint_id")
    @classmethod
    def _require_reference(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("optimization constraint reference is required")
        return value


class BudgetConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["budget"] = "budget"
    amount: Money
    hardness: ConstraintHardness


class RetailerPreferenceConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["retailer_preference"] = "retailer_preference"
    retailer_ids: tuple[str, ...]
    hardness: ConstraintHardness


class MaximumCheckoutGroupsConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["maximum_checkout_groups"] = "maximum_checkout_groups"
    maximum_checkout_groups: int
    hardness: ConstraintHardness


class InconveniencePenaltyConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["inconvenience_penalty"] = "inconvenience_penalty"
    penalty_units: int
    hardness: ConstraintHardness


class DeliveryPreferenceConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["delivery_preference"] = "delivery_preference"
    preference: str
    hardness: ConstraintHardness


class SubstitutionPolicyConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["substitution_policy"] = "substitution_policy"
    allow_substitutions: bool
    hardness: ConstraintHardness


class MembershipPreferenceConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["membership_preference"] = "membership_preference"
    preference: str
    hardness: ConstraintHardness


OptimizationConstraint = Annotated[
    BudgetConstraint
    | RetailerPreferenceConstraint
    | MaximumCheckoutGroupsConstraint
    | InconveniencePenaltyConstraint
    | DeliveryPreferenceConstraint
    | SubstitutionPolicyConstraint
    | MembershipPreferenceConstraint,
    Field(discriminator="kind"),
]


class CandidatePlanCoverage(BaseModel):
    """Immutable completeness declaration for a candidate-plan set."""

    model_config = ConfigDict(frozen=True)

    state: CoverageState
    scope_reference: str | None = None
    candidate_set_reference: str | None = None
    coverage_basis: str | None = None
    validation_reference: str | None = None
    rationale: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_declaration(self) -> "CandidatePlanCoverage":
        metadata = (
            self.scope_reference,
            self.candidate_set_reference,
            self.coverage_basis,
            self.validation_reference,
        )
        if self.state is CoverageState.COMPLETE:
            if any(value is None or not value.strip() for value in metadata):
                raise ValueError("complete coverage requires all metadata")
        elif not self.rationale or any(not item.strip() for item in self.rationale):
            raise ValueError("non-complete coverage requires deterministic rationale")
        return self


class CandidatePlan(BaseModel):
    """Immutable candidate allocation plan."""

    model_config = ConfigDict(frozen=True)

    plan_id: str
    inconvenience_penalty_units: int
    retailer_preference_priority: int
    retailer_allocations: tuple[RetailerAllocation, ...] = Field(default_factory=tuple)
    item_allocations: tuple[ItemAllocation, ...] = Field(default_factory=tuple)
    checkout_groups: tuple[CheckoutGroup, ...] = Field(default_factory=tuple)
    effective_cost_evaluation_reference: EffectiveCostEvaluationReference
    constraint_references: tuple[OptimizationConstraintReference, ...] = Field(
        default_factory=tuple
    )
    feasibility: PlanFeasibility
    unknown_components: tuple[str, ...] = Field(default_factory=tuple)
    provenance_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)

    @model_validator(mode="before")
    @classmethod
    def _normalize_candidate_allocations(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        allocations = data.get("item_allocations")
        if allocations is None:
            return data
        try:
            iterator = iter(allocations)
        except TypeError:
            return data
        normalized = tuple(
            allocation.to_item_allocation()
            if isinstance(allocation, CandidateItemAllocation)
            else allocation
            for allocation in iterator
        )
        return {**data, "item_allocations": normalized}


class RejectedPlan(BaseModel):
    """Plan retained in an optimization result with its rejection reason."""

    model_config = ConfigDict(frozen=True)

    plan_id: str
    code: PlanRejectionCode
    explanation: str | None = None


class CartOptimizationRequest(BaseModel):
    """Immutable input contract for Cart Optimization."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    optimization_policy_version: str
    cart_items: tuple[CartItemRequest, ...] = Field(default_factory=tuple)
    candidate_plans: tuple[CandidatePlan, ...] = Field(default_factory=tuple)
    candidate_plan_coverage: CandidatePlanCoverage
    constraints: tuple[OptimizationConstraint, ...] = Field(default_factory=tuple)
    effective_cost_evaluations: tuple[EffectiveCostEvaluationResult, ...] = Field(
        default_factory=tuple
    )
    provenance_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_evaluation_ids(self) -> "CartOptimizationRequest":
        evaluation_ids = [item.evaluation_id for item in self.effective_cost_evaluations]
        if len(evaluation_ids) != len(set(evaluation_ids)):
            raise ValueError("duplicate effective-cost evaluation IDs are invalid")
        return self


class CartOptimizationResult(BaseModel):
    """Immutable output contract for Cart Optimization."""

    model_config = ConfigDict(frozen=True)

    optimization_id: str
    request_id: str
    chosen_plan_id: str | None = None
    chosen_plan: CandidatePlan | None = None
    outcome: OptimizationOutcome
    rationale: tuple[str, ...] = Field(default_factory=tuple)
    unknowns: tuple[str, ...] = Field(default_factory=tuple)
    assumptions: tuple[str, ...] = Field(default_factory=tuple)
    provenance_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)
    ranked_plan_ids: tuple[str, ...] = Field(default_factory=tuple)
    alternative_plans: tuple[CandidatePlan, ...] = Field(default_factory=tuple)
    rejected_plans: tuple[RejectedPlan, ...] = Field(default_factory=tuple)
    rejection_reasons: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_chosen_plan_consistency(self) -> "CartOptimizationResult":
        if (self.chosen_plan_id is None) != (self.chosen_plan is None):
            raise ValueError("chosen_plan_id and chosen_plan must be provided together")
        if self.chosen_plan is not None and self.chosen_plan.plan_id != self.chosen_plan_id:
            raise ValueError("chosen_plan_id must match chosen_plan.plan_id")
        return self
