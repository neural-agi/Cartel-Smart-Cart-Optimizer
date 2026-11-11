from __future__ import annotations

import pytest

from app.retailer_adapters.capabilities import ALL_CAPABILITIES
from app.retailer_adapters.contracts import AdapterCapability, CapabilityStatus
from app.retailer_adapters.placeholders import (
    PLACEHOLDER_REASON,
    PlaceholderRetailerAdapter,
    build_placeholder_adapters,
)
from app.retailer_adapters.registry import (
    DuplicateAdapterRegistration,
    InvalidAdapterRegistration,
    RetailerAdapterRegistry,
    UnknownRetailerAdapter,
    build_default_registry,
)
from app.retailer_connections.lifecycle import SUPPORTED_RETAILER_IDS
from tests.unit.retailer_adapters.support import BareAdapter, FakeAdapter


def test_default_registry_covers_every_controlled_retailer() -> None:
    registry = build_default_registry()

    assert set(registry.retailer_ids) == SUPPORTED_RETAILER_IDS
    for retailer_id in SUPPORTED_RETAILER_IDS:
        descriptor = registry.descriptor(retailer_id)
        assert descriptor.adapter_id == f"{retailer_id.lower()}-placeholder"
        assert all(
            declaration.status is CapabilityStatus.UNSUPPORTED
            and declaration.reason_code == PLACEHOLDER_REASON
            for declaration in descriptor.capabilities
        )


def test_placeholders_never_declare_supported_capabilities() -> None:
    for adapter in build_placeholder_adapters():
        assert adapter.capabilities.supported_capabilities() == ()
        for capability in ALL_CAPABILITIES:
            assert not adapter.implements(capability)


def test_unknown_retailer_identifier_is_rejected() -> None:
    registry = build_default_registry()

    with pytest.raises(UnknownRetailerAdapter):
        registry.resolve("UNKNOWN_RETAILER")
    with pytest.raises(UnknownRetailerAdapter):
        registry.resolve("")


def test_duplicate_retailer_registration_is_rejected() -> None:
    registry = RetailerAdapterRegistry()
    registry.register(FakeAdapter(adapter_id="one"))

    with pytest.raises(DuplicateAdapterRegistration):
        registry.register(FakeAdapter(adapter_id="two"))


def test_duplicate_adapter_id_registration_is_rejected() -> None:
    registry = RetailerAdapterRegistry()
    registry.register(FakeAdapter(retailer_id="BLINKIT", adapter_id="same"))
    other = FakeAdapter(retailer_id="ZEPTO", adapter_id="same")

    with pytest.raises(DuplicateAdapterRegistration):
        registry.register(other)


def test_unsupported_retailer_registration_is_rejected() -> None:
    registry = RetailerAdapterRegistry()

    with pytest.raises(InvalidAdapterRegistration, match="unsupported_retailer_id"):
        registry.register(FakeAdapter(retailer_id="NOT_A_RETAILER", adapter_id="bad"))


def test_non_canonical_retailer_registration_is_rejected() -> None:
    registry = RetailerAdapterRegistry()

    with pytest.raises(InvalidAdapterRegistration, match="canonical"):
        registry.register(FakeAdapter(retailer_id="blinkit", adapter_id="bad"))


def test_supported_capability_requires_an_implementation() -> None:
    registry = RetailerAdapterRegistry()
    adapter = BareAdapter(
        adapter_id="bare",
        supported=(AdapterCapability.PRODUCT_DISCOVERY,),
    )

    with pytest.raises(
        InvalidAdapterRegistration,
        match="supported_capability_not_implemented",
    ):
        registry.register(adapter)


def test_supported_capability_with_implementation_is_accepted() -> None:
    registry = RetailerAdapterRegistry()
    adapter = FakeAdapter(
        adapter_id="implemented",
        supported=(AdapterCapability.PRODUCT_DISCOVERY,),
    )

    registry.register(adapter)

    assert registry.resolve("ZEPTO") is adapter
    assert (
        registry.capabilities("ZEPTO").status_for(AdapterCapability.PRODUCT_DISCOVERY)
        is CapabilityStatus.SUPPORTED
    )


def test_registry_exposes_capability_metadata_without_implementation_access() -> None:
    registry = RetailerAdapterRegistry()
    adapter = FakeAdapter(
        adapter_id="metadata",
        supported=(AdapterCapability.PRODUCT_DISCOVERY,),
    )
    registry.register(adapter)

    descriptor = registry.descriptor("ZEPTO")

    assert descriptor.adapter_id == "metadata"
    assert descriptor.retailer_id == "ZEPTO"
    assert descriptor.capabilities is adapter.capabilities
    assert descriptor.acquisition_method is adapter.acquisition_method


def test_registry_supports_injected_deterministic_adapters() -> None:
    registry = RetailerAdapterRegistry()
    blinkit = FakeAdapter(retailer_id="BLINKIT", adapter_id="fake-blinkit")
    zepto = FakeAdapter(retailer_id="ZEPTO", adapter_id="fake-zepto")
    registry.register(blinkit)
    registry.register(zepto)

    assert registry.resolve("blinkit") is blinkit
    assert registry.resolve("ZEPTO") is zepto
    assert registry.retailer_ids == ("BLINKIT", "ZEPTO")


def test_registry_rejects_adapter_without_capability_declarations() -> None:
    class Broken(FakeAdapter):
        def __init__(self) -> None:
            super().__init__(adapter_id="broken")
            self.capabilities = None

    registry = RetailerAdapterRegistry()

    with pytest.raises(InvalidAdapterRegistration, match="capability_declarations"):
        registry.register(Broken())


def test_placeholder_rejects_unknown_retailer_id() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        PlaceholderRetailerAdapter("NOT_A_RETAILER")


def test_application_accepts_an_injected_registry() -> None:
    from app.main import create_application

    registry = RetailerAdapterRegistry()
    application = create_application(adapter_registry=registry)

    assert application.state.adapter_registry is registry
