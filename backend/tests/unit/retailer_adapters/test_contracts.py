from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.cost_intelligence.shared.money import Money
from app.retailer_adapters.contracts import (
    AcquisitionMetadata,
    AdapterCapability,
    AdapterOutcome,
    AvailabilityObservation,
    AvailabilityResult,
    AvailabilityStatus,
    CapabilityDeclaration,
    CapabilityStatus,
    ConnectionValidationResult,
    ConnectionValidationState,
    LocationContextKind,
    PriceObservation,
    PriceResult,
    PriceSemantics,
    ProductDetailsResult,
    ProductSearchResult,
    RetailerLocationContext,
    RetailerProduct,
    SourceProvenance,
)
from app.retailer_data.contracts import AcquisitionMethod, LocationScope
from tests.unit.retailer_adapters.support import (
    NOW,
    acquisition,
    availability_observation,
    price_observation,
    product,
    search_location,
    verified_location,
)


def test_search_location_never_claims_verified_delivery() -> None:
    with pytest.raises(ValidationError, match="search locations"):
        RetailerLocationContext(
            kind=LocationContextKind.SEARCH_LOCATION,
            scope=LocationScope(
                country_code="IN",
                locality="Gurugram",
                scope_id="gurugram-1",
            ),
            verified_at=NOW,
        )


def test_verified_delivery_location_requires_reference_and_timestamp() -> None:
    with pytest.raises(ValidationError, match="retailer reference"):
        RetailerLocationContext(
            kind=LocationContextKind.VERIFIED_DELIVERY_LOCATION,
            scope=LocationScope(
                country_code="IN",
                locality="Gurugram",
                scope_id="gurugram-1",
            ),
        )


def test_location_provenance_is_preserved() -> None:
    location = verified_location()

    assert location.kind is LocationContextKind.VERIFIED_DELIVERY_LOCATION
    assert location.scope.scope_id == "gurugram-1"
    assert location.retailer_location_reference == "store:gurugram-1"
    assert location.verified_at == NOW


def test_unknown_price_remains_unknown_and_preserves_currency() -> None:
    observation = price_observation(amount_minor_units=None, currency="INR")

    assert observation.price is None
    assert observation.currency == "INR"
    assert observation.effective_currency == "INR"


def test_price_currency_must_match_observed_money() -> None:
    with pytest.raises(ValidationError, match="currency must match"):
        PriceObservation(
            retailer_id="BLINKIT",
            retailer_product_id="native-1",
            price=Money(currency="INR", minor_units=6200),
            currency="USD",
            price_semantics=PriceSemantics.SELLING_PRICE,
            location=search_location(),
            acquisition=acquisition(AdapterCapability.PRICE_ACQUISITION),
            captured_at=NOW,
        )


def test_checkout_price_requires_checkout_evidence() -> None:
    with pytest.raises(ValidationError, match="checkout evidence"):
        price_observation(semantics=PriceSemantics.CHECKOUT_PRICE)

    observation = price_observation(
        semantics=PriceSemantics.CHECKOUT_PRICE,
        checkout_evidence_reference="checkout-observation-1",
    )
    assert observation.checkout_evidence_reference == "checkout-observation-1"


def test_price_observation_requires_price_acquisition_metadata() -> None:
    with pytest.raises(ValidationError, match="price acquisition"):
        PriceObservation(
            retailer_id="BLINKIT",
            retailer_product_id="native-1",
            price=Money(currency="INR", minor_units=6200),
            currency="INR",
            price_semantics=PriceSemantics.SELLING_PRICE,
            location=search_location(),
            acquisition=acquisition(AdapterCapability.AVAILABILITY_ACQUISITION),
            captured_at=NOW,
        )


def test_unknown_availability_remains_unknown() -> None:
    observation = availability_observation(status=AvailabilityStatus.UNKNOWN)

    assert observation.status is AvailabilityStatus.UNKNOWN
    assert observation.raw_signal == "UNKNOWN"


def test_availability_observation_requires_availability_metadata() -> None:
    with pytest.raises(ValidationError, match="availability acquisition"):
        AvailabilityObservation(
            retailer_id="BLINKIT",
            retailer_product_id="native-1",
            status=AvailabilityStatus.IN_STOCK,
            location=search_location(),
            acquisition=acquisition(AdapterCapability.PRICE_ACQUISITION),
            captured_at=NOW,
        )


def test_retailer_response_time_is_distinct_from_retailer_update_time() -> None:
    later = NOW + timedelta(minutes=5)
    with pytest.raises(ValidationError, match="cannot be later"):
        AcquisitionMetadata(
            adapter_id="fake",
            retailer_id="BLINKIT",
            operation=AdapterCapability.PRICE_ACQUISITION,
            acquisition_method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
            response_received_at=NOW,
            retailer_updated_at=later,
        )

    metadata = AcquisitionMetadata(
        adapter_id="fake",
        retailer_id="BLINKIT",
        operation=AdapterCapability.PRICE_ACQUISITION,
        acquisition_method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
        response_received_at=NOW,
        retailer_updated_at=NOW - timedelta(minutes=1),
    )
    assert metadata.retailer_updated_at == NOW - timedelta(minutes=1)
    assert metadata.response_received_at == NOW


