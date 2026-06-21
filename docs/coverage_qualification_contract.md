# Coverage Qualification Contract

## Purpose

This contract defines how Candidate Generation earns a coverage state.
Variant Matching may consume the declared state, but it must not infer it.

## Owner

- **Coverage qualification owner:** Candidate Generation

## Scope Of This Contract

This contract defines how the following states are assigned:

- `representative`
- `partial`
- `unknown`
- `invalid`

It does not define matcher outcomes.
It does not define validation.

## Required Inputs

Coverage qualification is allowed only when Candidate Generation emits all required metadata for the generation run:

- `coverage_scope_id`
- `scope_descriptor`
- `source_attempts`
- `search_space_limits`
- `candidate_pool_summary`
- `qualification_rationale`
- `generator_version`
- `trace_id` or equivalent deterministic generation identifier

### Required Scope Descriptor

The scope descriptor must state, at minimum:

- platform or platform slice
- category or category slice
- query token set or equivalent search key
- source channels included in scope
- whether the search was intended to be recall-oriented or intentionally narrow

## Qualification Rules

### `representative`

`representative` may be emitted only when all of the following are true:

1. The scope descriptor is explicit and finite.
2. Every source channel declared in scope was attempted or explicitly accounted for.
3. No source attempt is missing, truncated, or silently omitted.
4. No hard timeout occurred on a required source channel.
5. No required search-space branch was skipped.
6. Candidate Generation did not intentionally narrow the pool below the declared scope.
7. The candidate pool summary is internally consistent with the trace.
8. The rationale explicitly states why the pool is broad enough for negative reasoning.

### `partial`

`partial` must be emitted when the run was scoped, but one or more required qualification conditions were not satisfied.

Examples:

- a declared source channel timed out
- a query branch was intentionally narrowed
- a page limit or candidate limit truncated the search space
- some plausible candidate families were not searched

### `unknown`

`unknown` must be emitted when no authoritative qualification decision exists.

Examples:

- the generation run has no coverage record
- the record was not completed
- the record is unavailable to downstream consumers

### `invalid`

`invalid` must be emitted when the declaration is malformed or contradictory.

Examples:

- the scope descriptor conflicts with the source attempts
- the trace id does not match the generation record
- required metadata is missing
- the declaration claims `representative` while the trace shows skipped required sources

## Deterministic Refusal Rules

Candidate Generation must refuse to emit `representative` when any of the following are true:

- the scope is not explicit
- the scope is not finite enough to reason about source coverage
- a required source channel was not attempted
- a required source channel timed out without a recorded completion state
- the search space was intentionally narrowed below the declared recall scope
- the trace is incomplete or not reproducible
- the rationale cannot explain why negative reasoning is safe
- the pool summary disagrees with the execution trace

## Required Rationale

The qualification rationale must state:

- the declared scope
- the executed source channels
- the executed search-space limits
- why the pool is representative, partial, unknown, or invalid
- any omitted or truncated branches
- any timeout or incomplete trace

## Required Metadata

The emitted coverage record must include:

- declaration id
- trace id
- generator version
- scope descriptor
- source attempt log
- search-space limits
- candidate count summary
- omission flags
- qualification rationale
- content hash or equivalent stable identifier

## Validation Invariants

- `representative` is never inferred from candidate count alone.
- `representative` is never inferred from pool diversity alone.
- `partial` is never upgraded to `representative` by downstream systems.
- `unknown` is not a synonym for `partial`; it means no authoritative declaration exists.
- `invalid` is never usable for rejection.
- a declaration that cannot be reproduced from its trace is not `representative`.
- coverage qualification never depends on freshness classification.

## Examples

1. Platform slice `Blinkit / milk`, all declared source channels attempted, no truncation, no omissions -> `representative`.
2. Platform slice `Blinkit / milk`, page limit hit intentionally -> `partial`.
3. Coverage record missing entirely -> `unknown`.
4. Scope says `milk` but source attempts show `bread` branches only -> `invalid`.
5. Scope says `representative` but the trace reveals an omitted required source -> `invalid`.

## Determinism Note

Two engineers must reach the same coverage state from the same execution trace.
If they cannot, the declaration is not sufficiently specified and must not be emitted as `representative`.
