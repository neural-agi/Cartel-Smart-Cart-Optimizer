"""Capture-timestamp integrity at consumer boundaries (scenarios 5-9)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.data_ingestion import (
    FilesystemObservationRegistry,
    InMemoryObservationRegistry,
)
from app.data_ingestion.timestamp_integrity import CaptureTimestampRejectionReason
from app.product_intelligence.models import (
    IdentityStatus,
    ProductLifecycleStatus,
    VariantLifecycleStatus,
)
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItemRequest,
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryService,
    CartCandidateDiscoveryStatus,
    PersistedCandidateReadiness,
)
from app.services.product_search import (
    ProductSearchRequest,
    ProductSearchService,
    latest_governed_observation_ids,
)
from tests.unit.timestamp_support import (
    FrozenClock,
    make_observation,
    write_stored_observation,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)


def _catalog() -> SimpleNamespace:
    product = SimpleNamespace(
        canonical_product_id="product-1",
        product_identity_status=IdentityStatus.established,
        lifecycle_status=ProductLifecycleStatus.active,
        canonical_display_name="Amul Taaza",
        product_type="milk",
        identity_attributes=(),
        brand_reference=SimpleNamespace(display_label="Amul"),
    )
    variant = SimpleNamespace(
        canonical_variant_id="variant-1",
        canonical_product_id="product-1",
        variant_identity_status=IdentityStatus.established,
        lifecycle_status=VariantLifecycleStatus.active,
        variant_identity_attributes=(),
        pack_configuration=SimpleNamespace(
            total_declared_content=SimpleNamespace(value="500", unit="ml"),
            consumer_unit_count=1,
            pack_configuration_status="complete",
        ),
    )
    return SimpleNamespace(
        load_state=lambda: SimpleNamespace(products=(product,), variants=(variant,)),
        get_product=lambda product_id: product if product_id == "product-1" else None,
        get_variant=lambda variant_id: variant if variant_id == "variant-1" else None,
    )


def _association(observation, listing_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        canonical_product_id="product-1",
        canonical_variant_id="variant-1",
        platform="ZEPTO",
        platform_listing_id=listing_id,
        observation_id=observation.observation_id,
    )


def _search(registry, associations, clock: FrozenClock) -> ProductSearchService:
    return ProductSearchService(
        catalog=_catalog(),
        association_registry=SimpleNamespace(all=lambda: tuple(associations)),
        observation_registry=registry,
        clock=clock,
    )


def _discovery(registry, associations, clock: FrozenClock) -> CartCandidateDiscoveryService:
    return CartCandidateDiscoveryService(
        catalog=_catalog(),
        association_registry=SimpleNamespace(all=lambda: tuple(associations)),
        observation_registry=registry,
        clock=clock,
    )


def _item_request() -> CartCandidateDiscoveryRequest:
    return CartCandidateDiscoveryRequest(
        items=(
            CartCandidateDiscoveryItemRequest(
                item_id="item-1",
                quantity=1,
                canonical_product_id="product-1",
                canonical_variant_id="variant-1",
            ),
        )
    )


# Scenario 5
def test_scenario_5_malformed_historical_artifact_does_not_crash_search(tmp_path) -> None:
    clock = FrozenClock(NOW)
    registry = FilesystemObservationRegistry(tmp_path, clock=clock)
    valid = make_observation(
        artifact_id="artifact-valid",
        timestamp=T1,
        record_id="record-valid",
        retailer_product_id="product-valid",
    )
    malformed = make_observation(
        artifact_id="artifact-malformed",
        timestamp=T1,
        record_id="record-malformed",
        retailer_product_id="product-malformed",
    )
    registry.register(valid)
    write_stored_observation(
        tmp_path, malformed, capture_timestamp_value="not-a-timestamp"
    )
    service = _search(
        registry,
        [
            _association(valid, "listing-valid"),
            _association(malformed, "listing-malformed"),
        ],
        clock,
    )

    result = service.search(ProductSearchRequest(query="amul"))

    assert result.items == ()
    assert registry.rejections[0].reason is CaptureTimestampRejectionReason.malformed
    assert registry.rejections[0].artifact_id == "artifact-malformed"


# Scenario 6
def test_scenario_6_malformed_historical_artifact_does_not_crash_optimization(tmp_path) -> None:
    clock = FrozenClock(NOW)
    registry = FilesystemObservationRegistry(tmp_path, clock=clock)
    valid = make_observation(
        artifact_id="artifact-valid",
        timestamp=T1,
        record_id="record-valid",
        retailer_product_id="product-valid",
    )
    malformed = make_observation(
        artifact_id="artifact-malformed",
        timestamp=T1,
        record_id="record-malformed",
        retailer_product_id="product-malformed",
    )
    registry.register(valid)
    write_stored_observation(
        tmp_path, malformed, capture_timestamp_value="not-a-timestamp"
    )
    service = _discovery(
        registry,
        [
            _association(valid, "listing-valid"),
            _association(malformed, "listing-malformed"),
        ],
        clock,
    )

    result = service.discover(_item_request())

    item = result.items[0]
    assert item.status is CartCandidateDiscoveryStatus.candidates_not_ready
    assert len(item.candidates) == 1
    assert item.candidates[0].readiness is PersistedCandidateReadiness.not_ready_for_allocation
    assert registry.rejections[0].reason is CaptureTimestampRejectionReason.malformed


# Scenario 7
def test_scenario_7_invalid_timestamp_cannot_suppress_valid_observation() -> None:
    clock = FrozenClock(NOW)
    registry = InMemoryObservationRegistry()
    first = make_observation(
        artifact_id="artifact-t1",
        timestamp=T1,
        record_id="record-t1",
        retailer_product_id="same-product",
    )
    second = make_observation(
        artifact_id="artifact-t2",
        timestamp=T2,
        record_id="record-t2",
        retailer_product_id="same-product",
    )
    future = make_observation(
        artifact_id="artifact-future",
        timestamp=FUTURE,
        record_id="record-future",
        retailer_product_id="same-product",
    )
    for observation in (first, second, future):
        registry.register(observation)
    associations = [
        _association(first, "listing-t1"),
        _association(second, "listing-t2"),
        _association(future, "listing-future"),
    ]

    current = latest_governed_observation_ids(associations, registry, clock=clock)
    result = _search(registry, associations, clock).search(ProductSearchRequest(query="amul"))

    assert current == frozenset()
    assert result.items == ()

    invalid_only = InMemoryObservationRegistry()
    invalid_only.register(future)
    assert latest_governed_observation_ids(
        [_association(future, "listing-future")], invalid_only, clock=clock
    ) == frozenset()


# Scenario 8
def test_scenario_8_equal_valid_timestamps_remain_ambiguous() -> None:
    clock = FrozenClock(NOW)
    registry = InMemoryObservationRegistry()
    first = make_observation(
        artifact_id="artifact-equal-a",
        timestamp=T1,
        record_id="record-equal-a",
        retailer_product_id="same-product",
    )
    second = make_observation(
        artifact_id="artifact-equal-b",
        timestamp=T1,
        record_id="record-equal-b",
        retailer_product_id="same-product",
    )
    registry.register(first)
    registry.register(second)
    associations = [
        _association(first, "listing-equal-a"),
        _association(second, "listing-equal-b"),
    ]

    current = latest_governed_observation_ids(associations, registry, clock=clock)
    result = _search(registry, associations, clock).search(ProductSearchRequest(query="amul"))

    assert current == frozenset()
    assert result.items == ()


# Scenario 9
def test_scenario_9_newer_valid_observation_keeps_supersession_behavior() -> None:
    clock = FrozenClock(NOW)
    registry = InMemoryObservationRegistry()
    older = make_observation(
        artifact_id="artifact-older",
        timestamp=T1,
        record_id="record-older",
        retailer_product_id="same-product",
        price_minor=10000,
    )
    newer = make_observation(
        artifact_id="artifact-newer",
        timestamp=T2,
        record_id="record-newer",
        retailer_product_id="same-product",
        price_minor=12000,
    )
    registry.register(older)
    registry.register(newer)
    associations = [
        _association(older, "listing-older"),
        _association(newer, "listing-newer"),
    ]

    current = latest_governed_observation_ids(associations, registry, clock=clock)
    result = _search(registry, associations, clock).search(ProductSearchRequest(query="amul"))

    assert current == frozenset()
    assert result.items == ()
