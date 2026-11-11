"""Base adapter contract and authorization guard.

Adapter implementations only override the private ``_perform_*`` operations.
Every public operation requires an executor-minted authorization token, so a
consumer service cannot invoke an adapter directly and bypass ownership,
lifecycle, capability, or vault checks.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.credential_vault.types import SecretType
from app.retailer_adapters.authorization import AuthorizedRetailerOperation
from app.retailer_adapters.capabilities import AdapterCapabilities
from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOperationError,
    AdapterOperationResult,
    AdapterOutcome,
    AvailabilityRequest,
    AvailabilityResult,
    CartPreparationRequest,
    CartPreparationResult,
    CheckoutHandoffRequest,
    CheckoutHandoffResult,
    ConnectionValidationRequest,
    ConnectionValidationResult,
    InvalidAdapterOperation,
    LocationSelectionRequest,
    LocationSelectionResult,
    OrderStatusRequest,
    OrderStatusResult,
    PriceRequest,
    PriceResult,
    ProductDetailsRequest,
    ProductDetailsResult,
    ProductSearchRequest,
    ProductSearchResult,
    UnauthorizedAdapterInvocation,
    request_type_for,
)
from app.retailer_adapters.credentials import RetailerCredentialBundle
from app.retailer_adapters.resilience import ExecutionPolicy
from app.retailer_data.contracts import AcquisitionMethod

_PERFORM_METHODS: Mapping[AdapterCapability, str] = {
    AdapterCapability.CONNECTION_VALIDATION: "_perform_connection_validation",
    AdapterCapability.PRODUCT_DISCOVERY: "_perform_product_search",
    AdapterCapability.PRODUCT_DETAILS: "_perform_product_details",
    AdapterCapability.PRICE_ACQUISITION: "_perform_price",
    AdapterCapability.AVAILABILITY_ACQUISITION: "_perform_availability",
    AdapterCapability.LOCATION_SELECTION: "_perform_location_selection",
    AdapterCapability.CART_PREPARATION: "_perform_cart_preparation",
    AdapterCapability.CHECKOUT_HANDOFF: "_perform_checkout_handoff",
    AdapterCapability.ORDER_STATUS: "_perform_order_status",
}

_PUBLIC_HANDLERS: Mapping[AdapterCapability, str] = {
    AdapterCapability.CONNECTION_VALIDATION: "validate_connection",
    AdapterCapability.PRODUCT_DISCOVERY: "search_products",
    AdapterCapability.PRODUCT_DETAILS: "get_product_details",
    AdapterCapability.PRICE_ACQUISITION: "get_price",
    AdapterCapability.AVAILABILITY_ACQUISITION: "get_availability",
    AdapterCapability.LOCATION_SELECTION: "select_location",
    AdapterCapability.CART_PREPARATION: "prepare_cart",
    AdapterCapability.CHECKOUT_HANDOFF: "handoff_checkout",
    AdapterCapability.ORDER_STATUS: "get_order_status",
}


class RetailerAdapter:
    """Provider-independent adapter surface for one retailer."""

    adapter_id: str
    retailer_id: str
    capabilities: AdapterCapabilities
    acquisition_method: AcquisitionMethod = AcquisitionMethod.AUTHORIZED_THIRD_PARTY
    execution_policy: ExecutionPolicy | None = None

    @classmethod
    def implements(cls, capability: AdapterCapability) -> bool:
        """Whether this class implements the operation behind ``capability``."""

        method_name = _PERFORM_METHODS[capability]
        base = getattr(RetailerAdapter, method_name)
        candidate = getattr(cls, method_name, None)
        return candidate is not None and candidate is not base

    def required_secret_types(
        self, capability: AdapterCapability
    ) -> tuple[SecretType, ...]:
        """Declare secrets the executor must resolve before this operation.

        The default is no secret material. Adapters must not fetch secrets
        themselves.
        """

        return ()

    async def execute(
        self,
        authorization: AuthorizedRetailerOperation,
        capability: AdapterCapability,
        request: object,
    ) -> AdapterOperationResult:
        """Authorized dispatch used by the shared executor."""

        self._require_authorization(authorization, capability)
        expected = request_type_for(capability)
        if not isinstance(request, expected):
            raise InvalidAdapterOperation(
                f"{capability.value} requires {expected.__name__}"
            )
        handler = getattr(self, _PUBLIC_HANDLERS[capability])
        return await handler(authorization, request)

    async def validate_connection(
        self,
        authorization: AuthorizedRetailerOperation,
        request: ConnectionValidationRequest,
    ) -> ConnectionValidationResult:
        self._require_authorization(
            authorization, AdapterCapability.CONNECTION_VALIDATION
        )
        return await self._perform_connection_validation(
            request, authorization.credentials
        )

    async def search_products(
        self,
        authorization: AuthorizedRetailerOperation,
        request: ProductSearchRequest,
    ) -> ProductSearchResult:
        self._require_authorization(
            authorization, AdapterCapability.PRODUCT_DISCOVERY
        )
        return await self._perform_product_search(request, authorization.credentials)

    async def get_product_details(
        self,
        authorization: AuthorizedRetailerOperation,
        request: ProductDetailsRequest,
    ) -> ProductDetailsResult:
        self._require_authorization(
            authorization, AdapterCapability.PRODUCT_DETAILS
        )
        return await self._perform_product_details(
            request, authorization.credentials
        )

    async def get_price(
        self,
        authorization: AuthorizedRetailerOperation,
        request: PriceRequest,
    ) -> PriceResult:
        self._require_authorization(
            authorization, AdapterCapability.PRICE_ACQUISITION
        )
        return await self._perform_price(request, authorization.credentials)

    async def get_availability(
        self,
        authorization: AuthorizedRetailerOperation,
        request: AvailabilityRequest,
    ) -> AvailabilityResult:
        self._require_authorization(
            authorization, AdapterCapability.AVAILABILITY_ACQUISITION
        )
        return await self._perform_availability(
            request, authorization.credentials
        )

    async def select_location(
        self,
        authorization: AuthorizedRetailerOperation,
        request: LocationSelectionRequest,
    ) -> LocationSelectionResult:
        self._require_authorization(
            authorization, AdapterCapability.LOCATION_SELECTION
        )
        return await self._perform_location_selection(
            request, authorization.credentials
        )

    async def prepare_cart(
        self,
        authorization: AuthorizedRetailerOperation,
        request: CartPreparationRequest,
    ) -> CartPreparationResult:
        self._require_authorization(
            authorization, AdapterCapability.CART_PREPARATION
        )
        return await self._perform_cart_preparation(
            request, authorization.credentials
        )

    async def handoff_checkout(
        self,
        authorization: AuthorizedRetailerOperation,
        request: CheckoutHandoffRequest,
    ) -> CheckoutHandoffResult:
        self._require_authorization(
            authorization, AdapterCapability.CHECKOUT_HANDOFF
        )
        return await self._perform_checkout_handoff(
            request, authorization.credentials
        )

    async def get_order_status(
        self,
        authorization: AuthorizedRetailerOperation,
        request: OrderStatusRequest,
    ) -> OrderStatusResult:
        self._require_authorization(
            authorization, AdapterCapability.ORDER_STATUS
        )
        return await self._perform_order_status(
            request, authorization.credentials
        )

    def _require_authorization(
        self,
        authorization: object,
        capability: AdapterCapability,
    ) -> AuthorizedRetailerOperation:
        if not isinstance(authorization, AuthorizedRetailerOperation):
            raise UnauthorizedAdapterInvocation(
                "adapter operations require the shared executor authorization"
            )
        if not authorization.authorizes(
            adapter_id=self.adapter_id,
            retailer_id=self.retailer_id,
            capability=capability,
        ):
            raise UnauthorizedAdapterInvocation(
                "authorization does not match this adapter, retailer, or capability"
            )
        return authorization

    # ------------------------------------------------------------------
    # Implementation hooks. The default is an explicit unsupported outcome;
    # an adapter declaring SUPPORTED must override the relevant hook, which the
    # registry verifies at registration time.
    # ------------------------------------------------------------------

    async def _perform_connection_validation(
        self,
        request: ConnectionValidationRequest,
        credentials: RetailerCredentialBundle,
    ) -> ConnectionValidationResult:
        raise _not_implemented()

    async def _perform_product_search(
        self,
        request: ProductSearchRequest,
        credentials: RetailerCredentialBundle,
    ) -> ProductSearchResult:
        raise _not_implemented()

    async def _perform_product_details(
        self,
        request: ProductDetailsRequest,
        credentials: RetailerCredentialBundle,
    ) -> ProductDetailsResult:
        raise _not_implemented()

    async def _perform_price(
        self,
        request: PriceRequest,
        credentials: RetailerCredentialBundle,
    ) -> PriceResult:
        raise _not_implemented()

    async def _perform_availability(
        self,
        request: AvailabilityRequest,
        credentials: RetailerCredentialBundle,
    ) -> AvailabilityResult:
        raise _not_implemented()

    async def _perform_location_selection(
        self,
        request: LocationSelectionRequest,
        credentials: RetailerCredentialBundle,
    ) -> LocationSelectionResult:
        raise _not_implemented()

    async def _perform_cart_preparation(
        self,
        request: CartPreparationRequest,
        credentials: RetailerCredentialBundle,
    ) -> CartPreparationResult:
        raise _not_implemented()

    async def _perform_checkout_handoff(
        self,
        request: CheckoutHandoffRequest,
        credentials: RetailerCredentialBundle,
    ) -> CheckoutHandoffResult:
        raise _not_implemented()

    async def _perform_order_status(
        self,
        request: OrderStatusRequest,
        credentials: RetailerCredentialBundle,
    ) -> OrderStatusResult:
        raise _not_implemented()


def _not_implemented() -> AdapterOperationError:
    return AdapterOperationError(
        AdapterOutcome.UNSUPPORTED,
        reason_code="operation_not_implemented",
    )


__all__ = ["RetailerAdapter"]
