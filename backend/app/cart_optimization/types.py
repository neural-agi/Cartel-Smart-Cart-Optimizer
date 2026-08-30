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
from app.cart_optimization.quantity_semantics import VariantQuantitySemantics
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


class LogicalCart(BaseModel):
    """Immutable logical representation of a user's shopping intent.

    This is the upstream input contract that precedes optimization.
    It captures which canonical Variants the user wants and in what
    quantities, without any platform-specific execution state, listing
    provenance, or cost information.

    The logical cart feeds into Cart Optimization, which produces
    candidate plans that map each cart item to a selected platform listing.
    """

    model_config = ConfigDict(frozen=True)

    cart_id: str
    cart_items: tuple[CartItemRequest, ...] = Field(default_factory=tuple)

    @field_validator("cart_id")
    @classmethod
    def _require_cart_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("cart_id is required")
        return value

    @model_validator(mode="after")
    def _validate_unique_item_ids(self) -> "LogicalCart":
        item_ids = [item.item_id for item in self.cart_items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("duplicate cart item IDs are invalid")
        return self


class RetailerAllocation(BaseModel):
    """Retailer assignment for one candidate checkout plan."""

    model_config = ConfigDict(frozen=True)

    retailer_id: str
    checkout_group_id: str


class ItemAllocation(BaseModel):
    """Fulfillment assignment for one requested cart item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_variant_id: str
    quantity: int
    retailer_id: str
    checkout_group_id: str


class CandidateListingProvenance(BaseModel):
    """Exact persisted listing and displayed-price source for an allocation."""

    model_config = ConfigDict(frozen=True)

    platform: str
    platform_listing_id: str
    observation_id: str
    observed_selling_price: Money
    retailer_product_id: str | None = None


class CandidateItemAllocation(BaseModel):
    """Candidate allocation retaining listing provenance without cart execution state."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_variant_id: str
    quantity: int
    retailer_id: str
    checkout_group_id: str
    listing_provenance: CandidateListingProvenance
    quantity_semantics: VariantQuantitySemantics | None = None

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
                retailer_product_id=observation.retailer_product_id,
            ),
        )

    def to_item_allocation(self) -> ItemAllocation:
        """Construct the provenance-stripped optimization representation.

        The returned ItemAllocation carries the same canonical variant identity,
        requested/allocation quantity, retailer identity, and checkout group
        identity as this candidate allocation. Listing provenance is intentionally
        excluded from ItemAllocation and must be retained separately via
        CandidatePlan.candidate_item_allocations.
        """
        return ItemAllocation(
            item_id=self.item_id,
            canonical_variant_id=self.canonical_variant_id,
            quantity=self.quantity,
            retailer_id=self.retailer_id,
            checkout_group_id=self.checkout_group_id,
        )

    @staticmethod
    def _identity_key(allocation: ItemAllocation | "CandidateItemAllocation") -> tuple[str, ...]:
        return (
            allocation.item_id,
            allocation.canonical_variant_id,
            str(allocation.quantity),
            allocation.retailer_id,
            allocation.checkout_group_id,
        )


class CheckoutGroup(BaseModel):
    """One retailer checkout represented by a candidate plan."""

    model_config = ConfigDict(frozen=True)

    checkout_group_id: str
    retailer_id: str
    effective_cost_evaluation_id: str


