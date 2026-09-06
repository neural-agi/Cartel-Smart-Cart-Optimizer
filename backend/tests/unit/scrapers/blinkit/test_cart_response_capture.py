import json

from app.scrapers.blinkit.cart import BlinkitCartResponseParser
from app.scrapers.blinkit.cart_response_capture import persist_cart_response


def valid_payload():
    return {
        "cart_id": "cart-1",
        "lines": [{"product_id": "19512", "retailer_cart_line_id": "line-1", "quantity": 1}],
        "token": "secret",
    }


def test_capture_is_bounded_sanitized_and_replayable(tmp_path):
    path = persist_cart_response(
        root=tmp_path, request_id="request-1", plan_id="plan-1", retailer_product_id="19512",
        status_code=200, endpoint_path="/v5/carts",
        headers={"Content-Type": "application/json", "Authorization": "secret", "Retry-After": "4"},
        body=valid_payload(),
    )
    artifact = json.loads(path.read_text())
    assert artifact["request_id"] == "request-1"
    assert artifact["headers"] == {"content-type": "application/json", "retry-after": "4"}
    assert artifact["body"]["token"] == "[REDACTED]"
    snapshot = BlinkitCartResponseParser().parse(
        artifact["body"], request_id=artifact["request_id"], plan_id=artifact["plan_id"],
        retailer_id="blinkit", source_reference=str(path),
    )
    assert snapshot.identity.retailer_cart_id == "cart-1"
    assert snapshot.lines[0].retailer_cart_line_id == "line-1"
    assert snapshot.lines[0].request_id == "request-1"
    assert snapshot.lines[0].plan_id == "plan-1"


def test_capture_does_not_write_large_body_to_stdout_or_artifact(tmp_path):
    path = persist_cart_response(
        root=tmp_path, request_id="request-1", plan_id="plan-1", retailer_product_id="19512",
        status_code=429, endpoint_path="/v5/carts", body={"large": "x" * 10_000}, max_body_bytes=100,
    )
    artifact = json.loads(path.read_text())
    assert artifact["body"] == {"body_truncated": True, "body_bytes": artifact["body"]["body_bytes"]}


def test_capture_path_is_deterministic_for_correlation(tmp_path):
    kwargs = dict(root=tmp_path, request_id="request-1", plan_id="plan-1", retailer_product_id="19512", status_code=429, endpoint_path="/v5/carts")
    first = persist_cart_response(**kwargs)
    second = persist_cart_response(**kwargs)
    assert first == second
