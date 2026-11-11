"""Integration coverage for bounded retry and attempt provenance."""

from __future__ import annotations

import pytest

from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOperationError,
    AdapterOutcome,
    CartItemRequest,
    CartPreparationRequest,
    ProductSearchRequest,
    ProductSearchResult,
)
from app.retailer_adapters.enforcement import RetailerAdapterExecutor
from app.retailer_adapters.registry import RetailerAdapterRegistry
from app.retailer_adapters.resilience import ExecutionPolicy, RetailerExecutionGuard
from app.retailer_connections.lifecycle import RetailerConnectionStatus
from tests.unit.retailer_adapters.support import (
    FakeAdapter,
    acquisition,
    search_location,
)


def executor_with_guard(adapter: FakeAdapter, guard: RetailerExecutionGuard):
    registry = RetailerAdapterRegistry()
    registry.register(adapter)
    return RetailerAdapterExecutor(registry=registry, guard=guard)


@pytest.mark.asyncio
async def test_retry_annotates_attempt_provenance(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    attempts = 0
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))

    async def flaky() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise AdapterOperationError(
                AdapterOutcome.TEMPORARY_FAILURE,
                reason_code="temporary",
            )
        return ProductSearchResult(
            outcome=AdapterOutcome.SUCCESS,
            acquisition=acquisition(AdapterCapability.PRODUCT_DISCOVERY),
        )

    adapter.behaviors[AdapterCapability.PRODUCT_DISCOVERY] = flaky
    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=2,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            jitter_ratio=0.0,
        )
    )
    executor = executor_with_guard(adapter, guard)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=ProductSearchRequest(query="milk", location=search_location()),
    )

    assert result.outcome is AdapterOutcome.SUCCESS
    assert result.acquisition is not None
    assert result.acquisition.attempt_count == 2
    assert result.acquisition.retried is True
    assert attempts == 2


@pytest.mark.asyncio
async def test_non_idempotent_mutation_is_not_retried(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    attempts = 0
    adapter = FakeAdapter(supported=(AdapterCapability.CART_PREPARATION,))

    async def temporary() -> None:
        nonlocal attempts
        attempts += 1
        raise AdapterOperationError(
            AdapterOutcome.TEMPORARY_FAILURE,
            reason_code="temporary",
        )

    adapter.behaviors[AdapterCapability.CART_PREPARATION] = temporary
    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=3,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            jitter_ratio=0.0,
        )
    )
    executor = executor_with_guard(adapter, guard)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.CART_PREPARATION,
        request=CartPreparationRequest(
            items=(CartItemRequest(retailer_product_id="native-1"),),
            location=search_location(),
        ),
    )

    assert result.outcome is AdapterOutcome.TEMPORARY_FAILURE
    assert attempts == 1
