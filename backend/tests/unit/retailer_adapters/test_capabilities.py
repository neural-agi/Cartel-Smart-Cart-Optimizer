from __future__ import annotations

import pytest

from app.retailer_adapters.capabilities import (
    ALL_CAPABILITIES,
    CAPABILITY_OPERATIONS,
    RETRY_SAFE_CAPABILITIES,
    AdapterCapabilities,
    CapabilityDeclarationError,
)
from app.retailer_adapters.contracts import (
    AdapterCapability,
    CapabilityDeclaration,
    CapabilityStatus,
)
from app.retailer_connections.lifecycle import RetailerOperation


def declarations(status: CapabilityStatus = CapabilityStatus.UNSUPPORTED):
    return tuple(
        CapabilityDeclaration(
            capability=capability,
            status=status,
            reason_code=None if status is CapabilityStatus.SUPPORTED else "test_reason",
        )
        for capability in ALL_CAPABILITIES
    )


def test_complete_declaration_set_exposes_every_capability() -> None:
    capabilities = AdapterCapabilities(declarations())

    assert len(capabilities) == len(ALL_CAPABILITIES)
    assert tuple(item.capability for item in capabilities) == ALL_CAPABILITIES
    assert capabilities.supported_capabilities() == ()
    assert capabilities.status_for(AdapterCapability.PRODUCT_DISCOVERY) is (
        CapabilityStatus.UNSUPPORTED
    )


def test_all_unsupported_declares_every_capability_with_reason() -> None:
    capabilities = AdapterCapabilities.all_unsupported("placeholder_not_implemented")

    assert len(capabilities) == len(ALL_CAPABILITIES)
    assert all(
        declaration.status is CapabilityStatus.UNSUPPORTED
        and declaration.reason_code == "placeholder_not_implemented"
        for declaration in capabilities
    )


def test_duplicate_declaration_is_rejected() -> None:
    items = list(declarations())
    items.append(items[0])

    with pytest.raises(CapabilityDeclarationError, match="duplicate"):
        AdapterCapabilities(items)


def test_missing_declaration_is_rejected() -> None:
    with pytest.raises(CapabilityDeclarationError, match="missing"):
        AdapterCapabilities(declarations()[:-1])


def test_non_supported_capability_requires_reason() -> None:
    with pytest.raises(ValueError, match="reason_code"):
        CapabilityDeclaration(
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            status=CapabilityStatus.NOT_VERIFIED,
        )


def test_supported_capability_must_not_carry_failure_reason() -> None:
    with pytest.raises(ValueError, match="must not carry"):
        CapabilityDeclaration(
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            status=CapabilityStatus.SUPPORTED,
            reason_code="leftover",
        )


def test_every_capability_maps_to_one_reviewed_lifecycle_operation() -> None:
    assert set(CAPABILITY_OPERATIONS) == set(ALL_CAPABILITIES)
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.CONNECTION_VALIDATION]
        is RetailerOperation.RETAILER_HEALTH_CHECK
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.PRODUCT_DISCOVERY]
        is RetailerOperation.PRODUCT_DISCOVERY
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.PRODUCT_DETAILS]
        is RetailerOperation.PRODUCT_DISCOVERY
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.LOCATION_SELECTION]
        is RetailerOperation.PRODUCT_DISCOVERY
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.PRICE_ACQUISITION]
        is RetailerOperation.PRICE_AVAILABILITY_ACQUISITION
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.AVAILABILITY_ACQUISITION]
        is RetailerOperation.PRICE_AVAILABILITY_ACQUISITION
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.CART_PREPARATION]
        is RetailerOperation.CART_PREPARATION
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.CHECKOUT_HANDOFF]
        is RetailerOperation.CHECKOUT
    )
    assert (
        CAPABILITY_OPERATIONS[AdapterCapability.ORDER_STATUS]
        is RetailerOperation.CHECKOUT
    )


def test_mutations_are_not_retry_safe() -> None:
    assert AdapterCapability.CART_PREPARATION not in RETRY_SAFE_CAPABILITIES
    assert AdapterCapability.CHECKOUT_HANDOFF not in RETRY_SAFE_CAPABILITIES
    assert AdapterCapability.PRODUCT_DISCOVERY in RETRY_SAFE_CAPABILITIES
    assert AdapterCapability.PRICE_ACQUISITION in RETRY_SAFE_CAPABILITIES
