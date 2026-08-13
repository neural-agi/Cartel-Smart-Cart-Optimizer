# Scrape Job Lifecycle Contract

## 1. Scope

This contract freezes the minimum executable lifecycle and attempt semantics required to persist `ScrapeJob` lifecycle state and finalized `ScrapeAttempt` state without changing the existing ingestion, normalization, or Product Intelligence contracts.

It covers:

- lifecycle transition ownership;
- state vocabulary and transition graph;
- transition ordering and identity;
- current-state derivation;
- attempt numbering and retry policy;
- restart and recovery semantics;
- relationship between lifecycle history and finalized attempts.

It does not define storage technology, queue technology, or any new product behavior.

## 2. Existing Guarantees

The repository already guarantees the following:

- `ScrapeJob` is a deterministic identity over immutable request-defining fields.
- `ScrapeAttempt` identity is deterministic within a job: `attempt_id = job_id + ":" + attempt_number`.
- `ScrapeAttempt` contains final outcome, timestamps, failure metadata, and artifact references.
- `LifecycleTransition` exists as a frozen contract type.
- `JobState` exists as a frozen contract type.
- `FailureCategory` exists as a frozen contract type.
- `IngestionWorkerResult` carries the finalized attempt outcome plus parsed batch or failure stage.
- `LocalIngestionWorker` currently executes a single attempt and returns a finalized `ScrapeAttempt`.
- `ProductIntelligenceRuntime` consumes the ingestion result but does not own lifecycle state.

## 3. Ownership

Decision: lifecycle transition creation is owned by the job execution boundary that advances the ingestion job through its stages.

Proposed MVP: `LocalIngestionWorker` or a thin lifecycle coordinator around it emits lifecycle transitions for the ingestion phases it executes.

Why it matters: a single authoritative boundary prevents `ProductIntelligenceRuntime` and the worker from creating competing lifecycle histories.

Repository support: the RFC assigns stage ownership to scheduler, queue, worker, registry, and downstream consumers; the current executable worker already owns ingestion stages. The repository does not yet provide a durable transition store.

Status: FROZEN at the contract level, OPEN at the persistence implementation level.

## 4. State Vocabulary

Decision: the canonical `JobState` vocabulary is the one already defined in the RFC and enum.

Proposed MVP states:

- `CREATED`
- `QUEUED`
- `DEQUEUED`
- `ACQUIRING`
- `ARTIFACT_CAPTURED`
- `PARSING`
- `PARSED`
- `NORMALIZING`
- `NORMALIZED`
- `REGISTERING_OBSERVATION`
- `REGISTERED`
- `PUBLISHING_PIPELINE_EVENT`
- `RETRY_SCHEDULED`
- `CANCEL_REQUESTED`
- `CANCELLED`
- `EXPIRED`
- `DEAD_LETTERED`
- `FAILED`
- `BLOCKED`
- `INVALID`
- `COMPLETED`

Why it matters: durability must persist the canonical vocabulary exactly, or state replay becomes ambiguous.

Repository support: `backend/app/data_ingestion/enums.py` already defines the vocabulary, and the RFC repeats it.

Status: FROZEN.

## 5. Transition Graph

Decision: valid transitions follow the RFC state machine.

Proposed MVP:

