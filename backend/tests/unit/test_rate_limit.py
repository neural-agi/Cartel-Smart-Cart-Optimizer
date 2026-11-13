import pytest

from app.core.rate_limit import RateLimitBackendUnavailable, RedisRateLimiter


class _RedisStub:
    def __init__(self, values=None, *, fail=False):
        self.values = iter(values or [])
        self.fail = fail

    async def eval(self, *_args):
        if self.fail:
            raise TimeoutError("redis timeout")
        return next(self.values)

    async def ping(self):
        if self.fail:
            raise ConnectionError("redis unavailable")

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_redis_limiter_maps_atomic_counter_to_allowance() -> None:
    limiter = RedisRateLimiter(
        url="redis://unused",
        connect_timeout=1,
        operation_timeout=1,
        max_connections=2,
        client=_RedisStub([1, 2, 3]),
    )

    decisions = [
        await limiter.allow(category="auth", identity="client", path="/login", limit=2, window_seconds=60)
        for _ in range(3)
    ]

    assert [decision.allowed for decision in decisions] == [True, True, False]
    assert decisions[-1].remaining == 0


@pytest.mark.asyncio
async def test_redis_failures_are_explicit() -> None:
    limiter = RedisRateLimiter(
        url="redis://unused",
        connect_timeout=1,
        operation_timeout=1,
        max_connections=2,
        client=_RedisStub(fail=True),
    )

    with pytest.raises(RateLimitBackendUnavailable):
        await limiter.allow(category="api", identity="client", path="/x", limit=2, window_seconds=60)
    with pytest.raises(RateLimitBackendUnavailable):
        await limiter.ping()
