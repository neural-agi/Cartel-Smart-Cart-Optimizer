from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOperationError,
    AdapterOutcome,
    ProductSearchResult,
)
from app.retailer_adapters.resilience import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitState,
    ExecutionFailure,
    ExecutionPolicy,
    RetailerExecutionGuard,
)
from tests.unit.retailer_adapters.support import acquisition


def success() -> ProductSearchResult:
    return ProductSearchResult(
        outcome=AdapterOutcome.SUCCESS,
        acquisition=acquisition(AdapterCapability.PRODUCT_DISCOVERY),
    )


def test_backoff_is_exponential_and_bounded() -> None:
    strategy = BackoffStrategy(
        base_seconds=1.0,
        max_seconds=8.0,
        jitter_ratio=0.2,
        random_source=lambda: 0.0,
    )

    assert strategy.delay(1) == 1.0
    assert strategy.delay(2) == 2.0
    assert strategy.delay(3) == 4.0
    assert strategy.delay(10) == 8.0


def test_backoff_applies_bounded_jitter() -> None:
    no_jitter = BackoffStrategy(
        base_seconds=1.0,
        max_seconds=8.0,
        jitter_ratio=0.2,
        random_source=lambda: 0.0,
    )
    full_jitter = BackoffStrategy(
        base_seconds=1.0,
        max_seconds=8.0,
        jitter_ratio=0.2,
        random_source=lambda: 1.0,
    )

    assert full_jitter.delay(1) == pytest.approx(1.2)
    assert full_jitter.delay(10) <= 8.0
    assert no_jitter.delay(1) < full_jitter.delay(1)


def test_policy_defaults_derive_from_existing_scraper_settings() -> None:
    settings = SimpleNamespace(
        scraper_timeout_seconds=3.0,
        scraper_max_retries=4,
        scraper_retry_backoff_seconds=0.5,
    )

    policy = ExecutionPolicy.from_settings(settings)  # type: ignore[arg-type]

    assert policy.timeout_seconds == 3.0
    assert policy.max_attempts == 4
    assert policy.base_backoff_seconds == 0.5
    assert policy.max_backoff_seconds == 4.0


@pytest.mark.asyncio
async def test_timeout_is_retried_for_retry_safe_operations() -> None:
    calls = 0
    sleeps: list[float] = []

    async def slow() -> ProductSearchResult:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return success()

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            timeout_seconds=0.01,
            max_attempts=2,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            jitter_ratio=0.0,
        ),
        sleep=sleep,
    )

    with pytest.raises(ExecutionFailure) as exc_info:
        await guard.run(
            retailer_id="BLINKIT",
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            call=slow,
        )

    assert exc_info.value.outcome is AdapterOutcome.TEMPORARY_FAILURE
    assert exc_info.value.reason_code == "timeout"
    assert calls == 2
    assert sleeps == [0.0]


@pytest.mark.asyncio
async def test_timeout_on_mutation_is_unknown_and_not_retried() -> None:
    calls = 0

    async def slow() -> ProductSearchResult:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return success()

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            timeout_seconds=0.01,
            max_attempts=3,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            jitter_ratio=0.0,
        )
    )

    with pytest.raises(ExecutionFailure) as exc_info:
        await guard.run(
            retailer_id="BLINKIT",
            capability=AdapterCapability.CART_PREPARATION,
            call=slow,
        )

    assert exc_info.value.outcome is AdapterOutcome.UNKNOWN_OUTCOME
    assert exc_info.value.reason_code == "timeout_unknown_outcome"
    assert calls == 1


@pytest.mark.asyncio
async def test_temporary_failure_is_retried_and_attempts_are_annotated() -> None:
    attempts = 0

    async def flaky() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise AdapterOperationError(
                AdapterOutcome.TEMPORARY_FAILURE,
                reason_code="temporary",
            )
        return success()

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=3,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            jitter_ratio=0.0,
        )
    )

    result = await guard.run(
        retailer_id="BLINKIT",
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        call=flaky,
    )

    assert result.outcome is AdapterOutcome.SUCCESS
    assert result.acquisition is not None
    assert result.acquisition.attempt_count == 2
    assert result.acquisition.retried is True
    assert attempts == 2


@pytest.mark.asyncio
async def test_access_denied_is_not_retried() -> None:
    attempts = 0

    async def denied() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        raise AdapterOperationError(
            AdapterOutcome.ACCESS_DENIED,
            reason_code="denied",
        )

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(max_attempts=3, base_backoff_seconds=0.0)
    )

    with pytest.raises(ExecutionFailure) as exc_info:
        await guard.run(
            retailer_id="BLINKIT",
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            call=denied,
        )

    assert exc_info.value.outcome is AdapterOutcome.ACCESS_DENIED
    assert attempts == 1


