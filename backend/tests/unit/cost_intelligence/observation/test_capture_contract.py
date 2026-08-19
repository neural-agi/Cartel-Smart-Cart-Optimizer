import json
from datetime import datetime, timezone

import pytest
from unittest.mock import Mock

from app.cart_optimization.types import CartItemRequest
from app.cost_intelligence.observation.capture import CheckoutCaptureRegistrationService
from app.cost_intelligence.observation.capture_contract import (
    CheckoutCaptureArtifact,
    CheckoutCaptureRequest,
    JsonCheckoutCaptureParser,
)
from app.cost_intelligence.observation.capture_service import (
    CheckoutCaptureAdapterUnavailable,
    CheckoutCaptureService,
    UnavailableCheckoutCaptureAdapter,
)
from app.cost_intelligence.observation.checkout_capture import FilesystemCheckoutObservationCorrelationStore
from app.data_ingestion.enums import CaptureType
from app.product_intelligence.models import EvidenceReference
from app.data_ingestion.artifact_store import LocalFilesystemArtifactStore
from app.data_ingestion.artifact_store import ArtifactAlreadyExists
from app.data_ingestion.artifact_store import StorageReference


def _request(request_id="request-1", plan_id="plan-1", platform="test-platform") -> CheckoutCaptureRequest:
    return CheckoutCaptureRequest(
        request_id=request_id,
        plan_id=plan_id,
        platform=platform,
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),),
    )


