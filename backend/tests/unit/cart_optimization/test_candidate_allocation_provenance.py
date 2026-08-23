import pytest
from pydantic import ValidationError

from app.cart_optimization import CandidateItemAllocation, CandidatePlan
from app.cart_optimization.enums import (
    CoverageState,
    OptimizationOutcome,
    PlanFeasibility,
)
from app.cart_optimization.identity import CandidatePlanIdentityBuilder
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.types import (
    CandidatePlanCoverage,
    CartOptimizationRequest,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    ItemAllocation,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import TaxStatus
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation
from app.product_intelligence.models import EvidenceReference


def _comparison(variant_id: str = "variant-1") -> ComparableRetailObservation:
    return ComparableRetailObservation(
        observation_id="observation-1",
        platform="BLINKIT",
        platform_listing_id="listing-1",
        canonical_product_id="product-1",
        canonical_variant_id=variant_id,
        observed_selling_price=Money(currency="INR", minor_units=10000),
        tax_status=TaxStatus.INCLUDED,
    )


def test_candidate_allocation_preserves_listing_and_observation_provenance() -> None:
    allocation = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=2,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
        observation=_comparison(),
    )

    assert allocation.canonical_variant_id == "variant-1"
    assert allocation.quantity == 2
    assert allocation.retailer_id == "BLINKIT"
    assert allocation.listing_provenance.platform == "BLINKIT"
    assert allocation.listing_provenance.platform_listing_id == "listing-1"
    assert allocation.listing_provenance.observation_id == "observation-1"
    assert allocation.listing_provenance.observed_selling_price == Money(
        currency="INR", minor_units=10000
    )


def test_candidate_allocation_rejects_association_for_another_variant() -> None:
    with pytest.raises(ValueError, match="does not target requested"):
        CandidateItemAllocation.from_comparable_observation(
            item_id="item-1",
            canonical_variant_id="variant-1",
            quantity=1,
            retailer_id="BLINKIT",
            checkout_group_id="checkout-1",
            observation=_comparison("variant-2"),
        )


def test_candidate_allocation_is_deterministically_serializable_and_immutable() -> None:
    first = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
        observation=_comparison(),
    )
    second = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
        observation=_comparison(),
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    with pytest.raises((TypeError, ValueError)):
        first.quantity = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration tests: connecting CandidateItemAllocation to CandidatePlan
# ---------------------------------------------------------------------------


def _candidate_allocation(
    *,
    item_id: str = "item-1",
    canonical_variant_id: str = "variant-1",
    quantity: int = 2,
    retailer_id: str = "BLINKIT",
    checkout_group_id: str = "checkout-1",
    observation: ComparableRetailObservation | None = None,
) -> CandidateItemAllocation:
    return CandidateItemAllocation.from_comparable_observation(
        item_id=item_id,
        canonical_variant_id=canonical_variant_id,
        quantity=quantity,
        retailer_id=retailer_id,
        checkout_group_id=checkout_group_id,
        observation=observation or _comparison(canonical_variant_id),
    )


def _eval_ref(eval_id: str = "eval-1") -> EffectiveCostEvaluationReference:
    return EffectiveCostEvaluationReference(effective_cost_evaluation_id=eval_id)


def _coverage(state: CoverageState = CoverageState.COMPLETE) -> CandidatePlanCoverage:
    if state is CoverageState.COMPLETE:
        return CandidatePlanCoverage(
            state=state,
            scope_reference="scope-1",
            candidate_set_reference="set-1",
            coverage_basis="unit-test",
            validation_reference="validation-1",
        )
    return CandidatePlanCoverage(
        state=state,
        rationale=(f"coverage is {state.value}",),
    )


def _request(
    *,
    candidate_plans: tuple[CandidatePlan, ...],
    evaluations: tuple[EffectiveCostEvaluationResult, ...] = (),
    coverage_state: CoverageState = CoverageState.COMPLETE,
    policy_version: str = "policy-v1",
) -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version=policy_version,
        candidate_plans=candidate_plans,
        candidate_plan_coverage=_coverage(coverage_state),
        effective_cost_evaluations=evaluations,
    )


def _provenance_bearing_plan(
    *,
    plan_id: str = "plan-1",
    eval_id: str = "eval-1",
    allocations: tuple[CandidateItemAllocation, ...] | None = None,
) -> CandidatePlan:
    allocations = allocations or (_candidate_allocation(),)
    return CandidatePlan.from_candidate_allocations(
        plan_id=plan_id,
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        candidate_item_allocations=allocations,
        checkout_groups=tuple(
            CheckoutGroup(
                checkout_group_id=group_id,
                retailer_id=next(
                    allocation.retailer_id
                    for allocation in allocations
                    if allocation.checkout_group_id == group_id
                ),
                effective_cost_evaluation_id=eval_id,
            )
            for group_id in sorted({allocation.checkout_group_id for allocation in allocations})
        ),
        effective_cost_evaluation_reference=_eval_ref(eval_id),
        feasibility=PlanFeasibility.FEASIBLE,
    )


