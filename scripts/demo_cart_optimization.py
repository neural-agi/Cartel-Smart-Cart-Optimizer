from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.cart_optimization.enums import CoverageState, PlanFeasibility
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.types import (
    CandidatePlan,
    CandidatePlanCoverage,
    CartItemRequest,
    CartOptimizationRequest,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    ItemAllocation,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money


def _plan(plan_id: str, evaluation_id: str, amount: int) -> tuple[CandidatePlan, EffectiveCostEvaluationResult]:
    plan = CandidatePlan(
        plan_id=plan_id,
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id=f"{plan_id}-checkout",
                retailer_id=f"{plan_id}-retailer",
                effective_cost_evaluation_id=evaluation_id,
            ),
        ),
        item_allocations=(
            ItemAllocation(
                item_id="milk-line",
                canonical_variant_id="amul-taaza-toned-milk-500ml",
                quantity=2,
                retailer_id=f"{plan_id}-retailer",
                checkout_group_id=f"{plan_id}-checkout",
            ),
        ),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id=evaluation_id
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )
    evaluation = EffectiveCostEvaluationResult(
        evaluation_id=evaluation_id,
        context_id=f"{evaluation_id}-context",
        effective_cost=Money(currency="INR", minor_units=amount),
    )
    return plan, evaluation


def _request() -> CartOptimizationRequest:
    first_plan, first_evaluation = _plan("blinkit-plan", "blinkit-effective-cost", 12800)
    second_plan, second_evaluation = _plan("zepto-plan", "zepto-effective-cost", 12100)
    return CartOptimizationRequest(
        request_id="demo-cart-optimization-request",
        optimization_policy_version="policy-v1",
        cart_items=(
            CartItemRequest(
                item_id="milk-line",
                canonical_variant_id="amul-taaza-toned-milk-500ml",
                quantity=2,
            ),
        ),
        candidate_plans=(first_plan, second_plan),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE,
            scope_reference="demo-scope",
            candidate_set_reference="demo-candidate-set",
            coverage_basis="demo fixture",
            validation_reference="demo-validation",
        ),
        effective_cost_evaluations=(first_evaluation, second_evaluation),
    )


def main() -> None:
    request = _request()
    service = CartOptimizationService()

    first = service.optimize(request)
    second = service.optimize(request)

    print("Optimization ID:")
    print(first.optimization_id)
    print()
    print("Outcome:")
    print(first.outcome.value)
    print()
    print("Chosen Plan ID:")
    print(first.chosen_plan_id)
    print()
    print("Ranked Plans:")
    for index, plan_id in enumerate(first.ranked_plan_ids, start=1):
        print(f"{index}. {plan_id}")
    print()
    print("Replay Equality:")
    print(first == second)


if __name__ == "__main__":
    main()
