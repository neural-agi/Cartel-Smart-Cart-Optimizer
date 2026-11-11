"""Centralized capability declarations and lifecycle mapping.

Capability support is a property of an adapter implementation, not of a
connection's lifecycle state. The lifecycle operation matrix remains the
authorization layer; this module only maps each adapter capability onto the
reviewed lifecycle operation that must permit it.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType

from app.retailer_adapters.contracts import (
    AdapterCapability,
    CapabilityDeclaration,
    CapabilityStatus,
)
from app.retailer_connections.lifecycle import RetailerOperation

ALL_CAPABILITIES: tuple[AdapterCapability, ...] = tuple(AdapterCapability)


# The lifecycle matrix predates the adapter capability vocabulary. These
# mappings are deliberately conservative and never widen lifecycle permission.
CAPABILITY_OPERATIONS: Mapping[AdapterCapability, RetailerOperation] = MappingProxyType(
    {
        AdapterCapability.CONNECTION_VALIDATION: RetailerOperation.RETAILER_HEALTH_CHECK,
        AdapterCapability.PRODUCT_DISCOVERY: RetailerOperation.PRODUCT_DISCOVERY,
        AdapterCapability.PRODUCT_DETAILS: RetailerOperation.PRODUCT_DISCOVERY,
        AdapterCapability.PRICE_ACQUISITION: (
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION
        ),
        AdapterCapability.AVAILABILITY_ACQUISITION: (
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION
        ),
        AdapterCapability.LOCATION_SELECTION: RetailerOperation.PRODUCT_DISCOVERY,
        AdapterCapability.CART_PREPARATION: RetailerOperation.CART_PREPARATION,
        AdapterCapability.CHECKOUT_HANDOFF: RetailerOperation.CHECKOUT,
        AdapterCapability.ORDER_STATUS: RetailerOperation.CHECKOUT,
    }
)

# Only read-only operations are safe to retry automatically. Cart preparation
# and checkout handoff are mutations; order status is a read but remains in the
# future-commerce group and is not implemented by any adapter in this phase.
RETRY_SAFE_CAPABILITIES: frozenset[AdapterCapability] = frozenset(
    {
        AdapterCapability.CONNECTION_VALIDATION,
        AdapterCapability.PRODUCT_DISCOVERY,
        AdapterCapability.PRODUCT_DETAILS,
        AdapterCapability.PRICE_ACQUISITION,
        AdapterCapability.AVAILABILITY_ACQUISITION,
        AdapterCapability.LOCATION_SELECTION,
        AdapterCapability.ORDER_STATUS,
    }
)


class CapabilityDeclarationError(Exception):
    """A capability declaration set is incomplete, duplicated, or invalid."""


class AdapterCapabilities:
    """Complete, immutable capability declaration for one adapter."""

    __slots__ = ("_declarations",)

    def __init__(self, declarations: Iterable[CapabilityDeclaration]) -> None:
        mapping: dict[AdapterCapability, CapabilityDeclaration] = {}
        for declaration in declarations:
            if declaration.capability in mapping:
                raise CapabilityDeclarationError(
                    f"duplicate capability declaration: {declaration.capability.value}"
                )
            mapping[declaration.capability] = declaration
        missing = set(ALL_CAPABILITIES) - set(mapping)
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise CapabilityDeclarationError(
                f"missing capability declarations: {names}"
            )
        self._declarations: Mapping[
            AdapterCapability, CapabilityDeclaration
        ] = MappingProxyType(mapping)

    @classmethod
    def all_unsupported(cls, reason_code: str) -> AdapterCapabilities:
        """Declare every capability unsupported with one explicit reason."""

        return cls(
            CapabilityDeclaration(
                capability=capability,
                status=CapabilityStatus.UNSUPPORTED,
                reason_code=reason_code,
            )
            for capability in ALL_CAPABILITIES
        )

    def declaration_for(self, capability: AdapterCapability) -> CapabilityDeclaration:
        return self._declarations[capability]

    def status_for(self, capability: AdapterCapability) -> CapabilityStatus:
        return self._declarations[capability].status

    def is_supported(self, capability: AdapterCapability) -> bool:
        return self.status_for(capability) is CapabilityStatus.SUPPORTED

    def supported_capabilities(self) -> tuple[AdapterCapability, ...]:
        return tuple(
            capability
            for capability in ALL_CAPABILITIES
            if self.is_supported(capability)
        )

    @property
    def declarations(self) -> tuple[CapabilityDeclaration, ...]:
        return tuple(
            self._declarations[capability] for capability in ALL_CAPABILITIES
        )

    def __getitem__(self, capability: AdapterCapability) -> CapabilityDeclaration:
        return self.declaration_for(capability)

    def __iter__(self) -> Iterator[CapabilityDeclaration]:
        return iter(self.declarations)

    def __len__(self) -> int:
        return len(self._declarations)


__all__ = [
    "ALL_CAPABILITIES",
    "CAPABILITY_OPERATIONS",
    "RETRY_SAFE_CAPABILITIES",
    "AdapterCapabilities",
    "CapabilityDeclarationError",
]
