from app.cart_optimization.orchestrator import CartOptimizationOrchestrator
from app.cart_optimization.types import (
    CandidatePlan,
    CandidatePlanCoverage,
    CartOptimizationRequest,
    EffectiveCostEvaluationReference,
)
from app.cart_optimization.enums import CoverageState, PlanFeasibility
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money


def build_request() -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="demo-request",
        optimization_policy_version="policy-v1",
        candidate_plans=(
            CandidatePlan(
                plan_id="demo-plan",
                inconvenience_penalty_units=0,
                retailer_preference_priority=0,
                effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                    effective_cost_evaluation_id="demo-evaluation"
                ),
                feasibility=PlanFeasibility.FEASIBLE,
            ),
        ),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE,
            scope_reference="demo-scope",
            candidate_set_reference="demo-candidates",
            coverage_basis="deterministic demo",
            validation_reference="demo-validation",
        ),
        effective_cost_evaluations=(
            EffectiveCostEvaluationResult(
                evaluation_id="demo-evaluation",
                context_id="demo-context",
                effective_cost=Money(currency="INR", minor_units=1000),
            ),
        ),
    )


def main() -> None:
    orchestrator = CartOptimizationOrchestrator()
    request = build_request()
    first = orchestrator.optimize(request)
    second = orchestrator.optimize(request)

    print(f"Optimization ID: {first.optimization_id}")
    print(f"Optimization Outcome: {first.outcome.value}")
    print(f"Chosen Plan ID: {first.chosen_plan_id}")
    print(f"Replay Equality: {first == second}")


if __name__ == "__main__":
    main()
