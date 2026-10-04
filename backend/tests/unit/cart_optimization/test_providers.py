import pytest

from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.providers import (
    ProductionCheckoutObservationProvider,
    PlanningProviderUnavailable,
    UnavailableCheckoutGroupProvider,
    UnavailablePlanPolicyProvider,
    UnavailableRetailerIdentityProvider,
)
from app.cost_intelligence.observation.types import CheckoutObservation


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


@pytest.mark.parametrize("source,parser", [
    ("fixture://capture/1", "parser-v1"),
    ("https://blinkit.com/checkout", "fixture-parser-v1"),
])
def test_consumer_provider_rejects_fixture_checkout_evidence(source, parser):
    class Provider:
        def get_observation(self, *, plan_id, request_id):
            return CheckoutObservation(
                platform="BLINKIT", source_artifact_reference=source,
                capture_timestamp="2026-01-01T00:00:00Z", parser_version=parser,
            )

    with pytest.raises(PlanningProviderUnavailable, match="fixture checkout evidence"):
        ProductionCheckoutObservationProvider(Provider()).get_observation(
            plan_id="plan-1", request_id="request-1"
        )


def test_consumer_provider_preserves_non_fixture_checkout_observation():
    observation = CheckoutObservation(
        platform="BLINKIT", source_artifact_reference="https://blinkit.com/checkout",
        capture_timestamp="2026-01-01T00:00:00Z", parser_version="blinkit-checkout-v1",
    )

    class Provider:
        def get_observation(self, *, plan_id, request_id):
            assert (request_id, plan_id) == ("request-1", "plan-1")
            return observation

    assert ProductionCheckoutObservationProvider(Provider()).get_observation(
        plan_id="plan-1", request_id="request-1"
    ) == observation
