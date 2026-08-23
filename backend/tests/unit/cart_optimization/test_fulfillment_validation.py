from __future__ import annotations

import pytest

from app.cart_optimization.enums import CoverageState, PlanFeasibility
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.types import (
    CandidateItemAllocation,
    CandidatePlan,
    CandidatePlanCoverage,
    CartItemRequest,
    CartOptimizationRequest,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import TaxStatus
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation


def _allocation(
    *, item_id: str = "item-1", variant_id: str = "variant-1", quantity: int = 1,
    checkout_group_id: str = "checkout-1",
) -> CandidateItemAllocation:
    return CandidateItemAllocation.from_comparable_observation(
        item_id=item_id,
        canonical_variant_id=variant_id,
        quantity=quantity,
        retailer_id="retailer-1",
        checkout_group_id=checkout_group_id,
        observation=ComparableRetailObservation(
            observation_id=f"observation-{item_id}-{variant_id}-{checkout_group_id}",
            platform="blinkit",
            platform_listing_id=f"listing-{item_id}-{variant_id}",
            canonical_product_id="product-1",
            canonical_variant_id=variant_id,
            observed_selling_price=Money(currency="INR", minor_units=100),
            tax_status=TaxStatus.INCLUDED,
        ),
    )


def _request(allocations: tuple[CandidateItemAllocation, ...], *, quantity: int = 1,
             variant_id: str = "variant-1") -> CartOptimizationRequest:
    plan = CandidatePlan.from_candidate_allocations(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        candidate_item_allocations=allocations,
        checkout_groups=tuple(
            CheckoutGroup(
                checkout_group_id=group_id,
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            )
            for group_id in sorted({allocation.checkout_group_id for allocation in allocations})
        ),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id=variant_id, quantity=quantity),),
        candidate_plans=(plan,),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE,
            scope_reference="scope-1",
            candidate_set_reference="set-1",
            coverage_basis="test",
            validation_reference="validation-1",
        ),
        effective_cost_evaluations=(
            EffectiveCostEvaluationResult(
                evaluation_id="eval-1",
                context_id="context-1",
                effective_cost=Money(currency="INR", minor_units=100),
            ),
        ),
    )


def test_exact_single_allocation_is_accepted() -> None:
    result = CartOptimizationService().optimize(_request((_allocation(),)))
    assert result.chosen_plan_id == "plan-1"


def test_split_allocations_are_accepted_when_the_sum_matches() -> None:
    result = CartOptimizationService().optimize(
        _request((_allocation(quantity=1, checkout_group_id="a"), _allocation(quantity=2, checkout_group_id="b")), quantity=3)
    )
    assert result.chosen_plan_id == "plan-1"


def test_multiple_allocations_may_share_a_declared_checkout_group() -> None:
    result = CartOptimizationService().optimize(
        _request(
            (
                _allocation(quantity=1, checkout_group_id="same"),
                _allocation(quantity=2, checkout_group_id="same"),
            ),
            quantity=3,
        )
    )
    assert result.chosen_plan_id == "plan-1"


@pytest.mark.parametrize(
    ("allocation_quantity", "requested_quantity"),
    ((1, 2), (2, 1)),
)
def test_mismatched_fulfillment_is_infeasible(
    allocation_quantity: int, requested_quantity: int
) -> None:
    result = CartOptimizationService().optimize(
        _request((_allocation(quantity=allocation_quantity),), quantity=requested_quantity)
    )
    assert result.outcome.value == "infeasible"
    assert result.chosen_plan_id is None


def test_variant_mismatch_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown cart item or variant"):
        CartOptimizationService().optimize(
            _request((_allocation(variant_id="variant-2"),), variant_id="variant-1")
        )


def test_allocation_free_plan_with_requested_items_is_infeasible() -> None:
    request = _request((_allocation(),)).model_copy(
        update={
            "candidate_plans": (
                CandidatePlan(
                    plan_id="plan-empty",
                    inconvenience_penalty_units=0,
                    retailer_preference_priority=0,
                    effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                        effective_cost_evaluation_id="eval-1"
                    ),
                    feasibility=PlanFeasibility.FEASIBLE,
                ),
            )
        }
    )
    result = CartOptimizationService().optimize(request)
    assert result.outcome.value == "infeasible"
    assert result.chosen_plan_id is None


def test_identical_allocation_identity_is_rejected() -> None:
    allocation = _allocation()
    with pytest.raises(ValueError, match="duplicate item allocation"):
        CartOptimizationService().optimize(_request((allocation, allocation)))
