import pytest

from app.cart_optimization import CandidateItemAllocation
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
