import pytest
from pydantic import ValidationError

from app.cart_optimization import CandidateItemAllocation, CandidatePlan
from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.types import EffectiveCostEvaluationReference
from app.cart_optimization.identity import CandidatePlanIdentityBuilder
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import TaxStatus
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation


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


def test_candidate_allocation_converts_to_optimizer_allocation_without_dropping_provenance() -> None:
    candidate = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
        observation=_comparison(),
    )

    allocation = candidate.to_item_allocation()

    assert allocation.item_id == candidate.item_id
    assert allocation.canonical_variant_id == candidate.canonical_variant_id
    assert allocation.quantity == candidate.quantity
    assert allocation.retailer_id == candidate.retailer_id
    assert allocation.checkout_group_id == candidate.checkout_group_id
    assert allocation.listing_provenance == candidate.listing_provenance


def test_candidate_plan_accepts_candidate_allocation_without_dropping_provenance() -> None:
    candidate = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
        observation=_comparison(),
    )

    plan = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        item_allocations=(candidate,),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )

    assert plan.item_allocations[0].listing_provenance == candidate.listing_provenance


def test_candidate_plan_rejects_non_iterable_item_allocations_through_pydantic() -> None:
    with pytest.raises(ValidationError):
        CandidatePlan(
            plan_id="plan-1",
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            item_allocations=123,  # type: ignore[arg-type]
            effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                effective_cost_evaluation_id="eval-1"
            ),
            feasibility=PlanFeasibility.FEASIBLE,
        )


def test_listing_provenance_is_excluded_from_candidate_plan_identity() -> None:
    candidate = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
        observation=_comparison(),
    )
    base = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=0,
        retailer_preference_priority=0,
        item_allocations=(candidate,),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )
    changed = base.model_copy(
        update={
            "item_allocations": (
                base.item_allocations[0].model_copy(
                    update={
                        "listing_provenance": base.item_allocations[0].listing_provenance.model_copy(
                            update={"observation_id": "observation-2"}
                        )
                    }
                ),
            )
        }
    )

    assert CandidatePlanIdentityBuilder().build(changed) == CandidatePlanIdentityBuilder().build(base)
