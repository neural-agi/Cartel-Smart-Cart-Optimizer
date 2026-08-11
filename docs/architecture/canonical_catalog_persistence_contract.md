# Canonical Catalog Persistence Contract

**Status:** Slice 7F contract freeze with explicit open decisions  
**Scope:** Authoritative catalog persistence, revision, and durability boundary

## 1. Scope

This contract defines the boundary:

```text
authoritative canonical catalog
  -> persisted Product/ProductVariant state
  -> deterministic catalog snapshot
  -> CandidateCatalogSnapshot
```

It does not select infrastructure or implement persistence, catalog entities,
ID assignment, governance, or snapshot construction.

## 2. Authoritative Catalog Source

No authoritative production catalog source exists in the repository. There is
no catalog repository, database, external catalog adapter, filesystem catalog,
curated seed source, or catalog service.

```text
OPEN — authoritative catalog source.
```

`CandidateCatalogSnapshot` is an in-memory derived container supplied to
candidate generation. It is not an authoritative source.

## 3. Persistence Ownership

Product Intelligence owns the eventual canonical catalog persistence boundary,
but no concrete persistence owner or service is established.

The following are explicitly not catalog persistence:

- Observation Registry;
- Evidence Registry;
- CandidateCatalogSnapshot;
- Product Intelligence test fixtures;
- assertion-manager in-memory state.

```text
OPEN — durable Product/ProductVariant persistence owner.
```

## 4. Product Persistence

Any future authoritative persistence must preserve the complete Product model,
including:

- `canonical_product_id` and identity status;
- brand, product type, display name, identity attributes;
- descriptive attributes and category reference;
- lifecycle status;
- catalog revision;
- evidence references;
- effective validity periods.

Identity, descriptive, provenance, lifecycle, revision, and evidence data must
remain distinguishable. No Product field may be discarded merely because it is
not used by candidate generation.

The persistence representation and write semantics are **OPEN**.

## 5. Variant Persistence

Any future authoritative persistence must preserve the complete ProductVariant
model, including:

- `canonical_variant_id`;
- parent `canonical_product_id`;
- variant identity attributes;
- pack configuration and measurements;
- lifecycle status;
- catalog revision;
- evidence references;
- effective validity periods.

Parent Product integrity must be validated by the future catalog boundary.
Persistence representation and write semantics are **OPEN**.

## 6. Revision Semantics

The models expose `catalog_revision`, lifecycle fields, and effective periods,
but the repository does not define whether catalog state is:

- immutable and append-only;
- mutable current state with history;
- represented by superseding revisions;
- versioned through external catalog revisions.

```text
OPEN — revision semantics and revision authority.
```

`catalog_revision` is not a canonical identity input under the existing
identity contracts. No implementation may infer that every update creates a
new canonical ID or that every update mutates the existing entity.

## 7. Historical Preservation

The repository does not establish whether prior Product/ProductVariant states,
corrections, evidence changes, or effective periods must be retained after a
new state is published.

```text
OPEN — historical retention and addressability.
```

No audit tables, revision store, or deletion behavior is authorized by this
contract.

## 8. Correction and Supersession

The repository does not define correction, replacement, merge, split, or
supersession operations for canonical entities.

Each remains:

```text
OPEN — correction/supersession semantics.
```

No persistence implementation may silently overwrite canonical identity or
merge entities.

## 9. Deprecation

The models expose lifecycle values such as active, discontinued, superseded,
deprecated, and unknown in related identity/lifecycle concepts. The repository
does not establish:

- whether deprecated entities remain persisted;
- whether deprecated IDs remain addressable;
- whether historical observations continue referencing them;
- whether deprecated or superseded entities enter a candidate snapshot.

```text
OPEN — deprecation persistence and snapshot visibility.
```

## 10. Snapshot Relationship

The following boundary is frozen:

```text
Authoritative Catalog
  -> deterministic snapshot builder
  -> CandidateCatalogSnapshot
  -> CandidateGenerator
```

`CandidateCatalogSnapshot` is a derived in-memory view. It must not become the
source of truth or a persistence substitute.

Only approved, internally consistent entities are eligible under the existing
catalog governance contract. The relationship between a snapshot and the
catalog revision it represents is:

```text
OPEN — snapshot/catalog revision binding.
```

Snapshot ordering, rebuild triggers, and empty-catalog semantics are also
**OPEN**.

## 11. Durability and Restart

No repository evidence establishes whether catalog state must survive process,
machine, worker, or deployment restarts.

```text
OPEN — durability and restart requirements.
```

No database, filesystem format, cache, or external storage mechanism is chosen
by this contract.

## 12. Replay Against Catalog State

The following identity-stability rules are frozen:

- replay must not change canonical Product or Variant identity because capture
  timestamps, runtime metadata, worker IDs, or artifact paths changed;
- replay must not create duplicate canonical entities;
- observation provenance remains linked to the existing evidence authority.

Behavior when replay occurs after catalog revision, deprecation, correction, or
supersession is:

```text
OPEN — replay against revised catalog state.
```

No conflict resolution or historical lookup behavior may be invented.

## 13. Identity Stability

`canonical_product_id` and `canonical_variant_id` remain distinct from
observation and listing identities. They must not be regenerated from storage
paths, timestamps, worker metadata, or replay order.

This contract does not define ID generation or assignment; those remain governed
by the creation contract and its unresolved decisions.

## 14. Provenance

Persistent catalog records and any revisions must remain explainable through:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers;
- platform listing identity;
- canonical Product and Variant IDs when assigned.

The Evidence Registry remains the provenance authority. No second provenance
system is introduced.

## 15. Explicit Non-Goals

This contract does not implement or authorize:

- a database or storage backend;
- Product/ProductVariant repositories;
- catalog entities or IDs;
- migrations or seed data;
- revision or audit tables;
- correction, merge, split, or supersession operations;
- deprecation workflow;
- snapshot builder;
- CandidateCatalogSnapshot population;
- candidate generation or matching.

## 16. Remaining Open Decisions

Before persistence implementation, the following must be frozen:

1. Authoritative catalog source.
2. Durable persistence owner and mechanism.
3. Product and Variant write semantics.
4. Revision model and authority.
5. Historical retention and addressability.
6. Correction, replacement, merge, split, and supersession behavior.
7. Deprecation persistence and snapshot eligibility.
8. Catalog durability and restart guarantees.
9. Replay behavior against revised catalog state.
10. Snapshot/catalog revision binding, ordering, rebuild, and empty behavior.

No implementation may resolve these decisions implicitly.
