"""Controlled registry of retailer adapters.

Consumer services depend on the resolver protocol, not on retailer-specific
implementations. Registration is explicit, rejects unknown or duplicate
identifiers, and refuses to declare a capability ``SUPPORTED`` unless the
adapter actually overrides the corresponding operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.retailer_adapters.base import RetailerAdapter
from app.retailer_adapters.capabilities import (
    ALL_CAPABILITIES,
    AdapterCapabilities,
    CapabilityDeclarationError,
)
from app.retailer_adapters.contracts import (
    CapabilityDeclaration,
    CapabilityStatus,
)
from app.retailer_connections.lifecycle import SUPPORTED_RETAILER_IDS
from app.retailer_data.contracts import AcquisitionMethod


class AdapterRegistryError(Exception):
    """Base class for registry failures."""


class UnknownRetailerAdapter(AdapterRegistryError):
    """No adapter is registered for the requested controlled retailer ID."""

    def __init__(self, retailer_id: object) -> None:
        self.retailer_id = retailer_id
        super().__init__(f"no retailer adapter registered for {retailer_id!r}")


class DuplicateAdapterRegistration(AdapterRegistryError):
    """An adapter ID or retailer ID was registered twice."""

    def __init__(self, *, adapter_id: str | None = None, retailer_id: str | None = None) -> None:
        self.adapter_id = adapter_id
        self.retailer_id = retailer_id
        detail = adapter_id or retailer_id
        super().__init__(f"duplicate adapter registration: {detail}")


class InvalidAdapterRegistration(AdapterRegistryError):
    """An adapter does not satisfy the registry contract."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid adapter registration: {code}")


@dataclass(frozen=True, slots=True)
class AdapterDescriptor:
    """Non-secret capability metadata for one registered adapter."""

    adapter_id: str
    retailer_id: str
    acquisition_method: AcquisitionMethod
    capabilities: AdapterCapabilities


class RetailerAdapterResolver(Protocol):
    """Consumer-facing registry surface independent of implementations."""

    def resolve(self, retailer_id: str) -> RetailerAdapter: ...

    def capabilities(self, retailer_id: str) -> AdapterCapabilities: ...

    def descriptors(self) -> tuple[AdapterDescriptor, ...]: ...


class RetailerAdapterRegistry:
    """Deterministic, injectable adapter registry."""

    def __init__(self) -> None:
        self._by_retailer: dict[str, RetailerAdapter] = {}
        self._by_adapter_id: dict[str, RetailerAdapter] = {}

    def register(self, adapter: RetailerAdapter) -> None:
        if not isinstance(adapter, RetailerAdapter):
            raise InvalidAdapterRegistration("adapter_must_extend_retailer_adapter")

        adapter_id = getattr(adapter, "adapter_id", None)
        if not isinstance(adapter_id, str) or not adapter_id.strip():
            raise InvalidAdapterRegistration("adapter_id_required")
        adapter_id = adapter_id.strip()

        raw_retailer_id = getattr(adapter, "retailer_id", None)
        try:
            retailer_id = _normalize_retailer_id(raw_retailer_id)
        except UnknownRetailerAdapter as exc:
            raise InvalidAdapterRegistration("unsupported_retailer_id") from exc
        if raw_retailer_id != retailer_id:
            raise InvalidAdapterRegistration("retailer_id_must_be_canonical")

        capabilities = getattr(adapter, "capabilities", None)
        if not isinstance(capabilities, AdapterCapabilities):
            raise InvalidAdapterRegistration("capability_declarations_required")

        acquisition_method = getattr(adapter, "acquisition_method", None)
        if not isinstance(acquisition_method, AcquisitionMethod):
            raise InvalidAdapterRegistration("acquisition_method_required")

        if adapter_id in self._by_adapter_id:
            raise DuplicateAdapterRegistration(adapter_id=adapter_id)
        if retailer_id in self._by_retailer:
            raise DuplicateAdapterRegistration(retailer_id=retailer_id)

        for capability in ALL_CAPABILITIES:
            declaration = capabilities.declaration_for(capability)
            if (
                declaration.status is CapabilityStatus.SUPPORTED
                and not adapter.implements(capability)
            ):
                raise InvalidAdapterRegistration(
                    f"supported_capability_not_implemented:{capability.value}"
                )

        self._by_adapter_id[adapter_id] = adapter
        self._by_retailer[retailer_id] = adapter

    def resolve(self, retailer_id: str) -> RetailerAdapter:
        normalized = _normalize_retailer_id(retailer_id)
        adapter = self._by_retailer.get(normalized)
        if adapter is None:
            raise UnknownRetailerAdapter(retailer_id)
        return adapter

    def capabilities(self, retailer_id: str) -> AdapterCapabilities:
        return self.resolve(retailer_id).capabilities

    def descriptor(self, retailer_id: str) -> AdapterDescriptor:
        adapter = self.resolve(retailer_id)
        return AdapterDescriptor(
            adapter_id=adapter.adapter_id,
            retailer_id=adapter.retailer_id,
            acquisition_method=adapter.acquisition_method,
            capabilities=adapter.capabilities,
        )

    def descriptors(self) -> tuple[AdapterDescriptor, ...]:
        return tuple(
            self.descriptor(retailer_id)
            for retailer_id in sorted(self._by_retailer)
        )

    def declarations(self, retailer_id: str) -> tuple[CapabilityDeclaration, ...]:
        return self.capabilities(retailer_id).declarations

    @property
    def retailer_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_retailer))

    def __contains__(self, retailer_id: object) -> bool:
        if not isinstance(retailer_id, str):
            return False
        try:
            normalized = _normalize_retailer_id(retailer_id)
        except UnknownRetailerAdapter:
            return False
        return normalized in self._by_retailer

    def __len__(self) -> int:
        return len(self._by_retailer)


def _normalize_retailer_id(value: object) -> str:
    if not isinstance(value, str):
        raise UnknownRetailerAdapter(value)
    normalized = value.strip().upper()
    if normalized not in SUPPORTED_RETAILER_IDS:
        raise UnknownRetailerAdapter(value)
    return normalized


def build_default_registry() -> RetailerAdapterRegistry:
    """Build the default registry of explicit, non-functional placeholders."""

    from app.retailer_adapters.placeholders import build_placeholder_adapters

    registry = RetailerAdapterRegistry()
    for adapter in build_placeholder_adapters():
        registry.register(adapter)
    return registry


__all__ = [
    "AdapterDescriptor",
    "AdapterRegistryError",
    "CapabilityDeclarationError",
    "DuplicateAdapterRegistration",
    "InvalidAdapterRegistration",
    "RetailerAdapterRegistry",
    "RetailerAdapterResolver",
    "UnknownRetailerAdapter",
    "build_default_registry",
]
