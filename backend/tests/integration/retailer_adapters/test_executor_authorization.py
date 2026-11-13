"""Integration coverage for the shared adapter enforcement path."""

from __future__ import annotations

import pytest

from app.retailer_adapters.capabilities import ALL_CAPABILITIES, AdapterCapabilities
from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOutcome,
    CapabilityDeclaration,
    CapabilityStatus,
    ConnectionValidationRequest,
    InvalidAdapterOperation,
    ProductSearchRequest,
)
from app.retailer_adapters.enforcement import RetailerAdapterExecutor
from app.retailer_adapters.registry import (
    RetailerAdapterRegistry,
    build_default_registry,
)
from app.retailer_connections.lifecycle import RetailerConnectionStatus
from tests.unit.retailer_adapters.support import (
    FakeAdapter,
    adapter_with_all_capabilities,
    search_location,
)


def make_executor(*adapters: FakeAdapter) -> RetailerAdapterExecutor:
    registry = RetailerAdapterRegistry()
    for adapter in adapters:
        registry.register(adapter)
    return RetailerAdapterExecutor(registry=registry)


def search_request() -> ProductSearchRequest:
    return ProductSearchRequest(query="milk", location=search_location())


@pytest.mark.asyncio
async def test_ownership_mismatch_is_indistinguishable_from_missing_connection(
    db_session, make_user, make_connection
) -> None:
    owner = make_user()
    other = make_user()
    connection = make_connection(
        user_id=owner.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=other.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.ACCESS_DENIED
    assert result.reason_code == "connection_not_found"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_pending_auth_requires_user_action(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.PENDING_AUTH
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.REQUIRES_USER_ACTION
    assert result.reason_code == "authentication_pending"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_reauth_required_requires_user_action(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.REAUTH_REQUIRED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.REQUIRES_USER_ACTION
    assert result.reason_code == "reauthorization_required"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_blocked_connection_is_access_denied(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.BLOCKED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.ACCESS_DENIED
    assert result.reason_code == "connection_blocked"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_degraded_connection_permits_health_check_but_not_discovery(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.DEGRADED
    )
    adapter = adapter_with_all_capabilities()
    executor = make_executor(adapter)

    denied = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )
    allowed = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.CONNECTION_VALIDATION,
        request=ConnectionValidationRequest(),
    )

    assert denied.outcome is AdapterOutcome.ACCESS_DENIED
    assert denied.reason_code == "connection_degraded"
    assert allowed.outcome is AdapterOutcome.SUCCESS
    assert [call[0] for call in adapter.calls] == [
        AdapterCapability.CONNECTION_VALIDATION
    ]


@pytest.mark.asyncio
async def test_placeholder_capability_is_explicitly_unsupported(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    executor = RetailerAdapterExecutor(registry=build_default_registry())

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.UNSUPPORTED
    assert result.reason_code == "placeholder_not_implemented"


@pytest.mark.asyncio
async def test_not_verified_capability_is_not_executed(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    adapter.capabilities = AdapterCapabilities(
        CapabilityDeclaration(
            capability=capability,
            status=(
                CapabilityStatus.NOT_VERIFIED
                if capability is AdapterCapability.PRODUCT_DISCOVERY
                else CapabilityStatus.UNSUPPORTED
            ),
            reason_code=(
                "not_verified"
                if capability is AdapterCapability.PRODUCT_DISCOVERY
                else "not_implemented"
            ),
        )
        for capability in ALL_CAPABILITIES
    )
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.UNSUPPORTED
    assert result.reason_code == "not_verified"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_capability_requiring_user_action_is_not_executed(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    adapter.capabilities = AdapterCapabilities(
        CapabilityDeclaration(
            capability=capability,
            status=(
                CapabilityStatus.REQUIRES_USER_ACTION
                if capability is AdapterCapability.PRODUCT_DISCOVERY
                else CapabilityStatus.UNSUPPORTED
            ),
            reason_code=(
                "retailer_consent_required"
                if capability is AdapterCapability.PRODUCT_DISCOVERY
                else "not_implemented"
            ),
        )
        for capability in ALL_CAPABILITIES
    )
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.REQUIRES_USER_ACTION
    assert result.reason_code == "retailer_consent_required"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_adapter_id_mismatch_is_access_denied(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
        adapter_id="another-adapter",
    )

    assert result.outcome is AdapterOutcome.ACCESS_DENIED
    assert result.reason_code == "adapter_mismatch"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_unregistered_retailer_adapter_is_unsupported(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id,
        status=RetailerConnectionStatus.CONNECTED,
        retailer_id="ZEPTO",
    )
    adapter = FakeAdapter(
        retailer_id="BLINKIT",
        adapter_id="fake-blinkit",
        supported=(AdapterCapability.PRODUCT_DISCOVERY,),
    )
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.UNSUPPORTED
    assert result.reason_code == "adapter_not_registered"


@pytest.mark.asyncio
async def test_blinkit_connection_is_policy_blocked_before_adapter_execution(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id,
        status=RetailerConnectionStatus.CONNECTED,
        retailer_id="BLINKIT",
    )
    adapter = FakeAdapter(
        retailer_id="BLINKIT",
        adapter_id="fake-blinkit",
        supported=(AdapterCapability.PRODUCT_DISCOVERY,),
    )
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
    )

    assert result.outcome is AdapterOutcome.POLICY_BLOCKED
    assert result.reason_code == "blinkit_commercial_authorization_required"
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_unknown_capability_is_rejected(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    executor = make_executor(
        FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    )

    with pytest.raises(InvalidAdapterOperation):
        await executor.execute(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            capability="NOT_A_CAPABILITY",
            request=search_request(),
        )


@pytest.mark.asyncio
async def test_successful_execution_returns_typed_result_and_provenance(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))
    executor = make_executor(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=search_request(),
        request_id="request-42",
    )

    assert result.outcome is AdapterOutcome.SUCCESS
    assert result.acquisition is not None
    assert result.acquisition.attempt_count == 1
    assert result.acquisition.retried is False
    assert result.acquisition.retailer_id == "ZEPTO"
    assert result.acquisition.request_id == "request-1"
    assert adapter.calls[0][0] is AdapterCapability.PRODUCT_DISCOVERY
