# Freshness Classification Contract

## Purpose

This contract defines how freshness states are assigned from a lineage snapshot.

## Owner

- **Freshness classification owner:** Assertion / context freshness classifier

## Inputs

Freshness classification consumes:

- the lineage snapshot
- the current canonical context record
- the revision chain
- supersession links
- revision type
- evidence references
- source artifact references
- current listing evidence

Freshness classification must not consume candidate coverage.
Freshness classification must not consume matcher outcome.

## Freshness States

### `fresh`

The context is the current authoritative revision for the evaluated scope, and no superseding revision invalidates it.

### `stale-compatible`

The context has been superseded or aged, but the lineage still shows compatibility with the current listing evidence.

### `stale-unresolved`

The context is no longer current enough to settle the decision, but the lineage does not prove a contradiction.

### `stale-conflicting`

The lineage proves that the context is incompatible with the current listing evidence.

### `missing`

No usable lineage snapshot is available.
Freshness cannot be computed.

### `invalid`

The lineage snapshot is malformed, cyclical, or contradictory.
Freshness cannot be trusted.

## Deterministic Classification Rules

### Assign `fresh` When

1. The lineage has a single authoritative head for the scope.
2. The current context is that head.
3. No superseding revision contradicts the current listing evidence.
4. The lineage evidence is complete enough to support current authority.

### Assign `stale-compatible` When

1. A newer revision exists.
2. The older context is still lineage-compatible with the listing evidence.
3. The older context no longer owns authority, but it still describes the same exact pack identity or a strictly compatible historical revision.

### Assign `stale-unresolved` When

1. The lineage exists.
2. The context is not current enough to be trusted as fresh.
3. The lineage does not prove compatibility or conflict.

Examples:

- missing revision linkage
- ambiguous split or merge history
- insufficient branch resolution

### Assign `stale-conflicting` When

1. The lineage proves a different pack identity.
2. A superseding revision contradicts the current listing evidence.
3. The context describes a retired state that cannot coexist with the observed listing.

### Assign `missing` When

1. No lineage snapshot is available.
2. No authoritative context record can be resolved.
3. The lineage record was not produced by the upstream authority.

### Assign `invalid` When

1. The lineage graph contains a cycle.
2. Required lineage links are missing.
3. Two active heads exist for the same exact scope.
4. The lineage metadata contradicts itself.

## Illegal Transitions

Freshness classification is computed from a snapshot.
A stored classification record must not be mutated into a different state without a new lineage snapshot.

Illegal transitions on the same stored record:

- `stale-conflicting` -> `fresh`
- `stale-conflicting` -> `stale-compatible`
- `invalid` -> any non-invalid state
- `stale-unresolved` -> `fresh`
- `missing` -> any non-missing state without a new lineage record
- `invalid` -> any non-invalid state without a new lineage record

## Legal Transitions

Legal changes occur when lineage evidence changes and a new classification record is emitted.

- `fresh` -> `stale-compatible`
- `fresh` -> `stale-unresolved`
- `fresh` -> `stale-conflicting`
- `stale-compatible` -> `stale-unresolved`
- `stale-compatible` -> `stale-conflicting`
- `stale-unresolved` -> `stale-compatible`
- `stale-unresolved` -> `stale-conflicting`
- `missing` -> `fresh` after a new lineage record is produced
- `invalid` -> `fresh` after the invalid record is replaced by a valid lineage snapshot

## Evidence Requirements

The classifier must preserve:

- lineage root id
- revision ids
- supersession ids
- evidence references
- source artifact references
- revision type
- classification rationale

## Validation Invariants

- freshness may not be inferred from age alone
- freshness may not be inferred from coverage
- freshness may not be inferred from matcher outcome
- freshness may not be assigned without lineage
- freshness may not be assigned without a current scope reference
- freshness classification never depends on coverage validation

## Examples

1. Current head matches listing exactly -> `fresh`.
2. Older but still compatible packaging title -> `stale-compatible`.
3. Split history exists but branch resolution is incomplete -> `stale-unresolved`.
4. Older pack size contradicted by superseding revision -> `stale-conflicting`.
5. Revision record is malformed -> `invalid`.

## Determinism Note

Two engineers examining the same lineage snapshot and the same listing evidence must assign the same freshness state.
