from __future__ import annotations

from uuid import uuid4

import pytest

from app.credential_vault.types import SecretType
from app.retailer_adapters.authorization import (
    _EXECUTOR_SENTINEL,
    AuthorizedRetailerOperation,
)
from app.retailer_adapters.base import RetailerAdapter
from app.retailer_adapters.capabilities import ALL_CAPABILITIES, CAPABILITY_OPERATIONS
from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOperationError,
    AdapterOutcome,
    AvailabilityRequest,
    AvailabilityResult,
    CartItemRequest,
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
    result_type_for,
)
from app.retailer_adapters.credentials import (
    SECRET_REDACTION,
    RetailerCredentialBundle,
    redact_log_fields,
)
from app.retailer_connections.lifecycle import RetailerConnectionStatus
from tests.unit.retailer_adapters.support import (
    BareAdapter,
    FakeAdapter,
    adapter_with_all_capabilities,
    search_location,
)


def authorization(
    adapter: RetailerAdapter,
    capability: AdapterCapability,
    *,
    adapter_id: str | None = None,
    retailer_id: str | None = None,
    credentials: RetailerCredentialBundle | None = None,
) -> AuthorizedRetailerOperation:
    return AuthorizedRetailerOperation(
        user_id=uuid4(),
        connection_id=uuid4(),
        retailer_id=retailer_id or adapter.retailer_id,
        lifecycle_status=RetailerConnectionStatus.CONNECTED,
        capability=capability,
        adapter_id=adapter_id or adapter.adapter_id,
        lifecycle_operation=CAPABILITY_OPERATIONS[capability],
        request_id="request-1",
        _sentinel=_EXECUTOR_SENTINEL,
        credentials=credentials or RetailerCredentialBundle({}),
    )


@pytest.mark.asyncio
async def test_direct_invocation_without_authorization_is_rejected() -> None:
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    request = ProductSearchRequest(query="milk", location=search_location())

    with pytest.raises(UnauthorizedAdapterInvocation):
        await adapter.search_products(None, request)  # type: ignore[arg-type]


def test_forged_authorization_token_is_rejected_at_construction() -> None:
    with pytest.raises(UnauthorizedAdapterInvocation):
        AuthorizedRetailerOperation(
            user_id=uuid4(),
            connection_id=uuid4(),
            retailer_id="BLINKIT",
            lifecycle_status=RetailerConnectionStatus.CONNECTED,
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            adapter_id="fake-blinkit",
            lifecycle_operation=CAPABILITY_OPERATIONS[
                AdapterCapability.PRODUCT_DISCOVERY
            ],
            request_id=None,
            _sentinel=object(),
        )


@pytest.mark.asyncio
async def test_authorization_for_another_adapter_is_rejected() -> None:
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    token = authorization(
        adapter,
        AdapterCapability.PRODUCT_DISCOVERY,
        adapter_id="other-adapter",
    )
    request = ProductSearchRequest(query="milk", location=search_location())

    with pytest.raises(UnauthorizedAdapterInvocation):
        await adapter.search_products(token, request)


@pytest.mark.asyncio
async def test_authorization_for_another_capability_is_rejected() -> None:
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    token = authorization(adapter, AdapterCapability.PRICE_ACQUISITION)
    request = ProductSearchRequest(query="milk", location=search_location())

    with pytest.raises(UnauthorizedAdapterInvocation):
        await adapter.search_products(token, request)


@pytest.mark.asyncio
async def test_authorized_execute_dispatches_to_typed_operation() -> None:
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    token = authorization(adapter, AdapterCapability.PRODUCT_DISCOVERY)
    request = ProductSearchRequest(query="milk", location=search_location())

    result = await adapter.execute(
        token, AdapterCapability.PRODUCT_DISCOVERY, request
    )

    assert isinstance(result, ProductSearchResult)
    assert result.outcome is AdapterOutcome.SUCCESS
    assert len(result.products) == 1
    assert adapter.calls[0][0] is AdapterCapability.PRODUCT_DISCOVERY


@pytest.mark.asyncio
async def test_execute_rejects_mismatched_request_type() -> None:
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    token = authorization(adapter, AdapterCapability.PRODUCT_DISCOVERY)

    with pytest.raises(InvalidAdapterOperation, match="ProductSearchRequest"):
        await adapter.execute(
            token,
            AdapterCapability.PRODUCT_DISCOVERY,
            PriceRequest(
                retailer_product_id="native-1",
                location=search_location(),
            ),
        )


