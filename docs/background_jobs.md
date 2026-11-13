# Background jobs

Cartel keeps HTTP request work synchronous unless it is network-heavy or otherwise unsuitable for holding an HTTP connection. The first asynchronous boundary is the additive `POST /api/v1/scrape/async` endpoint. It dispatches the existing governed scrape runtime; it does not change provider behavior or the filesystem ingestion lifecycle.

## Runtime

API instances write `background_jobs` rows in PostgreSQL. A dedicated worker claims rows with a transaction using `FOR UPDATE SKIP LOCKED`, commits the claim, executes outside that transaction, and persists the result in a second transaction. Redis remains rate-limit state only.

Jobs use `queued`, `running`, `succeeded`, `failed`, and `cancelled` states. A lease expiry returns a running job to the queue. Retryable failures use bounded exponential backoff with jitter and stop at `JOB_MAX_ATTEMPTS`; unsupported job types and other permanent failures are terminal. Delivery is at-least-once, so handlers must remain idempotent. The existing filesystem scrape lifecycle and application uniqueness protections provide the downstream deduplication boundary.

## Configuration

`WORKER_CONCURRENCY`, `JOB_POLL_INTERVAL_SECONDS`, `JOB_MAX_ATTEMPTS`, `JOB_RETRY_BASE_SECONDS`, `JOB_RETRY_MAX_SECONDS`, and `JOB_LEASE_SECONDS` control the worker. The Compose `worker` service is internal and shares PostgreSQL and the durable application data volume; it has no published port.

Authentication, product search, list mutations, and current local optimization remain synchronous because they are transactional or bounded in the current implementation.

## Email outbox

Verification and password-recovery requests create an `email_outbox_events` row in the same PostgreSQL transaction as the challenge. The worker claims pending events with `FOR UPDATE SKIP LOCKED`, leases them, performs `EmailDelivery` I/O after commit, and records `sent`, retryable `pending`, or terminal `failed` state. Local `FileEmailDelivery` and production SMTP remain the provider implementations.

Delivery is at-least-once. If SMTP accepts a message and the worker crashes before recording `sent`, the event can be retried and a duplicate email is possible. The outbox deduplicates logical event creation using the challenge identity, but it cannot provide exactly-once external email delivery.
