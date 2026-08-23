"""Tests for the LogicalCart and PlatformCartGroup domain contracts.

These tests verify the immutable domain boundary that connects a logical
cart (user intent) to platform-specific cart grouping (optimization
output), without performing any platform execution.

See: docs/architecture/cart_optimization_contract.md
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.cart_optimization import (
    CartItemRequest,
    CandidateItemAllocation,
    CandidatePlan,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    ItemAllocation,
    LogicalCart,
    PlatformCartGroup,
)
from app.cart_optimization.enums import PlanFeasibility, CoverageState
from app.cart_optimization.quantity_semantics import (
    QuantityResolutionStatus,
    VariantQuantityResolutionService,
)
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.types import CartOptimizationRequest
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import TaxStatus
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation
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


def _resolved_semantics(variant_id: str = "variant-1", quantity: int = 2) -> "object":
    return _QS_SERVICE.resolve(
        canonical_variant_id=variant_id,
        requested_quantity=quantity,
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            pack_configuration_status="complete",
        ),
    )


def _candidate_allocation(
    *,
    item_id: str = "item-1",
    canonical_variant_id: str = "variant-1",
    quantity: int = 2,
    retailer_id: str = "retailer-1",
    checkout_group_id: str = "checkout-1",
    platform: str = "BLINKIT",
    observation_id: str = "observation-1",
    platform_listing_id: str = "listing-1",
    observation: ComparableRetailObservation | None = None,
    quantity_semantics: object | None = None,
) -> CandidateItemAllocation:
    obs = observation or ComparableRetailObservation(
        observation_id=observation_id,
        platform=platform,
        platform_listing_id=platform_listing_id,
        canonical_product_id="product-1",
        canonical_variant_id=canonical_variant_id,
        observed_selling_price=Money(currency="INR", minor_units=10000),
        tax_status=TaxStatus.INCLUDED,
    )
    if observation is not None:
        obs = observation
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
            observation=obs,
        ).listing_provenance,
        quantity_semantics=quantity_semantics,
    )


def _plan(
    plan_id: str = "plan-1",
    eval_id: str = "eval-1",
    *,
    allocations: tuple[CandidateItemAllocation, ...] | None = None,
    feasibility: PlanFeasibility = PlanFeasibility.FEASIBLE,
    checkout_groups: tuple[CheckoutGroup, ...] | None = None,
    quantity_semantics_attached: bool = True,
) -> CandidatePlan:
    allocs = allocations
    if allocs is None:
        allocs = (_candidate_allocation(),)
    if quantity_semantics_attached:
        allocs = tuple(
            alloc.model_copy(update={"quantity_semantics": _resolved_semantics(
                variant_id=alloc.canonical_variant_id, quantity=alloc.quantity
            )})
            for alloc in allocs
        )
    return CandidatePlan.from_candidate_allocations(
        plan_id=plan_id,
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        candidate_item_allocations=allocs,
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id=eval_id
        ),
        feasibility=feasibility,
        checkout_groups=checkout_groups or (),
    )


def _eval(evaluation_id: str, amount: int | None, *, currency: str = "INR") -> EffectiveCostEvaluationResult:
    return EffectiveCostEvaluationResult(
        evaluation_id=evaluation_id,
        context_id=f"context-{evaluation_id}",
        effective_cost=Money(currency=currency, minor_units=amount) if amount is not None else None,
    )


def _coverage_complete() -> object:
    from app.cart_optimization.types import CandidatePlanCoverage
    return CandidatePlanCoverage(
        state=CoverageState.COMPLETE,
        scope_reference="scope-1",
        candidate_set_reference="set-1",
        coverage_basis="unit-test",
        validation_reference="validation-1",
    )


def _request(
    *,
    candidate_plans: tuple[CandidatePlan, ...],
    evaluations: tuple[EffectiveCostEvaluationResult, ...],
) -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),),
        candidate_plans=candidate_plans,
        candidate_plan_coverage=_coverage_complete(),
        effective_cost_evaluations=evaluations,
    )


# ---------------------------------------------------------------------------
# 1. Logical cart preserves canonical Variant requests
# ---------------------------------------------------------------------------


def test_logical_cart_preserves_canonical_variant_items() -> None:
    cart = LogicalCart(
        cart_id="cart-1",
        cart_items=(
            CartItemRequest(item_id="item-a", canonical_variant_id="variant-1", quantity=2),
            CartItemRequest(item_id="item-b", canonical_variant_id="variant-2", quantity=1),
        ),
    )

    assert cart.cart_id == "cart-1"
    assert len(cart.cart_items) == 2
    assert cart.cart_items[0].canonical_variant_id == "variant-1"
    assert cart.cart_items[1].canonical_variant_id == "variant-2"
    assert cart.cart_items[0].quantity == 2
    assert cart.cart_items[1].quantity == 1


def test_logical_cart_preserves_requested_quantity_as_canonical_units() -> None:
    cart = LogicalCart(
        cart_id="cart-1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=5),
        ),
    )

    assert cart.cart_items[0].quantity == 5


# ---------------------------------------------------------------------------
# 2. Requested quantity remains distinct from platform listing provenance
# ---------------------------------------------------------------------------


def test_cart_item_request_has_no_platform_or_listing_fields() -> None:
    item = CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2)

    assert not hasattr(item, "platform")
    assert not hasattr(item, "platform_listing_id")
    assert not hasattr(item, "listing_provenance")
    assert not hasattr(item, "retailer_id")
    assert not hasattr(item, "checkout_group_id")

    expected_fields = {"item_id", "canonical_variant_id", "quantity"}
    assert set(CartItemRequest.model_fields.keys()) == expected_fields


def test_cart_item_request_quantity_is_distinct_from_listing_provenance() -> None:
    allocation = _candidate_allocation(quantity=3)

    assert allocation.quantity == 3
    assert allocation.listing_provenance.platform == "BLINKIT"
    assert allocation.listing_provenance.platform_listing_id == "listing-1"


# ---------------------------------------------------------------------------
# 3. Platform grouping preserves platform identity
# ---------------------------------------------------------------------------


def test_platform_cart_group_preserves_platform_identity() -> None:
    allocation = _candidate_allocation(platform="BLINKIT", checkout_group_id="checkout-1")
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(allocation,),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    groups = plan.platform_cart_groups()
    assert len(groups) == 1
    assert groups[0].platform == "BLINKIT"


def test_platform_cart_group_preserves_multiple_platforms() -> None:
    blinkit_alloc = _candidate_allocation(
        item_id="item-1", platform="BLINKIT", checkout_group_id="checkout-blinkit"
    )
    zepto_alloc = _candidate_allocation(
        item_id="item-2", platform="ZEPTO", checkout_group_id="checkout-zepto",
        platform_listing_id="listing-2", observation_id="obs-2",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(blinkit_alloc, zepto_alloc),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-blinkit",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
            CheckoutGroup(
                checkout_group_id="checkout-zepto",
                retailer_id="retailer-2",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    groups = plan.platform_cart_groups()
    assert len(groups) == 2
    assert {g.platform for g in groups} == {"BLINKIT", "ZEPTO"}
    assert {g.checkout_group_id for g in groups} == {"checkout-blinkit", "checkout-zepto"}


# ---------------------------------------------------------------------------
# 4. Selected listing provenance is preserved
# ---------------------------------------------------------------------------


def test_platform_cart_group_preserves_listing_provenance() -> None:
    allocation = _candidate_allocation(
        platform="BLINKIT",
        platform_listing_id="listing-42",
        observation_id="obs-99",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(allocation,),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    groups = plan.platform_cart_groups()
    assert len(groups) == 1
    prov = groups[0].listing_allocations[0].listing_provenance
    assert prov.platform == "BLINKIT"
    assert prov.platform_listing_id == "listing-42"
    assert prov.observation_id == "obs-99"


def test_platform_cart_group_preserves_canonical_variant_traceability() -> None:
    allocation = _candidate_allocation(
        canonical_variant_id="variant-xyz",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(allocation,),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    groups = plan.platform_cart_groups()
    alloc = groups[0].listing_allocations[0]
    assert alloc.canonical_variant_id == "variant-xyz"


# ---------------------------------------------------------------------------
# 5. A logical cart item cannot accidentally reference a listing belonging
#    to another canonical Variant
# ---------------------------------------------------------------------------


def test_mismatched_variant_between_cart_item_and_allocation_rejected() -> None:
    cart = LogicalCart(
        cart_id="cart-1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-A", quantity=1),
        ),
    )
    allocation = _candidate_allocation(
        canonical_variant_id="variant-B",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(allocation,),
        quantity_semantics_attached=False,
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    assert cart.cart_items[0].canonical_variant_id != allocation.canonical_variant_id
    assert allocation.canonical_variant_id == "variant-B"


def test_candidate_item_allocation_rejects_mismatched_variant_from_observation() -> None:
    observation = ComparableRetailObservation(
        observation_id="obs-1",
        platform="BLINKIT",
        platform_listing_id="listing-1",
        canonical_product_id="product-1",
        canonical_variant_id="variant-1",
        observed_selling_price=Money(currency="INR", minor_units=10000),
        tax_status=TaxStatus.INCLUDED,
    )

    with pytest.raises(ValueError, match="does not target requested"):
        CandidateItemAllocation.from_comparable_observation(
            item_id="item-1",
            canonical_variant_id="variant-2",
            quantity=1,
            retailer_id="BLINKIT",
            checkout_group_id="checkout-1",
            observation=observation,
        )


# ---------------------------------------------------------------------------
# 6. Invalid empty identifiers fail closed
# ---------------------------------------------------------------------------


def test_logical_cart_empty_cart_id_fails_closed() -> None:
    with pytest.raises(ValidationError, match="cart_id is required"):
        LogicalCart(cart_id="", cart_items=())


def test_logical_cart_whitespace_cart_id_fails_closed() -> None:
    with pytest.raises(ValidationError, match="cart_id is required"):
        LogicalCart(cart_id="  ", cart_items=())


def test_logical_cart_duplicate_item_ids_fails_closed() -> None:
    with pytest.raises(ValidationError, match="duplicate cart item IDs"):
        LogicalCart(
            cart_id="cart-1",
            cart_items=(
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-2", quantity=2),
            ),
        )


def test_platform_cart_group_empty_platform_fails_closed() -> None:
    with pytest.raises(ValidationError, match="identifier fields must not be empty"):
        PlatformCartGroup(
            platform="",
            retailer_id="retailer-1",
            checkout_group_id="checkout-1",
            effective_cost_evaluation_id="eval-1",
            listing_allocations=(_candidate_allocation(),),
        )


def test_platform_cart_group_empty_checkout_group_id_fails_closed() -> None:
    with pytest.raises(ValidationError, match="identifier fields must not be empty"):
        PlatformCartGroup(
            platform="BLINKIT",
            retailer_id="retailer-1",
            checkout_group_id="  ",
            effective_cost_evaluation_id="eval-1",
            listing_allocations=(_candidate_allocation(),),
        )


def test_platform_cart_group_without_allocations_fails_closed() -> None:
    with pytest.raises(ValidationError, match="must contain at least one"):
        PlatformCartGroup(
            platform="BLINKIT",
            retailer_id="retailer-1",
            checkout_group_id="checkout-1",
            effective_cost_evaluation_id="eval-1",
            listing_allocations=(),
        )


# ---------------------------------------------------------------------------
# 7. Empty platform groups behave according to existing architecture
# ---------------------------------------------------------------------------


def test_empty_plan_yields_no_platform_cart_groups() -> None:
    plan = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )

    assert plan.platform_cart_groups() == ()


def test_plan_without_candidate_allocations_yields_empty_groups() -> None:
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(),
        quantity_semantics_attached=False,
    )

    assert plan.platform_cart_groups() == ()


# ---------------------------------------------------------------------------
# 8. Deterministic serialization
# ---------------------------------------------------------------------------


def test_logical_cart_serializes_deterministically() -> None:
    first = LogicalCart(
        cart_id="cart-1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
        ),
    )
    second = LogicalCart(
        cart_id="cart-1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
        ),
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_platform_cart_group_serializes_deterministically() -> None:
    alloc = _candidate_allocation()
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(alloc,),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    first = plan.platform_cart_groups()[0].model_dump(mode="json")
    second = plan.platform_cart_groups()[0].model_dump(mode="json")

    assert first == second


# ---------------------------------------------------------------------------
# 9. Immutability
# ---------------------------------------------------------------------------


def test_logical_cart_is_immutable() -> None:
    cart = LogicalCart(
        cart_id="cart-1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
        ),
    )

    with pytest.raises((TypeError, ValidationError)):
        cart.cart_id = "changed"  # type: ignore[misc]
    with pytest.raises((TypeError, ValidationError)):
        cart.cart_items = ()  # type: ignore[misc]


def test_platform_cart_group_is_immutable() -> None:
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(_candidate_allocation(),),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    group = plan.platform_cart_groups()[0]
    with pytest.raises((TypeError, ValidationError)):
        group.platform = "ZEPTO"  # type: ignore[misc]
    with pytest.raises((TypeError, ValidationError)):
        group.listing_allocations = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 10. Multiple platform groups can coexist deterministically
# ---------------------------------------------------------------------------


def test_multiple_platform_groups_coexist_deterministically() -> None:
    blinkit = _candidate_allocation(
        item_id="item-1", platform="BLINKIT", checkout_group_id="cg-1",
    )
    zepto = _candidate_allocation(
        item_id="item-2", platform="ZEPTO", checkout_group_id="cg-2",
        platform_listing_id="listing-2", observation_id="obs-2",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(blinkit, zepto),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="cg-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
            CheckoutGroup(
                checkout_group_id="cg-2",
                retailer_id="retailer-2",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    first = plan.platform_cart_groups()
    second = plan.platform_cart_groups()

    assert len(first) == 2
    assert first == second
    platforms = {g.platform for g in first}
    assert platforms == {"BLINKIT", "ZEPTO"}
    checkout_ids = {g.checkout_group_id for g in first}
    assert checkout_ids == {"cg-1", "cg-2"}


def test_platform_groups_are_sorted_by_checkout_group_id() -> None:
    c = _candidate_allocation(item_id="item-1", platform="BLINKIT", checkout_group_id="cg-c")
    a = _candidate_allocation(
        item_id="item-2", platform="ZEPTO", checkout_group_id="cg-a",
        platform_listing_id="listing-2", observation_id="obs-2",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(c, a),
        checkout_groups=(
            CheckoutGroup(checkout_group_id="cg-c", retailer_id="r1", effective_cost_evaluation_id="eval-1"),
            CheckoutGroup(checkout_group_id="cg-a", retailer_id="r2", effective_cost_evaluation_id="eval-1"),
        ),
    )

    groups = plan.platform_cart_groups()
    assert [g.checkout_group_id for g in groups] == ["cg-a", "cg-c"]


# ---------------------------------------------------------------------------
# 11. Existing CandidateItemAllocation behavior remains unchanged
# ---------------------------------------------------------------------------


def test_existing_candidate_allocation_without_quantity_semantics_still_works() -> None:
    allocation = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=2,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
        observation=_observation(),
    )

    assert allocation.quantity_semantics is None
    assert allocation.listing_provenance.platform == "BLINKIT"
    assert allocation.listing_provenance.platform_listing_id == "listing-1"
    assert allocation.canonical_variant_id == "variant-1"
    assert allocation.quantity == 2

    stripped = allocation.to_item_allocation()
    assert isinstance(stripped, ItemAllocation)
    assert stripped.item_id == allocation.item_id


# ---------------------------------------------------------------------------
# 12. Existing CandidatePlan behavior remains unchanged
# ---------------------------------------------------------------------------


def test_existing_candidate_plan_without_provenance_still_works() -> None:
    plan = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )

    assert plan.platform_cart_groups() == ()
    assert plan.quantity_semantics is None
    assert plan.candidate_item_allocations == ()


def test_existing_plan_with_provenance_remains_unchanged() -> None:
    allocation = _candidate_allocation()
    plan = CandidatePlan.from_candidate_allocations(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        candidate_item_allocations=(allocation,),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )

    assert len(plan.candidate_item_allocations) == 1
    assert len(plan.item_allocations) == 1
    assert plan.candidate_item_allocations[0] == allocation
    assert plan.item_allocations[0] == allocation.to_item_allocation()


# ---------------------------------------------------------------------------
# 13. Existing CartOptimizationService behavior remains unchanged
# ---------------------------------------------------------------------------


def test_service_behavior_unchanged_without_quantity_semantics() -> None:
    plan = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome.value == "selected"
    assert result.chosen_plan_id == "plan-1"


def test_service_unresolved_plan_still_blocks_recommendation() -> None:
    plan = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.UNRESOLVED,
    )
    request = CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
        ),
        candidate_plans=(plan,),
        candidate_plan_coverage=_coverage_complete(),
        effective_cost_evaluations=(_eval("eval-1", None),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome.value == "unresolved"
    assert result.chosen_plan_id is None


def test_service_infeasible_plan_still_rejected() -> None:
    plan = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.INFEASIBLE,
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_eval("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome.value == "infeasible"
    assert result.chosen_plan_id is None
    assert len(result.rejected_plans) == 1


# ---------------------------------------------------------------------------
# Platform group: relationship to logical cart item
# ---------------------------------------------------------------------------


def test_logical_cart_item_links_to_platform_listing_via_plan() -> None:
    """Verify the traceability chain:
    LogicalCart.cart_items → CandidateItemAllocation → ListingProvenance
    """
    cart = LogicalCart(
        cart_id="cart-1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
        ),
    )
    allocation = _candidate_allocation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=2,
        platform="BLINKIT",
        platform_listing_id="listing-777",
        observation_id="obs-777",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(allocation,),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    groups = plan.platform_cart_groups()
    assert len(groups) == 1

    group = groups[0]
    assert group.platform == "BLINKIT"

    alloc = group.listing_allocations[0]
    assert alloc.item_id == cart.cart_items[0].item_id
    assert alloc.canonical_variant_id == cart.cart_items[0].canonical_variant_id
    assert alloc.quantity == cart.cart_items[0].quantity

    assert alloc.listing_provenance.platform == "BLINKIT"
    assert alloc.listing_provenance.platform_listing_id == "listing-777"
    assert alloc.listing_provenance.observation_id == "obs-777"


def test_platform_cart_group_does_not_carry_execution_state() -> None:
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(_candidate_allocation(),),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    group = plan.platform_cart_groups()[0]

    exec_fields = {"auth_token", "session_id", "cookie", "credential", "access_token", "refresh_token"}
    model_fields = set(PlatformCartGroup.model_fields.keys())
    assert not (exec_fields & model_fields)


# ---------------------------------------------------------------------------
# Platform group: retailer_id distinct from platform
# ---------------------------------------------------------------------------


def test_platform_cart_group_keeps_retailer_id_distinct_from_platform() -> None:
    allocation = _candidate_allocation(
        platform="BLINKIT",
        retailer_id="retailer-1",
    )
    plan = _plan(
        plan_id="plan-1",
        eval_id="eval-1",
        allocations=(allocation,),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="checkout-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
    )

    group = plan.platform_cart_groups()[0]
    assert group.platform == "BLINKIT"
    assert group.retailer_id == "retailer-1"
    assert group.platform != group.retailer_id