@pytest.mark.asyncio
async def test_default_unimplemented_operation_is_explicitly_unsupported() -> None:
    adapter = BareAdapter(adapter_id="bare")
    token = authorization(adapter, AdapterCapability.PRODUCT_DISCOVERY)
    request = ProductSearchRequest(query="milk", location=search_location())

    with pytest.raises(AdapterOperationError) as exc_info:
        await adapter.search_products(token, request)

    assert exc_info.value.outcome is AdapterOutcome.UNSUPPORTED
    assert exc_info.value.reason_code == "operation_not_implemented"


def test_implements_reflects_private_operation_overrides() -> None:
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    bare = BareAdapter(adapter_id="bare")

    assert adapter.implements(AdapterCapability.PRODUCT_DISCOVERY)
    assert not bare.implements(AdapterCapability.PRODUCT_DISCOVERY)


def test_default_secret_requirement_is_empty() -> None:
    adapter = FakeAdapter(adapter_id="no-secrets")

    assert adapter.required_secret_types(AdapterCapability.PRODUCT_DISCOVERY) == ()


def test_credential_bundle_repr_never_contains_plaintext() -> None:
    bundle = RetailerCredentialBundle(
        {SecretType.OAUTH_REFRESH_TOKEN: b"super-secret-value"}
    )

    assert "super-secret-value" not in repr(bundle)
    assert "oauth_refresh_token" in repr(bundle)
    assert bundle.reveal(SecretType.OAUTH_REFRESH_TOKEN) == b"super-secret-value"


def test_redact_log_fields_removes_secret_shaped_values() -> None:
    redacted = redact_log_fields(
        {
            "retailer_id": "BLINKIT",
            "access_token": "secret-token",
            "api_key": "secret-key",
            "cookie": "session-cookie",
            "request_id": "request-1",
        }
    )

    assert redacted["retailer_id"] == "BLINKIT"
    assert redacted["request_id"] == "request-1"
    assert redacted["access_token"] == SECRET_REDACTION
    assert redacted["api_key"] == SECRET_REDACTION
    assert redacted["cookie"] == SECRET_REDACTION


def _requests() -> dict[AdapterCapability, object]:
    return {
        AdapterCapability.CONNECTION_VALIDATION: ConnectionValidationRequest(),
        AdapterCapability.PRODUCT_DISCOVERY: ProductSearchRequest(
            query="milk", location=search_location()
        ),
        AdapterCapability.PRODUCT_DETAILS: ProductDetailsRequest(
            retailer_product_id="native-1", location=search_location()
        ),
        AdapterCapability.PRICE_ACQUISITION: PriceRequest(
            retailer_product_id="native-1", location=search_location()
        ),
        AdapterCapability.AVAILABILITY_ACQUISITION: AvailabilityRequest(
            retailer_product_id="native-1", location=search_location()
        ),
        AdapterCapability.LOCATION_SELECTION: LocationSelectionRequest(
            location=search_location().scope
        ),
        AdapterCapability.CART_PREPARATION: CartPreparationRequest(
            items=(CartItemRequest(retailer_product_id="native-1"),),
            location=search_location(),
        ),
        AdapterCapability.CHECKOUT_HANDOFF: CheckoutHandoffRequest(
            cart_reference="cart-1", location=search_location()
        ),
        AdapterCapability.ORDER_STATUS: OrderStatusRequest(
            retailer_order_id="order-1"
        ),
    }


@pytest.mark.asyncio
async def test_all_typed_operations_dispatch_through_the_authorized_surface() -> None:
    adapter = adapter_with_all_capabilities()
    requests = _requests()

    for capability in ALL_CAPABILITIES:
        token = authorization(adapter, capability)
        result = await adapter.execute(token, capability, requests[capability])
        assert result.outcome is AdapterOutcome.SUCCESS

    assert {call[0] for call in adapter.calls} == set(ALL_CAPABILITIES)


def test_result_types_match_capability_contracts() -> None:
    expected = {
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

    for capability, result_type in expected.items():
        assert result_type_for(capability) is result_type
