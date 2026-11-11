"""Integration coverage for every typed adapter outcome."""

from __future__ import annotations

import pytest

from app.retailer_adapters.capabilities import ALL_CAPABILITIES
from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOperationError,
    AdapterOutcome,
    AvailabilityResult,
    AvailabilityStatus,
    ConnectionValidationRequest,
    ConnectionValidationResult,
    ConnectionValidationState,
    ProductSearchResult,
)
from app.retailer_adapters.enforcement import RetailerAdapterExecutor
from app.retailer_adapters.registry import RetailerAdapterRegistry
from app.retailer_adapters.resilience import ExecutionPolicy, RetailerExecutionGuard
from app.retailer_connections.lifecycle import RetailerConnectionStatus
from tests.unit.retailer_adapters.support import (
    FakeAdapter,
    acquisition,
    availability_observation,
    request_for,
    search_location,
)


def executor_for(adapter: FakeAdapter, *, guard=None) -> RetailerAdapterExecutor:
    registry = RetailerAdapterRegistry()
    registry.register(adapter)
    return RetailerAdapterExecutor(registry=registry, guard=guard)


@pytest.mark.asyncio
async def test_every_unsupported_capability_returns_unsupported(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=())
    executor = executor_for(adapter)

    for capability in ALL_CAPABILITIES:
        result = await executor.execute(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            capability=capability,
            request=request_for(capability),
        )
        assert result.outcome is AdapterOutcome.UNSUPPORTED
        assert result.reason_code == "not_implemented"

    assert adapter.calls == []


@pytest.mark.asyncio
async def test_authentication_failed_is_returned_without_lifecycle_mutation(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.CONNECTION_VALIDATION,))

    async def authentication_failed() -> ConnectionValidationResult:
        return ConnectionValidationResult(
            outcome=AdapterOutcome.AUTHENTICATION_FAILED,
            validation=ConnectionValidationState.AUTHENTICATION_FAILED,
            reason_code="authentication_failed",
            acquisition=acquisition(AdapterCapability.CONNECTION_VALIDATION),
        )

    adapter.behaviors[AdapterCapability.CONNECTION_VALIDATION] = authentication_failed
    executor = executor_for(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.CONNECTION_VALIDATION,
        request=ConnectionValidationRequest(),
    )

    assert result.outcome is AdapterOutcome.AUTHENTICATION_FAILED
    db_session.refresh(connection)
    assert connection.status == RetailerConnectionStatus.CONNECTED.value


@pytest.mark.asyncio
async def test_invalid_evidence_is_a_typed_outcome(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))

    async def invalid_evidence() -> ProductSearchResult:
        return ProductSearchResult(
            outcome=AdapterOutcome.INVALID_EVIDENCE,
            reason_code="missing_evidence",
        )

    adapter.behaviors[AdapterCapability.PRODUCT_DISCOVERY] = invalid_evidence
    executor = executor_for(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request_for(AdapterCapability.PRODUCT_DISCOVERY),
    )

    assert result.outcome is AdapterOutcome.INVALID_EVIDENCE
    assert result.reason_code == "missing_evidence"


@pytest.mark.asyncio
async def test_unexpected_adapter_failure_is_unknown_outcome(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))

    async def broken() -> ProductSearchResult:
        raise RuntimeError("unexpected")

    adapter.behaviors[AdapterCapability.PRODUCT_DISCOVERY] = broken
    executor = executor_for(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request_for(AdapterCapability.PRODUCT_DISCOVERY),
    )

    assert result.outcome is AdapterOutcome.UNKNOWN_OUTCOME
    assert result.reason_code == "unexpected_adapter_failure"


@pytest.mark.asyncio
async def test_out_of_stock_is_a_typed_outcome(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.AVAILABILITY_ACQUISITION,))

    async def out_of_stock() -> AvailabilityResult:
        return AvailabilityResult(
            outcome=AdapterOutcome.OUT_OF_STOCK,
            availability=availability_observation(
                status=AvailabilityStatus.OUT_OF_STOCK
            ),
        )

    adapter.behaviors[AdapterCapability.AVAILABILITY_ACQUISITION] = out_of_stock
    executor = executor_for(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.AVAILABILITY_ACQUISITION,
        request=request_for(AdapterCapability.AVAILABILITY_ACQUISITION),
    )

    assert result.outcome is AdapterOutcome.OUT_OF_STOCK
    assert result.availability is not None
    assert result.availability.status.value == "OUT_OF_STOCK"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome",
    [AdapterOutcome.TEMPORARY_FAILURE, AdapterOutcome.RATE_LIMITED],
)
async def test_terminal_transient_outcomes_are_returned_after_bounded_attempts(
    db_session, make_user, make_connection, outcome
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    attempts = 0
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))

    async def fails() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        raise AdapterOperationError(outcome, reason_code="transient")

    adapter.behaviors[AdapterCapability.PRODUCT_DISCOVERY] = fails
    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=1,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            jitter_ratio=0.0,
        )
    )
    executor = executor_for(adapter, guard=guard)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request_for(AdapterCapability.PRODUCT_DISCOVERY),
    )

    assert result.outcome is outcome
    assert attempts == 1


@pytest.mark.asyncio
async def test_access_denied_result_does_not_revoke_connection(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))

    async def forbidden() -> ProductSearchResult:
        return ProductSearchResult(
            outcome=AdapterOutcome.ACCESS_DENIED,
            reason_code="http_403",
        )

    adapter.behaviors[AdapterCapability.PRODUCT_DISCOVERY] = forbidden
    executor = executor_for(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request_for(AdapterCapability.PRODUCT_DISCOVERY),
    )

    assert result.outcome is AdapterOutcome.ACCESS_DENIED
    db_session.refresh(connection)
    assert connection.status == RetailerConnectionStatus.CONNECTED.value


@pytest.mark.asyncio
async def test_unknown_outcome_is_not_retried(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    attempts = 0
    adapter = FakeAdapter(supported=(AdapterCapability.PRODUCT_DISCOVERY,))

    async def unknown() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("unknown")

    adapter.behaviors[AdapterCapability.PRODUCT_DISCOVERY] = unknown
    executor = executor_for(adapter)

    result = await executor.execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request_for(AdapterCapability.PRODUCT_DISCOVERY),
    )

    assert result.outcome is AdapterOutcome.UNKNOWN_OUTCOME
    assert attempts == 1


def test_search_location_helper_is_explicit() -> None:
    assert search_location().verified_at is None
