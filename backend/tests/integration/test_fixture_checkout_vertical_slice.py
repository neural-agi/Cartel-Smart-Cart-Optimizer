from datetime import datetime, timezone

from app.cart_optimization.types import CandidateItemAllocation, CandidateListingProvenance
from app.cost_intelligence.observation.cart_capture import (
    RetailerCartIdentity,
    RetailerCartLine,
    RetailerCartSnapshot,
)
from app.cost_intelligence.observation.capture import CheckoutCaptureRegistrationService
from app.cost_intelligence.observation.capture_contract import CheckoutCaptureRequest, JsonCheckoutCaptureParser
from app.cost_intelligence.observation.capture_service import CheckoutCaptureService
from app.cost_intelligence.observation.checkout_capture import FilesystemCheckoutObservationCorrelationStore
from app.cost_intelligence.observation.fixture_adapter import FixtureCheckoutCaptureAdapter
from app.cost_intelligence.pipeline.service import CostIntelligencePipelineService
from app.cart_optimization.types import CartItemRequest, CartOptimizationRequest
from app.cost_intelligence.shared.money import Money


def test_fixture_checkout_capture_registers_and_produces_genuine_ece(tmp_path) -> None:
    allocation = CandidateItemAllocation(
        item_id="item-1", canonical_variant_id="variant-1", quantity=2,
        retailer_id="fixture-retailer", checkout_group_id="group-1",
        listing_provenance=CandidateListingProvenance(
            platform="fixture", platform_listing_id="listing-1", observation_id="obs-1",
            retailer_product_id="retailer-product-1",
            observed_selling_price=Money(currency="INR", minor_units=1000),
        ),
    )
    snapshot = RetailerCartSnapshot(
        identity=RetailerCartIdentity(
            retailer_id="fixture-retailer", request_id="request-1", plan_id="plan-1",
            retailer_cart_id="fixture-cart-1", identity_available=True,
        ),
        lines=(RetailerCartLine(
            retailer_product_id="retailer-product-1", quantity=2,
            retailer_id="fixture-retailer", request_id="request-1", plan_id="plan-1",
            source_reference="fixture://cart",
        ),),
    )
    payload = {
        "line_items": [{"label": "retailer-product-1", "quantity_text": "2", "displayed_price": {"currency": "INR", "minor_units": 2000}}],
        "fees": [{"label": "delivery", "amount": {"currency": "INR", "minor_units": 400}}],
        "offers": [{"label": "₹1 OFF", "amount": {"currency": "INR", "minor_units": 100}}],
        "totals": [{"label": "subtotal", "amount": {"currency": "INR", "minor_units": 2000}}, {"label": "total", "amount": {"currency": "INR", "minor_units": 2300}}],
    }
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path / "correlation")
    service = CheckoutCaptureService(
        adapter=FixtureCheckoutCaptureAdapter(snapshot=snapshot, checkout_payload=payload),
        parser=JsonCheckoutCaptureParser(),
        registration=CheckoutCaptureRegistrationService(store),
    )
    request = CheckoutCaptureRequest(
        request_id="request-1", plan_id="plan-1", platform="fixture",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),),
        candidate_allocations=(allocation,),
    )
    correlation = service.capture(request)
    observation = store.get("request-1", "plan-1").observation
    ece = CostIntelligencePipelineService().evaluate_observation(observation)
    assert correlation.request_id == "request-1"
    assert observation.capture_context_reference == "fixture-cart-1"
    assert ece.subtotal == Money(currency="INR", minor_units=2000)
    assert ece.effective_cost == Money(currency="INR", minor_units=2300)
    assert ece.effective_cost != allocation.listing_provenance.observed_selling_price
