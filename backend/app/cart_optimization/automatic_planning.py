"""User-shaped orchestration for automatic cart planning.

This module owns only the handoff from canonical cart demand to the existing
explicit planning service. It does not assign business identities or policy.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.cart_optimization.construction import (
    CandidateAllocationSet,
    CandidatePlanConstructionInput,
    CandidatePlanConstructionService,
)
from app.cart_optimization.planning import (
    CandidateKey,
    CartPlanningRequest,
    CartPlanningService,
    SuppliedCandidateContext,
    SuppliedPlan,
)
from app.cart_optimization.providers import (
    CheckoutGroupProvider,
    PlanPolicyProvider,
    PlanningProviderUnavailable,
    RetailerIdentityProvider,
)
from app.cart_optimization.types import (
    CandidateItemAllocation,
    CartItemRequest,
    CartOptimizationRequest,
    CartOptimizationResult,
    CandidatePlanCoverage,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    RetailerAllocation,
)
from app.cart_optimization.service import CartOptimizationService
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItemRequest,
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryService,
)
from app.cart_optimization.candidate_enrichment import CandidateAllocationEnrichment, CandidateAllocationEnrichmentService
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.observation.capture_contract import CheckoutCaptureRequest


class AutomaticPlanningStatus(StrEnum):
    READY = "ready"
    UNRESOLVED = "unresolved"


class AutomaticCartItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_product_id: str
    canonical_variant_id: str
    quantity: int

    @model_validator(mode="after")
    def _validate(self) -> "AutomaticCartItem":
        if any(not field.strip() for field in (self.item_id, self.canonical_product_id, self.canonical_variant_id)):
            raise ValueError("canonical cart item identity is required")
        if self.quantity <= 0:
            raise ValueError("canonical cart item quantity must be positive")
        return self


class AutomaticPlanningRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    cart_id: str
    items: tuple[AutomaticCartItem, ...] = Field(default_factory=tuple)


class AutomaticPlanningResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    status: AutomaticPlanningStatus
    optimization_result: CartOptimizationResult | None = None
    unresolved_reasons: tuple[str, ...] = Field(default_factory=tuple)


class PlanIdProvider(Protocol):
    def plan_id(
        self,
        *,
        request_id: str,
        combination_index: int,
        allocations: tuple[CandidateItemAllocation, ...],
    ) -> str: ...


class UnavailablePlanIdProvider:
    def plan_id(self, *, request_id: str, combination_index: int, allocations: tuple[CandidateItemAllocation, ...]) -> str:
        raise PlanningProviderUnavailable("plan identity provider is unavailable")


class AutomaticCartPlanningService:
    """Build explicit planning inputs from canonical demand when authorities exist."""

    def __init__(
        self,
        *,
        discovery: CartCandidateDiscoveryService,
        planning: CartPlanningService,
        retailer_provider: RetailerIdentityProvider,
        checkout_group_provider: CheckoutGroupProvider,
        policy_provider: PlanPolicyProvider,
        plan_id_provider: PlanIdProvider,
        checkout_observation_provider,
        cost_intelligence,
        checkout_capture=None,
        construction: CandidatePlanConstructionService | None = None,
        enrichment: CandidateAllocationEnrichmentService | None = None,
        optimization_policy_version: str = "configured",
    ) -> None:
        self._discovery = discovery
        self._planning = planning
        self._retailer_provider = retailer_provider
        self._checkout_group_provider = checkout_group_provider
        self._policy_provider = policy_provider
        self._plan_id_provider = plan_id_provider
        self._checkout_observation_provider = checkout_observation_provider
        self._cost_intelligence = cost_intelligence
        self._checkout_capture = checkout_capture
        self._construction = construction or CandidatePlanConstructionService()
        self._enrichment = enrichment or CandidateAllocationEnrichmentService()
        self._policy_version = optimization_policy_version

    def plan(self, request: AutomaticPlanningRequest) -> AutomaticPlanningResult:
        request_id = request.cart_id
        try:
            discovery = self._discovery.discover(
                CartCandidateDiscoveryRequest(items=tuple(
                    CartCandidateDiscoveryItemRequest(
                        item_id=item.item_id,
                        quantity=item.quantity,
                        canonical_product_id=item.canonical_product_id,
                        canonical_variant_id=item.canonical_variant_id,
                    )
                    for item in request.items
                ))
            )
            reasons = tuple(
                f"{item.item_id}: {item.reason or item.status.value}"
                for item in discovery.items
                if not item.candidates or item.status.value != "candidates_available"
            )
            if reasons:
                return self._unresolved(request_id, reasons)

            # The frozen provider contracts require checkout-group resolution
            # to receive a plan ID, while the current plan-ID authority is not
            # defined independently of the resulting allocation context. Do
            # not manufacture a provisional identity for production planning.
            if isinstance(self._plan_id_provider, UnavailablePlanIdProvider):
                raise PlanningProviderUnavailable(
                    "automatic planning requires an authoritative plan identity provider"
                )

            sets: list[CandidateAllocationSet] = []
            for item in discovery.items:
                allocations: list[CandidateItemAllocation] = []
                for candidate in item.candidates:
                    retailer_id = self._retailer_provider.retailer_id(
                        item_id=item.item_id,
                        platform=candidate.platform,
                        listing_id=candidate.platform_listing_id,
                    )
                    allocations.append(self._enrichment.enrich(
                        item, candidate, CandidateAllocationEnrichment(
                            item_id=item.item_id,
                            canonical_product_id=item.canonical_product_id,
                            canonical_variant_id=item.canonical_variant_id,
                            quantity=item.quantity,
                            retailer_id=retailer_id,
                            checkout_group_id="pending",
                        )
                    ).allocation)
                sets.append(CandidateAllocationSet(
                    item_id=item.item_id,
                    canonical_variant_id=item.canonical_variant_id,
                    quantity=item.quantity,
                    candidates=tuple(allocations),
                ))

            enumeration = self._construction.enumerate_allocations(tuple(sets))
            if not enumeration.combinations:
                return self._unresolved(request_id, (enumeration.reason or "no candidate plan",))
            construction_inputs: list[CandidatePlanConstructionInput] = []
            observations: dict[str, CheckoutObservation] = {}
            for index, raw_allocations in enumerate(enumeration.combinations):
                retailer_allocations: list[RetailerAllocation] = []
                groups: list[CheckoutGroup] = []
                allocations: list[CandidateItemAllocation] = []
                for allocation in raw_allocations:
                    group_id = self._checkout_group_provider.checkout_group_id(
                        plan_id="pending", item_id=allocation.item_id, retailer_id=allocation.retailer_id
                    )
                    enriched = allocation.model_copy(update={"checkout_group_id": group_id})
                    allocations.append(enriched)
                    if not any(item.retailer_id == enriched.retailer_id and item.checkout_group_id == group_id for item in retailer_allocations):
                        retailer_allocations.append(RetailerAllocation(retailer_id=enriched.retailer_id, checkout_group_id=group_id))
                plan_id = self._plan_id_provider.plan_id(
                    request_id=request_id, combination_index=index, allocations=tuple(allocations)
                )
                groups = [CheckoutGroup(checkout_group_id=item.checkout_group_id, retailer_id=item.retailer_id, effective_cost_evaluation_id="pending") for item in retailer_allocations]
                policy = self._policy_provider.resolve(plan_id=plan_id)
                if self._checkout_capture is not None:
                    capture_request = CheckoutCaptureRequest(
                        request_id=request_id,
                        plan_id=plan_id,
                        platform=allocations[0].listing_provenance.platform,
                        cart_items=tuple(
                            CartItemRequest(
                                item_id=item.item_id,
                                quantity=item.quantity,
                                canonical_variant_id=item.canonical_variant_id,
                            )
                            for item in request.items
                        ),
                        candidate_allocations=tuple(allocations),
                    )
                    self._checkout_capture.capture(capture_request)
                observation = self._checkout_observation_provider.get_observation(plan_id=plan_id, request_id=request_id)
                if observation is None:
                    raise PlanningProviderUnavailable(f"checkout observation is unavailable for plan {plan_id}")
                ece = self._cost_intelligence.evaluate_observation(observation)
                observations[plan_id] = observation
                groups = [item.model_copy(update={"effective_cost_evaluation_id": ece.evaluation_id}) for item in groups]
                construction_inputs.append(CandidatePlanConstructionInput(
                    plan_id=plan_id,
                    inconvenience_penalty_units=policy[0],
                    retailer_preference_priority=policy[1],
                    candidate_item_allocations=tuple(allocations),
                    retailer_allocations=tuple(retailer_allocations),
                    checkout_groups=tuple(groups),
                    effective_cost_evaluation_reference=EffectiveCostEvaluationReference(effective_cost_evaluation_id=ece.evaluation_id),
                    effective_cost_evaluation=ece,
                    feasibility=policy[2],
                    feasibility_evidence=policy[3],
                ))
            optimization_request = CartOptimizationRequest(
                request_id=request_id,
                optimization_policy_version=self._policy_version,
                cart_items=tuple(
                    CartItemRequest(
                        item_id=item.item_id,
                        quantity=item.quantity,
                        canonical_variant_id=item.canonical_variant_id,
                    )
                    for item in request.items
                ),
                candidate_plan_coverage=CandidatePlanCoverage(
                    state="complete",
                    scope_reference=request_id,
                    candidate_set_reference=request_id,
                    coverage_basis="automatic-cart-planning",
                    validation_reference=request_id,
                ),
            )
            attached = self._construction.attach_to_request(optimization_request, tuple(construction_inputs))
            result = CartOptimizationService().optimize(attached)
            return AutomaticPlanningResult(request_id=request_id, status=AutomaticPlanningStatus.READY, optimization_result=result)
        except (PlanningProviderUnavailable, ValueError) as exc:
            return self._unresolved(request_id, (str(exc),))

    @staticmethod
    def _unresolved(request_id: str, reasons: tuple[str, ...]) -> AutomaticPlanningResult:
        return AutomaticPlanningResult(request_id=request_id, status=AutomaticPlanningStatus.UNRESOLVED, unresolved_reasons=reasons)
