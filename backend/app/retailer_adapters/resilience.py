"""In-process resilience for retailer adapter execution.

The framework deliberately uses only process-local primitives: an ``asyncio``
timeout, bounded retries with exponential backoff and jitter, a per-retailer
semaphore, and a per-retailer circuit breaker. No distributed queue, shared
cache, or external control plane is introduced without a demonstrated need.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

from app.core.config import Settings
from app.retailer_adapters.capabilities import RETRY_SAFE_CAPABILITIES
from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOperationError,
    AdapterOperationResult,
    AdapterOutcome,
)

ResultT = TypeVar("ResultT", bound=AdapterOperationResult)

_RETRYABLE_OUTCOMES: frozenset[AdapterOutcome] = frozenset(
    {AdapterOutcome.TEMPORARY_FAILURE, AdapterOutcome.RATE_LIMITED}
)
_BREAKER_FAILURE_OUTCOMES: frozenset[AdapterOutcome] = frozenset(
    {
        AdapterOutcome.TEMPORARY_FAILURE,
        AdapterOutcome.RATE_LIMITED,
        AdapterOutcome.UNKNOWN_OUTCOME,
    }
)


@dataclass(frozen=True)
class ExecutionPolicy:
    """Bounded execution policy for one adapter operation."""

    timeout_seconds: float = 15.0
    max_attempts: int = 3
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 8.0
    jitter_ratio: float = 0.2
    max_concurrency_per_retailer: int = 2
    circuit_failure_threshold: int = 5
    circuit_reset_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.base_backoff_seconds < 0 or self.max_backoff_seconds < 0:
            raise ValueError("backoff seconds must not be negative")
        if self.max_backoff_seconds < self.base_backoff_seconds:
            raise ValueError("max_backoff_seconds must be >= base_backoff_seconds")
        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between zero and one")
        if self.max_concurrency_per_retailer < 1:
            raise ValueError("max_concurrency_per_retailer must be at least one")
        if self.circuit_failure_threshold < 1:
            raise ValueError("circuit_failure_threshold must be at least one")
        if self.circuit_reset_seconds <= 0:
            raise ValueError("circuit_reset_seconds must be positive")

    @classmethod
    def from_settings(cls, settings: Settings) -> ExecutionPolicy:
        """Derive defaults from the existing scraper timeout/retry settings."""

        base = settings.scraper_retry_backoff_seconds
        return cls(
            timeout_seconds=settings.scraper_timeout_seconds,
            max_attempts=max(1, settings.scraper_max_retries),
            base_backoff_seconds=base,
            max_backoff_seconds=max(base, base * 8),
        )


class BackoffStrategy:
    """Exponential backoff with bounded jitter."""

    def __init__(
        self,
        *,
        base_seconds: float,
        max_seconds: float,
        jitter_ratio: float = 0.2,
        random_source: Callable[[], float] | None = None,
    ) -> None:
        self._base = base_seconds
        self._max = max_seconds
        self._jitter_ratio = jitter_ratio
        self._random = random_source or random.random

    def delay(self, failed_attempt: int) -> float:
        if failed_attempt < 1:
            raise ValueError("failed_attempt must be at least one")
        delay = min(self._max, self._base * 2 ** (failed_attempt - 1))
        if self._jitter_ratio:
            delay += delay * self._jitter_ratio * self._random()
        return min(self._max, delay)


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Per-retailer failure isolation with a single half-open probe."""

    def __init__(
        self,
        *,
        failure_threshold: int,
        reset_seconds: float,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least one")
        if reset_seconds <= 0:
            raise ValueError("reset_seconds must be positive")
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._clock = clock or time.monotonic
        self._lock = asyncio.Lock()
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        return self._state

    async def allow(self) -> bool:
        async with self._lock:
            if self._state is CircuitState.CLOSED:
                return True
            if self._state is CircuitState.HALF_OPEN:
                return True
            assert self._opened_at is not None
            if self._clock() - self._opened_at >= self._reset_seconds:
                self._state = CircuitState.HALF_OPEN
                return True
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = None

    async def record_failure(self) -> None:
        async with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = self._clock()
                return
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = self._clock()


class ExecutionFailure(Exception):
    """Typed guard failure converted into a result by the executor."""

    def __init__(
        self,
        outcome: AdapterOutcome,
        *,
        reason_code: str,
        diagnostic: str | None = None,
        retryable: bool = False,
    ) -> None:
        self.outcome = outcome
        self.reason_code = reason_code
        self.diagnostic = diagnostic
        self.retryable = retryable
        super().__init__(f"{outcome.value}: {reason_code}")


class RetailerExecutionGuard:
    """Apply timeout, retry safety, concurrency, and circuit isolation."""

    def __init__(
        self,
        *,
        policy: ExecutionPolicy | None = None,
        clock: Callable[[], float] | None = None,
        random_source: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._policy = policy or ExecutionPolicy()
        self._clock = clock or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._backoff = BackoffStrategy(
            base_seconds=self._policy.base_backoff_seconds,
            max_seconds=self._policy.max_backoff_seconds,
            jitter_ratio=self._policy.jitter_ratio,
            random_source=random_source,
        )
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._breakers: dict[str, CircuitBreaker] = {}

    async def run(
        self,
        *,
        retailer_id: str,
        capability: AdapterCapability,
        call: Callable[[], Awaitable[ResultT]],
        policy: ExecutionPolicy | None = None,
    ) -> ResultT:
        effective = policy or self._policy
        semaphore = self._semaphore_for(retailer_id, effective)
        breaker = self._breaker_for(retailer_id, effective)
        retry_safe = capability in RETRY_SAFE_CAPABILITIES

        async with semaphore:
            attempt = 0
            while True:
                attempt += 1
                if not await breaker.allow():
                    raise ExecutionFailure(
                        AdapterOutcome.TEMPORARY_FAILURE,
                        reason_code="circuit_open",
                        retryable=False,
                    )
                try:
                    result = await asyncio.wait_for(
                        call(),
                        timeout=effective.timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    if retry_safe:
                        failure = ExecutionFailure(
                            AdapterOutcome.TEMPORARY_FAILURE,
                            reason_code="timeout",
                            retryable=True,
                        )
                    else:
                        failure = ExecutionFailure(
                            AdapterOutcome.UNKNOWN_OUTCOME,
                            reason_code="timeout_unknown_outcome",
                            retryable=False,
                        )
                except AdapterOperationError as exc:
                    failure = ExecutionFailure(
                        exc.outcome,
                        reason_code=exc.reason_code,
                        diagnostic=exc.diagnostic,
                        retryable=(
                            retry_safe and exc.outcome in _RETRYABLE_OUTCOMES
                        ),
                    )
                except ExecutionFailure as exc:
                    failure = exc
                except Exception as exc:  # noqa: BLE001 - adapter boundary
                    failure = ExecutionFailure(
                        AdapterOutcome.UNKNOWN_OUTCOME,
                        reason_code="unexpected_adapter_failure",
                        diagnostic=type(exc).__name__,
                        retryable=False,
                    )
                else:
                    outcome = result.outcome
                    if outcome in _RETRYABLE_OUTCOMES:
                        await breaker.record_failure()
                        if retry_safe and attempt < effective.max_attempts:
                            await self._sleep(self._backoff.delay(attempt))
                            continue
                    elif outcome in _BREAKER_FAILURE_OUTCOMES:
                        await breaker.record_failure()
                    else:
                        await breaker.record_success()
                    return self._annotate(result, attempt)

                if failure.outcome in _BREAKER_FAILURE_OUTCOMES:
                    await breaker.record_failure()
                else:
                    await breaker.record_success()
                if failure.retryable and attempt < effective.max_attempts:
                    await self._sleep(self._backoff.delay(attempt))
                    continue
                raise failure

    def _semaphore_for(
        self,
        retailer_id: str,
        policy: ExecutionPolicy,
    ) -> asyncio.Semaphore:
        semaphore = self._semaphores.get(retailer_id)
        if semaphore is None:
            semaphore = asyncio.Semaphore(policy.max_concurrency_per_retailer)
            self._semaphores[retailer_id] = semaphore
        return semaphore

    def _breaker_for(
        self,
        retailer_id: str,
        policy: ExecutionPolicy,
    ) -> CircuitBreaker:
        breaker = self._breakers.get(retailer_id)
        if breaker is None:
            breaker = CircuitBreaker(
                failure_threshold=policy.circuit_failure_threshold,
                reset_seconds=policy.circuit_reset_seconds,
                clock=self._clock,
            )
            self._breakers[retailer_id] = breaker
        return breaker

    @staticmethod
    def _annotate(result: ResultT, attempt: int) -> ResultT:
        if result.acquisition is None:
            return result
        acquisition = result.acquisition.model_copy(
            update={"attempt_count": attempt, "retried": attempt > 1}
        )
        return result.model_copy(update={"acquisition": acquisition})


__all__ = [
    "BackoffStrategy",
    "CircuitBreaker",
    "CircuitState",
    "ExecutionFailure",
    "ExecutionPolicy",
    "RetailerExecutionGuard",
]