def test_retailer_product_preserves_native_identity_and_provenance() -> None:
    item = product()

    assert item.retailer_product_id == "native-1"
    assert item.identifiers == (("sku", "native-1"),)
    assert item.provenance.retailer_id == "ZEPTO"
    assert item.provenance.adapter_id == "fake-zepto"
    assert item.captured_at == NOW
    assert item.raw_payload_reference == "artifact-1"


def test_retailer_product_rejects_provenance_retailer_mismatch() -> None:
    with pytest.raises(ValidationError, match="provenance retailer"):
        RetailerProduct(
            retailer_id="BLINKIT",
            retailer_product_id="native-1",
            title="Milk",
            location=search_location(),
            provenance=SourceProvenance(
                adapter_id="fake",
                retailer_id="ZEPTO",
                acquisition_method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
            ),
            captured_at=NOW,
        )


def test_success_requires_acquisition_metadata() -> None:
    with pytest.raises(ValidationError, match="acquisition metadata"):
        ProductSearchResult(outcome=AdapterOutcome.SUCCESS)


def test_failure_requires_a_reason() -> None:
    with pytest.raises(ValidationError, match="reason_code"):
        ProductSearchResult(outcome=AdapterOutcome.UNSUPPORTED)


def test_failed_search_must_not_carry_products() -> None:
    with pytest.raises(ValidationError, match="must not carry products"):
        ProductSearchResult(
            outcome=AdapterOutcome.ACCESS_DENIED,
            reason_code="denied",
            products=(product(),),
        )


def test_successful_details_require_a_product() -> None:
    with pytest.raises(ValidationError, match="require a product"):
        ProductDetailsResult(
            outcome=AdapterOutcome.SUCCESS,
            acquisition=acquisition(AdapterCapability.PRODUCT_DETAILS),
        )


def test_out_of_stock_requires_an_out_of_stock_observation() -> None:
    with pytest.raises(ValidationError, match="out-of-stock"):
        AvailabilityResult(
            outcome=AdapterOutcome.OUT_OF_STOCK,
            availability=availability_observation(status=AvailabilityStatus.IN_STOCK),
        )

    result = AvailabilityResult(
        outcome=AdapterOutcome.OUT_OF_STOCK,
        availability=availability_observation(status=AvailabilityStatus.OUT_OF_STOCK),
    )
    assert result.availability is not None
    assert result.availability.status is AvailabilityStatus.OUT_OF_STOCK


def test_successful_availability_rejects_out_of_stock_status() -> None:
    with pytest.raises(ValidationError, match="OUT_OF_STOCK outcome"):
        AvailabilityResult(
            outcome=AdapterOutcome.SUCCESS,
            availability=availability_observation(status=AvailabilityStatus.OUT_OF_STOCK),
            acquisition=acquisition(AdapterCapability.AVAILABILITY_ACQUISITION),
        )


def test_successful_connection_validation_requires_valid_state() -> None:
    with pytest.raises(ValidationError, match="VALID"):
        ConnectionValidationResult(
            outcome=AdapterOutcome.SUCCESS,
            validation=ConnectionValidationState.UNKNOWN,
            acquisition=acquisition(AdapterCapability.CONNECTION_VALIDATION),
        )


def test_user_action_connection_validation_requires_reauth_state() -> None:
    with pytest.raises(ValidationError, match="REAUTH_REQUIRED"):
        ConnectionValidationResult(
            outcome=AdapterOutcome.REQUIRES_USER_ACTION,
            reason_code="reauth",
        )


def test_capability_declaration_status_is_explicit() -> None:
    declaration = CapabilityDeclaration(
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        status=CapabilityStatus.NOT_VERIFIED,
        reason_code="not_tested",
    )
    assert declaration.status is CapabilityStatus.NOT_VERIFIED
    assert declaration.reason_code == "not_tested"


def test_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        PriceObservation(
            retailer_id="BLINKIT",
            retailer_product_id="native-1",
            price=Money(currency="INR", minor_units=6200),
            currency="INR",
            price_semantics=PriceSemantics.SELLING_PRICE,
            location=search_location(),
            acquisition=acquisition(AdapterCapability.PRICE_ACQUISITION),
            captured_at=datetime.fromisoformat("2026-06-01T12:00:00"),
        )


def test_price_result_success_requires_observation() -> None:
    with pytest.raises(ValidationError, match="price observation"):
        PriceResult(
            outcome=AdapterOutcome.SUCCESS,
            acquisition=acquisition(AdapterCapability.PRICE_ACQUISITION),
        )


def test_price_result_failure_must_not_carry_observation() -> None:
    with pytest.raises(ValidationError, match="must not carry a price"):
        PriceResult(
            outcome=AdapterOutcome.TEMPORARY_FAILURE,
            reason_code="timeout",
            price=price_observation(),
        )


def test_utc_normalization_preserves_instant() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    observation = price_observation()
    item = RetailerProduct(
        retailer_id="BLINKIT",
        retailer_product_id="native-2",
        title="Curd",
        location=search_location(),
        provenance=SourceProvenance(
            adapter_id="fake",
            retailer_id="BLINKIT",
            acquisition_method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
        ),
        captured_at=datetime(2026, 6, 1, 17, 30, tzinfo=offset),
    )
    assert item.captured_at == observation.captured_at
    assert item.captured_at.tzinfo == timezone.utc
