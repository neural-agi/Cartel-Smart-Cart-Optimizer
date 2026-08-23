import pytest

from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.providers import (
    PlanningProviderUnavailable,
    UnavailableCheckoutGroupProvider,
    UnavailablePlanPolicyProvider,
    UnavailableRetailerIdentityProvider,
)


def test_retailer_identity_provider_fails_closed_without_authoritative_source() -> None:
    with pytest.raises(PlanningProviderUnavailable, match="retailer identity"):
        UnavailableRetailerIdentityProvider().retailer_id(
            item_id="item-1", platform="blinkit", listing_id="listing-1"
        )


def test_checkout_group_provider_fails_closed_without_explicit_context() -> None:
    with pytest.raises(PlanningProviderUnavailable, match="checkout group"):
        UnavailableCheckoutGroupProvider().checkout_group_id(
            plan_id="plan-1", item_id="item-1", retailer_id="retailer-1"
        )


def test_plan_policy_provider_fails_closed_without_upstream_policy() -> None:
    with pytest.raises(PlanningProviderUnavailable, match="plan policy"):
        UnavailablePlanPolicyProvider().resolve(plan_id="plan-1")

