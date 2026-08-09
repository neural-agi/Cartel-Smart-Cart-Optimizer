# Local Ingestion Worker Contract Amendment

Status: Frozen contract amendment

Applies to:

- `docs/architecture/real_data_ingestion_rfc.md`
- `docs/architecture/scrape_job_lifecycle_rfc.md`
- `docs/architecture/scrape_job_contract_amendment.md`
- `docs/architecture/artifact_storage_contract_amendment.md`
- `docs/architecture/parsed_normalized_observation_contract_amendment.md`
- `docs/architecture/completeness_evidence_contract_amendment.md`

This amendment freezes only the interfaces required for the local ingestion
worker slice. It does not add a queue, distributed execution, API, downstream
trigger, or new retailer architecture.

## 1. Motivation and Current Gap

The existing Blinkit scraper returns raw bytes and performs local diagnostic
writing internally. That is insufficient for a worker to publish a durable
`RawArtifactReference`, preserve acquisition completeness facts, and invoke the
existing parser bridge without filesystem coupling.

This amendment introduces the missing public boundaries:

```text
ScrapeJob / ScrapeAttempt
  -> AcquisitionResult
  -> artifact identity
  -> ArtifactStore.store
  -> RawArtifactReference
  -> BlinkitParserBridge
  -> ParsedRetailObservationBatch
  -> IngestionWorkerResult
```

## 2. AcquisitionResult

`AcquisitionResult` is an immutable value object produced by a platform
acquisition adapter and consumed by the local worker. It contains capture facts,
not parser output.

| Field | Type | Required | Identity | Meaning |
|---|---|---:|---:|---|
| `payload` | `bytes` | yes | no | Exact captured bytes passed to artifact storage |
| `source_reference` | non-empty string | yes | no | Stable source URL/request reference supplied by acquisition |
| `content_type` | non-empty string | yes | no | Captured payload media type |
| `capture_timestamp` | datetime | yes | no | Acquisition audit timestamp |
| `evaluation_scope` | non-empty string | yes | yes | Declared scope evaluated by acquisition |
| `pages_evaluated` | positive integer | yes | yes | Pages or equivalent result segments acquired |
| `pagination_complete` | boolean or `None` | yes | yes | Explicit pagination completion evidence |
| `termination_reason` | non-empty string | yes | yes | Deterministic acquisition termination reason |
| `capture_type` | `CaptureType` | yes | yes | Capture type requested by the job |
| `warnings` | tuple of non-empty strings | yes | no | Acquisition diagnostics in emission order |

The acquisition adapter is the sole producer of these facts. The worker does
not infer them from product count, parser termination, source paths, or
timestamps. `payload` is immutable and is never modified by the worker.

The result may be returned only after acquisition has either captured a valid
payload or raised the applicable failure. A failed acquisition does not return
a successful `AcquisitionResult`.

## 3. Artifact Identity Ownership

Artifact identity is assigned by the acquisition boundary through the worker's
artifact identity builder. `ArtifactStore` only validates and stores the
identity supplied in `RawArtifactReference`.

The canonical artifact identity input is:

```json
{
  "job_id": "...",
  "attempt_id": "...",
  "capture_type": "...",
  "content_digest": "..."
}
```

`artifact_id` is the SHA-256 digest of the canonical UTF-8 JSON representation
of those fields, with sorted keys and stable separators.

Artifact identity is distinct from:

- `job_id`: identity of the requested governed job;
- `attempt_id`: identity of one numbered execution attempt;
- `content_digest`: integrity digest of the captured bytes;
- `storage_reference`: opaque location returned by `ArtifactStore`.

The following never participate in `artifact_id`:

- source paths;
- timestamps;
- worker/process IDs;
- queue state;
- random values;
- storage backend or filesystem layout;
- parser or normalization output.

The same bytes captured by different attempts have different artifact identities
because `attempt_id` is an identity input. Repeating the same valid attempt with
the same governed capture bytes produces the same artifact identity.

## 4. Raw Artifact Publication

The worker performs this exact sequence:

1. Receive an immutable `AcquisitionResult`.
2. Compute `content_digest = SHA-256(payload)`.
3. Compute `artifact_id` using the identity inputs above.
4. Construct the artifact-store publication input using job/attempt identity,
   acquisition metadata, digest, capture type, and source reference.
5. Call `ArtifactStore.store` with the reference data and payload.
6. Receive the opaque `StorageReference`.
7. Construct the published `RawArtifactReference` with the returned opaque
   storage reference identifier.
8. Treat the artifact as published only after `store` returns successfully.

The public worker result may contain only the published reference. Filesystem
paths and temporary files never cross this boundary. Storage conflicts and
corruption are failures; the worker must not continue to parsing.

## 5. Completeness Acquisition Contract

The acquisition adapter supplies `evaluation_scope`, `pages_evaluated`,
`pagination_complete`, and `termination_reason` in `AcquisitionResult`.

For Blinkit search captures:

- `evaluation_scope` is derived from the job's explicit request and capture
  context, not from a source path or query display text alone;
- `pagination_complete=True` is allowed only when Blinkit exposes an explicit
  exhausted/no-next-page condition;
- `pagination_complete=False` means the adapter knows that additional scope
  remains;
- `pagination_complete=None` means completion cannot be established.

The worker does not convert these values. The parser bridge maps them to the
frozen `ObservationCompleteness` rules:

- empty plus explicit completion: `EMPTY`;
- non-empty plus incomplete pagination: `PARTIAL`;
- non-empty plus unknown pagination: `UNKNOWN`;
- non-empty plus explicit completion: `COMPLETE`;
- empty without explicit completion: fail closed and no successful batch.

