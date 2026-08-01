# RFC: Real Data Ingestion Architecture for Cartel

Status: Architecture proposal

This RFC defines the real-data ingestion subsystem that extends Cartel's existing deterministic Product Intelligence, Cost Intelligence, and Cart Optimization pipelines. It does not replace those pipelines or change their domain contracts.

## 1. Overall Architecture

The complete flow is:

```text
Retailer
  -> platform scraper
  -> raw scrape artifact
  -> platform parser
  -> parsed retail observation
  -> ingestion normalization
  -> canonical observation
  -> evidence and observation registry
  -> Product Intelligence
  -> Cost Intelligence
  -> Cart Optimization
  -> API response
```

### Retailer

Retailers expose platform-specific pages, APIs, sessions, checkout flows, delivery-slot data, and anti-bot behavior. Retailer behavior is an external dependency and is never treated as canonical domain truth.

### Platform scraper

The scraper acquires a page or response using a platform adapter. It owns request execution, browser interaction, session scope, and capture metadata. It does not create canonical products, evaluate offers, or make matching decisions.

### Raw scrape artifact

The exact acquired response, together with request and capture metadata, is preserved before parsing. This is the replay boundary for parser and normalization work.

### Platform parser

The parser interprets a raw artifact according to one platform's layout. It emits structured, platform-native parsed observations and parser diagnostics. It does not infer canonical product identity or effective cost.

### Ingestion normalization

Normalization converts a parsed platform observation into a platform-independent observation contract. It owns field-shape conversion, unit representation, explicit missingness, and source references. It does not perform Product Matching.

### Canonical observation and registries

The canonical observation is registered with preserved evidence and provenance. The existing Evidence Registry remains the provenance foundation. The observation registry is the boundary at which immutable observations enter downstream intelligence.

### Product Intelligence

The existing pipeline performs candidate generation, Product Matching, Variant Matching, review, and assertion updates. It remains the sole owner of canonical product identity and mapping decisions.

### Cost Intelligence and Cart Optimization

Once a canonical checkout observation exists, the existing Cost Context, Offer, Fee, Membership, Effective Cost, and Cart Optimization stages may consume it. Scraper and worker code must not duplicate those rules.

### API response

User-facing APIs expose job state, results, provenance, and deterministic downstream outputs. A synchronous API request must not hide a long-running scrape behind a normal request timeout.

## 2. Scraper Architecture

The existing `backend/app/scrapers/` package is the acquisition boundary. It should evolve around explicit platform adapters while retaining the current Blinkit implementation.

### Responsibilities

The scraper layer owns:

- page and response fetching;
- browser and HTTP lifecycle;
- session and location context;
- platform-specific request construction;
- anti-bot and access-block detection;
- raw artifact capture;
- platform adapter invocation.

It does not own:

- canonical observation construction;
- Product Matching or Variant Matching;
- offer, fee, membership, or effective-cost evaluation;
- durable job state;
- retry scheduling outside the declared job policy;
- business recommendations.

### Adapter interfaces

The eventual contracts should distinguish capture types rather than force every retailer into one method:

- search results;
- product detail;
- cart;
- checkout;
- delivery slots.

Each adapter should expose a deterministic operation for a declared platform and capture type. The operation receives an immutable capture context and returns a raw artifact or a typed failure artifact.

### Parser interfaces

Parsers consume raw artifacts only and emit parsed platform-native observations. A parser must declare its platform and parser version. Parser output must retain source selectors or raw-field references sufficient to trace every parsed field back to the artifact.

### Session management

Session management owns cookies, storage state, geolocation, authentication state, user-agent selection, and browser context lifetime. A session is scoped to an explicit job/capture context. Session state must not leak between unrelated jobs.

The current Blinkit location-aware Playwright session is the reference implementation for location and storage-state behavior. A shared browser lifecycle helper may be introduced only after multiple adapters demonstrate stable common behavior.

### Browser lifecycle and isolation

Playwright browser processes may be reused by a worker, but browser contexts must be isolated per job or explicitly declared session scope. Pages are created and closed within the job boundary. Failure artifacts are captured before context teardown where possible.

### Anti-bot handling

The system detects and records CAPTCHA, access blocks, suspicious response patterns, and challenge pages. It does not attempt unapproved bypass behavior. Such results are explicit blocked failures, not empty product results.

### Retries and rate limits

