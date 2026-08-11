# Canonical Catalog Persistence Decision Contract

**Status:** Slice 7I-D contract with approved MVP decisions and deferred extensions  
**Scope:** Authoritative Product/ProductVariant persistence, revision, and durability

## 1. Scope

This contract covers the boundary:

```text
canonical entity creation and governance
  -> authoritative catalog persistence
  -> deterministic catalog snapshot
```

It consumes canonical identity, creation, and governance outcomes. It does not
define identity equality, ID assignment, approval, listing association, or
snapshot construction.

## 2. Authoritative Catalog Source

No authoritative production catalog source is established in the repository.
There is no production catalog repository, database, external catalog adapter,
governed file, seed source, or catalog service.

```text
OPEN — authoritative catalog source of truth.
```

`CandidateCatalogSnapshot` is a derived in-memory input to candidate generation;
it is not an authoritative catalog.

## 3. Persistence Owner

Product Intelligence owns the eventual canonical catalog boundary, but no
concrete persistence owner or service exists. `ObservationRegistry`,
`EvidenceRegistry`, snapshots, and test fixtures are not canonical catalog
persistence.

```text
OPEN — canonical Product/ProductVariant persistence owner.
```

## 4. Product Persistence Semantics

Any authoritative persistence boundary must preserve the complete Product
model, including:

- `canonical_product_id` and identity status;
- brand, product type, canonical display name, identity attributes, and
  descriptive attributes;
- category reference;
- lifecycle status;
- `catalog_revision`;
- evidence references;
- effective validity periods.

Identity, descriptive, governance, lifecycle, revision, and provenance data
must remain distinguishable. The repository does not define whether writes are
insert-only, replacement-based, mutable, or revisioned.

```text
OPEN — Product persistence representation and write semantics.
```

## 5. Variant Persistence Semantics

Any authoritative persistence boundary must preserve the complete
ProductVariant model, including:

- `canonical_variant_id`;
- parent `canonical_product_id`;
- variant identity attributes;
- pack configuration;
- lifecycle status;
- `catalog_revision`;
- evidence references;
- effective validity periods.

A persisted Variant must retain exactly one parent Product identity. The
repository does not define storage or update semantics for parent/revision
consistency.

```text
OPEN — Variant persistence representation and parent consistency semantics.
```

## 6. Canonical ID Preservation

Persistence consumes canonical IDs assigned by the separate identity/creation
authority. It must never:

- generate a replacement Product or Variant ID;
- use a database row ID as canonical identity;
- derive identity from storage paths, timestamps, replay order, or runtime
  metadata;
- replace canonical IDs with storage keys.

Canonical ID authority remains open in the upstream creation contracts; this
document does not resolve it.

## 7. Revision Versus Identity

The following identities remain distinct:

```text
canonical_product_id
!= canonical_variant_id
!= catalog_revision
!= observation_id
```

`catalog_revision` is a model field, but the repository does not establish
whether it identifies an immutable entity revision, a catalog-wide version, an
effective state, or an externally supplied revision.

```text
OPEN — revision meaning, numbering, authority, and write model.
```

Persistence must not infer that every correction creates a new canonical ID or
that every correction mutates an existing record.

## 8. Historical Preservation

The models expose `effective_period_start` and `effective_period_end`, but no
repository behavior establishes whether historical Product/Variant states,
evidence, or corrections must remain recoverable.

```text
OPEN — historical retention and historical addressability.
```

No append-only history, audit store, revision table, or deletion policy is
authorized by this contract.

## 9. Corrections and Updates

The repository does not define whether changes to descriptive attributes,
identity evidence, category, brand, or pack configuration are handled by:

- in-place correction;
- a new revision;
- supersession;
- a new canonical identity;
- governance review;
- another mechanism.

```text
OPEN — correction, replacement, merge, split, and supersession semantics.
```

No persistence implementation may silently overwrite canonical identity or
merge distinct entities.

## 10. Deprecation and Removal

Product and Variant models expose lifecycle values such as `active`,
`discontinued`, `superseded`, and `unknown`. The repository does not establish
whether these states are persisted records, revisions, deletion markers, or
snapshot eligibility predicates.

