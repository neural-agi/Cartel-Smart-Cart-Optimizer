from unittest.mock import Mock

from app.cart_optimization.automatic_planning import (
    AutomaticCartItem,
    AutomaticCartPlanningService,
    AutomaticPlanningRequest,
    AutomaticPlanningStatus,
    UnavailablePlanIdProvider,
)
from app.cart_optimization.planning import CartPlanningService
from app.cart_optimization.providers import (
    UnavailableCheckoutGroupProvider,
    UnavailablePlanPolicyProvider,
    UnavailableRetailerIdentityProvider,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.shared.money import Money
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    CartCandidateDiscoveryResult,
    CartCandidateDiscoveryStatus,
)


def _request() -> AutomaticPlanningRequest:
    return AutomaticPlanningRequest(
        cart_id="cart-1",
        items=(AutomaticCartItem(
            item_id="item-1",
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            quantity=2,
        ),),
    )


def test_automatic_planning_preserves_canonical_cart_shape_for_discovery() -> None:
    discovery = Mock()
    discovery.discover.return_value = CartCandidateDiscoveryResult(items=(
        CartCandidateDiscoveryItem(
            item_id="item-1",
            quantity=2,
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            status=CartCandidateDiscoveryStatus.no_candidates,
            reason="no persisted listing candidates available",
        ),
    ))
    service = AutomaticCartPlanningService(
        discovery=discovery,
        planning=Mock(spec=CartPlanningService),
        retailer_provider=UnavailableRetailerIdentityProvider(),
        checkout_group_provider=UnavailableCheckoutGroupProvider(),
        policy_provider=UnavailablePlanPolicyProvider(),
        plan_id_provider=UnavailablePlanIdProvider(),
        checkout_observation_provider=Mock(),
        cost_intelligence=Mock(),
    )

    result = service.plan(_request())

    assert result.status is AutomaticPlanningStatus.UNRESOLVED
    discovery.discover.assert_called_once()
    item = discovery.discover.call_args.args[0].items[0]
    assert item.canonical_product_id == "product-1"
    assert item.canonical_variant_id == "variant-1"
    assert item.quantity == 2


def test_automatic_planning_fails_closed_when_plan_identity_authority_is_missing() -> None:
    from app.services.cart_candidate_discovery import PersistedListingCandidate, PersistedCandidateReadiness
    from app.data_ingestion.types import NormalizedObservation
    from app.cost_intelligence.shared.money import Money

    discovery = Mock()
    discovery.discover.return_value = CartCandidateDiscoveryResult(items=(
        CartCandidateDiscoveryItem(
            item_id="item-1",
            quantity=1,
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            status=CartCandidateDiscoveryStatus.candidates_available,
            candidates=(PersistedListingCandidate(
                platform="blinkit",
                platform_listing_id="listing-1",
                canonical_product_id="product-1",
                canonical_variant_id="variant-1",
                observation_id="observation-1",
                observation=NormalizedObservation.model_construct(
                    observed_selling_price=Money(currency="INR", minor_units=100),
                ),
                readiness=PersistedCandidateReadiness.ready_for_allocation,
            ),),
        ),
    ))
    service = AutomaticCartPlanningService(
        discovery=discovery,
        planning=Mock(spec=CartPlanningService),
        retailer_provider=UnavailableRetailerIdentityProvider(),
        checkout_group_provider=UnavailableCheckoutGroupProvider(),
        policy_provider=UnavailablePlanPolicyProvider(),
        plan_id_provider=UnavailablePlanIdProvider(),
        checkout_observation_provider=Mock(),
        cost_intelligence=Mock(),
    )

    result = service.plan(_request())

    assert result.status is AutomaticPlanningStatus.UNRESOLVED
    assert "authoritative plan identity provider" in result.unresolved_reasons[0]


def test_canonical_cart_validation_rejects_invalid_quantity() -> None:
    import pytest

    with pytest.raises(ValueError, match="quantity must be positive"):
        AutomaticCartItem(
            item_id="item-1",
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            quantity=0,
        )


def test_automatic_planning_links_checkout_observation_to_optimization() -> None:
    from app.services.cart_candidate_discovery import PersistedListingCandidate, PersistedCandidateReadiness
    from app.data_ingestion.types import NormalizedObservation

    discovery = Mock()
    discovery.discover.return_value = CartCandidateDiscoveryResult(items=(
        CartCandidateDiscoveryItem(
            item_id="item-1", quantity=1, canonical_product_id="product-1",
            canonical_variant_id="variant-1", status=CartCandidateDiscoveryStatus.candidates_available,
            candidates=(PersistedListingCandidate(
                platform="blinkit", platform_listing_id="listing-1",
                canonical_product_id="product-1", canonical_variant_id="variant-1",
                observation_id="observation-1",
                observation=NormalizedObservation.model_construct(
                    observed_selling_price=Money(currency="INR", minor_units=100),
                    platform_identifiers=(("retailer_product_id", "637879"),),
                ), readiness=PersistedCandidateReadiness.ready_for_allocation,
            ),),
        ),
    ))

    class Retailer:
        def retailer_id(self, **kwargs):
            return "retailer-1"

    class Group:
        def checkout_group_id(self, **kwargs):
            return "group-1"

    class Policy:
        def resolve(self, **kwargs):
            from app.cart_optimization.enums import PlanFeasibility
            return 0, 0, PlanFeasibility.FEASIBLE, ("checkout-observation",)

    class PlanIds:
        def plan_id(self, **kwargs):
            return "plan-1"

    class Checkout:
        def get_observation(self, **kwargs):
            return CheckoutObservation.model_construct(platform="blinkit")

    class Cost:
        calls = 0

        def evaluate_observation(self, observation):
            self.calls += 1
            return EffectiveCostEvaluationResult(
                evaluation_id="ece-1", context_id="checkout-context-1",
                effective_cost=Money(currency="INR", minor_units=125),
            )

    cost = Cost()
    service = AutomaticCartPlanningService(
        discovery=discovery,
        planning=Mock(spec=CartPlanningService),
        retailer_provider=Retailer(),
        checkout_group_provider=Group(),
        policy_provider=Policy(),
        plan_id_provider=PlanIds(),
        checkout_observation_provider=Checkout(),
        cost_intelligence=cost,
        optimization_policy_version="policy-v1",
    )

    result = service.plan(_request())

    assert result.status is AutomaticPlanningStatus.READY
    assert result.optimization_result is not None
    assert result.optimization_result.request_id == "cart-1"
    assert cost.calls == 1
    assert result.optimization_result.outcome.value in {"selected", "infeasible", "unresolved"}