The scraper reports failure classification to the worker. It does not silently retry arbitrary failures. Rate-limit ownership belongs to the execution boundary, with platform-specific limits represented in adapter configuration and job policy. Initial implementation should use explicit bounded policies and deterministic backoff without random jitter.

## 3. Worker Architecture

Workers execute jobs and coordinate the scraper, parser, normalizer, registry, and optional downstream trigger. They do not own domain decisions.

### Worker responsibilities

- consume a job;
- validate the job contract;
- invoke the platform adapter;
- persist or register raw artifacts;
- invoke the parser and normalizer;
- register immutable observations and evidence;
- update job state;
- classify failures;
- schedule bounded retries;
- route terminal failures to a dead-letter state;
- optionally publish an explicit downstream pipeline request.

The worker does not perform matching, review decisions, assertion updates, cost evaluation, or cart optimization.

### Queue topology

The logical queues are:

- `scrape.requested`;
- `scrape.retry`;
- `scrape.dead_letter`;
- `pipeline.product_intelligence`;
- `pipeline.cost_intelligence`;
- `pipeline.cart_optimization`.

The first local implementation may use an in-memory or filesystem-backed execution adapter, but the contracts must not depend on that choice. Redis is already configured in the repository and is the natural later queue adapter; it is not currently a complete worker implementation.

### Job states

The job lifecycle should use explicit states:

- created;
- queued;
- running;
- succeeded;
- failed;
- retry_scheduled;
- dead_lettered;
- cancel_requested;
- cancelled;
- expired.

Transitions are validated by the worker/job-state owner. Invalid transitions fail closed.

### Retry policy

Retry classification must be explicit. Network errors and bounded timeouts may be retryable. CAPTCHA, access blocks, parser layout changes, and invalid contracts must not be retried indefinitely. The initial policy should define a fixed maximum attempt count and deterministic exponential backoff without jitter.

### Idempotency

Job identity must be derived from immutable request-defining inputs, such as:

- platform;
- capture type;
- canonical request parameters;
- location and session context;
- parser/normalization policy versions;
- requested downstream mode.

Submission time, worker identity, random UUIDs, and runtime insertion order must not participate in idempotency identity. Duplicate jobs should resolve to the same job identity or deterministically return an already-known result.

### Cancellation and timeouts

Cancellation is a state transition, not an exception swallowed by a worker. Workers must check cancellation at bounded boundaries and record whether cancellation occurred before or after artifact capture. Timeouts are classified by layer: request, browser, parser, normalization, and downstream trigger.

## 4. Canonical Contracts

The following contracts are required before executable multi-platform ingestion is implemented. They should be immutable, explicitly versioned where interpretation can change, and serializable deterministically.

### RetailPlatform

Owner: ingestion platform boundary.

Producer: platform registration.

Consumers: scraper adapters, parsers, jobs, evidence metadata.

Identity: explicit platform value.

Lifecycle: stable vocabulary; adding a platform is additive.

### CaptureType

Owner: ingestion capture boundary.

Producer: job request.

Consumers: adapter, parser, normalization, replay.

Identity: capture type plus its canonical request parameters.

### CaptureContext

Owner: ingestion context boundary.

Producer: API or job creator.

Consumers: scraper and provenance records.

Contents include location, country, currency expectations, session scope, and other explicit capture inputs. Hidden account or session lookups are forbidden.

### ScrapeJob

Owner: worker/job lifecycle.

Producer: API or scheduler.

Consumers: queue, worker, scraper, status API.

Identity: deterministic idempotency key derived from canonical request inputs.

Immutability: request fields immutable after creation; lifecycle state is represented by new state records.

### RawScrapeArtifact

Owner: acquisition/evidence boundary.

Producer: scraper.

Consumers: parser, replay tooling, audit.

Identity: source/platform plus content and capture metadata according to the frozen artifact contract.

Contents include URL/request reference, status, headers where safe, body or object reference, content type, capture context, scraper version, and capture timestamp as provenance metadata.

### RawScrapeFailureArtifact

Owner: acquisition/evidence boundary.

Producer: scraper or worker.

Consumers: retry policy, dead-letter handling, diagnostics, replay review.

Identity: job attempt and failure artifact identity.

Contents include failure category, safe diagnostic details, source reference, and whether the failure is retryable.

### ParsedRetailObservationBatch

Owner: parser boundary.

Producer: platform parser.

Consumers: normalizer, parser tests, replay.

