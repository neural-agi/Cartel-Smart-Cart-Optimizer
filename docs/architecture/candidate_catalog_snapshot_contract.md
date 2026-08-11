# Candidate Catalog Snapshot Contract

**Status:** Slice 7H contract freeze with explicit open decisions  
**Scope:** Authoritative catalog state to deterministic `CandidateCatalogSnapshot`

## 1. Scope

This contract defines:

```text
Authoritative Catalog
  -> deterministic snapshot build
  -> CandidateCatalogSnapshot
  -> candidate generation
```

It does not implement a catalog source, snapshot builder, persistence, Product
or Variant creation, identity resolution, or candidate ranking.

## 2. Snapshot Source

`CandidateCatalogSnapshot` is currently an immutable in-memory container of
Product and ProductVariant tuples. It is not an authoritative catalog and no
production source or snapshot builder exists.

```text
OPEN — authoritative snapshot input source and builder ownership.
```

The eventual source must be the governed authoritative catalog, not ingestion
observations, test fixtures, or the snapshot itself.

## 3. Product Eligibility

The following rule is already established by the catalog governance contract:

Only approved, internally consistent canonical Products may enter the snapshot.

The repository does not define an approval enum/value or the exact meaning of
internal consistency. Therefore:

```text
OPEN — Product approval and eligibility predicate.
```

Unresolved or unapproved Products must not be treated as eligible by default.

## 4. Variant Eligibility

The following boundary is established:

- a Variant must have a governed parent Product;
- an orphaned Variant cannot be considered internally consistent;
- unresolved Variants cannot be admitted as approved candidates;
- Product/Variant identity remains separate from snapshot construction.

Whether an approved Variant additionally requires an approved parent, and the
precise lifecycle filtering for deprecated or superseded Variants, is:

```text
OPEN — Variant eligibility predicate.
```

## 5. Listing Association Dependency

The current `CandidateCatalogSnapshot` contains only Products and Variants; it
does not contain PlatformListing or ListingObservation values.

Therefore snapshot construction does not currently require listing association
data in its executable container. Listing association remains a separate
catalog boundary and must not be invented inside the snapshot.

Whether eligibility requires a Product/Variant to have at least one associated
listing is:

```text
OPEN — listing-association eligibility requirement.
```

## 6. Catalog Revision Binding

Product and Variant models expose `catalog_revision`, but the repository does
not define whether all snapshot entities must share one revision or how a
snapshot records the revision it represents.

```text
OPEN — snapshot-to-catalog revision binding.
```

The snapshot must not silently mix incompatible catalog state once revision
semantics are defined.

## 7. Snapshot Identity

No stable snapshot identity is defined. The repository has no snapshot version,
content identity, build identifier, or revision binding suitable for reuse.

```text
OPEN — snapshot identity.
```

Timestamps, UUIDs, process IDs, worker IDs, and filesystem paths are not valid
implicit snapshot identity inputs.

## 8. Deterministic Ordering

The candidate generator deterministically ranks candidates after receiving a
request, but the repository does not define ordering of Products or Variants
inside `CandidateCatalogSnapshot`.

```text
OPEN — Product and Variant snapshot ordering.
```

No implementation may choose names, IDs, tuple insertion order, or another key
as a frozen ordering policy without a later decision.

## 9. Duplicate and Conflict Semantics

The repository does not define behavior when the authoritative source contains:

- duplicate Product IDs;
- duplicate Variant IDs;
- duplicate identities;
- a Variant with conflicting parents;
- conflicting canonical entity content.

```text
OPEN — duplicate and conflict behavior.
```

A snapshot builder must not silently deduplicate, overwrite, or merge entities.

## 10. Parent Consistency

Every included Variant must have a parent Product identified by
`canonical_product_id`. The parent must be present in the same coherent
eligible catalog view once the eligibility contract is implemented.

The behavior for an orphaned or conflicting Variant is:

```text
OPEN — reject, exclude, or fail-whole snapshot semantics.
```

## 11. Empty Catalog Behavior

The existing candidate-generation service supports a default empty
`CandidateCatalogSnapshot`, so an empty in-memory snapshot is representable.

Whether an authoritative empty catalog is a valid snapshot, a special state,
or a build failure is:

```text
OPEN — authoritative empty-catalog semantics.
```

No Products or Variants may be fabricated to avoid emptiness.

## 12. Rebuild Semantics

For identical authoritative catalog state, a future builder must produce
equivalent Product/Variant sets and deterministic ordering.

Whether equivalent builds must have an identical snapshot identity is dependent
on the unresolved snapshot identity decision:

```text
OPEN — rebuild identity semantics.
```

Runtime metadata must not affect snapshot content.

## 13. Catalog Changes

The snapshot is a derived view, so changes to the authoritative catalog may
produce a different snapshot. The repository does not define behavior for
Products or Variants being added, removed, corrected, deprecated, superseded,
or reassigned.

```text
OPEN — catalog-change and snapshot replacement semantics.
```

These changes must not be handled by mutating the snapshot as a source of truth.

## 14. Atomicity and Consistency

The intended boundary requires one coherent authoritative catalog state, but no
transaction, revision, lock, or read-consistency mechanism exists.

```text
OPEN — snapshot atomicity and consistency boundary.
```

Mixed Product/Variant revisions must not be accepted once this contract is
implemented, but the enforcement mechanism is not defined here.

## 15. Replay Semantics

The following rules are frozen:

- snapshot content is determined by authoritative catalog state;
- ingestion runtime metadata does not affect snapshot content;
- replaying the same observations does not itself create snapshot entities;
- approval or catalog changes may affect later snapshots only through the
  authoritative catalog boundary.

Replay behavior after catalog revisions, approvals, deprecations, or
supersession remains:

```text
OPEN — replay against changed catalog state.
```

## 16. Candidate Generation Boundary

The existing boundary remains:

```text
CandidateCatalogSnapshot
  -> CandidateGenerationRequest
  -> DeterministicCandidateGenerationService
```

The snapshot builder must not perform:

- identity resolution;
- Product or Variant creation;
- listing association;
- candidate ranking;
- product matching;
- variant matching;
- cross-platform matching.

## 17. Provenance

Snapshot construction must preserve canonical entity provenance already present
on Products and Variants, including references to:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers and listing identity;
- canonical IDs.

The Evidence Registry remains the provenance authority. No second evidence
system is introduced.

## 18. Explicit Non-Goals

This contract does not implement or authorize:

- SnapshotBuilder;
- catalog repositories or persistence;
- Product/ProductVariant creation;
- ID generation;
- approval or governance;
- listing association;
- CandidateCatalogSnapshot modification;
- candidate generation or matching.

## 19. Remaining Open Decisions

Before snapshot construction, the following must be frozen:

1. Authoritative catalog source and builder ownership.
2. Product approval and eligibility predicate.
3. Variant approval and eligibility predicate.
4. Listing-association eligibility requirement.
5. Snapshot/catalog revision binding.
6. Snapshot identity.
7. Product and Variant ordering.
8. Duplicate/conflict semantics.
9. Parent-consistency failure behavior.
10. Empty-catalog behavior.
11. Rebuild identity semantics.
12. Catalog-change replacement semantics.
13. Atomicity and consistency mechanism.
14. Replay behavior across catalog state changes.
