import pytest

from app.cost_intelligence.observation.cart_capture import CartOwnershipVerifier, CartVerificationStatus
from app.scrapers.blinkit.cart import BlinkitCartResponseError, BlinkitCartResponseParser


def test_cart_response_preserves_authoritative_identity_and_quantity() -> None:
    snapshot = BlinkitCartResponseParser().parse(
        {"cart_id": "cart-1", "lines": [{"product_id": "637879", "retailer_cart_line_id": "line-1", "quantity": 1}]},
        request_id="request-1", plan_id="plan-1", retailer_id="blinkit", source_reference="https://blinkit.com/v5/carts",
    )
    assert snapshot.identity.retailer_cart_id == "cart-1"
    assert snapshot.lines[0].retailer_product_id == "637879"
    assert snapshot.lines[0].retailer_cart_line_id == "line-1"
    assert snapshot.lines[0].quantity == 1


@pytest.mark.parametrize("payload", [
    {"lines": []},
    {"cart_id": "cart-1", "lines": [{"product_id": "637879", "quantity": 1}]},
    {"cart_id": "cart-1", "lines": [{"product_id": "637879", "line_id": "array-local-id", "quantity": 1}]},
])
def test_cart_response_requires_authoritative_ids(payload) -> None:
    with pytest.raises(BlinkitCartResponseError):
        BlinkitCartResponseParser().parse(payload, request_id="request-1", plan_id="plan-1", retailer_id="blinkit", source_reference="fixture://cart")


def test_cart_response_carries_both_correlation_keys_into_identity_and_line() -> None:
    snapshot = BlinkitCartResponseParser().parse(
        {"cart_id": "cart-1", "lines": [{"product_id": "637879", "retailer_cart_line_id": "line-1", "quantity": 1}]},
        request_id="request-a", plan_id="plan-a", retailer_id="blinkit", source_reference="fixture://cart",
    )
    assert snapshot.identity.request_id == "request-a"
    assert snapshot.identity.plan_id == "plan-a"
    assert snapshot.lines[0].request_id == "request-a"
    assert snapshot.lines[0].plan_id == "plan-a"
