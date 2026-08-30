from unittest.mock import Mock

from app.cart_optimization.automatic_planning import (
    AutomaticCartItem,
    AutomaticCartPlanningService,
    AutomaticPlanningRequest,
)
from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.planning import CartPlanningService
from app.cart_optimization.providers import (
    ConfiguredCheckoutGroupProvider,
    ConfiguredPlanPolicyProvider,
    ConfiguredRetailerIdentityProvider,
)
from app.cart_optimization.automatic_planning import PlanIdProvider
from app.cart_optimization.types import CartItemRequest, CandidateItemAllocation
from app.cost_intelligence.observation.cart_capture import (
    RetailerCartIdentity,
    RetailerCartLine,
    RetailerCartSnapshot,
)
from app.cost_intelligence.observation.capture import CheckoutCaptureRegistrationService
from app.cost_intelligence.observation.capture_contract import JsonCheckoutCaptureParser
from app.cost_intelligence.observation.capture_service import CheckoutCaptureService
from app.cost_intelligence.observation.checkout_capture import FilesystemCheckoutObservationCorrelationStore
from app.cost_intelligence.observation.fixture_adapter import FixtureCheckoutCaptureAdapter
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    CartCandidateDiscoveryResult,
    CartCandidateDiscoveryStatus,
    PersistedCandidateReadiness,
    PersistedListingCandidate,
)
from app.data_ingestion.types import NormalizedObservation
from app.cost_intelligence.shared.money import Money
from app.cost_intelligence.observation.checkout_capture import CheckoutObservationCorrelationStore


def test_automatic_planning_invokes_fixture_capture_and_evaluates_ece(tmp_path) -> None:
    discovery = Mock()
    discovery.discover.return_value = CartCandidateDiscoveryResult(items=(
        CartCandidateDiscoveryItem(
            item_id="item-1", quantity=2, canonical_product_id="product-1",
            canonical_variant_id="variant-1", status=CartCandidateDiscoveryStatus.candidates_available,
            candidates=(PersistedListingCandidate(
                platform="fixture", platform_listing_id="listing-1",
                canonical_product_id="product-1", canonical_variant_id="variant-1",
                observation_id="observation-1",
                observation=NormalizedObservation.model_construct(
                    observed_selling_price=Money(currency="INR", minor_units=1000),
                    platform_identifiers=(("retailer_product_id", "retailer-product-1"),),
                ), readiness=PersistedCandidateReadiness.ready_for_allocation,
            ),),
        ),
    ))
    store: CheckoutObservationCorrelationStore = FilesystemCheckoutObservationCorrelationStore(tmp_path / "captures")
    snapshot = RetailerCartSnapshot(
        identity=RetailerCartIdentity(
            retailer_id="fixture-retailer", request_id="cart-1", plan_id="plan-0",
            retailer_cart_id="fixture-cart-1", identity_available=True,
        ),
        lines=(RetailerCartLine(
            retailer_product_id="retailer-product-1", quantity=2,
            retailer_id="fixture-retailer", request_id="cart-1", plan_id="plan-0",
            source_reference="fixture://cart",
        ),),
    )
    # The plan-ID provider is deterministic; the fixture is keyed to its result.
    class PlanIds:
        def plan_id(self, **kwargs): return "plan-0"
    class CheckoutProvider:
        def get_observation(self, *, request_id, plan_id):
            record = store.get(request_id, plan_id)
            return record.observation if record else None
    capture = CheckoutCaptureService(
        adapter=FixtureCheckoutCaptureAdapter(snapshot=snapshot, checkout_payload={
            "line_items": [{"label": "retailer-product-1", "quantity_text": "2", "displayed_price": {"currency": "INR", "minor_units": 2000}}],
            "fees": [{"label": "delivery", "amount": {"currency": "INR", "minor_units": 400}}],
            "offers": [{"label": "₹1 OFF", "amount": {"currency": "INR", "minor_units": 100}}],
            "totals": [{"label": "subtotal", "amount": {"currency": "INR", "minor_units": 2000}}, {"label": "total", "amount": {"currency": "INR", "minor_units": 2300}}],
        }), parser=JsonCheckoutCaptureParser(), registration=CheckoutCaptureRegistrationService(store)
    )
    class Policy:
        def resolve(self, **kwargs): return 0, 0, PlanFeasibility.FEASIBLE, ("fixture evidence",)
    class Retailer:
        def retailer_id(self, **kwargs): return "fixture-retailer"
    class Groups:
        def checkout_group_id(self, **kwargs): return "group-1"
    service = AutomaticCartPlanningService(
        discovery=discovery, planning=Mock(spec=CartPlanningService),
        retailer_provider=Retailer(), checkout_group_provider=Groups(), policy_provider=Policy(),
        plan_id_provider=PlanIds(), checkout_observation_provider=CheckoutProvider(),
        cost_intelligence=__import__("app.cost_intelligence.pipeline.service", fromlist=["CostIntelligencePipelineService"]).CostIntelligencePipelineService(),
        checkout_capture=capture,
        optimization_policy_version="policy-v1",
    )
    result = service.plan(AutomaticPlanningRequest(cart_id="cart-1", items=(AutomaticCartItem(
        item_id="item-1", canonical_product_id="product-1", canonical_variant_id="variant-1", quantity=2,
    ),)))
    assert result.status.value == "ready"
    assert result.optimization_result is not None
    assert result.optimization_result.chosen_plan is not None
    observation = store.get("cart-1", "plan-0").observation
    ece = service._cost_intelligence.evaluate_observation(observation)
    assert ece.effective_cost == Money(currency="INR", minor_units=2300)
    assert result.optimization_result.chosen_plan.effective_cost_evaluation_reference.effective_cost_evaluation_id == ece.evaluation_id
