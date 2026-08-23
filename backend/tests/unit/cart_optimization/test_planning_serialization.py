from datetime import datetime, timezone

from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.planning import (
    CandidateKey,
    CartPlanningRequest,
    SuppliedCandidateContext,
    SuppliedPlan,
)
from app.cart_optimization.types import CheckoutGroup, EffectiveCostEvaluationReference
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.shared.money import Money


def test_planning_request_round_trip_preserves_explicit_inputs() -> None:
    request = CartPlanningRequest(
        discovery={"items": [{
            "item_id": "item-1",
            "quantity": 2,
            "canonical_product_id": "product-1",
            "canonical_variant_id": "variant-1",
        }]},
        candidate_contexts=(SuppliedCandidateContext(
            key=CandidateKey(
                item_id="item-1",
                platform="BLINKIT",
                platform_listing_id="listing-1",
                observation_id="observation-1",
            ),
            retailer_id="retailer-1",
            checkout_group_id="group-1",
        ),),
        plans=(SuppliedPlan(
            plan_id="plan-1",
            combination_index=0,
            inconvenience_penalty_units=3,
            retailer_preference_priority=7,
            checkout_groups=(CheckoutGroup(
                checkout_group_id="group-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="ece-1",
            ),),
            effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                effective_cost_evaluation_id="ece-1"
            ),
            effective_cost_evaluation=EffectiveCostEvaluationResult(
                evaluation_id="ece-1",
                context_id="context-1",
                effective_cost=Money(currency="INR", minor_units=200),
            ),
            feasibility=PlanFeasibility.FEASIBLE,
            feasibility_evidence=("feasibility-evidence-1",),
        ),),
        request_id="request-1",
        optimization_policy_version="policy-v1",
        checkout_observations={
            "plan-1": CheckoutObservation.model_construct(
                platform="checkout",
                source_artifact_reference="artifact-1",
                capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                parser_version="checkout-v1",
                evidence_references=tuple(),
                totals=tuple(),
            )
        },
    )

    restored = CartPlanningRequest.model_validate_json(request.model_dump_json())

    assert restored == request
    assert restored.request_id == "request-1"
    assert restored.plans[0].plan_id == "plan-1"
    assert restored.candidate_contexts[0].checkout_group_id == "group-1"
    assert restored.plans[0].effective_cost_evaluation_reference.effective_cost_evaluation_id == "ece-1"