Identity: raw artifact identity plus parser version.

Contents are platform-native parsed records and parser warnings. Raw source references are mandatory.

### ParsedRetailObservation

Owner: platform parser.

Producer: parser.

Consumers: normalizer only, until normalized.

This is not canonical product intelligence. It may contain raw title, raw quantity, raw category, platform IDs, raw price text, offer text, availability signal, and field-level source references.

### NormalizedObservation

Owner: ingestion normalization boundary.

Producer: normalizer.

Consumers: observation registry and Product Intelligence ingestion.

Identity: canonical observation identity based on immutable observation-defining inputs.

It represents normalized platform observations without making canonical Product or ProductVariant assertions.

### ScrapeEvidence

Owner: evidence registry.

Producer: artifact/parser/normalizer stages.

Consumers: Product Intelligence, replay, review, audit.

Identity: the existing evidence identity rules, preserving source type and source identifier semantics.

Evidence is immutable and append-only or content-addressed according to the existing registry contract.

### ScrapeResult

Owner: worker execution boundary.

Producer: worker.

Consumers: job status, API, downstream trigger.

Contains raw artifact references, parsed/normalized result references, evidence references, completeness state, and failure state.

### WorkerResult

Owner: worker lifecycle.

Producer: worker.

Consumers: queue/status/audit.

Contains job identity, final state, attempt information, result references, and terminal failure information. It does not duplicate domain results.

### PlatformSnapshot

Owner: observation registry/snapshot boundary.

Producer: successful normalized observation registration.

Consumers: Product Intelligence and API history.

It describes the immutable set of observations captured for a declared platform, location, and capture context. Partial snapshots must be explicit and never be mistaken for complete catalog coverage.

## 5. Platform Abstraction

Use explicit adapter classes with a registry, matching the repository's existing typed, deterministic style. Do not begin with dynamic third-party plugins or configuration-driven executable code.

The vocabulary should include at least:

- Blinkit;
- Zepto;
- Instamart;
- BigBasket;
- Flipkart Minutes.

Each platform package owns its adapter, session integration, parser, fixtures, and adapter tests. The common ingestion contracts remain platform-independent. Adding a retailer should require a new platform module and registration plus tests, not edits to Product Intelligence or Cost Intelligence models.

## 6. Persistence

### Raw HTML and response bodies

Persist raw bodies outside relational domain tables, keyed by immutable artifact identity. The existing filesystem persistence is a valid local first step. Object storage can replace the filesystem later without changing artifact contracts.

### Parsed JSON

Persist parser output for replay and parser-regression analysis. It must reference the raw artifact and parser version.

### Normalized observations

Register normalized observations through the observation registry. They should preserve raw and evidence references and be independently replayable.

### Evidence

Use the existing Evidence Registry as the provenance authority. Evidence references should not be re-created independently by each downstream package.

### Screenshots and failure artifacts

Persist screenshots, challenge pages, HTML diagnostics, and parser failure reports when safe and useful. They should be linked to the job attempt and raw artifact context.

### Logs and metrics

Operational logs and metrics are not domain evidence. They may reference job and artifact identities but must not be treated as product facts.

### Retention

Retention must be explicit by artifact type. Raw artifacts and evidence require a longer audit/replay period than transient worker logs. Deletion or redaction must produce an auditable lifecycle event and must never silently change a historical domain decision.

## 7. Observability

### Structured logs

Log job ID, idempotency key, platform, capture type, location scope, attempt, worker, stage, outcome, and artifact references. Never log passwords, tokens, cookies, credentials, or full payment data.

### Tracing

Trace boundaries should connect API request, job, scrape attempt, parser, normalizer, registry registration, Product Intelligence, Cost Intelligence, and Cart Optimization. Trace IDs are operational metadata and must not participate in domain identity.

### Metrics

Minimum metrics include:

- jobs by state and platform;
- retry and dead-letter counts;
- scrape duration and timeout counts;
- block/CAPTCHA/403 rates;
- parser and normalization failures;
- observation registration counts;
- queue depth and age;
- worker concurrency;
- downstream pipeline success/failure.

### Audit and replay

Replay must be possible from preserved raw artifacts through parser and normalization versions. Downstream deterministic pipelines must receive the same immutable observation inputs and policy versions to reproduce results.

## 8. Failure Model

Failure behavior must be explicit and fail closed.