class PlatformCartGroup(BaseModel):
    """A platform-specific grouping of selected listing allocations.

    Derived from a CandidatePlan, this represents one platform checkout
    containing all candidate allocations that share a checkout_group_id.

    It makes explicit the platform identity, retailer abstraction, and
    the selected listing provenance for each item in the group, without
    conflating platform with retailer_id.

    This contract stops before any platform execution. It does NOT carry:
    - authentication tokens;
    - browser sessions;
    - cart session IDs;
    - mutable platform cart state;
    - credentials;
    - payment information.
    """

    model_config = ConfigDict(frozen=True)

    platform: str
    retailer_id: str
    checkout_group_id: str
    effective_cost_evaluation_id: str
    listing_allocations: tuple[CandidateItemAllocation, ...] = Field(default_factory=tuple)

    @field_validator("platform", "checkout_group_id", "effective_cost_evaluation_id")
    @classmethod
    def _require_non_empty_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identifier fields must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_all_allocations_have_provenance(self) -> "PlatformCartGroup":
        if not self.listing_allocations:
            raise ValueError("platform_cart_group must contain at least one listing allocation")
        for alloc in self.listing_allocations:
            if alloc.listing_provenance is None:
                raise ValueError(
                    f"platform listing provenance required for item_id={alloc.item_id}"
                )
        return self


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
    candidate_item_allocations: tuple[CandidateItemAllocation, ...] = Field(default_factory=tuple)
    checkout_groups: tuple[CheckoutGroup, ...] = Field(default_factory=tuple)
    effective_cost_evaluation_reference: EffectiveCostEvaluationReference
    constraint_references: tuple[OptimizationConstraintReference, ...] = Field(
        default_factory=tuple
    )
    feasibility: PlanFeasibility
    unknown_components: tuple[str, ...] = Field(default_factory=tuple)
    provenance_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)

    @classmethod
    def from_candidate_allocations(
        cls,
        *,
        plan_id: str,
        inconvenience_penalty_units: int,
        retailer_preference_priority: int,
        candidate_item_allocations: tuple[CandidateItemAllocation, ...],
        retailer_allocations: tuple[RetailerAllocation, ...] = (),
        checkout_groups: tuple[CheckoutGroup, ...] = (),
        effective_cost_evaluation_reference: EffectiveCostEvaluationReference,
        constraint_references: tuple[OptimizationConstraintReference, ...] = (),
        feasibility: PlanFeasibility,
        unknown_components: tuple[str, ...] = (),
        provenance_references: tuple[EvidenceReference, ...] = (),
    ) -> "CandidatePlan":
        """Construct a plan from provenance-rich candidate allocations.

        Each CandidateItemAllocation is projected to a provenance-stripped
        ItemAllocation for the item_allocations field. The original
        candidate_item_allocations are retained verbatim so that listing
        provenance is never lost.
        """
        return cls(
            plan_id=plan_id,
            inconvenience_penalty_units=inconvenience_penalty_units,
            retailer_preference_priority=retailer_preference_priority,
            retailer_allocations=retailer_allocations,
            item_allocations=tuple(
                allocation.to_item_allocation() for allocation in candidate_item_allocations
            ),
            candidate_item_allocations=candidate_item_allocations,
            checkout_groups=checkout_groups,
            effective_cost_evaluation_reference=effective_cost_evaluation_reference,
            constraint_references=constraint_references,
            feasibility=feasibility,
            unknown_components=unknown_components,
            provenance_references=provenance_references,
        )

    @model_validator(mode="after")
    def _validate_allocation_provenance_consistency(self) -> "CandidatePlan":
        """When candidate_item_allocations is populated, it must match
        item_allocations exactly — one-to-one, same identity keys. This
        prevents silent provenance loss or mismatched Variant attribution.

        When quantity_semantics is attached to a candidate allocation, its
        canonical_variant_id and requested_quantity must match the allocation's
        own values so that resolution results cannot be silently reassigned.
        """
        if not self.candidate_item_allocations:
            return self
        if len(self.candidate_item_allocations) != len(self.item_allocations):
            raise ValueError(
                "candidate_item_allocations count must match item_allocations count"
            )
        allocation_keys = {
            CandidateItemAllocation._identity_key(item) for item in self.item_allocations
        }
        for candidate in self.candidate_item_allocations:
            if CandidateItemAllocation._identity_key(candidate) not in allocation_keys:
                raise ValueError(
                    f"candidate item allocation for item_id={candidate.item_id} "
                    f"has no matching ItemAllocation"
                )
            if candidate.quantity_semantics is not None:
                sem = candidate.quantity_semantics
                if sem.canonical_variant_id != candidate.canonical_variant_id:
                    raise ValueError(
                        f"quantity_semantics for item_id={candidate.item_id} "
                        f"references canonical_variant_id={sem.canonical_variant_id} "
                        f"but allocation targets {candidate.canonical_variant_id}"
                    )
                if sem.requested_quantity != candidate.quantity:
                    raise ValueError(
                        f"quantity_semantics for item_id={candidate.item_id} "
                        f"references requested_quantity={sem.requested_quantity} "
                        f"but allocation requests {candidate.quantity}"
                    )
        return self

    @property
    def quantity_semantics(self) -> tuple[VariantQuantitySemantics, ...] | None:
        """Quantity-resolution results retained on this plan's candidate allocations.

        Returns ``None`` when no allocation carries quantity semantics,
        signalling that the plan was constructed without the quantity
        semantics bridge (backward-compatible path).

        When non-``None``, callers can inspect each allocation's
        resolution status, canonical Variant, requested quantity, pack
        semantics, and rationale.
        """
        semantics = tuple(
            alloc.quantity_semantics
            for alloc in self.candidate_item_allocations
            if alloc.quantity_semantics is not None
        )
        return semantics if semantics else None

    def platform_cart_groups(self) -> tuple[PlatformCartGroup, ...]:
        """Derive platform-specific cart groups from this plan's allocations.

        Groups ``candidate_item_allocations`` by ``checkout_group_id``.
        Each group represents the items that would be purchased together
        on one platform checkout, with their selected listing provenance.

        Returns an empty tuple when the plan has no candidate allocations.
        """
        if not self.candidate_item_allocations:
            return ()

        checkout_groups_map = {
            cg.checkout_group_id: cg for cg in self.checkout_groups
        }

        grouped: dict[str, list[CandidateItemAllocation]] = {}
        for alloc in self.candidate_item_allocations:
            grouped.setdefault(alloc.checkout_group_id, []).append(alloc)

        groups: list[PlatformCartGroup] = []
        for checkout_group_id in sorted(grouped):
            allocations = tuple(sorted(grouped[checkout_group_id], key=lambda a: a.item_id))
            checkout = checkout_groups_map.get(checkout_group_id)
            if checkout is not None:
                effective_cost_eval_id = checkout.effective_cost_evaluation_id
                retailer_id = checkout.retailer_id
            else:
                effective_cost_eval_id = (
                    self.effective_cost_evaluation_reference.effective_cost_evaluation_id
                )
                retailer_id = allocations[0].retailer_id
            groups.append(
                PlatformCartGroup(
                    platform=allocations[0].listing_provenance.platform,
                    retailer_id=retailer_id,
                    checkout_group_id=checkout_group_id,
                    effective_cost_evaluation_id=effective_cost_eval_id,
                    listing_allocations=allocations,
                )
            )
        return tuple(groups)


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
        logical_item_ids = [
            (item.item_id, item.canonical_variant_id) for item in self.cart_items
        ]
        if len(logical_item_ids) != len(set(logical_item_ids)):
            raise ValueError("duplicate cart item identities are invalid")
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
        if self.chosen_plan is not None and self.chosen_plan_id != self.chosen_plan.plan_id:
            raise ValueError("chosen_plan_id must match chosen_plan.plan_id")
        if self.outcome is OptimizationOutcome.SELECTED and self.chosen_plan is None:
            raise ValueError("selected outcome requires a chosen plan")
        if self.outcome is not OptimizationOutcome.SELECTED and self.chosen_plan is not None:
            raise ValueError("non-selected outcome cannot contain a chosen plan")
        return self
