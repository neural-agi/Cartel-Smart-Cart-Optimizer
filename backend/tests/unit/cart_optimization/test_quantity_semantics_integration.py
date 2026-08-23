"""Integration tests for quantity-resolution semantics in Cart Optimization.

These tests verify that VariantQuantitySemantics, when attached to
CandidateItemAllocations and retained by CandidatePlan, correctly
governs plan effectiveness without modifying ranking semantics for
equally valid plans.

Architectural decisions verified:
  - UNRESOLVED quantity → plan treated as UNRESOLVED (blocks recommendation)
  - UNSUPPORTED quantity → plan treated as INFEASIBLE (deterministically disproven)
  - RESOLVED quantity → plan eligibility unchanged (backward compatible)
  - Plans without quantity_semantics remain backward compatible
  - Provenance bridge remains intact
  - ItemAllocation remains unchanged
  - Ranking semantics unchanged for equally valid plans
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.cart_optimization.enums import (
    CoverageState,
    OptimizationOutcome,
    PlanFeasibility,
)
from app.cart_optimization.quantity_semantics import (
    QuantityResolutionStatus,
    VariantQuantityResolutionService,
    VariantQuantitySemantics,
)
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.types import (
    CandidateItemAllocation,
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
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation
from app.data_ingestion.enums import TaxStatus
from app.product_intelligence.models import PackConfiguration, PackKind


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QS_SERVICE = VariantQuantityResolutionService()


def _observation(variant_id: str = "variant-1") -> ComparableRetailObservation:
    return ComparableRetailObservation(
        observation_id="observation-1",
        platform="BLINKIT",
        platform_listing_id="listing-1",
        canonical_product_id="product-1",
        canonical_variant_id=variant_id,
        observed_selling_price=Money(currency="INR", minor_units=10000),
        tax_status=TaxStatus.INCLUDED,
    )


def _allocation(
    *,
    item_id: str = "item-1",
    canonical_variant_id: str = "variant-1",
    quantity: int = 2,
    retailer_id: str = "BLINKIT",
    checkout_group_id: str = "checkout-1",
    observation: ComparableRetailObservation | None = None,
    quantity_semantics: VariantQuantitySemantics | None = None,
) -> CandidateItemAllocation:
    return CandidateItemAllocation(
        item_id=item_id,
        canonical_variant_id=canonical_variant_id,
        quantity=quantity,
        retailer_id=retailer_id,
        checkout_group_id=checkout_group_id,
        listing_provenance=CandidateItemAllocation.from_comparable_observation(
            item_id=item_id,
            canonical_variant_id=canonical_variant_id,
            quantity=quantity,
            retailer_id=retailer_id,
            checkout_group_id=checkout_group_id,
            observation=observation or _observation(canonical_variant_id),
        ).listing_provenance,
        quantity_semantics=quantity_semantics,
    )


def _resolved_semantics(
    variant_id: str = "variant-1", quantity: int = 2
) -> VariantQuantitySemantics:
    return _QS_SERVICE.resolve(
        canonical_variant_id=variant_id,
        requested_quantity=quantity,
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            pack_configuration_status="complete",
        ),
    )


def _unresolved_semantics(
    variant_id: str = "variant-1", quantity: int = 2
) -> VariantQuantitySemantics:
    return _QS_SERVICE.resolve(
        canonical_variant_id=variant_id,
        requested_quantity=quantity,
        pack_configuration=None,
    )


def _unsupported_semantics(
    variant_id: str = "variant-1", quantity: int = 2
) -> VariantQuantitySemantics:
    return _QS_SERVICE.resolve(
        canonical_variant_id=variant_id,
        requested_quantity=quantity,
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.combo,
            consumer_unit_count=3,
            pack_configuration_status="complete",
        ),
    )


def _plan(
    plan_id: str,
    eval_id: str,
    *,
    allocations: tuple[CandidateItemAllocation, ...] | None = None,
    feasibility: PlanFeasibility = PlanFeasibility.FEASIBLE,
) -> CandidatePlan:
    allocations = allocations or (_allocation(),)
    return CandidatePlan.from_candidate_allocations(
        plan_id=plan_id,
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        candidate_item_allocations=allocations,
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id=eval_id
        ),
        feasibility=feasibility,
    )


def _coverage(state: CoverageState = CoverageState.COMPLETE) -> CandidatePlanCoverage:
    if state is CoverageState.COMPLETE:
        return CandidatePlanCoverage(
            state=state,
            scope_reference="scope-1",
            candidate_set_reference="set-1",
            coverage_basis="unit-test",
            validation_reference="validation-1",
        )
    return CandidatePlanCoverage(state=state, rationale=(f"coverage is {state.value}",))


def _eval(
    evaluation_id: str,
    amount: int | None,
    *,
    currency: str = "INR",
) -> EffectiveCostEvaluationResult:
    return EffectiveCostEvaluationResult(
        evaluation_id=evaluation_id,
        context_id=f"context-{evaluation_id}",
        effective_cost=Money(currency=currency, minor_units=amount) if amount is not None else None,
    )


def _request(
    *,
    candidate_plans: tuple[CandidatePlan, ...],
    evaluations: tuple[EffectiveCostEvaluationResult, ...] = (),
) -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
        ),
        candidate_plans=candidate_plans,
        candidate_plan_coverage=_coverage(CoverageState.COMPLETE),
        effective_cost_evaluations=evaluations,
    )


# ---------------------------------------------------------------------------
# 1. RESOLVED quantity allows FEASIBLE plan state
# ---------------------------------------------------------------------------


def test_resolved_quantity_allows_feasible_plan_to_be_selected() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"


# ---------------------------------------------------------------------------
# 2. UNRESOLVED quantity is fail-closed (blocks recommendation, not error)
# ---------------------------------------------------------------------------


def test_unresolved_quantity_blocks_recommendation() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_unresolved_semantics()),),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.UNRESOLVED
    assert result.chosen_plan_id is None
    assert result.chosen_plan is None


def test_unresolved_quantity_plan_ranked_behind_feasible() -> None:
    unresolved_plan = _plan(
        "plan-unresolved",
        "eval-unresolved",
        allocations=(_allocation(quantity_semantics=_unresolved_semantics()),),
    )
    feasible_plan = _plan(
        "plan-feasible",
        "eval-feasible",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    request = _request(
        candidate_plans=(unresolved_plan, feasible_plan),
        evaluations=(
            _eval("eval-unresolved", 800),
            _eval("eval-feasible", 1000),
        ),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.UNRESOLVED
    assert result.chosen_plan_id is None
    assert result.ranked_plan_ids == ("plan-feasible",)
    assert "plan-unresolved" not in result.ranked_plan_ids


# ---------------------------------------------------------------------------
# 3. UNSUPPORTED quantity is fail-closed (infeasible, rejected)
# ---------------------------------------------------------------------------


def test_unsupported_quantity_is_infeasible_and_rejected() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_unsupported_semantics()),),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.INFEASIBLE
    assert result.chosen_plan_id is None
    assert len(result.rejected_plans) == 1
    assert result.rejected_plans[0].plan_id == "plan-1"


def test_unsupported_quantity_blocks_selection_with_feasible_alternative() -> None:
    unsupported_plan = _plan(
        "plan-unsupported",
        "eval-unsupported",
        allocations=(_allocation(quantity_semantics=_unsupported_semantics()),),
    )
    feasible_plan = _plan(
        "plan-feasible",
        "eval-feasible",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    request = _request(
        candidate_plans=(unsupported_plan, feasible_plan),
        evaluations=(
            _eval("eval-unsupported", 500),
            _eval("eval-feasible", 1000),
        ),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-feasible"
    assert result.ranked_plan_ids == ("plan-feasible",)
    assert len(result.rejected_plans) == 1
    assert result.rejected_plans[0].plan_id == "plan-unsupported"


# ---------------------------------------------------------------------------
# 4. Quantity-resolution state survives CandidatePlan construction
# ---------------------------------------------------------------------------


def test_quantity_semantics_retained_on_candidate_plan() -> None:
    resolved = _resolved_semantics()
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=resolved),),
    )

    semantics = plan.quantity_semantics
    assert semantics is not None
    assert len(semantics) == 1
    assert semantics[0] is resolved
    assert semantics[0].status is QuantityResolutionStatus.RESOLVED
    assert semantics[0].canonical_variant_id == "variant-1"
    assert semantics[0].requested_quantity == 2
    assert semantics[0].pack_kind is PackKind.single_unit
    assert semantics[0].pack_configuration_status == "complete"
    assert semantics[0].resolved_listing_units == 2


def test_quantity_semantics_none_when_not_attached() -> None:
    plan = _plan("plan-1", "eval-1")

    assert plan.quantity_semantics is None


def test_quantity_semantics_aggregates_across_multiple_allocations() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(
            _allocation(item_id="item-1", quantity_semantics=_resolved_semantics(quantity=2)),
            _allocation(
                item_id="item-2",
                canonical_variant_id="variant-2",
                quantity=1,
                quantity_semantics=_resolved_semantics(
                    variant_id="variant-2", quantity=1
                ),
            ),
        ),
    )

    semantics = plan.quantity_semantics
    assert semantics is not None
    assert len(semantics) == 2
    assert {s.canonical_variant_id for s in semantics} == {"variant-1", "variant-2"}


# ---------------------------------------------------------------------------
# 5. Existing provenance remains intact
# ---------------------------------------------------------------------------


def test_listing_provenance_remains_intact_when_quantity_semantics_present() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )

    provenance = plan.candidate_item_allocations[0].listing_provenance
    assert provenance.platform == "BLINKIT"
    assert provenance.platform_listing_id == "listing-1"
    assert provenance.observation_id == "observation-1"
    assert provenance.observed_selling_price == Money(currency="INR", minor_units=10000)


def test_to_item_allocation_strips_quantity_semantics() -> None:
    allocation = _allocation(quantity_semantics=_resolved_semantics())
    stripped = allocation.to_item_allocation()

    assert stripped.item_id == allocation.item_id
    assert stripped.canonical_variant_id == allocation.canonical_variant_id
    assert stripped.quantity == allocation.quantity
    assert stripped.retailer_id == allocation.retailer_id
    assert stripped.checkout_group_id == allocation.checkout_group_id
    assert not hasattr(stripped, "quantity_semantics")
    assert not hasattr(stripped, "listing_provenance")
    assert isinstance(stripped, ItemAllocation)


def test_item_allocation_is_unchanged_type() -> None:
    allocation = _allocation(quantity_semantics=_resolved_semantics())
    stripped = allocation.to_item_allocation()

    expected_fields = {"item_id", "canonical_variant_id", "quantity", "retailer_id", "checkout_group_id"}
    assert set(ItemAllocation.model_fields.keys()) == expected_fields
    assert "quantity_semantics" not in ItemAllocation.model_fields
    assert "listing_provenance" not in ItemAllocation.model_fields


# ---------------------------------------------------------------------------
# 6. Existing ranking behavior unchanged for equally valid plans
# ---------------------------------------------------------------------------


def test_ranking_unchanged_for_resolved_quantity_plans() -> None:
    expensive = _plan(
        "plan-expensive",
        "eval-expensive",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    cheap = _plan(
        "plan-cheap",
        "eval-cheap",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    request = _request(
        candidate_plans=(expensive, cheap),
        evaluations=(
            _eval("eval-expensive", 1200),
            _eval("eval-cheap", 900),
        ),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-cheap"
    assert result.ranked_plan_ids == ("plan-cheap", "plan-expensive")


def test_ranking_tie_breakers_unchanged_with_resolved_quantity() -> None:
    by_penalty = _plan(
        "plan-b", "eval-b",
        allocations=(_allocation(quantity_semantics=_resolved_semantics(quantity=2)),),
        # Note: inconvenience_penalty_units not settable via _plan; use different plan_ids
    )
    by_id = _plan(
        "plan-a", "eval-a",
        allocations=(_allocation(quantity_semantics=_resolved_semantics(quantity=2)),),
    )
    request = _request(
        candidate_plans=(by_penalty, by_id),
        evaluations=(_eval("eval-b", 1000), _eval("eval-a", 1000)),
    )

    result = CartOptimizationService().optimize(request)

    assert result.ranked_plan_ids == ("plan-a", "plan-b")
    assert result.chosen_plan_id == "plan-a"


# ---------------------------------------------------------------------------
# 7. Quantity semantics consistency validation
# ---------------------------------------------------------------------------


def test_mismatched_variant_id_in_quantity_semantics_rejected() -> None:
    allocation = _allocation(
        canonical_variant_id="variant-1",
        quantity_semantics=_resolved_semantics(variant_id="variant-99"),
    )
    with pytest.raises(ValueError, match="canonical_variant_id"):
        CandidatePlan.from_candidate_allocations(
            plan_id="plan-1",
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            candidate_item_allocations=(allocation,),
            effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                effective_cost_evaluation_id="eval-1"
            ),
            feasibility=PlanFeasibility.FEASIBLE,
        )


def test_mismatched_quantity_in_quantity_semantics_rejected() -> None:
    allocation = _allocation(quantity=3, quantity_semantics=_resolved_semantics(quantity=2))
    with pytest.raises(ValueError, match="requested_quantity"):
        CandidatePlan.from_candidate_allocations(
            plan_id="plan-1",
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            candidate_item_allocations=(allocation,),
            effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                effective_cost_evaluation_id="eval-1"
            ),
            feasibility=PlanFeasibility.FEASIBLE,
        )


# ---------------------------------------------------------------------------
# 8. Backward compatibility: plans without quantity bridge
# ---------------------------------------------------------------------------


def test_plan_without_quantity_semantics_works_unchanged() -> None:
    plan = _plan("plan-1", "eval-1")
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"
    assert plan.quantity_semantics is None


def test_mixed_plans_one_with_semantics_one_without() -> None:
    plan_with_sem = _plan(
        "plan-with-sem",
        "eval-with-sem",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    plan_without_sem = _plan("plan-no-sem", "eval-no-sem")
    request = _request(
        candidate_plans=(plan_with_sem, plan_without_sem),
        evaluations=(_eval("eval-with-sem", 1000), _eval("eval-no-sem", 800)),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-no-sem"
    assert result.ranked_plan_ids == ("plan-no-sem", "plan-with-sem")


# ---------------------------------------------------------------------------
# 9. Deterministic serialization
# ---------------------------------------------------------------------------


def test_candidate_allocation_with_quantity_semantics_serializes_deterministically() -> None:
    first = _allocation(quantity_semantics=_resolved_semantics())
    second = _allocation(quantity_semantics=_resolved_semantics())

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_candidate_plan_with_quantity_semantics_serializes_deterministically() -> None:
    plan_a = _plan(
        "plan-1", "eval-1",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    plan_b = _plan(
        "plan-1", "eval-1",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )

    assert plan_a.model_dump(mode="json") == plan_b.model_dump(mode="json")


# ---------------------------------------------------------------------------
# 10. Immutability
# ---------------------------------------------------------------------------


def test_quantity_semantics_field_is_immutable() -> None:
    allocation = _allocation(quantity_semantics=_resolved_semantics())

    with pytest.raises((TypeError, ValueError)):
        allocation.quantity_semantics = None  # type: ignore[misc]


def test_quantity_semantics_property_is_read_only() -> None:
    plan = _plan(
        "plan-1", "eval-1",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )

    with pytest.raises((TypeError, ValidationError)):
        plan.quantity_semantics = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 11. End-to-end CartOptimizationService with quantity semantics
# ---------------------------------------------------------------------------


def test_e2e_resolved_quantity_optimizes_successfully() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )
    service = CartOptimizationService()

    result = service.optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan is not None
    assert result.chosen_plan.quantity_semantics is not None
    assert len(result.chosen_plan.quantity_semantics) == 1
    assert result.chosen_plan.quantity_semantics[0].status is QuantityResolutionStatus.RESOLVED


def test_e2e_unresolved_quantity_returns_unresolved_outcome() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_unresolved_semantics()),),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.UNRESOLVED
    assert result.chosen_plan_id is None
    assert result.ranked_plan_ids == ()


def test_e2e_unsupported_quantity_returns_infeasible_outcome() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_unsupported_semantics()),),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.INFEASIBLE
    assert result.chosen_plan_id is None
    assert len(result.rejected_plans) == 1


def test_e2e_mixed_resolved_and_unsupported_picks_resolved() -> None:
    resolved_plan = _plan(
        "plan-resolved",
        "eval-resolved",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    unsupported_plan = _plan(
        "plan-unsupported",
        "eval-unsupported",
        allocations=(_allocation(quantity_semantics=_unsupported_semantics()),),
    )
    request = _request(
        candidate_plans=(resolved_plan, unsupported_plan),
        evaluations=(
            _eval("eval-resolved", 1000),
            _eval("eval-unsupported", 500),
        ),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-resolved"
    assert len(result.rejected_plans) == 1
    assert result.rejected_plans[0].plan_id == "plan-unsupported"


def test_e2e_replay_deterministic_with_quantity_semantics() -> None:
    plan = _plan(
        "plan-1",
        "eval-1",
        allocations=(_allocation(quantity_semantics=_resolved_semantics()),),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )
    service = CartOptimizationService()

    first = service.optimize(request)
    second = service.optimize(request)

    assert first == second
    assert first.optimization_id == second.optimization_id