The current single-page Blinkit scraper must therefore return `None` for
`pagination_complete` unless it has explicit platform evidence. It may not claim
completion merely because one page was captured.

## 6. Worker Execution Contract

The worker exposes one synchronous public operation:

```text
execute(job: ScrapeJob) -> IngestionWorkerResult
```

The worker creates the 1-based attempt for this local execution using the
existing `ScrapeAttempt` identity rule. It does not create a second job or
attempt identity system.

`IngestionWorkerResult` is immutable and contains:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `job_id` | non-empty string | yes | Executed job identity |
| `attempt` | `ScrapeAttempt` | yes | Finalized attempt view |
| `artifact_reference` | `RawArtifactReference` or `None` | no | Published raw artifact, when available |
| `parsed_batch` | `ParsedRetailObservationBatch` or `None` | no | Successful parser result, when available |
| `failed_stage` | non-empty string or `None` | no | `acquisition`, `artifact_storage`, or `parsing` when failed |

Exactly one of `parsed_batch` or terminal failure is present. A successful
result always contains the published artifact reference and parsed batch.
`artifact_reference` may be present on failure when capture or storage completed
before a later stage failed.

The worker propagates unexpected programming errors unchanged; governed stage
failures are represented with existing `JobFailure` inside `ScrapeAttempt`.

## 7. Lifecycle Transition Ownership

The worker owns lifecycle transitions for its execution, using only existing
`JobState` values and `LifecycleTransition` records.

The ordered stage transitions are:

```text
CREATED -> DEQUEUED -> ACQUIRING -> ARTIFACT_CAPTURED
         -> PARSING -> PARSED -> COMPLETED
```

`NORMALIZING`, `NORMALIZED`, registration, and downstream publication states are
not entered by Slice 4.

On failure, the worker emits the applicable existing terminal or retry-scheduled
state according to `FailureCategory` semantics. It does not decide new retry
policy. Attempt timestamps and transition timestamps are assigned by the worker
as audit metadata and never participate in any domain identity.

The worker owns attempt creation, stage transition ordering, final outcome, and
terminal transition emission. It does not mutate an existing immutable job.

## 8. Failure and Partial Execution

| Stage | Successful parsed output | Artifact may remain | Failure representation |
|---|---:|---:|---|
| Acquisition | no | only if acquisition produced a valid partial artifact | existing `JobFailure` with acquisition category |
| Artifact storage | no | storage outcome determines whether a published artifact exists | existing storage failure category |
| Parser bridge | no | yes, published raw artifact is preserved | existing parser/contract failure category |

A failed attempt never emits a successful parsed batch. Published raw evidence is
append-only and is not deleted because a later parser or lifecycle stage fails.
Retries do not silently reuse an artifact from another attempt; replay may
explicitly reuse a preserved artifact through `ReplayReference`.

## 9. Replay

An `IngestionWorkerResult` preserves:

- `job_id` and `attempt_id`;
- the published `RawArtifactReference` and its artifact identity;
- parser version and `ParsedRetailObservationBatch.batch_id`;
- completeness metadata in the parsed batch.

Replay of a historical artifact is governed by `ReplayReference` and parser
version. It does not use the current source path, current scraper behavior,
worker identity, or current runtime timestamps as historical inputs.

## 10. Slice Boundary

Slice 4 owns:

```text
ScrapeJob
 -> local worker
 -> acquisition result
 -> artifact publication
 -> Blinkit parser bridge
 -> worker result and lifecycle records
```

Slice 4 does not own:

- HTTP ingestion APIs;
- queues, Redis, Postgres, or distributed execution;
- schedulers;
- Product Intelligence or Cost Intelligence triggers;
- catalog/search APIs;
- additional retailers;
- normalization beyond the existing parser bridge boundary.

Those concerns remain future slices.

## 11. Compatibility Implications

The existing `BlinkitScraper.search_products() -> bytes` signature is not an
ingestion-compliant acquisition contract. It may remain available for existing
callers, but Slice 4 requires an acquisition adapter boundary that returns
`AcquisitionResult` and does not expose the scraper's internal saved path.

The existing ArtifactStore interface remains unchanged. `RawArtifactReference`
remains the durable evidence contract, and the worker supplies its identity
before calling the store.

## 12. Implementation Checklist

Before Slice 4 implementation, the local worker must:

- accept only a valid `ScrapeJob`;
- use the existing attempt identity rule;
- obtain an immutable acquisition result;
- compute artifact identity from the frozen inputs;
- publish bytes through `ArtifactStore` only;
- preserve acquisition completeness metadata;
- invoke `BlinkitParserBridge` with the published artifact reference;
- return an immutable worker result;
- emit existing lifecycle/failure records without new states;
- never trigger downstream intelligence or expose filesystem paths.

## 13. Open Contract Decisions

One contract decision remains before Slice 4 can begin:

`ArtifactStore.store()` currently accepts `RawArtifactReference`, whose
`storage_reference` field is required and non-empty, while the storage contract
also defines `storage_reference` as the opaque value produced by the artifact
store. The worker therefore has no contract-defined value to place in the
pre-publication input without inventing a sentinel or changing the existing
interface.

This must be resolved by one of the existing contract owners before coding:

- define a frozen pre-publication reference input contract; or
- amend the artifact-store input operation to accept capture metadata without a
  published `RawArtifactReference`.

No Slice 4 implementation should invent this value.
