"""Application handoff from persisted candidate discovery to optimization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from app.core.logging import get_logger

from app.cart_optimization.candidate_enrichment import (
    CandidateAllocationEnrichment,
    CandidateAllocationEnrichmentService,
)
from app.cart_optimization.construction import (
    CandidateAllocationSet,
    CandidatePlanConstructionInput,
    CandidatePlanConstructionService,
)
from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.providers import (
    CheckoutObservationProvider,
    PlanningProviderUnavailable,
    UnavailableCheckoutObservationProvider,
)
from app.cart_optimization.types import (
    CartItemRequest,
    CartOptimizationRequest,
    CartOptimizationResult,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    RetailerAllocation,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.pipeline.service import CostIntelligencePipelineService
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryResult,
    CartCandidateDiscoveryService,
    PersistedListingCandidate,
)


logger = get_logger(__name__)


class CandidateKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    platform: str
    platform_listing_id: str
    observation_id: str


class SuppliedCandidateContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: CandidateKey
    retailer_id: str
    checkout_group_id: str


class SuppliedPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    combination_index: int
    inconvenience_penalty_units: int
    retailer_preference_priority: int
    retailer_allocations: tuple[RetailerAllocation, ...] = Field(default_factory=tuple)
    checkout_groups: tuple[CheckoutGroup, ...]
    effective_cost_evaluation_reference: EffectiveCostEvaluationReference | None = None
    effective_cost_evaluation: EffectiveCostEvaluationResult | None = None
    feasibility: PlanFeasibility
    feasibility_evidence: tuple[str, ...]


class CartPlanningRequest(BaseModel):
    """Explicit application inputs; no missing value is inferred."""

    model_config = ConfigDict(frozen=True)

    discovery: CartCandidateDiscoveryRequest
    candidate_contexts: tuple[SuppliedCandidateContext, ...]
    plans: tuple[SuppliedPlan, ...]
    request_id: str
    optimization_policy_version: str
    checkout_observations: dict[str, CheckoutObservation] = Field(default_factory=dict)


class CartPlanningService:
    def __init__(
        self,
        *,
        discovery: CartCandidateDiscoveryService,
        enrichment: CandidateAllocationEnrichmentService | None = None,
        construction: CandidatePlanConstructionService | None = None,
        cost_intelligence: CostIntelligencePipelineService | None = None,
        checkout_provider: CheckoutObservationProvider | None = None,
        max_cart_items: int = 20,
        max_candidates_per_item: int = 20,
        max_combinations: int = 10000,
        max_supplied_plans: int = 100,
    ) -> None:
        self._discovery = discovery
        self._enrichment = enrichment or CandidateAllocationEnrichmentService()
        self._construction = construction or CandidatePlanConstructionService()
        self._cost_intelligence = cost_intelligence or CostIntelligencePipelineService()
        self._checkout_provider = checkout_provider or UnavailableCheckoutObservationProvider()
        self._max_cart_items = max_cart_items
        self._max_candidates_per_item = max_candidates_per_item
        self._max_combinations = max_combinations
        self._max_supplied_plans = max_supplied_plans

    def plan(self, request: CartPlanningRequest) -> CartOptimizationResult:
        self._validate_observation_keys(request)
        if len(request.discovery.items) > self._max_cart_items:
            raise ValueError("planning cart item limit exceeded")
        if len(request.plans) > self._max_supplied_plans:
            raise ValueError("planning supplied-plan limit exceeded")
        discovered = self._discovery.discover(request.discovery)
        sets = self._enrich_sets(discovered, request.candidate_contexts)
        for item in sets:
            if len(item.candidates) > self._max_candidates_per_item:
                raise ValueError(
                    f"planning candidate limit exceeded for logical item {item.item_id}"
                )
        estimated = 1
        for item in sets:
            estimated *= len(item.candidates)
            if estimated > self._max_combinations:
                raise ValueError("planning combination limit exceeded")
        enumeration = self._construction.enumerate_allocations(tuple(sets))
        logger.info(
            "cart_planning_enumerated request_id=%s cart_items=%s candidate_counts=%s combinations=%s submitted_plans=%s checkout_provider_mode=%s",
            request.request_id,
            len(request.discovery.items),
            tuple(len(item.candidates) for item in sets),
            len(enumeration.combinations),
            len(request.plans),
            "caller_observation" if request.checkout_observations else "provider_or_precomputed",
        )
        if enumeration.status.value != "complete":
            raise ValueError(enumeration.reason or "candidate enumeration produced no plan")
        if not request.plans:
            raise ValueError("at least one supplied plan is required")
        if any(item.combination_index < 0 for item in request.plans):
            raise ValueError("combination index must be non-negative")
        if any(item.combination_index >= len(enumeration.combinations) for item in request.plans):
            raise ValueError("combination index is outside enumerated plans")
        resolved_evaluations: dict[str, EffectiveCostEvaluationResult] = {}
        inputs = tuple(
            CandidatePlanConstructionInput(
                plan_id=plan.plan_id,
                inconvenience_penalty_units=plan.inconvenience_penalty_units,
                retailer_preference_priority=plan.retailer_preference_priority,
                candidate_item_allocations=enumeration.combinations[plan.combination_index],
                retailer_allocations=plan.retailer_allocations,
                checkout_groups=plan.checkout_groups,
                effective_cost_evaluation_reference=self._ece_reference(
                    plan, request, resolved_evaluations
                ),
                effective_cost_evaluation=self._ece_result(
                    plan, request, resolved_evaluations
                ),
                feasibility=plan.feasibility,
                feasibility_evidence=plan.feasibility_evidence,
            )
            for plan in request.plans
        )
        optimization_request = CartOptimizationRequest(
            request_id=request.request_id,
            optimization_policy_version=request.optimization_policy_version,
            cart_items=tuple(
                CartItemRequest(
                    item_id=item.item_id,
                    canonical_variant_id=item.canonical_variant_id,
                    quantity=item.quantity,
                )
                for item in request.discovery.items
            ),
            candidate_plan_coverage={
                "state": "complete",
                "scope_reference": request.request_id,
                "candidate_set_reference": request.request_id,
                "coverage_basis": "cart-planning",
                "validation_reference": request.request_id,
            },
        )
        attached = self._construction.attach_to_request(optimization_request, inputs)
        result = self._optimize(attached)
        logger.info(
            "cart_planning_completed request_id=%s ece_count=%s chosen_plan_id=%s",
            request.request_id,
            len(attached.effective_cost_evaluations),
            result.chosen_plan_id,
        )
        return result

    def _ece_result(
        self,
        plan: SuppliedPlan,
        request: CartPlanningRequest,
        resolved: dict[str, EffectiveCostEvaluationResult],
    ) -> EffectiveCostEvaluationResult:
        if plan.plan_id in resolved:
            return resolved[plan.plan_id]
        observation = request.checkout_observations.get(plan.plan_id)
        if observation is None and plan.effective_cost_evaluation is None:
            observation = self._checkout_provider.get_observation(
                plan_id=plan.plan_id, request_id=request.request_id
            )
            if observation is None:
                raise PlanningProviderUnavailable(
                    f"checkout observation is unavailable for plan {plan.plan_id}"
                )
        if observation is not None:
            if plan.effective_cost_evaluation is not None:
                raise ValueError(
                    f"conflicting precomputed ECE and checkout observation for plan {plan.plan_id}"
                )
            result = self._cost_intelligence.evaluate_observation(observation)
            resolved[plan.plan_id] = result
            return result
        if plan.effective_cost_evaluation is None:
            raise ValueError(f"missing ECE input for plan {plan.plan_id}")
        resolved[plan.plan_id] = plan.effective_cost_evaluation
        return resolved[plan.plan_id]

    def _ece_reference(
        self,
        plan: SuppliedPlan,
        request: CartPlanningRequest,
        resolved: dict[str, EffectiveCostEvaluationResult],
    ) -> EffectiveCostEvaluationReference:
        result = self._ece_result(plan, request, resolved)
        if plan.effective_cost_evaluation_reference is None:
            if (
                plan.effective_cost_evaluation is not None
                and plan.plan_id not in request.checkout_observations
            ):
                raise ValueError(f"missing ECE reference for plan {plan.plan_id}")
            return EffectiveCostEvaluationReference(
                effective_cost_evaluation_id=result.evaluation_id
            )
        if plan.effective_cost_evaluation_reference.effective_cost_evaluation_id != result.evaluation_id:
            raise ValueError(f"ECE reference does not match result for plan {plan.plan_id}")
        return plan.effective_cost_evaluation_reference

    @staticmethod
    def _validate_observation_keys(request: CartPlanningRequest) -> None:
        plan_ids = {plan.plan_id for plan in request.plans}
        unknown = sorted(set(request.checkout_observations) - plan_ids)
        if unknown:
            raise ValueError(
                "checkout observations reference unknown plans: " + ", ".join(unknown)
            )

    def _optimize(self, request: CartOptimizationRequest) -> CartOptimizationResult:
        from app.cart_optimization.service import CartOptimizationService

        return CartOptimizationService().optimize(request)

    def _enrich_sets(
        self,
        result: CartCandidateDiscoveryResult,
        contexts: tuple[SuppliedCandidateContext, ...],
    ) -> list[CandidateAllocationSet]:
        by_key = {context.key: context for context in contexts}
        if len(by_key) != len(contexts):
            raise ValueError("duplicate candidate context identities are invalid")
        sets: list[CandidateAllocationSet] = []
        for item in result.items:
            allocations = []
            for candidate in item.candidates:
                context = by_key.get(self._key(item, candidate))
                if context is None:
                    key = self._key(item, candidate)
                    raise ValueError(
                        "missing candidate context for "
                        f"{key.item_id}/{key.platform}/{key.platform_listing_id}/{key.observation_id}"
                    )
                enriched = self._enrichment.enrich(
                    item,
                    candidate,
                    CandidateAllocationEnrichment(
                        item_id=item.item_id,
                        canonical_product_id=item.canonical_product_id,
                        canonical_variant_id=item.canonical_variant_id,
                        quantity=item.quantity,
                        retailer_id=context.retailer_id,
                        checkout_group_id=context.checkout_group_id,
                    ),
                )
                allocations.append(enriched.allocation)
            sets.append(
                CandidateAllocationSet(
                    item_id=item.item_id,
                    canonical_variant_id=item.canonical_variant_id,
                    quantity=item.quantity,
                    candidates=tuple(allocations),
                )
            )
            if not allocations:
                raise ValueError(
                    f"no allocation-ready candidates for logical item {item.item_id}"
                )
        return sets

    @staticmethod
    def _key(item: CartCandidateDiscoveryItem, candidate: PersistedListingCandidate) -> CandidateKey:
        return CandidateKey(
            item_id=item.item_id,
            platform=candidate.platform,
            platform_listing_id=candidate.platform_listing_id,
            observation_id=candidate.observation_id,
        )