| Failure | Default classification | Required behavior |
|---|---|---|
| Network error | Retryable | Retry within fixed policy; preserve every attempt artifact where possible. |
| Request timeout | Retryable, bounded | Retry only within the layer's attempt limit; then terminal failure. |
| Browser timeout | Retryable, bounded | Recreate isolated page/context as policy permits; preserve diagnostics. |
| CAPTCHA or anti-bot challenge | Blocked | Do not treat as empty data; avoid indefinite retry and surface explicit blocked state. |
| HTTP 403 | Blocked | Record access failure; no silent fallback to empty result. |
| HTTP 404 | Context-dependent terminal failure | Product detail may be unavailable; search scope may be a malformed request. Preserve the classification. |
| Layout change | Parser failure | Fail closed; retain raw artifact for parser update and replay. |
| Missing required fields | Invalid/partial parse | Emit explicit field-level missingness; do not fabricate canonical values. |
| Malformed HTML/JSON | Parser failure | Preserve raw input and diagnostics; no downstream registration unless the contract permits a partial observation. |
| Empty results | Valid only with explicit completeness evidence | Never equate empty with successful complete coverage by default. |
| Duplicate job | Idempotent duplicate | Reuse deterministic job identity/result or return the existing state. |
| Worker crash | Recoverable execution failure | Queue visibility/lease expiry must permit recovery without duplicate domain effects. |
| Partial scrape | Partial result | Register only if completeness and scope are explicit; downstream coverage must remain partial or unknown. |
| Cancellation | Terminal cancelled state | Preserve artifacts already captured and stop at a defined boundary. |
| Invalid contract | Non-retryable | Fail immediately and route to diagnostics/dead-letter as appropriate. |

The exact retry count, backoff schedule, timeout values, failure enum, and partial-snapshot rules must be frozen in ingestion contracts before implementation.

## 9. API Design

The first public ingestion API should be asynchronous:

- `POST /api/v1/ingestion/scrape-jobs` creates or returns an idempotent job;
- `GET /api/v1/ingestion/scrape-jobs/{job_id}` returns lifecycle state and safe diagnostics;
- `GET /api/v1/ingestion/scrape-jobs/{job_id}/result` returns registered result references when complete;
- `POST /api/v1/ingestion/scrape-jobs/{job_id}/cancel` requests cancellation.

Later endpoints may expose latest snapshots, history, and explicit replay. A synchronous scrape-and-optimize endpoint should not be introduced as the primary contract because scraping and browser work are long-running and failure-prone.

The API must not expose mutable internal worker objects or raw secrets. It should return immutable status/result views with evidence and provenance references.

## 10. Scalability

### One worker

Use local filesystem artifacts, bounded concurrency, and one isolated browser context per job. In-memory queue execution may support development only.

### Ten workers

Use Redis or an equivalent queue adapter for leases and delivery, and Postgres for job/index state. Keep raw bodies in filesystem/object storage.

### One hundred workers

Partition queues by platform/capture type, enforce distributed platform rate limits, use object storage for artifacts, and separate parser/normalizer capacity from browser capacity.

### Multiple countries and currencies

Make country, currency, locale, location, and session scope explicit in CaptureContext and observation identity. Cost evaluation must fail closed on incompatible currency inputs rather than silently converting.

### Millions of products

Use immutable artifact references, incremental snapshots, bounded result batches, indexed observation identity, and platform-specific pagination. Product Intelligence remains downstream and receives bounded observations rather than raw crawler internals.

## 11. Implementation Roadmap

Each slice should be independently mergeable and leave existing deterministic tests passing.

### Slice 1: Ingestion contracts

Approximate size: 6-10 files; medium complexity.

Create `backend/app/ingestion/` contracts for platform, capture context, jobs, raw artifacts, parsed batches, normalized observations, failures, and result references. Freeze identity, state, and serialization rules first.

### Slice 2: Platform adapter registry

Approximate size: 4-8 files; small to medium complexity.

Define explicit adapter registration and platform capability declarations without changing existing Blinkit behavior.

### Slice 3: Raw artifact store boundary

Approximate size: 5-8 files; medium complexity.

Wrap existing filesystem persistence behind an explicit artifact contract and make artifact replay references stable.

### Slice 4: Blinkit parser bridge

Approximate size: 6-12 files; medium complexity.

Adapt existing `RawExtractionResult` and Blinkit parser output into the platform-independent parsed/normalized contracts. Preserve raw evidence and parser version.