```text
OPEN — deprecation, removal, addressability, and historical-reference semantics.
```

No implementation may delete or hide canonical entities based only on a
lifecycle field without a frozen catalog policy.

## 11. Product/Variant Consistency

The persisted relationship is:

```text
ProductVariant.canonical_product_id
  -> exactly one canonical Product identity
```

The repository does not define whether a Variant may reference a Product from
another catalog revision, a deprecated Product, or an unavailable Product, nor
does it define transaction or atomicity guarantees.

```text
OPEN — Product/Variant consistency and atomic persistence boundary.
```

## 12. Replay and Idempotency

The following principles are frozen:

- replay must not change canonical identity because capture timestamps, worker
  metadata, artifact paths, or runtime metadata changed;
- replay must not silently create duplicate canonical entities;
- canonical IDs are not regenerated by persistence;
- provenance remains linked to the existing Evidence Registry.

Exact duplicate-write, same-revision, conflict, and replay-after-correction
results are not defined.

```text
OPEN — persistence replay, duplicate, and conflict semantics.
```

## 13. Concurrent Updates

No repository component defines concurrency behavior for simultaneous Product
or Variant updates, conflicting revisions, or concurrent lifecycle changes.

```text
OPEN — concurrent update and consistency semantics.
```

This contract does not authorize locks, optimistic concurrency, transactions,
or distributed coordination.

## 14. Durability and Restart

No evidence establishes whether canonical catalog state must survive process,
worker, machine, or deployment restart. No persistence technology is selected.

```text
OPEN — durability, restart, and deployment guarantees.
```

PostgreSQL, SQLite, JSON, filesystem, Redis, and other storage mechanisms are
not implied by this contract.

## 15. Snapshot Relationship

The source relationship remains:

```text
Authoritative Catalog
  -> deterministic snapshot builder
  -> CandidateCatalogSnapshot
  -> Candidate Generation
```

`CandidateCatalogSnapshot` must remain a derived view, not a persistence
substitute. Snapshot revision binding, ordering, rebuild, and empty-catalog
semantics belong to the snapshot contract and are not resolved here.

## 16. Test Fixture Boundary

Product, ProductVariant, and CandidateCatalogSnapshot instances constructed in
tests are fixtures only. They are not authoritative catalog state, seed data,
or a persistence implementation.

## 17. Provenance

Persistent catalog records and any future revisions must preserve or reference:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers;
- platform listing identity;
- canonical Product and Variant IDs when assigned.

The Evidence Registry remains the evidence authority. No second provenance
system is introduced.

## 18. Explicit Non-Goals

This contract does not implement or authorize:

- a database, file format, or storage backend;
- repositories, persistence adapters, or migrations;
- Product/ProductVariant entities or IDs;
- identity or creation authority;
- approval or governance workflows;
- revision, audit, correction, merge, split, or supersession operations;
- listing association;
- snapshot construction or CandidateCatalogSnapshot population;
- candidate generation, matching, APIs, or frontend behavior.

## Approved MVP Decisions

- Exactly one governed authoritative catalog state/source exists conceptually.
- Canonical catalog state must survive process restart; process-local memory is
  not authoritative.
- Storage technology and concrete persistence owner remain implementation
  decisions.

## 19. Remaining Open Decisions

Before persistence implementation, the following require product, business, or
architecture decisions:

1. Authoritative catalog source of truth.
2. Durable persistence owner and mechanism.
3. Product and Variant write representation and semantics.
4. Revision meaning, numbering, authority, and immutability.
5. Historical retention and addressability.
6. Correction, replacement, merge, split, and supersession behavior.
7. Deprecation/removal persistence and canonical-ID addressability.
8. Product/Variant parent consistency and atomicity guarantees.
9. Replay, duplicate, and conflict results.
10. Concurrent update semantics.
11. Durability and restart guarantees.
12. Snapshot/catalog revision binding and related rebuild semantics.

No implementation may resolve these decisions implicitly.
