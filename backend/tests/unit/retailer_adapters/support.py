"""Deterministic fake adapters and evidence builders for adapter tests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime, timezone
from typing import Any

from app.cost_intelligence.shared.money import Money
from app.credential_vault.types import SecretType
from app.retailer_adapters.base import RetailerAdapter
from app.retailer_adapters.capabilities import ALL_CAPABILITIES, AdapterCapabilities
from app.retailer_adapters.contracts import (
    AcquisitionMetadata,
    AdapterCapability,
    AdapterOperationResult,
    AdapterOutcome,
    AvailabilityObservation,
    AvailabilityRequest,
    AvailabilityResult,
    AvailabilityStatus,
    CapabilityDeclaration,
    CapabilityStatus,
    CartItemRequest,
    CartPreparationRequest,
    CartPreparationResult,
    CheckoutHandoffRequest,
    CheckoutHandoffResult,
    ConnectionValidationRequest,
    ConnectionValidationResult,
    ConnectionValidationState,
    LocationContextKind,
    LocationSelectionRequest,
    LocationSelectionResult,
    OrderStatusRequest,
    OrderStatusResult,
    PriceObservation,
    PriceRequest,
    PriceResult,
    PriceSemantics,
    ProductDetailsRequest,
    ProductDetailsResult,
    ProductSearchRequest,
    ProductSearchResult,
    RetailerLocationContext,
    RetailerProduct,
    SourceProvenance,
)
from app.retailer_adapters.credentials import RetailerCredentialBundle
from app.retailer_data.contracts import AcquisitionMethod, LocationScope

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
RETAILER_ID = "ZEPTO"


def search_location(scope_id: str = "gurugram-1") -> RetailerLocationContext:
    return RetailerLocationContext(
        kind=LocationContextKind.SEARCH_LOCATION,
        scope=LocationScope(
            country_code="IN",
            locality="Gurugram",
            scope_id=scope_id,
        ),
    )


def verified_location(scope_id: str = "gurugram-1") -> RetailerLocationContext:
    return RetailerLocationContext(
        kind=LocationContextKind.VERIFIED_DELIVERY_LOCATION,
        scope=LocationScope(
            country_code="IN",
            locality="Gurugram",
            scope_id=scope_id,
        ),
        retailer_location_reference=f"store:{scope_id}",
        verified_at=NOW,
    )


def acquisition(
    operation: AdapterCapability,
    *,
    retailer_id: str = RETAILER_ID,
    adapter_id: str = "fake-zepto",
) -> AcquisitionMetadata:
    return AcquisitionMetadata(
        adapter_id=adapter_id,
        retailer_id=retailer_id,
        operation=operation,
        acquisition_method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
        request_id="request-1",
        response_received_at=NOW,
        retailer_updated_at=NOW,
        location=search_location(),
        source_reference="https://example.test/source",
        raw_payload_reference="artifact-1",
    )


def request_for(capability: AdapterCapability) -> object:
    if capability is AdapterCapability.CONNECTION_VALIDATION:
        return ConnectionValidationRequest()
    if capability is AdapterCapability.PRODUCT_DISCOVERY:
        return ProductSearchRequest(query="milk", location=search_location())
    if capability is AdapterCapability.PRODUCT_DETAILS:
        return ProductDetailsRequest(
            retailer_product_id="native-1", location=search_location()
        )
    if capability is AdapterCapability.PRICE_ACQUISITION:
        return PriceRequest(
            retailer_product_id="native-1", location=search_location()
        )
    if capability is AdapterCapability.AVAILABILITY_ACQUISITION:
        return AvailabilityRequest(
            retailer_product_id="native-1", location=search_location()
        )
    if capability is AdapterCapability.LOCATION_SELECTION:
        return LocationSelectionRequest(location=search_location().scope)
    if capability is AdapterCapability.CART_PREPARATION:
        return CartPreparationRequest(
            items=(CartItemRequest(retailer_product_id="native-1"),),
            location=search_location(),
        )
    if capability is AdapterCapability.CHECKOUT_HANDOFF:
        return CheckoutHandoffRequest(
            cart_reference="cart-1", location=search_location()
        )
    return OrderStatusRequest(retailer_order_id="order-1")


def product(
    *,
    retailer_id: str = RETAILER_ID,
    adapter_id: str = "fake-zepto",
    product_id: str = "native-1",
) -> RetailerProduct:
    return RetailerProduct(
        retailer_id=retailer_id,
        retailer_product_id=product_id,
        title="Amul Taaza Milk",
        quantity_text="500 ml",
        category_text="Dairy",
        product_url="https://example.test/product/native-1",
        identifiers=(("sku", product_id),),
        location=search_location(),
        provenance=SourceProvenance(
            adapter_id=adapter_id,
            retailer_id=retailer_id,
            acquisition_method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
            source_reference="https://example.test/source",
            raw_payload_reference="artifact-1",
        ),
        captured_at=NOW,
        raw_payload_reference="artifact-1",
    )


def price_observation(
    *,
    retailer_id: str = RETAILER_ID,
    product_id: str = "native-1",
    amount_minor_units: int | None = 6200,
    currency: str | None = "INR",
    semantics: PriceSemantics = PriceSemantics.SELLING_PRICE,
    checkout_evidence_reference: str | None = None,
) -> PriceObservation:
    return PriceObservation(
        retailer_id=retailer_id,
        retailer_product_id=product_id,
        price=(
            None
            if amount_minor_units is None
            else Money(currency=currency or "INR", minor_units=amount_minor_units)
        ),
        currency=currency,
        display_text=None if amount_minor_units is None else "Rs 62",
        reference_display_text=None if amount_minor_units is None else "Rs 65",
        price_semantics=semantics,
        checkout_evidence_reference=checkout_evidence_reference,
        location=search_location(),
        acquisition=acquisition(
            AdapterCapability.PRICE_ACQUISITION, retailer_id=retailer_id
        ),
        captured_at=NOW,
    )


def availability_observation(
    *,
    retailer_id: str = RETAILER_ID,
    product_id: str = "native-1",
    status: AvailabilityStatus = AvailabilityStatus.IN_STOCK,
) -> AvailabilityObservation:
    return AvailabilityObservation(
        retailer_id=retailer_id,
        retailer_product_id=product_id,
        status=status,
        raw_signal=status.value,
        location=search_location(),
        acquisition=acquisition(
            AdapterCapability.AVAILABILITY_ACQUISITION, retailer_id=retailer_id
        ),
        captured_at=NOW,
    )


Behavior = Callable[[], Awaitable[AdapterOperationResult]]


class FakeAdapter(RetailerAdapter):
    """A deterministic adapter implementing only the capabilities it declares."""

    def __init__(
        self,
        *,
        retailer_id: str = RETAILER_ID,
        adapter_id: str = "fake-zepto",
        supported: Iterable[AdapterCapability] = (),
        secret_types: Iterable[SecretType] = (),
        behaviors: dict[AdapterCapability, Behavior] | None = None,
    ) -> None:
        self.retailer_id = retailer_id
        self.adapter_id = adapter_id
        self._supported = frozenset(supported)
        self._secret_types = tuple(secret_types)
        self.capabilities = AdapterCapabilities(
            CapabilityDeclaration(
                capability=capability,
                status=(
                    CapabilityStatus.SUPPORTED
                    if capability in self._supported
                    else CapabilityStatus.UNSUPPORTED
                ),
                reason_code=(
                    None
                    if capability in self._supported
                    else "not_implemented"
                ),
            )
            for capability in ALL_CAPABILITIES
        )
        self.behaviors = dict(behaviors or {})
        self.calls: list[tuple[AdapterCapability, RetailerCredentialBundle]] = []

    def required_secret_types(
        self, capability: AdapterCapability
    ) -> tuple[SecretType, ...]:
        return self._secret_types

    async def _behavior(
        self,
        capability: AdapterCapability,
        credentials: RetailerCredentialBundle,
    ) -> AdapterOperationResult:
        self.calls.append((capability, credentials))
        behavior = self.behaviors.get(capability)
        if behavior is not None:
            return await behavior()
        return self._default_result(capability)

    async def _perform_connection_validation(
        self,
        request: ConnectionValidationRequest,
        credentials: RetailerCredentialBundle,
    ) -> ConnectionValidationResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.CONNECTION_VALIDATION, credentials
        )

    async def _perform_product_search(
        self,
        request: ProductSearchRequest,
        credentials: RetailerCredentialBundle,
    ) -> ProductSearchResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.PRODUCT_DISCOVERY, credentials
        )

    async def _perform_product_details(
        self,
        request: ProductDetailsRequest,
        credentials: RetailerCredentialBundle,
    ) -> ProductDetailsResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.PRODUCT_DETAILS, credentials
        )

    async def _perform_price(
        self,
        request: PriceRequest,
        credentials: RetailerCredentialBundle,
    ) -> PriceResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.PRICE_ACQUISITION, credentials
        )

    async def _perform_availability(
        self,
        request: AvailabilityRequest,
        credentials: RetailerCredentialBundle,
    ) -> AvailabilityResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.AVAILABILITY_ACQUISITION, credentials
        )

    async def _perform_location_selection(
        self,
        request: LocationSelectionRequest,
        credentials: RetailerCredentialBundle,
    ) -> LocationSelectionResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.LOCATION_SELECTION, credentials
        )

    async def _perform_cart_preparation(
        self,
        request: CartPreparationRequest,
        credentials: RetailerCredentialBundle,
    ) -> CartPreparationResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.CART_PREPARATION, credentials
        )

    async def _perform_checkout_handoff(
        self,
        request: CheckoutHandoffRequest,
        credentials: RetailerCredentialBundle,
    ) -> CheckoutHandoffResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.CHECKOUT_HANDOFF, credentials
        )

    async def _perform_order_status(
        self,
        request: OrderStatusRequest,
        credentials: RetailerCredentialBundle,
    ) -> OrderStatusResult:
        return await self._behavior(  # type: ignore[return-value]
            AdapterCapability.ORDER_STATUS, credentials
        )

    def _default_result(self, capability: AdapterCapability) -> AdapterOperationResult:
        if capability is AdapterCapability.CONNECTION_VALIDATION:
            return ConnectionValidationResult(
                outcome=AdapterOutcome.SUCCESS,
                validation=ConnectionValidationState.VALID,
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        if capability is AdapterCapability.PRODUCT_DISCOVERY:
            return ProductSearchResult(
                outcome=AdapterOutcome.SUCCESS,
                products=(
                    product(
                        retailer_id=self.retailer_id,
                        adapter_id=self.adapter_id,
                    ),
                ),
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        if capability is AdapterCapability.PRODUCT_DETAILS:
            return ProductDetailsResult(
                outcome=AdapterOutcome.SUCCESS,
                product=product(
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        if capability is AdapterCapability.PRICE_ACQUISITION:
            return PriceResult(
                outcome=AdapterOutcome.SUCCESS,
                price=price_observation(retailer_id=self.retailer_id),
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        if capability is AdapterCapability.AVAILABILITY_ACQUISITION:
            return AvailabilityResult(
                outcome=AdapterOutcome.SUCCESS,
                availability=availability_observation(retailer_id=self.retailer_id),
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        if capability is AdapterCapability.LOCATION_SELECTION:
            return LocationSelectionResult(
                outcome=AdapterOutcome.SUCCESS,
                selected=verified_location(),
                candidates=(verified_location(),),
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        if capability is AdapterCapability.CART_PREPARATION:
            return CartPreparationResult(
                outcome=AdapterOutcome.SUCCESS,
                cart_reference="cart-1",
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        if capability is AdapterCapability.CHECKOUT_HANDOFF:
            return CheckoutHandoffResult(
                outcome=AdapterOutcome.SUCCESS,
                handoff_reference="handoff-1",
                acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
            )
        return OrderStatusResult(
            outcome=AdapterOutcome.SUCCESS,
            order_status="PLACED",
            acquisition=acquisition(
                    capability,
                    retailer_id=self.retailer_id,
                    adapter_id=self.adapter_id,
                ),
        )


class BareAdapter(RetailerAdapter):
    """Declares capabilities without overriding any implementation hook."""

    def __init__(
        self,
        *,
        retailer_id: str = RETAILER_ID,
        adapter_id: str = "bare-zepto",
        supported: Iterable[AdapterCapability] = (),
    ) -> None:
        self.retailer_id = retailer_id
        self.adapter_id = adapter_id
        self.capabilities = AdapterCapabilities(
            CapabilityDeclaration(
                capability=capability,
                status=(
                    CapabilityStatus.SUPPORTED
                    if capability in set(supported)
                    else CapabilityStatus.UNSUPPORTED
                ),
                reason_code=(
                    None if capability in set(supported) else "not_implemented"
                ),
            )
            for capability in ALL_CAPABILITIES
        )


def adapter_with_all_capabilities(**kwargs: Any) -> FakeAdapter:
    return FakeAdapter(supported=ALL_CAPABILITIES, **kwargs)