- `CREATED -> QUEUED | INVALID | CANCEL_REQUESTED | EXPIRED`
- `QUEUED -> DEQUEUED | CANCEL_REQUESTED | EXPIRED`
- `DEQUEUED -> ACQUIRING | RETRY_SCHEDULED | CANCEL_REQUESTED | FAILED | INVALID | EXPIRED`
- `ACQUIRING -> ARTIFACT_CAPTURED | RETRY_SCHEDULED | BLOCKED | FAILED | CANCEL_REQUESTED | DEAD_LETTERED`
- `ARTIFACT_CAPTURED -> PARSING | CANCEL_REQUESTED | FAILED | DEAD_LETTERED`
- `PARSING -> PARSED | RETRY_SCHEDULED | FAILED | DEAD_LETTERED | CANCEL_REQUESTED`
- `PARSED -> NORMALIZING | CANCEL_REQUESTED | FAILED | DEAD_LETTERED`
- `NORMALIZING -> NORMALIZED | RETRY_SCHEDULED | FAILED | DEAD_LETTERED | CANCEL_REQUESTED`
- `NORMALIZED -> REGISTERING_OBSERVATION | CANCEL_REQUESTED | FAILED | DEAD_LETTERED`
- `REGISTERING_OBSERVATION -> REGISTERED | RETRY_SCHEDULED | FAILED | DEAD_LETTERED | CANCEL_REQUESTED`
- `REGISTERED -> PUBLISHING_PIPELINE_EVENT | COMPLETED | CANCEL_REQUESTED`
- `PUBLISHING_PIPELINE_EVENT -> COMPLETED | RETRY_SCHEDULED | FAILED | DEAD_LETTERED`
- `RETRY_SCHEDULED -> QUEUED | DEAD_LETTERED | CANCEL_REQUESTED | EXPIRED`
- `CANCEL_REQUESTED -> CANCELLED | current in-flight stage acknowledgement`
- `COMPLETED`, `CANCELLED`, `EXPIRED`, `DEAD_LETTERED`, `FAILED`, `BLOCKED`, `INVALID` have no outbound transitions

Why it matters: persistence must reject invalid edges and preserve deterministic replay.

Repository support: the RFC enumerates the transition table and states that invalid transitions fail closed.

Status: FROZEN.

## 6. Initial And Terminal States

Decision: `CREATED` is the initial job state; terminal states are `COMPLETED`, `CANCELLED`, `EXPIRED`, `DEAD_LETTERED`, `FAILED`, `BLOCKED`, and `INVALID`.

Proposed MVP: persisted lifecycle history begins at `CREATED` and ends only in a terminal state or `RETRY_SCHEDULED`.

Why it matters: durable state reconstruction needs a clear start and end boundary.

Repository support: the RFC states `CREATED` is the starting state, and terminal states are immutable.

Status: FROZEN.

## 7. Transition Ownership Boundary

Decision: `ScrapeJob -> LifecycleTransition -> current JobState` is the authoritative lifecycle model.

Proposed MVP: only the job execution boundary appends transitions; `ProductIntelligenceRuntime` reads the outcome but does not author lifecycle transitions.

Why it matters: one authoritative transition boundary avoids conflicting histories.

Repository support: the worker and queue semantics in the RFC describe a single execution path; the runtime is downstream of ingestion and Product Intelligence.

Status: FROZEN conceptually, OPEN for the concrete durable writer implementation.

## 8. Transition Ordering

Decision: transition ordering is deterministic and append-only.

Proposed MVP:

- transition history is ordered by a monotonic persisted sequence per job when available;
- if a sequence is not yet persisted, the append order written by the lifecycle store is authoritative;
- wall-clock timestamps are retained as metadata, not as the sole ordering key.

Why it matters: timestamps can collide; replay and recovery need a stable order.

Repository support: the RFC requires append-only lifecycle records and says replay compares policy decisions, not wall-clock times. The repository does not yet define a durable ordering field.

Status: OPEN for the exact persisted ordering key.

## 9. Current-State Derivation

Decision: current state is derived from ordered persisted transition history rather than maintained as an independent mutable field.

Proposed MVP: the latest valid transition defines current job state; current state is a projection of history.

Why it matters: a projection model is replayable and avoids divergent mutable state.

Repository support: the RFC explicitly favors append-only lifecycle records and immutable terminal states, but it does not yet define a durable current-state projection.

Status: OPEN for the concrete derivation mechanism.

## 10. Transition Identity And Idempotency

Decision: a lifecycle transition must have a deterministic identity so repeated recording of the same transition is idempotent and conflicting payloads fail closed.

Proposed MVP:

- the identity must be derived from the immutable transition payload;
- repeated writes of the same payload return success;
- the same transition identity with a different payload is a conflict;
- no random UUID may be used for lifecycle transition identity.

Why it matters: durable persistence must tolerate duplicate delivery without mutating history.

Repository support: the RFC requires duplicate delivery to avoid duplicate domain effects and says invalid transitions fail closed, but the repository does not currently expose a concrete transition identity builder.

Status: OPEN for the exact identity function.

## 11. Attempt Numbering And Allocation

Decision: attempt numbering remains `1-based`, with attempt identity `job_id + ":" + attempt_number`.

