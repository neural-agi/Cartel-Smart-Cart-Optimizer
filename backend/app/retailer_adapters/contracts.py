"""Provider-independent retailer adapter contracts.

The adapter layer is deliberately *not* an acquisition, authentication, or
commerce implementation. It defines the typed operations a future retailer
integration must satisfy, together with the provenance and evidence fields that
must survive every projection into Product Intelligence.

Nothing in this module creates canonical products, fabricates price or
availability, or treats proximity as delivery eligibility.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.cost_intelligence.shared.money import Money
from app.retailer_connections.lifecycle import (
    SUPPORTED_RETAILER_IDS,
    RetailerConnectionStatus,
)
from app.retailer_data.contracts import AcquisitionMethod, LocationScope


class AdapterCapability(StrEnum):
    """The controlled capability vocabulary for every retailer adapter."""

    CONNECTION_VALIDATION = "CONNECTION_VALIDATION"
    PRODUCT_DISCOVERY = "PRODUCT_DISCOVERY"
    PRODUCT_DETAILS = "PRODUCT_DETAILS"
    PRICE_ACQUISITION = "PRICE_ACQUISITION"
    AVAILABILITY_ACQUISITION = "AVAILABILITY_ACQUISITION"
    LOCATION_SELECTION = "LOCATION_SELECTION"
    CART_PREPARATION = "CART_PREPARATION"
    CHECKOUT_HANDOFF = "CHECKOUT_HANDOFF"
    ORDER_STATUS = "ORDER_STATUS"


class CapabilityStatus(StrEnum):
    """Explicit capability declaration status.

    ``SUPPORTED`` is only valid when the adapter implements the operation and
    the registry can verify that implementation. A connected lifecycle state is
    never evidence of retailer capability.
    """

    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    REQUIRES_USER_ACTION = "REQUIRES_USER_ACTION"
    NOT_VERIFIED = "NOT_VERIFIED"


class AdapterOutcome(StrEnum):
    """Typed terminal outcome for one adapter operation."""

    SUCCESS = "SUCCESS"
    UNSUPPORTED = "UNSUPPORTED"
    REQUIRES_USER_ACTION = "REQUIRES_USER_ACTION"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    ACCESS_DENIED = "ACCESS_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


class LocationContextKind(StrEnum):
    """Whether a location is a search hint or verified delivery coverage."""

    SEARCH_LOCATION = "SEARCH_LOCATION"
    VERIFIED_DELIVERY_LOCATION = "VERIFIED_DELIVERY_LOCATION"


class PriceSemantics(StrEnum):
    """Meaning of a retailer price observation.

    ``CHECKOUT_PRICE`` is only admissible with an explicit checkout evidence
    reference. No adapter may present a browse price as checkout-backed.
    """

    SELLING_PRICE = "SELLING_PRICE"
    LIST_PRICE = "LIST_PRICE"
    OFFER_PRICE = "OFFER_PRICE"
    CHECKOUT_PRICE = "CHECKOUT_PRICE"
    UNKNOWN = "UNKNOWN"


class AvailabilityStatus(StrEnum):
    """Availability as observed; absence of a signal is never in-stock."""

    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"


class ConnectionValidationState(StrEnum):
    """Outcome of validating an existing retailer connection."""

    VALID = "VALID"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    UNKNOWN = "UNKNOWN"


def _nonblank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("value must not be blank")
    return value


def _optional_nonblank(value: str | None) -> str | None:
    return None if value is None else _nonblank(value)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


class CapabilityDeclaration(BaseModel):
    """One adapter's declaration for one capability."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: AdapterCapability
    status: CapabilityStatus
    reason_code: str | None = None

    @field_validator("reason_code")
    @classmethod
    def _reason_code(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @model_validator(mode="after")
    def _status_requires_reason(self) -> CapabilityDeclaration:
        if self.status is CapabilityStatus.SUPPORTED and self.reason_code is not None:
            raise ValueError("SUPPORTED capabilities must not carry a failure reason")
        if self.status is not CapabilityStatus.SUPPORTED and self.reason_code is None:
            raise ValueError("non-SUPPORTED capabilities require an explicit reason_code")
        return self


class RetailerConnectionReference(BaseModel):
    """Non-secret reference to the persisted connection an operation uses."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    connection_id: UUID
    retailer_id: str
    status: RetailerConnectionStatus
    version: int = Field(ge=1)

    @field_validator("retailer_id")
    @classmethod
    def _retailer_id(cls, value: str) -> str:
        value = _nonblank(value).upper()
        if value not in SUPPORTED_RETAILER_IDS:
            raise ValueError("unsupported retailer identifier")
        return value


class RetailerOperationContext(BaseModel):
    """Authenticated user context for one adapter operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: UUID
    connection: RetailerConnectionReference
    capability: AdapterCapability
    request_id: str | None = None

    @field_validator("request_id")
    @classmethod
    def _request_id(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)


class RetailerLocationContext(BaseModel):
    """Explicit retailer location with provenance.

    A search location is a query hint. It is never evidence that the retailer
    delivers to that location. Only a ``VERIFIED_DELIVERY_LOCATION`` carries a
    retailer reference and verification timestamp.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: LocationContextKind
    scope: LocationScope
    retailer_location_reference: str | None = None
    verified_at: datetime | None = None

    @field_validator("retailer_location_reference")
    @classmethod
    def _reference(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @field_validator("verified_at")
    @classmethod
    def _verified_at(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _aware(value)

    @model_validator(mode="after")
    def _verification_contract(self) -> RetailerLocationContext:
        if self.kind is LocationContextKind.VERIFIED_DELIVERY_LOCATION:
            if self.retailer_location_reference is None or self.verified_at is None:
                raise ValueError(
                    "verified delivery locations require a retailer reference and "
                    "verification timestamp"
                )
        elif self.verified_at is not None:
            raise ValueError(
                "search locations must not claim verified delivery coverage"
            )
        return self


class SourceProvenance(BaseModel):
    """Where an adapter observation came from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter_id: str
    retailer_id: str
    acquisition_method: AcquisitionMethod
    source_reference: str | None = None
    raw_payload_reference: str | None = None

    @field_validator("adapter_id")
    @classmethod
    def _adapter_id(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("retailer_id")
    @classmethod
    def _retailer_id(cls, value: str) -> str:
        value = _nonblank(value).upper()
        if value not in SUPPORTED_RETAILER_IDS:
            raise ValueError("unsupported retailer identifier")
        return value

    @field_validator("source_reference", "raw_payload_reference")
    @classmethod
    def _optional_reference(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)


class AcquisitionMetadata(BaseModel):
    """Bounded execution and timing metadata for one adapter operation.

    ``response_received_at`` is when the retailer answered. ``retailer_updated_at``
    is the retailer's own stated update time, which may be earlier. The two are
    deliberately distinct and are never substituted for one another.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter_id: str
    retailer_id: str
    operation: AdapterCapability
    acquisition_method: AcquisitionMethod
    request_id: str | None = None
    response_received_at: datetime | None = None
    retailer_updated_at: datetime | None = None
    attempt_count: int = Field(default=1, ge=1)
    retried: bool = False
    location: RetailerLocationContext | None = None
    source_reference: str | None = None
    raw_payload_reference: str | None = None

    @field_validator("adapter_id")
    @classmethod
    def _adapter_id(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("retailer_id")
    @classmethod
    def _retailer_id(cls, value: str) -> str:
        value = _nonblank(value).upper()
        if value not in SUPPORTED_RETAILER_IDS:
            raise ValueError("unsupported retailer identifier")
        return value

    @field_validator("request_id", "source_reference", "raw_payload_reference")
    @classmethod
    def _optional_reference(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @field_validator("response_received_at", "retailer_updated_at")
    @classmethod
    def _timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _aware(value)

    @model_validator(mode="after")
    def _timing_contract(self) -> AcquisitionMetadata:
        if (
            self.response_received_at is not None
            and self.retailer_updated_at is not None
            and self.retailer_updated_at > self.response_received_at
        ):
            raise ValueError(
                "retailer-side update time cannot be later than the response time"
            )
        return self


class ConnectionValidationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    include_capability_declarations: bool = False


class ProductSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    location: RetailerLocationContext
    limit: int = Field(default=20, ge=1, le=100)
    page_token: str | None = None

    @field_validator("query")
    @classmethod
    def _query(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("page_token")
    @classmethod
    def _page_token(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)


class ProductDetailsRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_product_id: str
    location: RetailerLocationContext

    @field_validator("retailer_product_id")
    @classmethod
    def _product_id(cls, value: str) -> str:
        return _nonblank(value)


class PriceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_product_id: str
    location: RetailerLocationContext

    @field_validator("retailer_product_id")
    @classmethod
    def _product_id(cls, value: str) -> str:
        return _nonblank(value)


class AvailabilityRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_product_id: str
    location: RetailerLocationContext

    @field_validator("retailer_product_id")
    @classmethod
    def _product_id(cls, value: str) -> str:
        return _nonblank(value)


class LocationSelectionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    location: LocationScope
    retailer_location_reference: str | None = None

    @field_validator("retailer_location_reference")
    @classmethod
    def _reference(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)


class CartItemRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_product_id: str
    quantity: int = Field(default=1, ge=1)

    @field_validator("retailer_product_id")
    @classmethod
    def _product_id(cls, value: str) -> str:
        return _nonblank(value)


class CartPreparationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[CartItemRequest, ...]
    location: RetailerLocationContext

    @model_validator(mode="after")
    def _items(self) -> CartPreparationRequest:
        if not self.items:
            raise ValueError("cart preparation requires at least one item")
        return self


class CheckoutHandoffRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cart_reference: str
    location: RetailerLocationContext

    @field_validator("cart_reference")
    @classmethod
    def _cart_reference(cls, value: str) -> str:
        return _nonblank(value)


class OrderStatusRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_order_id: str

    @field_validator("retailer_order_id")
    @classmethod
    def _order_id(cls, value: str) -> str:
        return _nonblank(value)


class RetailerProduct(BaseModel):
    """A retailer-native product result. Never a canonical product."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_id: str
    retailer_product_id: str
    title: str
    quantity_text: str | None = None
    category_text: str | None = None
    product_url: str | None = None
    identifiers: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    location: RetailerLocationContext
    provenance: SourceProvenance
    captured_at: datetime
    raw_payload_reference: str | None = None

    @field_validator("retailer_id")
    @classmethod
    def _retailer_id(cls, value: str) -> str:
        value = _nonblank(value).upper()
        if value not in SUPPORTED_RETAILER_IDS:
            raise ValueError("unsupported retailer identifier")
        return value

    @field_validator("retailer_product_id", "title")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("quantity_text", "category_text", "product_url", "raw_payload_reference")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @field_validator("captured_at")
    @classmethod
    def _captured_at(cls, value: datetime) -> datetime:
        return _aware(value)

    @field_validator("identifiers")
    @classmethod
    def _identifiers(
        cls, value: tuple[tuple[str, str], ...]
    ) -> tuple[tuple[str, str], ...]:
        seen: set[str] = set()
        normalized: list[tuple[str, str]] = []
        for key, item in value:
            key = _nonblank(key)
            if key in seen:
                raise ValueError("duplicate retailer identifier key")
            seen.add(key)
            normalized.append((key, _nonblank(item)))
        return tuple(normalized)

    @model_validator(mode="after")
    def _provenance(self) -> RetailerProduct:
        if self.provenance.retailer_id != self.retailer_id:
            raise ValueError("product retailer must match its provenance retailer")
        return self


class PriceObservation(BaseModel):
    """Observed price with explicit currency and semantics.

    A missing amount stays ``None``. Currency may still be preserved when the
    retailer's currency is known but the amount is not.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_id: str
    retailer_product_id: str
    price: Money | None = None
    currency: str | None = None
    reference_price: Money | None = None
    display_text: str | None = None
    reference_display_text: str | None = None
    price_semantics: PriceSemantics
    checkout_evidence_reference: str | None = None
    location: RetailerLocationContext
    acquisition: AcquisitionMetadata
    captured_at: datetime

    @field_validator("retailer_id")
    @classmethod
    def _retailer_id(cls, value: str) -> str:
        value = _nonblank(value).upper()
        if value not in SUPPORTED_RETAILER_IDS:
            raise ValueError("unsupported retailer identifier")
        return value

    @field_validator("retailer_product_id")
    @classmethod
    def _product_id(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if len(value) != 3:
            raise ValueError("currency must be a 3-letter ISO code")
        return value

    @field_validator(
        "display_text",
        "reference_display_text",
        "checkout_evidence_reference",
    )
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @field_validator("captured_at")
    @classmethod
    def _captured_at(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def _price_contract(self) -> PriceObservation:
        if (
            self.price is not None
            and self.currency is not None
            and self.price.currency != self.currency
        ):
            raise ValueError("currency must match the observed price currency")
        if (
            self.price_semantics is PriceSemantics.CHECKOUT_PRICE
            and self.checkout_evidence_reference is None
        ):
            raise ValueError(
                "checkout price semantics require an explicit checkout evidence reference"
            )
        if self.acquisition.operation is not AdapterCapability.PRICE_ACQUISITION:
            raise ValueError("price observations require price acquisition metadata")
        if self.acquisition.retailer_id != self.retailer_id:
            raise ValueError("price retailer must match acquisition metadata")
        return self

    @property
    def effective_currency(self) -> str | None:
        if self.currency is not None:
            return self.currency
        return None if self.price is None else self.price.currency


class AvailabilityObservation(BaseModel):
    """Observed availability; an unknown signal remains explicitly unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer_id: str
    retailer_product_id: str
    status: AvailabilityStatus
    raw_signal: str | None = None
    location: RetailerLocationContext
    acquisition: AcquisitionMetadata
    captured_at: datetime

    @field_validator("retailer_id")
    @classmethod
    def _retailer_id(cls, value: str) -> str:
        value = _nonblank(value).upper()
        if value not in SUPPORTED_RETAILER_IDS:
            raise ValueError("unsupported retailer identifier")
        return value

    @field_validator("retailer_product_id")
    @classmethod
    def _product_id(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("raw_signal")
    @classmethod
    def _raw_signal(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @field_validator("captured_at")
    @classmethod
    def _captured_at(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def _availability_contract(self) -> AvailabilityObservation:
        if self.acquisition.operation is not AdapterCapability.AVAILABILITY_ACQUISITION:
            raise ValueError(
                "availability observations require availability acquisition metadata"
            )
        if self.acquisition.retailer_id != self.retailer_id:
            raise ValueError("availability retailer must match acquisition metadata")
        return self


class AdapterOperationResult(BaseModel):
    """Common envelope for every typed adapter outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: AdapterOutcome
    reason_code: str | None = None
    diagnostic: str | None = None
    acquisition: AcquisitionMetadata | None = None

    @field_validator("reason_code", "diagnostic")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @model_validator(mode="after")
    def _result_contract(self) -> AdapterOperationResult:
        if self.outcome is AdapterOutcome.SUCCESS and self.acquisition is None:
            raise ValueError("successful operations require acquisition metadata")
        if (
            self.outcome
            not in {AdapterOutcome.SUCCESS, AdapterOutcome.OUT_OF_STOCK}
            and self.reason_code is None
            and self.diagnostic is None
        ):
            raise ValueError("non-success outcomes require a reason_code or diagnostic")
        return self


class ConnectionValidationResult(AdapterOperationResult):
    validation: ConnectionValidationState | None = None
    capabilities: tuple[CapabilityDeclaration, ...] = Field(default_factory=tuple)
    requires_user_action: bool = False

    @model_validator(mode="after")
    def _validation_contract(self) -> ConnectionValidationResult:
        if self.outcome is AdapterOutcome.SUCCESS:
            if self.validation is not ConnectionValidationState.VALID:
                raise ValueError("successful validation requires a VALID state")
        elif self.outcome is AdapterOutcome.AUTHENTICATION_FAILED:
            if self.validation is not ConnectionValidationState.AUTHENTICATION_FAILED:
                raise ValueError(
                    "authentication failure requires AUTHENTICATION_FAILED validation"
                )
        elif (
            self.outcome is AdapterOutcome.REQUIRES_USER_ACTION
            and (
                self.validation is not ConnectionValidationState.REAUTH_REQUIRED
                or not self.requires_user_action
            )
        ):
            raise ValueError(
                "user action requires REAUTH_REQUIRED validation and an explicit flag"
            )
        return self


class ProductSearchResult(AdapterOperationResult):
    products: tuple[RetailerProduct, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _search_contract(self) -> ProductSearchResult:
        if self.outcome is not AdapterOutcome.SUCCESS and self.products:
            raise ValueError("failed searches must not carry products")
        return self


class ProductDetailsResult(AdapterOperationResult):
    product: RetailerProduct | None = None

    @model_validator(mode="after")
    def _details_contract(self) -> ProductDetailsResult:
        if self.outcome is AdapterOutcome.SUCCESS and self.product is None:
            raise ValueError("successful details require a product")
        if self.outcome is not AdapterOutcome.SUCCESS and self.product is not None:
            raise ValueError("failed details must not carry a product")
        return self


class PriceResult(AdapterOperationResult):
    price: PriceObservation | None = None

    @model_validator(mode="after")
    def _price_result_contract(self) -> PriceResult:
        if self.outcome is AdapterOutcome.SUCCESS and self.price is None:
            raise ValueError("successful price acquisition requires a price observation")
        if self.outcome is not AdapterOutcome.SUCCESS and self.price is not None:
            raise ValueError("failed price acquisition must not carry a price")
        return self


class AvailabilityResult(AdapterOperationResult):
    availability: AvailabilityObservation | None = None

    @model_validator(mode="after")
    def _availability_result_contract(self) -> AvailabilityResult:
        if self.outcome is AdapterOutcome.SUCCESS:
            if self.availability is None:
                raise ValueError(
                    "successful availability acquisition requires an observation"
                )
            if self.availability.status is AvailabilityStatus.OUT_OF_STOCK:
                raise ValueError(
                    "out-of-stock availability must use the OUT_OF_STOCK outcome"
                )
        elif self.outcome is AdapterOutcome.OUT_OF_STOCK:
            if (
                self.availability is None
                or self.availability.status is not AvailabilityStatus.OUT_OF_STOCK
            ):
                raise ValueError(
                    "OUT_OF_STOCK requires an out-of-stock availability observation"
                )
        elif self.availability is not None:
            raise ValueError("failed availability acquisition must not carry an observation")
        return self


class LocationSelectionResult(AdapterOperationResult):
    selected: RetailerLocationContext | None = None
    candidates: tuple[RetailerLocationContext, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _location_contract(self) -> LocationSelectionResult:
        if self.outcome is AdapterOutcome.SUCCESS:
            if self.selected is None:
                raise ValueError("successful location selection requires a selection")
            if self.selected.kind is not LocationContextKind.VERIFIED_DELIVERY_LOCATION:
                raise ValueError(
                    "selected locations must be verified delivery locations"
                )
        elif self.selected is not None:
            raise ValueError("failed location selection must not carry a selection")
        return self


class CartPreparationResult(AdapterOperationResult):
    cart_reference: str | None = None
    checkout_ready: bool = False

    @field_validator("cart_reference")
    @classmethod
    def _cart_reference(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @model_validator(mode="after")
    def _cart_contract(self) -> CartPreparationResult:
        if self.outcome is AdapterOutcome.SUCCESS:
            if self.cart_reference is None:
                raise ValueError("successful cart preparation requires a cart reference")
        elif self.cart_reference is not None or self.checkout_ready:
            raise ValueError("failed cart preparation must not claim a prepared cart")
        if self.checkout_ready and self.cart_reference is None:
            raise ValueError("checkout readiness requires a prepared cart reference")
        return self


class CheckoutHandoffResult(AdapterOperationResult):
    handoff_reference: str | None = None

    @field_validator("handoff_reference")
    @classmethod
    def _handoff_reference(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @model_validator(mode="after")
    def _handoff_contract(self) -> CheckoutHandoffResult:
        if self.outcome is AdapterOutcome.SUCCESS and self.handoff_reference is None:
            raise ValueError("successful checkout handoff requires a reference")
        if self.outcome is not AdapterOutcome.SUCCESS and self.handoff_reference is not None:
            raise ValueError("failed checkout handoff must not carry a reference")
        return self


class OrderStatusResult(AdapterOperationResult):
    retailer_order_id: str | None = None
    order_status: str | None = None

    @field_validator("retailer_order_id", "order_status")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return _optional_nonblank(value)

    @model_validator(mode="after")
    def _order_contract(self) -> OrderStatusResult:
        if self.outcome is AdapterOutcome.SUCCESS and self.order_status is None:
            raise ValueError("successful order status requires an order status")
        if self.outcome is not AdapterOutcome.SUCCESS and self.order_status is not None:
            raise ValueError("failed order status must not carry an order status")
        return self


class AdapterOperationError(Exception):
    """Typed failure raised by an adapter implementation.

    The executor converts this into the operation-specific result model. An
    adapter never needs to fabricate a payload to report a failure.
    """

    def __init__(
        self,
        outcome: AdapterOutcome,
        *,
        reason_code: str,
        diagnostic: str | None = None,
    ) -> None:
        if outcome is AdapterOutcome.SUCCESS:
            raise ValueError("AdapterOperationError cannot represent success")
        self.outcome = outcome
        self.reason_code = reason_code
        self.diagnostic = diagnostic
        super().__init__(f"{outcome.value}: {reason_code}")


class UnauthorizedAdapterInvocation(Exception):
    """An adapter operation was invoked outside the authorized executor path."""


class InvalidAdapterOperation(Exception):
    """A caller supplied an unknown capability or mismatched request type."""


def request_type_for(capability: AdapterCapability) -> type[BaseModel]:
    """Return the typed request model for ``capability``."""

    return _REQUEST_TYPES[capability]


def result_type_for(capability: AdapterCapability) -> type[AdapterOperationResult]:
    """Return the typed result model for ``capability``."""

    return _RESULT_TYPES[capability]


_REQUEST_TYPES: dict[AdapterCapability, type[BaseModel]] = {
    AdapterCapability.CONNECTION_VALIDATION: ConnectionValidationRequest,
    AdapterCapability.PRODUCT_DISCOVERY: ProductSearchRequest,
    AdapterCapability.PRODUCT_DETAILS: ProductDetailsRequest,
    AdapterCapability.PRICE_ACQUISITION: PriceRequest,
    AdapterCapability.AVAILABILITY_ACQUISITION: AvailabilityRequest,
    AdapterCapability.LOCATION_SELECTION: LocationSelectionRequest,
    AdapterCapability.CART_PREPARATION: CartPreparationRequest,
    AdapterCapability.CHECKOUT_HANDOFF: CheckoutHandoffRequest,
    AdapterCapability.ORDER_STATUS: OrderStatusRequest,
}

_RESULT_TYPES: dict[AdapterCapability, type[AdapterOperationResult]] = {
    AdapterCapability.CONNECTION_VALIDATION: ConnectionValidationResult,
    AdapterCapability.PRODUCT_DISCOVERY: ProductSearchResult,
    AdapterCapability.PRODUCT_DETAILS: ProductDetailsResult,
    AdapterCapability.PRICE_ACQUISITION: PriceResult,
    AdapterCapability.AVAILABILITY_ACQUISITION: AvailabilityResult,
    AdapterCapability.LOCATION_SELECTION: LocationSelectionResult,
    AdapterCapability.CART_PREPARATION: CartPreparationResult,
    AdapterCapability.CHECKOUT_HANDOFF: CheckoutHandoffResult,
    AdapterCapability.ORDER_STATUS: OrderStatusResult,
}


def failure_result(
    capability: AdapterCapability,
    outcome: AdapterOutcome,
    *,
    reason_code: str,
    diagnostic: str | None = None,
    acquisition: AcquisitionMetadata | None = None,
) -> AdapterOperationResult:
    """Build the correct typed failure result for ``capability``."""

    result_type = result_type_for(capability)
    payload: dict[str, Any] = {
        "outcome": outcome,
        "reason_code": reason_code,
        "diagnostic": diagnostic,
        "acquisition": acquisition,
    }
    if result_type is ConnectionValidationResult:
        if outcome is AdapterOutcome.REQUIRES_USER_ACTION:
            payload["validation"] = ConnectionValidationState.REAUTH_REQUIRED
            payload["requires_user_action"] = True
        elif outcome is AdapterOutcome.AUTHENTICATION_FAILED:
            payload["validation"] = ConnectionValidationState.AUTHENTICATION_FAILED
    return result_type(**payload)


__all__ = [
    "AcquisitionMetadata",
    "AdapterCapability",
    "AdapterOperationError",
    "AdapterOperationResult",
    "AdapterOutcome",
    "AvailabilityObservation",
    "AvailabilityRequest",
    "AvailabilityResult",
    "AvailabilityStatus",
    "CapabilityDeclaration",
    "CapabilityStatus",
    "CartItemRequest",
    "CartPreparationRequest",
    "CartPreparationResult",
    "CheckoutHandoffRequest",
    "CheckoutHandoffResult",
    "ConnectionValidationRequest",
    "ConnectionValidationResult",
    "ConnectionValidationState",
    "InvalidAdapterOperation",
    "LocationContextKind",
    "LocationSelectionRequest",
    "LocationSelectionResult",
    "OrderStatusRequest",
    "OrderStatusResult",
    "PriceObservation",
    "PriceRequest",
    "PriceResult",
    "PriceSemantics",
    "ProductDetailsRequest",
    "ProductDetailsResult",
    "ProductSearchRequest",
    "ProductSearchResult",
    "RetailerConnectionReference",
    "RetailerLocationContext",
    "RetailerOperationContext",
    "RetailerProduct",
    "SourceProvenance",
    "UnauthorizedAdapterInvocation",
    "failure_result",
    "request_type_for",
    "result_type_for",
]
