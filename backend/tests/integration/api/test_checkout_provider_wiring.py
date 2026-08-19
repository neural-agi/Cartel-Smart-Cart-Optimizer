from datetime import datetime, timezone

from app.cart_optimization.providers import (
    RegistryCheckoutObservationProvider,
    UnavailableCheckoutObservationProvider,
)
from app.core.config import Settings
from app.cost_intelligence.observation.capture import CheckoutCaptureRegistration
from app.cost_intelligence.observation.capture_contract import (
    CheckoutCaptureArtifact,
    CheckoutCaptureRequest,
    JsonCheckoutCaptureParser,
)
from app.cost_intelligence.observation.capture_service import CheckoutCaptureService
from app.cost_intelligence.observation.checkout_capture import FilesystemCheckoutObservationCorrelationStore
from app.cart_optimization.types import CartItemRequest
from app.data_ingestion.enums import CaptureType
from app.cost_intelligence.observation.types import CheckoutObservation, CheckoutTotalObservation
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference
from app.main import create_application


def _settings(tmp_path, **overrides):
    values = {
        "_env_file": None,
        "data_dir": tmp_path,
        "checkout_observation_provider_mode": "unavailable",
    }
    values.update(overrides)
    return Settings(**values)


def _observation() -> CheckoutObservation:
    return CheckoutObservation(
        platform="checkout-platform",
        source_artifact_reference="checkout-artifact",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(
            EvidenceReference(source_type="test", source_id="checkout-evidence"),
        ),
        totals=(
            CheckoutTotalObservation(
                label="subtotal", amount=Money(currency="INR", minor_units=100)
            ),
        ),
    )


def test_default_application_keeps_checkout_provider_fail_closed(tmp_path) -> None:
    application = create_application(_settings(tmp_path))

    assert isinstance(application.state.cart_planning._checkout_provider, UnavailableCheckoutObservationProvider)
    assert application.state.checkout_capture is not None


def test_registry_mode_wires_store_registration_and_request_plan_provider(tmp_path) -> None:
    application = create_application(
        _settings(tmp_path, checkout_observation_provider_mode="registry")
    )
    registration = application.state.checkout_capture_registration
    provider = application.state.cart_planning._checkout_provider

    assert isinstance(provider, RegistryCheckoutObservationProvider)
    assert application.state.checkout_observation_correlation_store.root_dir == (
        tmp_path / "cost_intelligence" / "checkout_captures"
    )
    correlation = registration.register(
        CheckoutCaptureRegistration(
            request_id="request-1", plan_id="plan-1", observation=_observation()
        )
    )

    assert provider.get_observation(plan_id="plan-1", request_id="request-1") == correlation.observation
    assert provider.get_observation(plan_id="plan-1", request_id="request-2") is None


def test_registry_mode_does_not_cross_resolve_same_plan_id_between_requests(tmp_path) -> None:
    application = create_application(
        _settings(tmp_path, checkout_observation_provider_mode="registry")
    )
    registration = application.state.checkout_capture_registration
    provider = application.state.cart_planning._checkout_provider

    registration.register(
        CheckoutCaptureRegistration(
            request_id="request-1", plan_id="same-plan", observation=_observation()
        )
    )

    assert provider.get_observation(plan_id="same-plan", request_id="request-1") is not None
    assert provider.get_observation(plan_id="same-plan", request_id="request-2") is None


def test_checkout_capture_api_is_unavailable_by_default(tmp_path) -> None:
    from fastapi.testclient import TestClient

    application = create_application(_settings(tmp_path))
    payload = {
        "request_id": "request-1",
        "plan_id": "plan-1",
        "platform": "blinkit",
        "cart_items": [{"item_id": "item-1", "canonical_variant_id": "variant-1", "quantity": 1}],
    }
    with TestClient(application) as client:
        response = client.post("/api/v1/cart/checkout-capture", json=payload)

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_checkout_capture_api_accepts_only_explicit_test_adapter(tmp_path) -> None:
    from fastapi.testclient import TestClient

    application = create_application(
        _settings(tmp_path, checkout_observation_provider_mode="registry")
    )
    request = CheckoutCaptureRequest(
        request_id="request-api",
        plan_id="plan-api",
        platform="test-platform",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),),
    )
    observation = _observation()
    artifact = CheckoutCaptureArtifact(
        artifact_id="api-test-checkout",
        capture_type=CaptureType.CHECKOUT,
        platform=request.platform,
        capture_timestamp=observation.capture_timestamp,
        source_reference=observation.source_artifact_reference,
        capture_version="test-fixture-v1",
        parser_version="checkout-json-v1",
        content_type="application/json",
        request_id=request.request_id,
        plan_id=request.plan_id,
        evidence_references=observation.evidence_references,
        payload=b'{"totals":[{"label":"total","amount":{"currency":"INR","minor_units":100}}]}',
    )

    class FixtureAdapter:
        def capture(self, capture_request):
            return artifact

    application.state.checkout_capture = CheckoutCaptureService(
        adapter=FixtureAdapter(),
        parser=JsonCheckoutCaptureParser(),
        registration=application.state.checkout_capture_registration,
        artifact_store=application.state.checkout_artifact_store,
    )
    with TestClient(application) as client:
        response = client.post("/api/v1/cart/checkout-capture", json=request.model_dump(mode="json"))

    assert response.status_code == 200, response.text
    assert response.json()["request_id"] == "request-api"
    assert response.json()["plan_id"] == "plan-api"
