# Distributed Rate Limiting

Cartel uses Redis only for distributed request-limit state. PostgreSQL remains the source of truth for users, sessions, idempotency, lists, catalog data, and optimization records.

## Algorithm

The API uses a fixed window per category, identity, and path. A Redis Lua script atomically increments a bounded key and sets its TTL only on the first increment. The configured `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` values remain the general API limit; `AUTH_RATE_LIMIT_REQUESTS` uses the same window for login, signup, verification, recovery, and OAuth start/callback paths.

Authentication limits use the client address because authentication has not yet established a user identity. Protected API limits use the authenticated user ID, falling back to the client address for anonymous requests. The Redis key contains a SHA-256 digest rather than the raw identity.

## Failure Policy

Redis connection and operation timeouts are bounded by `REDIS_CONNECT_TIMEOUT_SECONDS` and `REDIS_OPERATION_TIMEOUT_SECONDS`. Authentication and protected API requests fail closed with a safe `503 rate_limit_unavailable` response when Redis cannot enforce the limit. They are never silently allowed through.

Production startup validates Redis. Compose waits for Redis health before starting the API. Rate-limit state is intentionally ephemeral and is not persisted across a complete Redis restart.

## Operations

Configure `REDIS_URL`, `REDIS_MAX_CONNECTIONS`, `REDIS_CONNECT_TIMEOUT_SECONDS`, and `REDIS_OPERATION_TIMEOUT_SECONDS`. Run multiple API instances against the same Redis service; their counters are shared. The implementation is process-independent, but the current rate limiter is still a fixed-window limiter rather than a global fairness or abuse-prevention system.