@pytest.mark.asyncio
async def test_rate_limited_is_retried_for_retry_safe_operations() -> None:
    attempts = 0

    async def limited() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise AdapterOperationError(
                AdapterOutcome.RATE_LIMITED,
                reason_code="rate_limited",
            )
        return success()

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=2,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            jitter_ratio=0.0,
        )
    )

    result = await guard.run(
        retailer_id="BLINKIT",
        capability=AdapterCapability.PRICE_ACQUISITION,
        call=limited,
    )

    assert result.outcome is AdapterOutcome.SUCCESS
    assert attempts == 2


@pytest.mark.asyncio
async def test_unexpected_failure_is_unknown_and_not_retried() -> None:
    attempts = 0

    async def broken() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("boom")

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(max_attempts=3, base_backoff_seconds=0.0)
    )

    with pytest.raises(ExecutionFailure) as exc_info:
        await guard.run(
            retailer_id="BLINKIT",
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            call=broken,
        )

    assert exc_info.value.outcome is AdapterOutcome.UNKNOWN_OUTCOME
    assert exc_info.value.diagnostic == "RuntimeError"
    assert attempts == 1


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_recovers_after_reset() -> None:
    now = 0.0
    attempts = 0

    async def always_fails() -> ProductSearchResult:
        nonlocal attempts
        attempts += 1
        raise AdapterOperationError(
            AdapterOutcome.TEMPORARY_FAILURE,
            reason_code="temporary",
        )

    async def succeeds() -> ProductSearchResult:
        return success()

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=1,
            base_backoff_seconds=0.0,
            circuit_failure_threshold=2,
            circuit_reset_seconds=10.0,
        ),
        clock=lambda: now,
    )

    for _ in range(2):
        with pytest.raises(ExecutionFailure):
            await guard.run(
                retailer_id="BLINKIT",
                capability=AdapterCapability.PRODUCT_DISCOVERY,
                call=always_fails,
            )

    with pytest.raises(ExecutionFailure) as exc_info:
        await guard.run(
            retailer_id="BLINKIT",
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            call=succeeds,
        )
    assert exc_info.value.reason_code == "circuit_open"
    assert attempts == 2

    now = 11.0
    result = await guard.run(
        retailer_id="BLINKIT",
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        call=succeeds,
    )
    assert result.outcome is AdapterOutcome.SUCCESS


@pytest.mark.asyncio
async def test_circuit_breaker_isolates_retailers() -> None:
    now = 0.0

    async def fails() -> ProductSearchResult:
        raise AdapterOperationError(
            AdapterOutcome.TEMPORARY_FAILURE,
            reason_code="temporary",
        )

    async def succeeds() -> ProductSearchResult:
        return success()

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=1,
            base_backoff_seconds=0.0,
            circuit_failure_threshold=1,
            circuit_reset_seconds=10.0,
        ),
        clock=lambda: now,
    )

    with pytest.raises(ExecutionFailure):
        await guard.run(
            retailer_id="BLINKIT",
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            call=fails,
        )

    with pytest.raises(ExecutionFailure, match="circuit_open"):
        await guard.run(
            retailer_id="BLINKIT",
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            call=succeeds,
        )

    result = await guard.run(
        retailer_id="ZEPTO",
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        call=succeeds,
    )
    assert result.outcome is AdapterOutcome.SUCCESS


@pytest.mark.asyncio
async def test_per_retailer_concurrency_is_bounded() -> None:
    active = 0
    max_active = 0

    async def tracked() -> ProductSearchResult:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return success()

    guard = RetailerExecutionGuard(
        policy=ExecutionPolicy(
            max_attempts=1,
            max_concurrency_per_retailer=1,
        )
    )

    await asyncio.gather(
        *[
            guard.run(
                retailer_id="BLINKIT",
                capability=AdapterCapability.PRODUCT_DISCOVERY,
                call=tracked,
            )
            for _ in range(4)
        ]
    )

    assert max_active == 1


@pytest.mark.asyncio
async def test_breaker_half_open_failure_reopens_immediately() -> None:
    now = 0.0

    async def fails() -> ProductSearchResult:
        raise AdapterOperationError(
            AdapterOutcome.TEMPORARY_FAILURE,
            reason_code="temporary",
        )

    breaker = CircuitBreaker(
        failure_threshold=1,
        reset_seconds=5.0,
        clock=lambda: now,
    )

    assert await breaker.allow() is True
    await breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    assert await breaker.allow() is False

    now = 6.0
    assert await breaker.allow() is True
    assert breaker.state is CircuitState.HALF_OPEN

    await breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    assert await breaker.allow() is False
