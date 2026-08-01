import pytest
from pydantic import ValidationError

from app.cart_optimization.enums import (
    CoverageState,
    OptimizationOutcome,
    PlanFeasibility,
)
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.types import (
    CandidatePlan,
    CandidatePlanCoverage,
    CartItemRequest,
    CartOptimizationRequest,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _evaluation(
    evaluation_id: str,
    amount: int | None,
    *,
    currency: str = "INR",
    unknown_components: tuple[str, ...] = (),
) -> EffectiveCostEvaluationResult:
    return EffectiveCostEvaluationResult(
        evaluation_id=evaluation_id,
        context_id=f"context-{evaluation_id}",
        effective_cost=Money(currency=currency, minor_units=amount) if amount is not None else None,
        unknown_components=unknown_components,
        evidence_references=(
            EvidenceReference(source_type="effective_cost", source_id=evaluation_id),
        ),
    )


def _plan(
    plan_id: str,
    evaluation_id: str,
    *,
    feasibility: PlanFeasibility = PlanFeasibility.FEASIBLE,
    checkout_groups: int = 1,
    inconvenience_penalty_units: int = 0,
    retailer_preference_priority: int = 0,
    unknown_components: tuple[str, ...] = (),
) -> CandidatePlan:
    return CandidatePlan(
        plan_id=plan_id,
        inconvenience_penalty_units=inconvenience_penalty_units,
        retailer_preference_priority=retailer_preference_priority,
        checkout_groups=tuple(
            CheckoutGroup(
                checkout_group_id=f"{plan_id}-checkout-{index}",
                retailer_id=f"retailer-{index}",
                effective_cost_evaluation_id=evaluation_id,
            )
            for index in range(checkout_groups)
        ),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id=evaluation_id
        ),
        feasibility=feasibility,
        unknown_components=unknown_components,
        provenance_references=(
            EvidenceReference(source_type="candidate_plan", source_id=plan_id),
        ),
    )


def _coverage(state: CoverageState = CoverageState.COMPLETE) -> CandidatePlanCoverage:
    return CandidatePlanCoverage(
        state=state,
        scope_reference="scope-1" if state is CoverageState.COMPLETE else None,
        candidate_set_reference="candidate-set-1" if state is CoverageState.COMPLETE else None,
        coverage_basis="unit-test" if state is CoverageState.COMPLETE else None,
        validation_reference="coverage-validation-1" if state is CoverageState.COMPLETE else None,
        rationale=() if state is CoverageState.COMPLETE else (f"coverage is {state.value}",),
    )


def _request(
    *,
    candidate_plans: tuple[CandidatePlan, ...],
    evaluations: tuple[EffectiveCostEvaluationResult, ...],
    coverage_state: CoverageState = CoverageState.COMPLETE,
    policy_version: str = "policy-v1",
) -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version=policy_version,
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
        ),
        candidate_plans=candidate_plans,
        candidate_plan_coverage=_coverage(coverage_state),
        effective_cost_evaluations=evaluations,
        provenance_references=(
            EvidenceReference(source_type="request", source_id="request-1"),
        ),
    )


def test_complete_coverage_selects_highest_ranked_feasible_plan() -> None:
    expensive = _plan("plan-expensive", "eval-expensive")
    cheap = _plan("plan-cheap", "eval-cheap")
    request = _request(
        candidate_plans=(expensive, cheap),
        evaluations=(_evaluation("eval-expensive", 1200), _evaluation("eval-cheap", 900)),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-cheap"
    assert result.ranked_plan_ids == ("plan-cheap", "plan-expensive")


def test_partial_unknown_and_invalid_coverage_block_recommendation() -> None:
    plan = _plan("plan-1", "eval-1")
    evaluation = _evaluation("eval-1", 1000)

    for state in (CoverageState.PARTIAL, CoverageState.UNKNOWN, CoverageState.INVALID):
        request = _request(
            candidate_plans=(plan,),
            evaluations=(evaluation,),
            coverage_state=state,
        )
        result = CartOptimizationService().optimize(request)

        assert result.outcome is OptimizationOutcome.UNRESOLVED
        assert result.chosen_plan is None
        assert result.ranked_plan_ids == ("plan-1",)


def test_all_plans_infeasible_returns_infeasible() -> None:
    plan = _plan("plan-1", "eval-1", feasibility=PlanFeasibility.INFEASIBLE)
    request = _request(candidate_plans=(plan,), evaluations=(_evaluation("eval-1", 1000),))

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.INFEASIBLE
    assert result.chosen_plan_id is None
    assert result.rejected_plans[0].plan_id == "plan-1"


def test_unresolved_plan_blocks_recommendation_and_preserves_unknowns() -> None:
    feasible = _plan("plan-feasible", "eval-feasible")
    unresolved = _plan(
        "plan-unresolved",
        "eval-unresolved",
        feasibility=PlanFeasibility.UNRESOLVED,
        unknown_components=("availability",),
    )
    request = _request(
        candidate_plans=(feasible, unresolved),
        evaluations=(
            _evaluation("eval-feasible", 1000),
            _evaluation("eval-unresolved", None, unknown_components=("effective_cost",)),
        ),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.UNRESOLVED
    assert result.chosen_plan_id is None
    assert result.ranked_plan_ids == ("plan-feasible",)
    assert result.unknowns == ("availability", "effective_cost")


def test_invalid_plan_blocks_optimization() -> None:
    plan = _plan("plan-1", "eval-1", feasibility=PlanFeasibility.INVALID)
    request = _request(candidate_plans=(plan,), evaluations=(_evaluation("eval-1", 1000),))

    with pytest.raises(ValueError, match="invalid candidate plan"):
        CartOptimizationService().optimize(request)


def test_duplicate_plan_ids_fail_closed() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"), _plan("plan-1", "eval-2")),
        evaluations=(_evaluation("eval-1", 1000), _evaluation("eval-2", 900)),
    )

    with pytest.raises(ValueError, match="duplicate candidate plan IDs"):
        CartOptimizationService().optimize(request)


def test_unsupported_policy_version_fails_closed() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
        policy_version="unsupported-policy",
    )

    with pytest.raises(ValueError, match="unsupported optimization policy version"):
        CartOptimizationService().optimize(request)


