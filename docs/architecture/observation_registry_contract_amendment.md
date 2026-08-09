# Observation Registry Contract Amendment

**Status:** Frozen contract amendment  
**Scope:** Cartel Slice 5C only

## Motivation

The ingestion architecture defines the boundary:

```text
NormalizedObservation -> Observation Registry -> Product Intelligence
```

`NormalizedObservation` is already frozen and executable, but the repository
does not define an executable observation-registry interface. This amendment
freezes the smallest contract required to materialize Slice 5C.

This amendment does not change normalized-observation identity or any
Product Intelligence contract.

## Registry Responsibility

The Observation Registry stores and retrieves immutable
`NormalizedObservation` values. It preserves the complete observation object,
including raw artifact, evidence, field references, completeness, and
normalization version.

The registry does not normalize data, store raw artifacts, extract evidence,
create products or variants, perform matching, calculate prices, or trigger
downstream intelligence.

## Public Interface

The registry exposes exactly these synchronous operations:

```text
register(observation: NormalizedObservation) -> NormalizedObservation
get(observation_id: str) -> NormalizedObservation | None
exists(observation_id: str) -> bool
```

`register` returns the canonical registered observation. The returned value is
structurally equal to the input for a new registration and to the previously
registered value for an identical replay.

No search, listing, filtering, pagination, update, delete, or bulk operation
is part of this contract.

### Input validation

The input must be a valid `NormalizedObservation`. The registry uses its
derived `observation_id`; callers cannot provide a separate registry ID.

An empty or malformed lookup key is invalid input and fails deterministically.

### Retrieval

`get` returns `None` for an unknown observation ID. A known observation is
returned as an immutable structural copy, so callers cannot mutate registry
state through the returned object.

`exists` returns `True` exactly when the observation ID is registered and
`False` otherwise.

## Identity

`NormalizedObservation.observation_id` is the sole registry identity and lookup
key. The existing `NormalizedObservationIdentityBuilder` remains authoritative.

The registry does not generate or persist another identity. Timestamps, UUIDs,
database row IDs, filesystem paths, worker IDs, queue state, and insertion
ordering do not participate in registry identity.

## Idempotency and Conflicts

Registering an observation whose ID is not present stores it and returns it.

Registering the same observation ID again is an idempotent replay. The stored
content must be compared using deterministic canonical serialization. If the
content is identical, registration returns the existing observation and does
not create a second logical record.

If the same observation ID is submitted with different content, registration
raises `ObservationRegistrationConflict`. The original observation remains
unchanged and the conflicting value is not stored.

The registry never silently overwrites an immutable observation.

## Immutability and Provenance

Registered observations are immutable. No update or patch operation exists.
Corrections require a new observation identity under the existing observation
contract.

The registry preserves, without reinterpretation:

- `RawArtifactReference`;
- `EvidenceReference` values;
- `ObservationFieldReference` values;
- normalized values and platform identifiers;
- completeness;
- normalization version.

Internal storage keys must not replace these provenance values. Filesystem paths
must never become registry provenance.

## Persistence and Lifecycle

Slice 5C uses a process-local in-memory registry, matching the existing local
checkout-observation registry pattern and the current one-process ingestion
architecture.

The registry lifetime is the lifetime of its instance. Observations do not
survive process restart. Replay within the same process is supported through
deterministic observation identity and idempotent registration.

Durable observation persistence across restarts is intentionally deferred. No
database, filesystem record format, external service, or retention policy is
introduced by this contract.

Because storage is process-local, there is no durable registry serialization
format in Slice 5C. In-memory comparisons use deterministic canonical
serialization only for conflict detection.

## Concurrency

Slice 5C supports single-process registration. Registration is an atomic
check-and-store operation with respect to the registry instance: two concurrent
registrations for the same ID must resolve to either the identical existing
observation or one deterministic `ObservationRegistrationConflict`, and must
never overwrite data or create two logical records.

Distributed locking and multi-process coordination are outside this contract.

## Product Intelligence Boundary

The registry does not create `Product`, `ProductVariant`, product matches, or
candidate-generation records. It does not perform cross-platform matching and
does not invoke Product Intelligence. A separate downstream integration may
consume registered observations under its own contract.

## Slice 5C Boundary

Slice 5C implements only:

```text
NormalizedObservation
    -> ObservationRegistry.register()
    -> immutable process-local record
    -> ObservationRegistry.get()/exists()
```

The normalizer remains responsible only for producing normalized observations.
Worker integration, Product Intelligence ingestion, API exposure, durable
persistence, and cross-process coordination are outside this slice.

## Compatibility Implications

The contract reuses the existing immutable Pydantic model and its identity
builder. It does not modify `NormalizedObservation`, the parser contracts, the
normalizer, `EvidenceRegistry`, or Product Intelligence models.

The dedicated conflict exception is part of the registry package and is not a
replacement for any existing ingestion or evidence exception hierarchy.

## Contract Freeze

This amendment freezes:

1. `observation_id` as the sole registry identity.
2. Synchronous `register`, `get`, and `exists` operations only.
3. `register` returning the canonical registered `NormalizedObservation`.
4. Idempotent identical replay behavior.
5. `ObservationRegistrationConflict` for same-ID, different-content input.
6. Immutable, provenance-preserving stored observations.
7. Process-local in-memory lifecycle for Slice 5C.
8. No registry serialization or restart durability in Slice 5C.
9. Atomic single-process check-and-store semantics.
10. No Product Intelligence behavior inside the registry.

## Open Contract Decisions

None for Slice 5C. Durable persistence across process restarts, distributed
coordination, and downstream Product Intelligence integration remain explicitly
deferred rather than unresolved requirements of this slice.
