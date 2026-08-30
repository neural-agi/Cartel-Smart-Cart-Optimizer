from fastapi.testclient import TestClient

from app.main import create_application


def test_automatic_cart_planning_returns_structured_unresolved_result() -> None:
    with TestClient(create_application()) as client:
        response = client.post(
            "/api/v1/cart/optimize",
            json={
                "cart_id": "cart-api-1",
                "items": [{
                    "item_id": "item-1",
                    "canonical_product_id": "product-1",
                    "canonical_variant_id": "variant-1",
                    "quantity": 1,
                }],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "request_id": "cart-api-1",
        "status": "unresolved",
        "optimization_result": None,
        "unresolved_reasons": ["item-1: no persisted listing candidates available"],
    }
