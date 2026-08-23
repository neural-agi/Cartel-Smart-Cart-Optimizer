from app.cart_optimization.planning import CartPlanningRequest
from app.cart_optimization.serialization import CartPlanningSerialization
from app.cart_optimization.enums import OptimizationOutcome
from app.cart_optimization.types import CartOptimizationResult


def test_planning_request_serialization_is_canonical_and_validated() -> None:
    request = CartPlanningRequest(
        discovery={"items": []},
        candidate_contexts=(),
        plans=(),
        request_id="request-1",
        optimization_policy_version="policy-v1",
    )

    first = CartPlanningSerialization.request_json(request)
    second = CartPlanningSerialization.request_json(
        CartPlanningSerialization.request_from_json(first)
    )

    assert first == second
    assert CartPlanningSerialization.request_from_json(first) == request


def test_optimization_result_serialization_round_trips_without_loss() -> None:
    result = CartOptimizationResult(
        optimization_id="optimization-1",
        request_id="request-1",
        outcome=OptimizationOutcome.UNRESOLVED,
        rejected_plans=(),
        chosen_plan_id=None,
        chosen_plan=None,
        ranked_plan_ids=(),
        provenance_references=(),
    )

    payload = CartPlanningSerialization.result_json(result)

    assert CartPlanningSerialization.result_from_json(payload) == result
