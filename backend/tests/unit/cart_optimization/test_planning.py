from unittest.mock import Mock

from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.planning import (
    CandidateKey,
    CartPlanningRequest,
    CartPlanningService,
    SuppliedCandidateContext,
    SuppliedPlan,
)
from app.cart_optimization.types import CheckoutGroup, EffectiveCostEvaluationReference
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.types import NormalizedObservation
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryResult,
    CartCandidateDiscoveryStatus,
    PersistedCandidateReadiness,
    PersistedListingCandidate,
)
import pytest


def test_planning_service_connects_discovery_to_optimization() -> None:
    candidate = PersistedListingCandidate(
        platform="platform-1",
        platform_listing_id="listing-1",
        canonical_product_id="product-1",
        canonical_variant_id="variant-1",
        observation_id="observation-1",
        observation=NormalizedObservation.model_construct(
            observed_selling_price=Money(currency="INR", minor_units=100),
        ),
        readiness=PersistedCandidateReadiness.ready_for_allocation,
    )
    discovery_item = CartCandidateDiscoveryItem(
        item_id="item-1",
        quantity=1,
        canonical_product_id="product-1",
        canonical_variant_id="variant-1",
        status=CartCandidateDiscoveryStatus.candidates_available,
        candidates=(candidate,),
    )
    discovery = Mock()
    discovery.discover.return_value = CartCandidateDiscoveryResult(items=(discovery_item,))
    service = CartPlanningService(discovery=discovery)
    request = CartPlanningRequest(
        discovery=CartCandidateDiscoveryRequest(items=(
            {"item_id": "item-1", "quantity": 1, "canonical_product_id": "product-1", "canonical_variant_id": "variant-1"},
        )),
        candidate_contexts=(SuppliedCandidateContext(
            key=CandidateKey(
                item_id="item-1",
                platform="platform-1",
                platform_listing_id="listing-1",
                observation_id="observation-1",
            ),
            retailer_id="retailer-explicit",
            checkout_group_id="group-explicit",
        ),),
        plans=(SuppliedPlan(
            plan_id="plan-supplied-1",
            combination_index=0,
            inconvenience_penalty_units=4,
            retailer_preference_priority=8,
            checkout_groups=(CheckoutGroup(
                checkout_group_id="group-explicit",
                retailer_id="retailer-explicit",
                effective_cost_evaluation_id="ece-1",
            ),),
            effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                effective_cost_evaluation_id="ece-1"
            ),
            effective_cost_evaluation=EffectiveCostEvaluationResult(
                evaluation_id="ece-1",
                context_id="context-1",
                effective_cost=Money(currency="INR", minor_units=100),
            ),
            feasibility=PlanFeasibility.FEASIBLE,
            feasibility_evidence=("upstream-evidence-1",),
        ),),
        request_id="planning-request-1",
        optimization_policy_version="policy-v1",
    )

    result = service.plan(request)

    discovery.discover.assert_called_once()
    assert result.chosen_plan_id == "plan-supplied-1"
    assert result.chosen_plan is not None
    assert result.chosen_plan.item_allocations[0].retailer_id == "retailer-explicit"
    assert result.chosen_plan.item_allocations[0].checkout_group_id == "group-explicit"
    assert result.chosen_plan.effective_cost_evaluation_reference.effective_cost_evaluation_id == "ece-1"


def test_planning_limits_reject_candidate_explosion() -> None:
    candidate = PersistedListingCandidate(
        platform="platform-1", platform_listing_id="listing-1",
        canonical_product_id="product-1", canonical_variant_id="variant-1",
        observation_id="observation-1",
        observation=NormalizedObservation.model_construct(
            observed_selling_price=Money(currency="INR", minor_units=100)
        ),
        readiness=PersistedCandidateReadiness.ready_for_allocation,
    )
    item = CartCandidateDiscoveryItem(
        item_id="item-1", quantity=1, canonical_product_id="product-1",
        canonical_variant_id="variant-1",
        status=CartCandidateDiscoveryStatus.candidates_available,
        candidates=(candidate,),
    )
    discovery = Mock()
    discovery.discover.return_value = CartCandidateDiscoveryResult(items=(item,))
    request = CartPlanningRequest(
        discovery=CartCandidateDiscoveryRequest(items=({
            "item_id": "item-1", "quantity": 1,
            "canonical_product_id": "product-1", "canonical_variant_id": "variant-1",
        },)),
        candidate_contexts=(SuppliedCandidateContext(
            key=CandidateKey(item_id="item-1", platform="platform-1",
                             platform_listing_id="listing-1", observation_id="observation-1"),
            retailer_id="retailer-1", checkout_group_id="group-1",
        ),), plans=(), request_id="request-1", optimization_policy_version="v1",
    )
    with pytest.raises(ValueError, match="candidate limit"):
        CartPlanningService(discovery=discovery, max_candidates_per_item=0).plan(request)
