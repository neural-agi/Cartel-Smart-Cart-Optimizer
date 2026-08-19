from datetime import datetime, timezone

import pytest

from app.cart_optimization.providers import RegistryCheckoutObservationProvider, UnavailableCheckoutObservationProvider
from app.cost_intelligence.observation.checkout_capture import FilesystemCheckoutObservationCorrelationStore
from app.cost_intelligence.observation.capture import (
    CheckoutCaptureRegistration,
    CheckoutCaptureRegistrationService,
)
from app.cost_intelligence.observation.types import CheckoutObservation, CheckoutTotalObservation
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _observation(total: int = 100) -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="checkout-artifact",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(EvidenceReference(source_type="capture", source_id="capture-1"),),
        totals=(CheckoutTotalObservation(label="subtotal", amount=Money(currency="INR", minor_units=total)),),
    )


def test_plan_correlated_checkout_store_is_deterministic_and_distinct_from_listing_data(tmp_path) -> None:
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path)
    first = store.register("request-1", "plan-1", _observation())
    second = store.register("request-1", "plan-1", _observation())

    assert first == second
    assert store.get("request-1", "plan-1") == first
    assert store.get("request-1", "listing-observation-1") is None
    assert first.plan_id == "plan-1"
    assert first.request_id == "request-1"
    assert first.observation_id.startswith("checkout_observation_")


def test_conflicting_checkout_observation_for_plan_is_rejected(tmp_path) -> None:
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path)
    store.register("request-1", "plan-1", _observation(100))
    with pytest.raises(ValueError, match="conflicting"):
        store.register("request-1", "plan-1", _observation(200))


def test_unknown_plan_lookup_is_explicitly_empty(tmp_path) -> None:
    provider = RegistryCheckoutObservationProvider(
        FilesystemCheckoutObservationCorrelationStore(tmp_path)
    )
    assert provider.get_observation(plan_id="missing-plan", request_id="request-1") is None


def test_registry_provider_returns_only_explicit_plan_correlations(tmp_path) -> None:
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path)
    store.register("request-1", "plan-1", _observation())
    provider = RegistryCheckoutObservationProvider(store)

    assert provider.get_observation(plan_id="plan-1", request_id="request-1") == _observation()
    assert provider.get_observation(plan_id="plan-2", request_id="request-1") is None


def test_same_plan_id_from_different_request_does_not_cross_ownership(tmp_path) -> None:
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path)
    store.register("request-1", "plan-1", _observation())
    assert store.get("request-2", "plan-1") is None
    provider = RegistryCheckoutObservationProvider(store)
    assert provider.get_observation(plan_id="plan-1", request_id="request-2") is None


def test_same_plan_id_can_be_registered_under_a_distinct_request(tmp_path) -> None:
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path)
    first = store.register("request-1", "plan-1", _observation(100))
    second = store.register("request-2", "plan-1", _observation(200))
    assert first != second
    assert store.get("request-1", "plan-1").observation == _observation(100)
    assert store.get("request-2", "plan-1").observation == _observation(200)


def test_unavailable_provider_remains_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="unavailable"):
        UnavailableCheckoutObservationProvider().get_observation(
            plan_id="plan-1", request_id="request-1"
        )


def test_capture_registration_service_preserves_explicit_correlation(tmp_path) -> None:
    service = CheckoutCaptureRegistrationService(
        FilesystemCheckoutObservationCorrelationStore(tmp_path)
    )
    observation = _observation()
    result = service.register(CheckoutCaptureRegistration(
        request_id="request-1", plan_id="plan-1", observation=observation
    ))
    assert result.request_id == "request-1"
    assert result.plan_id == "plan-1"
    assert result.observation == observation
    assert result.observation == observation


def test_capture_registration_service_round_trips_through_provider(tmp_path) -> None:
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path)
    service = CheckoutCaptureRegistrationService(store)
    observation = _observation()
    service.register(CheckoutCaptureRegistration(
        request_id="request-1", plan_id="plan-1", observation=observation
    ))
    provider = RegistryCheckoutObservationProvider(store)
    assert provider.get_observation(plan_id="plan-1", request_id="request-1") == observation


@pytest.mark.parametrize("field", ["request_id", "plan_id"])
def test_capture_registration_requires_correlation_ids(tmp_path, field: str) -> None:
    values = {"request_id": "request-1", "plan_id": "plan-1", "observation": _observation()}
    values[field] = " "
    with pytest.raises(ValueError):
        CheckoutCaptureRegistrationService(
            FilesystemCheckoutObservationCorrelationStore(tmp_path)
        ).register(CheckoutCaptureRegistration(**values))


@pytest.mark.parametrize("value", ["", "  "])
def test_blank_plan_correlation_is_rejected(tmp_path, value: str) -> None:
    with pytest.raises(ValueError, match="plan_id"):
        FilesystemCheckoutObservationCorrelationStore(tmp_path).register("request-1", value, _observation())
