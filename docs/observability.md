# Observability

Cartel currently provides lightweight, dependency-free operational telemetry. It does not include Prometheus, Grafana, centralized log aggregation, an OpenTelemetry collector, or alert routing.

## Logging and correlation

Backend logs are JSON with timestamp, level, component, event, message, and request ID. HTTP completion events include method, normalized route, status, and duration. Request IDs are accepted only in the existing bounded `X-Request-ID` format and are returned in the response header. Credentials, cookies, tokens, passwords, email contents, and request bodies are not logged.

## Metrics

`/api/v1/metrics` exposes Prometheus-compatible text and is protected by the normal API authentication boundary. Labels are bounded to normalized routes, methods, status classes, limiter category/outcome, idempotency operation, job type, and email event type. Current metrics include:

- `cartel_http_requests_total`
- `cartel_http_request_duration_ms_count` and `_sum`
- `cartel_rate_limit_requests_total`
- `cartel_idempotency_total`
- `cartel_background_jobs_total`
- `cartel_email_outbox_total`

The registry is process-local. For horizontally scaled deployments, each instance must be scraped separately or metrics must later be moved to an external aggregation system.

## Health and dependencies

`/health` is a cheap liveness response. `/ready` checks required runtime dependencies, including PostgreSQL when configured and the rate-limiter runtime, without exposing connection details. Redis failures retain the existing fail-closed behavior for protected requests.

## Workers and email

Background-job and email-outbox claim, success, retry, failure, and lease-driven recovery events are emitted with bounded job/event type labels. Email addresses, message bodies, tokens, and provider responses are excluded. The database remains the source of truth for queue state.

## Future integrations

Production deployments can consume JSON logs and scrape metrics with their existing systems. Distributed tracing, centralized aggregation, dashboards, alert routing, and durable cross-instance metrics are intentionally future integrations rather than capabilities claimed by this repository today.
