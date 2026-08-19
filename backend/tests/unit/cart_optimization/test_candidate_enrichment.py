import pytest

from app.cart_optimization.candidate_enrichment import (
    CandidateAllocationEnrichment,
    CandidateAllocationEnrichmentService,
)
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.types import NormalizedObservation
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    CartCandidateDiscoveryStatus,
    PersistedCandidateReadiness,
    PersistedListingCandidate,
)


def _candidate(
    *, listing_id="listing-1", observation_id="observation-1", platform="platform-1",
    item_id="item-1", product_id="product-1", variant_id="variant-1", quantity=2,
    price=100,
):
    observation = NormalizedObservation.model_construct(
        observed_selling_price=Money(currency="INR", minor_units=price),
    )
    return PersistedListingCandidate(
        platform=platform,
        platform_listing_id=listing_id,
        canonical_product_id=product_id,
        canonical_variant_id=variant_id,
        observation_id=observation_id,
        observation=observation,
        readiness=PersistedCandidateReadiness.ready_for_allocation,
    )


def _context(candidate, **overrides):
    values = {
        "item_id": "item-1",
        "canonical_product_id": candidate.canonical_product_id,
        "canonical_variant_id": candidate.canonical_variant_id,
        "quantity": 2,
        "retailer_id": "retailer-authoritative",
        "checkout_group_id": "checkout-authoritative",
    }
    values.update(overrides)
    return CandidateAllocationEnrichment(**values)


def _item(candidate, *, quantity=2):
    return CartCandidateDiscoveryItem(
        item_id="item-1",
        quantity=quantity,
        canonical_product_id=candidate.canonical_product_id,
        canonical_variant_id=candidate.canonical_variant_id,
        status=CartCandidateDiscoveryStatus.candidates_available,
        candidates=(candidate,),
    )


def test_explicit_enrichment_preserves_candidate_and_supplied_context() -> None:
    candidate = _candidate()
    result = CandidateAllocationEnrichmentService().enrich(_item(candidate), candidate, _context(candidate))

    assert result.candidate is candidate
    assert result.allocation.item_id == "item-1"
    assert result.allocation.canonical_variant_id == "variant-1"
    assert result.allocation.quantity == 2
    assert result.allocation.retailer_id == "retailer-authoritative"
    assert result.allocation.checkout_group_id == "checkout-authoritative"
    assert result.allocation.listing_provenance.platform == "platform-1"
    assert result.allocation.listing_provenance.platform_listing_id == "listing-1"
    assert result.allocation.listing_provenance.observation_id == "observation-1"
    assert result.allocation.listing_provenance.observed_selling_price == Money(currency="INR", minor_units=100)


@pytest.mark.parametrize("field", ["retailer_id", "checkout_group_id"])
def test_missing_or_blank_context_is_rejected(field: str) -> None:
    candidate = _candidate()
    with pytest.raises(ValueError):
        _context(candidate, **{field: ""})


def test_identity_and_quantity_mismatches_fail_closed() -> None:
    candidate = _candidate()
    service = CandidateAllocationEnrichmentService()

    with pytest.raises(ValueError, match="identity"):
        service.enrich(_item(candidate), candidate, _context(candidate, canonical_variant_id="other-variant"))
    with pytest.raises(ValueError, match="quantity"):
        service.enrich(_item(candidate), candidate, _context(candidate, quantity=3))


def test_platform_and_listing_do_not_supply_retailer_or_checkout_group() -> None:
    candidate = _candidate(platform="blinkit", listing_id="listing-9")
    result = CandidateAllocationEnrichmentService().enrich(
        _item(candidate), candidate,
        _context(candidate, retailer_id="retailer-explicit", checkout_group_id="group-explicit"),
    )

    assert result.allocation.retailer_id == "retailer-explicit"
    assert result.allocation.checkout_group_id == "group-explicit"
    assert result.allocation.retailer_id != result.allocation.listing_provenance.platform


def test_distinct_candidates_are_preserved_and_order_is_deterministic() -> None:
    first = _candidate(listing_id="listing-b", observation_id="observation-b", price=200)
    second = _candidate(listing_id="listing-a", observation_id="observation-a", price=100)
    service = CandidateAllocationEnrichmentService()
    contexts = ((_item(first), first, _context(first)), (_item(second), second, _context(second)))

    result = service.enrich_many(contexts)
    reordered = service.enrich_many(tuple(reversed(contexts)))

    assert result == reordered
    assert len(result) == 2
    assert [item.candidate.platform_listing_id for item in result] == ["listing-a", "listing-b"]
    assert [item.candidate.observation_id for item in result] == ["observation-a", "observation-b"]


def test_not_ready_candidate_cannot_be_enriched() -> None:
    candidate = _candidate().model_copy(
        update={
            "readiness": PersistedCandidateReadiness.not_ready_for_allocation,
            "readiness_reason": "missing typed price",
        }
    )
    with pytest.raises(ValueError, match="not ready"):
        CandidateAllocationEnrichmentService().enrich(_item(candidate), candidate, _context(candidate))
