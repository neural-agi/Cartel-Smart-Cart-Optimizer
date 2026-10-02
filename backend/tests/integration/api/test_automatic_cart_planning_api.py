from fastapi.testclient import TestClient

from app.core.config import Settings
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


def test_production_user_journey_requires_bearer_and_reports_unavailable_checkout(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        docs_enabled=False,
        auth_required=True,
        auth_tokens="release-user=release-secret",
        data_dir=tmp_path,
        checkout_capture_adapter_mode="unavailable",
        checkout_observation_provider_mode="unavailable",
    )
    with TestClient(create_application(settings)) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        rejected = client.post("/api/v1/cart/optimize", json={"cart_id": "release-1", "items": []})
        optimized = client.post(
            "/api/v1/cart/optimize",
            headers={"Authorization": "Bearer release-secret"},
            json={"cart_id": "release-1", "items": []},
        )

    assert health.status_code == 200
    assert ready.status_code == 200
    assert ready.json()["checks"]["checkout_capture"] == "unavailable"
    assert rejected.status_code == 401
    assert optimized.status_code == 200
    assert optimized.json()["status"] == "unresolved"
    assert optimized.json()["optimization_result"] is None