# --- Test 1: CandidateItemAllocation can enter the existing optimization flow ---


def test_candidate_item_allocation_enters_candidate_plan_via_factory() -> None:
    allocation = _candidate_allocation()
    plan = _provenance_bearing_plan(allocations=(allocation,))

    assert len(plan.candidate_item_allocations) == 1
    assert len(plan.item_allocations) == 1
    assert plan.candidate_item_allocations[0] == allocation
    assert plan.item_allocations[0] == allocation.to_item_allocation()


# --- Tests 2-9: All provenance fields preserved ---


def test_candidate_plan_preserves_all_provenance_fields_through_optimization() -> None:
    allocation = _candidate_allocation(
        item_id="item-42",
        canonical_variant_id="variant-99",
        quantity=3,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-A",
        observation=ComparableRetailObservation(
            observation_id="obs-777",
            platform="BLINKIT",
            platform_listing_id="listing-888",
            canonical_product_id="product-1",
            canonical_variant_id="variant-99",
            observed_selling_price=Money(currency="INR", minor_units=10000),
            tax_status=TaxStatus.INCLUDED,
        ),
    )
    plan = _provenance_bearing_plan(plan_id="plan-1", allocations=(allocation,))
    provenance = plan.candidate_item_allocations[0].listing_provenance

    assert provenance is not None
    assert plan.candidate_item_allocations[0].canonical_variant_id == "variant-99"
    assert plan.candidate_item_allocations[0].quantity == 3
    assert plan.candidate_item_allocations[0].retailer_id == "BLINKIT"
    assert plan.candidate_item_allocations[0].checkout_group_id == "checkout-A"
    assert provenance.platform == "BLINKIT"
    assert provenance.platform_listing_id == "listing-888"
    assert provenance.observation_id == "obs-777"
    assert provenance.observed_selling_price == Money(currency="INR", minor_units=10000)


# --- Test 10: Provenance remains immutable ---


def test_candidate_item_allocation_provenance_is_immutable() -> None:
    allocation = _candidate_allocation()
    provenance = allocation.listing_provenance

    assert provenance.platform == "BLINKIT"
    with pytest.raises((TypeError, ValidationError)):
        provenance.platform = "ZEPTO"  # type: ignore[misc]
    with pytest.raises((TypeError, ValidationError)):
        allocation.quantity = 99  # type: ignore[misc]


# --- Test 11: Deterministic serialization/identity remains deterministic ---


def test_candidate_plan_identity_includes_provenance_deterministically() -> None:
    plan = _provenance_bearing_plan()

    builder = CandidatePlanIdentityBuilder()
    first = builder.build(plan)
    second = builder.build(plan)

    assert first == second
    assert len(first["candidate_item_allocations"]) == 1


def test_candidate_plan_identity_changes_when_provenance_changes() -> None:
    allocation_a = _candidate_allocation(
        observation=ComparableRetailObservation(
            observation_id="obs-1",
            platform="BLINKIT",
            platform_listing_id="listing-1",
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            observed_selling_price=Money(currency="INR", minor_units=10000),
            tax_status=TaxStatus.INCLUDED,
        ),
    )
    allocation_b = _candidate_allocation(
        observation=ComparableRetailObservation(
            observation_id="obs-2",
            platform="ZEPTO",
            platform_listing_id="listing-2",
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            observed_selling_price=Money(currency="INR", minor_units=10000),
            tax_status=TaxStatus.INCLUDED,
        ),
    )
    plan_a = _provenance_bearing_plan(plan_id="plan-1")
    plan_b = _provenance_bearing_plan(
        plan_id="plan-1",
        allocations=(allocation_b,),
    )

    builder = CandidatePlanIdentityBuilder()
    assert builder.build(plan_a) != builder.build(plan_b)


def test_candidate_item_allocation_to_item_allocation_strips_provenance_only() -> None:
    allocation = _candidate_allocation()
    stripped = allocation.to_item_allocation()

    assert stripped.item_id == allocation.item_id
    assert stripped.canonical_variant_id == allocation.canonical_variant_id
    assert stripped.quantity == allocation.quantity
    assert stripped.retailer_id == allocation.retailer_id
    assert stripped.checkout_group_id == allocation.checkout_group_id
    assert not hasattr(stripped, "listing_provenance")
    assert not hasattr(stripped, "platform")
    assert not hasattr(stripped, "platform_listing_id")
    assert not hasattr(stripped, "observation_id")
    assert not hasattr(stripped, "observed_selling_price")


# --- Test 12: CandidatePlanCoverage behavior is unchanged ---


def test_coverage_blocking_behavior_unchanged_with_provenance_plans() -> None:
    plan = _provenance_bearing_plan()
    service = CartOptimizationService()

    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
        coverage_state=CoverageState.COMPLETE,
    )
    result = service.optimize(request)
    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"

    for state in (CoverageState.PARTIAL, CoverageState.UNKNOWN, CoverageState.INVALID):
        uncovered = _request(
            candidate_plans=(plan,),
            evaluations=(_evaluation("eval-1", 1000),),
            coverage_state=state,
        )
        result = service.optimize(uncovered)
        assert result.outcome is OptimizationOutcome.UNRESOLVED
        assert result.chosen_plan is None


