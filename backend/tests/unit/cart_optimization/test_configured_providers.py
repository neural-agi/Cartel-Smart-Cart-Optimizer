import pytest

from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.providers import (
    ConfiguredCheckoutGroupProvider,
    ConfiguredPlanPolicyProvider,
    ConfiguredRetailerIdentityProvider,
    DeterministicPlanIdProvider,
    PlanningProviderUnavailable,
    parse_mapping,
)
from app.cart_optimization.types import CandidateItemAllocation, CandidateListingProvenance
from app.cost_intelligence.shared.money import Money


def _allocation() -> CandidateItemAllocation:
    return CandidateItemAllocation(
        item_id="item-1", canonical_variant_id="variant-1", quantity=1,
        retailer_id="retailer-1", checkout_group_id="group-1",
        listing_provenance=CandidateListingProvenance(
            platform="blinkit", platform_listing_id="listing-1", observation_id="obs-1",
            observed_selling_price=Money(currency="INR", minor_units=100),
        ),
    )


def test_configured_identity_providers_use_exact_explicit_keys() -> None:
    retailer = ConfiguredRetailerIdentityProvider({"blinkit|listing-1": "opaque-retailer"})
    group = ConfiguredCheckoutGroupProvider({"item-1|opaque-retailer": "group-1"})
    assert retailer.retailer_id(item_id="item-1", platform="blinkit", listing_id="listing-1") == "opaque-retailer"
    assert group.checkout_group_id(plan_id="pending", item_id="item-1", retailer_id="opaque-retailer") == "group-1"
    with pytest.raises(PlanningProviderUnavailable):
        retailer.retailer_id(item_id="item-1", platform="blinkit", listing_id="missing")


def test_configured_policy_requires_explicit_evidence() -> None:
    policy = ConfiguredPlanPolicyProvider(
        inconvenience_penalty_units=2,
        retailer_preference_priority=1,
        feasibility=PlanFeasibility.FEASIBLE,
        evidence=("operator-policy-v1",),
    )
    assert policy.resolve(plan_id="plan-1") == (2, 1, PlanFeasibility.FEASIBLE, ("operator-policy-v1",))
    with pytest.raises(ValueError):
        ConfiguredPlanPolicyProvider(
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            feasibility=PlanFeasibility.FEASIBLE,
            evidence=(),
        )


def test_plan_identity_is_replayable_and_excludes_request_id() -> None:
    provider = DeterministicPlanIdProvider()
    allocation = (_allocation(),)
    first = provider.plan_id(request_id="request-a", combination_index=0, allocations=allocation)
    replay = provider.plan_id(request_id="request-b", combination_index=0, allocations=allocation)
    changed = provider.plan_id(request_id="request-a", combination_index=1, allocations=allocation)
    assert first == replay
    assert first != changed


def test_mapping_parser_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        parse_mapping("[]")