Proposed MVP:

- the first attempt is `attempt_number = 1`;
- a retry creates the next attempt number;
- finalized attempts are immutable;
- a failed attempt is never reused for a different execution;
- attempt allocation is deterministic and survives restart because it is derived from the job identity and counted attempts.

Why it matters: durable attempt state needs a stable key and stable retry policy.

Repository support: the contract and enum already define `attempt_id`, `attempt_number`, `max_attempts = 3`, and retry counting as `attempt_number - 1`.

Status: FROZEN for identity and numbering, OPEN for the durable allocator implementation.

## 12. Retry Semantics

Decision: retry is permitted only when the current failure category and policy mark the attempt retryable, and only up to the frozen default maximum of 3 total attempts.

Proposed MVP:

- retry preserves `job_id` and immutable request fields;
- retry creates a new attempt record;
- retry does not overwrite prior attempt records;
- the default maximum is 3 attempts total;
- deterministic backoff is `min(300, 30 * 2^(next_attempt_number - 2))`;
- a completed terminal job is not retried.

Why it matters: retry policy determines whether durable lifecycle records can be reconciled across restarts.

Repository support: the RFC freezes max attempts and backoff policy and states retry mutates job lifecycle while replay does not.

Status: FROZEN.

## 13. Restart And Recovery

Decision: interrupted work is not silently resumed by the durable store; recovery follows the existing retry and lease semantics.

Proposed MVP:

- if a worker stops mid-stage, the incomplete attempt is recoverable only through the existing retry policy;
- the lifecycle store does not invent a second execution attempt for the same attempt number;
- a finalized attempt remains finalized after restart;
- duplicate delivery of a terminal job is a no-op;
- duplicate delivery of an in-progress leased job fails closed or is rejected by ownership/lease checks.

Why it matters: restart behavior must not rewrite execution history or invent recovery semantics.

Repository support: the RFC states crash recovery is governed by lease expiry and retry policy, and duplicate delivery must not create duplicate effects.

Status: FROZEN at the behavior level, OPEN for the concrete restart implementation.

## 14. Relationship Between Lifecycle History And Final Attempt State

Decision: lifecycle transitions describe execution history; `ScrapeAttempt` represents the finalized attempt outcome; `ScrapeJob` represents request-level identity.

Proposed MVP:

- transitions record the path through the lifecycle;
- attempts record the final outcome for a bounded execution;
- job identity remains request identity only;
- current state is derived from transitions;
- `IngestionWorkerResult` is the finalized execution result handed downstream.

Why it matters: this separation prevents duplicating state across job, attempt, and transition records.

Repository support: existing types already separate `ScrapeJob`, `ScrapeAttempt`, `LifecycleTransition`, and `IngestionWorkerResult`.

Status: FROZEN conceptually.

## 15. Existing Implementation Gap

Decision: the repository still lacks the executable lifecycle boundary that writes, orders, and replays transitions durably.

Proposed MVP:

- one lifecycle store/writer owns persistence;
- it accepts the frozen state machine and attempt policy above;
- it exposes exact job state reconstruction from ordered history.

Why it matters: this is the minimum missing implementation boundary before durable lifecycle persistence can be built.

Repository support: the current worker executes a single attempt but does not persist lifecycle transitions or derive current state from them.

Status: OPEN for implementation.

## 16. Explicit Non-Goals

This contract does not define:

- PostgreSQL or any other storage technology;
- SQLAlchemy or ORM models;
- distributed queues;
- scheduler design;
- automatic retries beyond the frozen policy;
- new `JobState` values;
- new attempt identity algorithms;
- Product Intelligence behavior;
- observation registry behavior;
- API behavior.

## 17. Remaining Open Decisions

The remaining open implementation decisions are:

- the exact durable storage mechanism for lifecycle transitions;
- the exact persisted ordering key for transitions;
- the exact deterministic transition identity function;
- the concrete lifecycle writer service boundary;
- the exact restart recovery implementation for interrupted in-flight work.

## 18. Next Implementation Slice Unlocked

The next safe implementation slice is a durable lifecycle store that appends frozen `LifecycleTransition` records, derives current job state from ordered history, and persists finalized `ScrapeAttempt` records without changing existing job, attempt, or Product Intelligence semantics.