# --- Test 13: optimization_policy_version behavior is unchanged ---


def test_unsupported_policy_version_fails_closed_with_provenance_plan() -> None:
    plan = _provenance_bearing_plan()
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
        policy_version="unsupported-policy",
    )

    with pytest.raises(ValueError, match="unsupported optimization policy version"):
        CartOptimizationService().optimize(request)


# --- Test 14: Existing optimizer behavior unchanged for non-provenance candidates ---


def test_optimizer_behavior_unchanged_without_provenance_bridge() -> None:
    plan = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=_eval_ref("eval-1"),
        feasibility=PlanFeasibility.FEASIBLE,
        candidate_item_allocations=(),
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"
    assert len(plan.candidate_item_allocations) == 0


def test_optimizer_ranking_unchanged_with_and_without_provenance() -> None:
    plan_cheap_with_prov = _provenance_bearing_plan(
        plan_id="plan-cheap", eval_id="eval-cheap"
    )
    plan_expensive_no_prov = CandidatePlan(
        plan_id="plan-expensive",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=_eval_ref("eval-expensive"),
        feasibility=PlanFeasibility.FEASIBLE,
        candidate_item_allocations=(),
    )
    request_with = _request(
        candidate_plans=(plan_cheap_with_prov, plan_expensive_no_prov),
        evaluations=(
            _evaluation("eval-cheap", 500),
            _evaluation("eval-expensive", 1000),
        ),
    )
    result_with = CartOptimizationService().optimize(request_with)

    plan_cheap_no_prov = CandidatePlan(
        plan_id="plan-cheap",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=_eval_ref("eval-cheap"),
        feasibility=PlanFeasibility.FEASIBLE,
        candidate_item_allocations=(),
    )
    plan_expensive_no_prov_b = CandidatePlan(
        plan_id="plan-expensive",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=_eval_ref("eval-expensive"),
        feasibility=PlanFeasibility.FEASIBLE,
        candidate_item_allocations=(),
    )
    request_without = _request(
        candidate_plans=(plan_cheap_no_prov, plan_expensive_no_prov_b),
        evaluations=(
            _evaluation("eval-cheap", 500),
            _evaluation("eval-expensive", 1000),
        ),
    )
    result_without = CartOptimizationService().optimize(request_without)

    assert result_with.ranked_plan_ids == result_without.ranked_plan_ids
    assert result_with.chosen_plan_id == result_without.chosen_plan_id
    assert result_with.outcome == result_without.outcome
    assert result_with.chosen_plan_id == "plan-cheap"


# --- Test 15: Mismatched canonical Variant provenance is rejected ---


def test_mismatched_variant_between_candidate_and_item_allocation_rejected() -> None:
    allocation = _candidate_allocation(
        item_id="item-1",
        canonical_variant_id="variant-1",
    )
    wrong_item = ItemAllocation(
        item_id="item-1",
        canonical_variant_id="variant-2",
        quantity=2,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
    )
    with pytest.raises(ValueError, match="no matching ItemAllocation"):
        CandidatePlan(
            plan_id="plan-1",
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            item_allocations=(wrong_item,),
            candidate_item_allocations=(allocation,),
            effective_cost_evaluation_reference=_eval_ref(),
            feasibility=PlanFeasibility.FEASIBLE,
        )


def test_mismatched_quantity_between_candidate_and_item_allocation_rejected() -> None:
    allocation = _candidate_allocation(quantity=2)
    wrong_item = ItemAllocation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
    )
    with pytest.raises(ValueError, match="no matching ItemAllocation"):
        CandidatePlan(
            plan_id="plan-1",
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            item_allocations=(wrong_item,),
            candidate_item_allocations=(allocation,),
            effective_cost_evaluation_reference=_eval_ref(),
            feasibility=PlanFeasibility.FEASIBLE,
        )


def test_provenance_count_mismatch_rejected() -> None:
    allocation = _candidate_allocation()
    with pytest.raises(ValueError, match="must match item_allocations count"):
        CandidatePlan(
            plan_id="plan-1",
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            item_allocations=tuple(),
            candidate_item_allocations=(allocation,),
            effective_cost_evaluation_reference=_eval_ref(),
            feasibility=PlanFeasibility.FEASIBLE,
        )


# --- Additional: optimizer correctly preserves provenance through result ---


def test_optimizer_preserves_provenance_in_chosen_plan() -> None:
    plan = _provenance_bearing_plan(plan_id="plan-1", eval_id="eval-1")
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 500),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"
    assert result.chosen_plan is not None
    assert len(result.chosen_plan.candidate_item_allocations) == 1
    provenance = result.chosen_plan.candidate_item_allocations[0].listing_provenance
    assert provenance.observation_id == "observation-1"
    assert provenance.platform_listing_id == "listing-1"
    assert provenance.platform == "BLINKIT"
    assert provenance.observed_selling_price == Money(currency="INR", minor_units=10000)


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
