from __future__ import annotations

import pytest

from app.product_intelligence.evidence.types import EvidenceBundle
from app.product_intelligence.models import ListingObservation, PlatformListing
from app.retailer_adapters.contracts import (
    AvailabilityStatus,
    LocationContextKind,
    RetailerLocationContext,
)
from app.retailer_adapters.ingestion_bridge import (
    AdapterListingProjection,
    InvalidAdapterEvidence,
    RetailerAdapterIngestionBridge,
)
from app.retailer_data.contracts import LocationScope
from tests.unit.retailer_adapters.support import (
    availability_observation,
    price_observation,
    product,
    verified_location,
)


def test_projection_uses_existing_governed_models_without_canonical_product() -> None:
    projection = RetailerAdapterIngestionBridge().project(
        product(),
        price=price_observation(),
        availability=availability_observation(),
    )

    assert isinstance(projection, AdapterListingProjection)
    assert isinstance(projection.platform_listing, PlatformListing)
    assert isinstance(projection.listing_observation, ListingObservation)
    assert isinstance(projection.evidence_bundle, EvidenceBundle)
    assert projection.platform_listing.platform_listing_id == "native-1"
    assert projection.platform_listing.platform == "ZEPTO"
    assert projection.listing_observation.displayed_price == "Rs 62"
    assert projection.listing_observation.reference_price == "Rs 65"
    assert projection.listing_observation.availability_signal == "IN_STOCK"
    assert projection.listing_observation.capture_context_reference == "gurugram-1"
    assert projection.pipeline_request.platform_listing == projection.platform_listing
    assert (
        projection.pipeline_request.listing_observation
        == projection.listing_observation
    )


def test_projection_preserves_unknown_price_and_availability() -> None:
    projection = RetailerAdapterIngestionBridge().project(
        product(),
        price=price_observation(amount_minor_units=None),
        availability=availability_observation(status=AvailabilityStatus.UNKNOWN),
    )

    assert projection.listing_observation.displayed_price is None
    assert projection.listing_observation.reference_price is None
    assert projection.price is not None
    assert projection.price.price is None
    assert projection.price.currency == "INR"
    assert projection.availability is not None
    assert projection.availability.status is AvailabilityStatus.UNKNOWN


def test_projection_requires_raw_artifact_reference() -> None:
    item = product()
    item = item.model_copy(update={"raw_payload_reference": None})

    with pytest.raises(InvalidAdapterEvidence, match="raw_payload_reference"):
        RetailerAdapterIngestionBridge().project(item)


def test_projection_rejects_product_mismatch() -> None:
    with pytest.raises(InvalidAdapterEvidence, match="retailer_product_id"):
        RetailerAdapterIngestionBridge().project(
            product(product_id="native-1"),
            price=price_observation(product_id="native-2"),
        )


def test_projection_rejects_location_scope_mismatch() -> None:
    other_location = RetailerLocationContext(
        kind=LocationContextKind.SEARCH_LOCATION,
        scope=LocationScope(
            country_code="IN",
            locality="Delhi",
            scope_id="delhi-1",
        ),
    )
    price = price_observation().model_copy(update={"location": other_location})

    with pytest.raises(InvalidAdapterEvidence, match="location_scope"):
        RetailerAdapterIngestionBridge().project(product(), price=price)


def test_projection_evidence_note_preserves_semantics_and_provenance() -> None:
    projection = RetailerAdapterIngestionBridge().project(
        product(),
        price=price_observation(),
        availability=availability_observation(),
    )

    reference = projection.evidence_bundle.evidence_references[0]
    assert reference.source_type == "retailer_adapter_observation"
    assert reference.source_id == "artifact-1"
    assert "adapter=fake-zepto" in (reference.note or "")
    assert "location_kind=SEARCH_LOCATION" in (reference.note or "")
    assert "price_semantics=SELLING_PRICE" in (reference.note or "")
    assert "availability=IN_STOCK" in (reference.note or "")


def test_projection_uses_explicit_parser_provenance_marker() -> None:
    projection = RetailerAdapterIngestionBridge().project(
        product(),
        price=price_observation(),
    )

    assert (
        projection.listing_observation.parser_version
        == "retailer-adapter:fake-zepto:v1"
    )
    assert projection.evidence_bundle.parser_version == (
        "retailer-adapter:fake-zepto:v1"
    )


def test_projection_preserves_retailer_native_identifier() -> None:
    projection = RetailerAdapterIngestionBridge().project(product())

    assert projection.platform_listing.platform_listing_id == "native-1"
    assert projection.source_provenance.adapter_id == "fake-zepto"
    assert projection.location.scope.scope_id == "gurugram-1"
    assert projection.price is None
    assert projection.availability is None


def test_projection_does_not_infer_delivery_from_search_location() -> None:
    projection = RetailerAdapterIngestionBridge().project(product())

    assert projection.location.kind is LocationContextKind.SEARCH_LOCATION
    assert projection.location.verified_at is None


def test_projection_accepts_explicit_verified_delivery_location() -> None:
    item = product().model_copy(update={"location": verified_location()})

    projection = RetailerAdapterIngestionBridge().project(item)

    assert projection.location.kind is LocationContextKind.VERIFIED_DELIVERY_LOCATION
    assert projection.location.verified_at is not None
    assert projection.location.retailer_location_reference == "store:gurugram-1"
