from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.cart_optimization import (
    BudgetConstraint,
    CandidatePlan,
    CandidatePlanCoverage,
    CartItemRequest,
    CartOptimizationRequest,
    CartOptimizationResult,
    ConstraintHardness,
    CoverageState,
    OptimizationOutcome,
    PlanFeasibility,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money


def _coverage() -> CandidatePlanCoverage:
    return CandidatePlanCoverage(
        state=CoverageState.COMPLETE,
        scope_reference="scope-1",
        candidate_set_reference="plans-1",
        coverage_basis="fixture",
        validation_reference="validation-1",
    )


def _plan() -> CandidatePlan:
    return CandidatePlan(plan_id="plan-1", feasibility=PlanFeasibility.FEASIBLE)


def _request() -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
        ),
        candidate_plans=(_plan(),),
        candidate_plan_coverage=_coverage(),
        constraints=(
            BudgetConstraint(
                amount=Money(currency="INR", minor_units=1000),
                hardness=ConstraintHardness.HARD,
            ),
        ),
        effective_cost_evaluations=(
            EffectiveCostEvaluationResult(evaluation_id="eval-1", context_id="context-1"),
        ),
    )


def test_request_is_immutable_and_requires_policy_version() -> None:
    request = _request()
    assert request.optimization_policy_version == "policy-v1"

    with pytest.raises((TypeError, ValidationError)):
        request.request_id = "changed"  # type: ignore[misc]

    with pytest.raises(ValidationError):
        CartOptimizationRequest(
            request_id="request-1",
            candidate_plan_coverage=_coverage(),
        )


def test_result_is_immutable_and_optional_fields_are_empty_by_default() -> None:
    result = CartOptimizationResult(
        optimization_id="optimization-1",
        request_id="request-1",
        outcome=OptimizationOutcome.UNRESOLVED,
    )
    assert result.chosen_plan is None
    assert result.ranked_plan_ids == ()

    with pytest.raises((TypeError, ValidationError)):
        result.request_id = "changed"  # type: ignore[misc]


def test_coverage_supports_all_frozen_states() -> None:
    for state in CoverageState:
        coverage = CandidatePlanCoverage(
            state=state,
            scope_reference="scope-1" if state is CoverageState.COMPLETE else None,
            candidate_set_reference="plans-1" if state is CoverageState.COMPLETE else None,
            coverage_basis="fixture" if state is CoverageState.COMPLETE else None,
            validation_reference="validation-1" if state is CoverageState.COMPLETE else None,
            rationale=() if state is CoverageState.COMPLETE else (state.value,),
        )
        assert coverage.state is state


def test_coverage_fails_closed_without_required_metadata_or_rationale() -> None:
    with pytest.raises(ValidationError):
        CandidatePlanCoverage(state=CoverageState.COMPLETE)
    with pytest.raises(ValidationError):
        CandidatePlanCoverage(state=CoverageState.UNKNOWN)


def test_candidate_plan_and_constraints_are_immutable() -> None:
    plan = _plan()
    constraint = BudgetConstraint(
        amount=Money(currency="INR", minor_units=500),
        hardness=ConstraintHardness.SOFT,
    )

    with pytest.raises((TypeError, ValidationError)):
        plan.plan_id = "changed"  # type: ignore[misc]
    with pytest.raises((TypeError, ValidationError)):
        constraint.hardness = ConstraintHardness.HARD  # type: ignore[misc]


def test_serialization_is_deterministic_and_preserves_identity_fields() -> None:
    first = _request()
    second = _request()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.request_id == "request-1"
    assert first.optimization_policy_version == "policy-v1"
    assert first.candidate_plans[0].plan_id == "plan-1"