### Slice 5: Local ingestion worker

Approximate size: 8-15 files; large complexity.

Implement one-process execution with explicit job states, bounded retries, idempotency, and dead-letter behavior. Do not yet require distributed infrastructure.

### Slice 6: Ingestion API

Approximate size: 5-10 files; medium complexity.

Expose job creation/status/result/cancellation after job contracts are stable.

### Slice 7: Product Intelligence trigger

Approximate size: 5-10 files; medium complexity.

Trigger the existing Product Intelligence pipeline from normalized observations without embedding matching or assertion logic in workers.

### Slice 8: Checkout capture and Cost Intelligence trigger

Approximate size: 6-12 files; medium to large complexity.

Add explicit checkout capture contracts and connect complete checkout observations to the existing Cost Intelligence pipeline.

### Slice 9: Distributed queue and indexed state

Approximate size: 10-20 files; large complexity.

Add Redis queue delivery and Postgres job/snapshot indexes only after local worker semantics are tested.

### Slice 10: Additional retailers

Approximate size: platform-specific; medium to large per retailer.

Add Zepto, Instamart, BigBasket, and Flipkart Minutes adapters independently with fixtures and parser regression tests.

## 12. Required Contract Freeze Before Coding

The following are implementation blockers because different engineers could otherwise produce different behavior:

- exact `RetailPlatform` and `CaptureType` vocabularies;
- CaptureContext identity and session scope;
- ScrapeJob identity and idempotency key;
- valid job-state transitions;
- retryable versus terminal failure categories;
- exact retry count and deterministic backoff;
- timeout ownership by layer;
- raw artifact identity and storage layout;
- parser version and parsed-batch identity;
- normalized observation handoff to the existing registry;
- partial snapshot completeness semantics;
- evidence identity and artifact retention rules;
- worker lease/recovery behavior;
- cancellation boundary;
- API status/result response contracts;
- replay mode and replay equality;
- rate-limit ownership and session isolation.

## 13. Ownership Boundaries

```text
Scraper Adapter
  acquisition, browser/session, raw artifact

Parser
  platform-specific interpretation of raw artifact

Normalizer
  conversion into platform-independent observation shape

Worker
  job lifecycle and stage orchestration

Evidence Registry / Observation Registry
  durable provenance and immutable observation registration

Product Intelligence
  product identity, variants, review, assertions

Cost Intelligence
  checkout context, offers, fees, membership, effective cost

Cart Optimization
  alternatives, constraints, ranking, recommendation
```

No downstream component should reach backward into a scraper implementation to recover missing facts. Missing data must be represented in the upstream contract and handled according to the downstream stage's existing fail-closed rules.

## 14. Architecture Review

### Risks

- Retailer anti-bot behavior can make acquisition unreliable even when domain contracts are correct.
- Browser execution is expensive and requires explicit concurrency and resource limits.
- Parser versions can change interpretation of historical artifacts; parser version must remain part of replay inputs.
- Partial snapshots can be incorrectly treated as complete candidate coverage without explicit completeness contracts.
- Redis/Postgres are configured in the repository but are not yet equivalent to a finished queue or job repository.

### Tradeoffs

- A typed ingestion contract adds up-front work but prevents platform-specific fields from leaking into canonical intelligence.
- Filesystem artifacts are simple and replayable locally but require an object-storage migration for large-scale retention.
- Explicit adapters require registration code but keep platform behavior testable and deterministic.
- Fixed retry policies are predictable but may underperform until platform-specific operational data is available.

### Future bottlenecks

- Browser concurrency and platform rate limits;
- parser maintenance as retailer layouts evolve;
- artifact storage and retention volume;
- distributed idempotency and worker lease correctness;
- completeness determination for search and catalog snapshots.

### Intentionally postponed

- cloud-specific queue implementations;
- dynamic plugin loading;
- ML-based extraction or matching;
- automatic anti-bot bypass;
- broad catalog crawling;
- cost and optimization policy changes;
- frontend ingestion dashboards;
- deletion/retention automation beyond explicit artifact contracts.

## 15. Recommendation

The first implementation slice should be the ingestion contract package, preceded by freezing the contracts listed above in a dedicated architecture document. Once those contracts are stable, the Blinkit adapter bridge is the shortest path to a real end-to-end ingestion flow while preserving the existing Product Intelligence boundary.