def test_missing_or_unknown_linked_effective_cost_for_feasible_plan_fails_closed() -> None:
    missing_request = _request(
        candidate_plans=(_plan("plan-1", "missing-eval"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    unknown_request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", None, unknown_components=("effective_cost",)),),
    )

    with pytest.raises(ValueError, match="missing effective-cost evaluation"):
        CartOptimizationService().optimize(missing_request)
    with pytest.raises(ValueError, match="known linked effective cost"):
        CartOptimizationService().optimize(unknown_request)


def test_currency_mismatch_fails_closed() -> None:
    request = _request(
        candidate_plans=(_plan("plan-inr", "eval-inr"), _plan("plan-usd", "eval-usd")),
        evaluations=(_evaluation("eval-inr", 1000), _evaluation("eval-usd", 900, currency="USD")),
    )

    with pytest.raises(ValueError, match="currencies must match"):
        CartOptimizationService().optimize(request)


def test_ranking_tie_breakers_are_deterministic() -> None:
    by_checkout_count = _plan("plan-b", "eval-b", checkout_groups=2)
    by_penalty = _plan("plan-c", "eval-c", inconvenience_penalty_units=5)
    by_priority = _plan("plan-d", "eval-d", retailer_preference_priority=1)
    by_plan_id = _plan("plan-a", "eval-a")
    request = _request(
        candidate_plans=(by_checkout_count, by_penalty, by_priority, by_plan_id),
        evaluations=(
            _evaluation("eval-b", 1000),
            _evaluation("eval-c", 1000),
            _evaluation("eval-d", 1000),
            _evaluation("eval-a", 1000),
        ),
    )

    result = CartOptimizationService().optimize(request)

    assert result.ranked_plan_ids == ("plan-d", "plan-a", "plan-c", "plan-b")
    assert result.chosen_plan_id == "plan-d"


def test_deterministic_replay_and_optimization_id_stability() -> None:
    request = _request(
        candidate_plans=(_plan("plan-2", "eval-2"), _plan("plan-1", "eval-1")),
        evaluations=(_evaluation("eval-1", 900), _evaluation("eval-2", 1100)),
    )
    service = CartOptimizationService()

    first = service.optimize(request)
    second = service.optimize(request)

    assert first == second
    assert first.optimization_id == second.optimization_id


def test_provenance_is_preserved_and_deduplicated_by_identity() -> None:
    shared = EvidenceReference(source_type="shared", source_id="same")
    plan = _plan("plan-1", "eval-1").model_copy(
        update={"provenance_references": (shared, shared)}
    )
    request = CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        candidate_plans=(plan,),
        candidate_plan_coverage=_coverage(),
        effective_cost_evaluations=(
            EffectiveCostEvaluationResult(
                evaluation_id="eval-1",
                context_id="context-1",
                effective_cost=Money(currency="INR", minor_units=1000),
                evidence_references=(shared,),
            ),
        ),
        provenance_references=(shared,),
    )

    result = CartOptimizationService().optimize(request)

    assert result.provenance_references == (shared,)


def test_result_and_request_are_immutable() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    result = CartOptimizationService().optimize(request)

    with pytest.raises((TypeError, ValidationError)):
        request.request_id = "changed"  # type: ignore[misc]
    with pytest.raises((TypeError, ValidationError)):
        result.request_id = "changed"  # type: ignore[misc]