def _artifact(request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact:
    return CheckoutCaptureArtifact(
        artifact_id="synthetic-checkout-artifact",
        capture_type=CaptureType.CHECKOUT,
        platform=request.platform,
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_reference="synthetic://checkout-fixture",
        capture_version="test-fixture-v1",
        parser_version="checkout-json-v1",
        content_type="application/json",
        request_id=request.request_id,
        plan_id=request.plan_id,
        evidence_references=(EvidenceReference(source_type="test-fixture", source_id="checkout-1"),),
        payload=json.dumps({
            "line_items": [{"label": "Milk", "quantity_text": "2", "displayed_price": {"currency": "INR", "minor_units": 100}}],
            "fees": [{"label": "delivery", "amount": {"currency": "INR", "minor_units": 20}}],
            "offers": [{"label": "discount", "amount": {"currency": "INR", "minor_units": 10}}],
            "totals": [{"label": "subtotal", "amount": {"currency": "INR", "minor_units": 200}}, {"label": "total", "amount": {"currency": "INR", "minor_units": 210}}],
        }).encode(),
    )


class _FixtureAdapter:
    def __init__(self, artifact: CheckoutCaptureArtifact) -> None:
        self.artifact = artifact

    def capture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact:
        return self.artifact


def test_fixture_artifact_parses_and_registers_without_listing_conversion(tmp_path) -> None:
    request = _request()
    store = FilesystemCheckoutObservationCorrelationStore(tmp_path)
    service = CheckoutCaptureService(
        adapter=_FixtureAdapter(_artifact(request)),
        parser=JsonCheckoutCaptureParser(),
        registration=CheckoutCaptureRegistrationService(store),
        artifact_store=LocalFilesystemArtifactStore(tmp_path / "raw", "checkout"),
    )

    correlation = service.capture(request)

    assert correlation.request_id == request.request_id
    assert correlation.plan_id == request.plan_id
    assert correlation.observation.source_artifact_reference != "synthetic://checkout-fixture"
    assert any(
        evidence.source_type == "checkout_capture_source"
        and evidence.source_id == "synthetic://checkout-fixture"
        for evidence in correlation.observation.evidence_references
    )
    assert correlation.observation.totals[-1].amount.minor_units == 210
    assert correlation.observation.fees[0].amount.minor_units == 20


def test_parser_rejects_malformed_or_non_checkout_artifacts() -> None:
    request = _request()
    artifact = _artifact(request)
    with pytest.raises(ValueError):
        JsonCheckoutCaptureParser().parse(artifact.model_copy(update={"payload": b"not-json"}))
    with pytest.raises(ValueError):
        CheckoutCaptureArtifact.model_validate(
            artifact.model_dump(mode="python", exclude={"capture_type"})
        )


def test_json_parser_rejects_non_json_content_type() -> None:
    artifact = _artifact(_request()).model_copy(update={"content_type": "text/html"})

    with pytest.raises(ValueError, match="application/json"):
        JsonCheckoutCaptureParser().parse(artifact)


def test_json_parser_accepts_json_content_type_parameters() -> None:
    artifact = _artifact(_request()).model_copy(
        update={"content_type": "application/json; charset=utf-8"}
    )

    parsed = JsonCheckoutCaptureParser().parse(artifact)

    assert parsed.parser_version == artifact.parser_version


def test_parser_artifact_metadata_cannot_be_overridden_by_payload() -> None:
    request = _request()
    artifact = _artifact(request)
    payload = json.loads(artifact.payload)
    payload.update({
        "source_artifact_reference": "forged-source",
        "parser_version": "forged-parser",
    })
    parsed = JsonCheckoutCaptureParser().parse(
        artifact.model_copy(update={"payload": json.dumps(payload).encode()})
    )

    assert parsed.source_artifact_reference == artifact.source_reference
    assert parsed.parser_version == artifact.parser_version


def test_capture_service_rejects_artifact_for_different_ownership(tmp_path) -> None:
    request = _request()
    artifact = _artifact(request).model_copy(update={"plan_id": "other-plan"})
    service = CheckoutCaptureService(
        adapter=_FixtureAdapter(artifact),
        parser=JsonCheckoutCaptureParser(),
        registration=CheckoutCaptureRegistrationService(
            FilesystemCheckoutObservationCorrelationStore(tmp_path)
        ),
    )

    with pytest.raises(ValueError, match="ownership"):
        service.capture(request)


def test_artifact_store_keeps_same_payload_under_distinct_capture_artifacts(tmp_path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "raw", "checkout")
    first = _artifact(_request("request-1", "plan-1")).model_copy(
        update={"artifact_id": "checkout-artifact-1"}
    )
    second = _artifact(_request("request-2", "plan-2")).model_copy(
        update={"artifact_id": "checkout-artifact-2"}
    )
    first_service = CheckoutCaptureService(
        adapter=_FixtureAdapter(first),
        parser=JsonCheckoutCaptureParser(),
        registration=CheckoutCaptureRegistrationService(
            FilesystemCheckoutObservationCorrelationStore(tmp_path / "correlations")
        ),
        artifact_store=store,
    )
    second_service = CheckoutCaptureService(
        adapter=_FixtureAdapter(second),
        parser=JsonCheckoutCaptureParser(),
        registration=CheckoutCaptureRegistrationService(
            FilesystemCheckoutObservationCorrelationStore(tmp_path / "correlations")
        ),
        artifact_store=store,
    )

    first_result = first_service.capture(_request("request-1", "plan-1"))
    second_result = second_service.capture(_request("request-2", "plan-2"))

    assert first_result.observation.source_artifact_reference != second_result.observation.source_artifact_reference


def test_artifact_store_rejects_changed_payload_for_same_artifact_identity(tmp_path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path / "raw", "checkout")
    artifact = _artifact(_request())
    service = CheckoutCaptureService(
        adapter=_FixtureAdapter(artifact),
        parser=JsonCheckoutCaptureParser(),
        registration=CheckoutCaptureRegistrationService(
            FilesystemCheckoutObservationCorrelationStore(tmp_path / "correlations")
        ),
        artifact_store=store,
    )
    service.capture(_request())
    changed = artifact.model_copy(update={"payload": artifact.payload + b" "})
    with pytest.raises(ArtifactAlreadyExists):
        CheckoutCaptureService(
            adapter=_FixtureAdapter(changed),
            parser=JsonCheckoutCaptureParser(),
            registration=CheckoutCaptureRegistrationService(
                FilesystemCheckoutObservationCorrelationStore(tmp_path / "correlations")
            ),
            artifact_store=store,
        ).capture(_request())


def _mock_store() -> Mock:
    store = Mock()
    store.store.return_value = StorageReference(
        storage_reference_id="durable-checkout-reference",
        artifact_id="synthetic-checkout-artifact",
        store_namespace="checkout",
        storage_backend="fake",
        content_digest="a" * 64,
        content_type="application/json",
    )
    return store


def test_ownership_failure_occurs_before_artifact_publication() -> None:
    request = _request()
    store = _mock_store()
    service = CheckoutCaptureService(
        adapter=_FixtureAdapter(_artifact(request).model_copy(update={"request_id": "other-request"})),
        parser=JsonCheckoutCaptureParser(),
        registration=Mock(),
        artifact_store=store,
    )

    with pytest.raises(ValueError, match="ownership"):
        service.capture(request)

    store.store.assert_not_called()


def test_parser_failure_does_not_register_but_retains_published_raw_evidence() -> None:
    request = _request()
    store = _mock_store()
    registration = Mock()
    parser = Mock()
    parser.parse.side_effect = ValueError("malformed checkout")
    service = CheckoutCaptureService(
        adapter=_FixtureAdapter(_artifact(request)),
        parser=parser,
        registration=registration,
        artifact_store=store,
    )

    with pytest.raises(ValueError, match="malformed checkout"):
        service.capture(request)

    store.store.assert_called_once()
    registration.register.assert_not_called()


def test_registration_failure_does_not_return_success_after_publication() -> None:
    request = _request()
    store = _mock_store()
    registration = Mock()
    registration.register.side_effect = ValueError("registration conflict")
    service = CheckoutCaptureService(
        adapter=_FixtureAdapter(_artifact(request)),
        parser=JsonCheckoutCaptureParser(),
        registration=registration,
        artifact_store=store,
    )

    with pytest.raises(ValueError, match="registration conflict"):
        service.capture(request)

    store.store.assert_called_once()


def test_unavailable_adapter_fails_closed() -> None:
    with pytest.raises(CheckoutCaptureAdapterUnavailable):
        UnavailableCheckoutCaptureAdapter().capture(_request())


@pytest.mark.parametrize("field", ["request_id", "plan_id", "platform"])
def test_capture_request_requires_ownership_fields(field: str) -> None:
    with pytest.raises(ValueError):
        _request(**{field: " "})


def test_capture_request_requires_cart_items() -> None:
    with pytest.raises(ValueError):
        CheckoutCaptureRequest(
            request_id="request-1", plan_id="plan-1", platform="test", cart_items=()
        )
