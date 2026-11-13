"""Redis-backed distributed request limiting."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from redis.asyncio import Redis
from app.core.metrics import metrics


class RateLimitBackendUnavailable(RuntimeError):
    """Redis cannot currently enforce the configured limit."""


_INCREMENT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int


class RedisRateLimiter:
    def __init__(
        self,
        *,
        url: str,
        connect_timeout: float,
        operation_timeout: float,
        max_connections: int,
        client: Redis | None = None,
    ) -> None:
        self._redis: Redis = client or Redis.from_url(
            url,
            decode_responses=False,
            socket_connect_timeout=connect_timeout,
            socket_timeout=operation_timeout,
            health_check_interval=30,
            max_connections=max_connections,
        )

    @staticmethod
    def _key(category: str, identity: str, path: str) -> str:
        digest = hashlib.sha256(f"{identity}\0{path}".encode()).hexdigest()
        return f"cartel:ratelimit:v1:{category}:{digest}"

    async def allow(self, *, category: str, identity: str, path: str, limit: int, window_seconds: int) -> RateLimitDecision:
        key = self._key(category, identity, path)
        try:
            current = int(await self._redis.eval(_INCREMENT_SCRIPT, 1, key, window_seconds))
        except Exception as exc:
            metrics.inc("cartel_rate_limit_requests_total", category=category, outcome="redis_error")
            raise RateLimitBackendUnavailable from exc
        remaining = max(limit - current, 0)
        metrics.inc("cartel_rate_limit_requests_total", category=category, outcome="allowed" if current <= limit else "limited")
        return RateLimitDecision(allowed=current <= limit, remaining=remaining)

    async def ping(self) -> None:
        try:
            await self._redis.ping()
        except Exception as exc:
            raise RateLimitBackendUnavailable from exc

    async def close(self) -> None:
        await self._redis.aclose()
