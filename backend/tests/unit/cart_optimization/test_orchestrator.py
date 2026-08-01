from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.cart_optimization.enums import CoverageState, OptimizationOutcome, PlanFeasibility
from app.cart_optimization.orchestrator import CartOptimizationOrchestrator
from app.cart_optimization.types import (
    CandidatePlan,
    CandidatePlanCoverage,
    CartOptimizationRequest,
    CartOptimizationResult,
    EffectiveCostEvaluationReference,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult


def _request() -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        candidate_plans=(
            CandidatePlan(
                plan_id="plan-1",
                inconvenience_penalty_units=0,
                retailer_preference_priority=0,
                effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                    effective_cost_evaluation_id="eval-1"
                ),
                feasibility=PlanFeasibility.FEASIBLE,
            ),
        ),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE,
            scope_reference="scope-1",
            candidate_set_reference="plans-1",
            coverage_basis="test",
            validation_reference="validation-1",
        ),
        effective_cost_evaluations=(
            EffectiveCostEvaluationResult(evaluation_id="eval-1", context_id="context-1"),
        ),
    )


def _result() -> CartOptimizationResult:
    return CartOptimizationResult(
        optimization_id="cartopt-1",
        request_id="request-1",
        outcome=OptimizationOutcome.UNRESOLVED,
    )


def test_delegates_once_and_returns_result_unchanged() -> None:
    request = _request()
    result = _result()
    service = Mock()
    service.optimize.return_value = result

    actual = CartOptimizationOrchestrator(service).optimize(request)

    assert actual is result
    service.optimize.assert_called_once_with(request)


def test_repeated_execution_is_deterministic_and_does_not_mutate_request() -> None:
    request = _request()
    result = _result()
    service = Mock()
    service.optimize.return_value = result
    orchestrator = CartOptimizationOrchestrator(service)

    first = orchestrator.optimize(request)
    second = orchestrator.optimize(request)

    assert first == second
    assert request.request_id == "request-1"
    assert service.optimize.call_count == 2


def test_service_exception_propagates_unchanged() -> None:
    error = RuntimeError("service failure")
    service = Mock()
    service.optimize.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        CartOptimizationOrchestrator(service).optimize(_request())

    assert raised.value is error


def test_orchestrator_does_not_transform_immutable_result() -> None:
    result = _result()
    service = Mock()
    service.optimize.return_value = result

    actual = CartOptimizationOrchestrator(service).optimize(_request())

    assert actual.model_dump(mode="json") == result.model_dump(mode="json")
    with pytest.raises((TypeError, ValidationError)):
        actual.request_id = "changed"  # type: ignore[misc]
