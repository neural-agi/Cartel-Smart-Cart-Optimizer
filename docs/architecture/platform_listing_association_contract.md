# Platform Listing Association Contract

**Status:** Slice 7G contract freeze with explicit open decisions  
**Scope:** PlatformListing/ListingObservation association to canonical entities

## 1. Scope

This contract covers the boundary:

```text
PlatformListing + ListingObservation
  -> resolved canonical identity
  -> Product/ProductVariant association
```

It does not implement a listing registry, association service, catalog
persistence, identity resolution, or snapshot construction.

## 2. Listing Identity

`PlatformListing` is the stable platform-level listing representation. Its
identity is the pair:

```text
(platform, platform_listing_id)
```

`source_record_id` is mapped into `platform_listing_id` by the existing 6B
handoff, but it remains an ingestion source identifier and does not become a
canonical Product or Variant ID.

The following identities remain distinct:

```text
PlatformListing identity
!= ListingObservation identity
!= observation_id
!= canonical_product_id
!= canonical_variant_id
```

Listing URLs, source references, artifact IDs, timestamps, and runtime metadata
do not define stable listing identity under the current architecture.

## 3. Listing and Observation Distinction

```text
PlatformListing
  = stable platform-level listing identity and descriptive listing data

ListingObservation
  = captured price/availability/promotion observation at a point in time
```

Observations must remain independently addressable and must not be collapsed
into listing identity. The repository does not currently define a separate
ListingObservation ID algorithm.

## 4. Association Target

The existing Product Intelligence models do not contain a listing-association
record or fields attaching `PlatformListing` to Product/ProductVariant.

The exact target is therefore:

```text
OPEN — Product-only, Variant-only, both, or a separate association structure.
```

No implementation may omit a Variant relationship merely because Product
identity is known, and no implementation may invent an association field in an
existing model.

## 5. Ownership

Listing association belongs to the governed Product Intelligence catalog
boundary. Ingestion constructs platform-native listings and observations but
does not attach them to canonical entities.

No production listing-association authority exists in the repository.

```text
OPEN — concrete association owner and persistence authority.
```

## 6. Identity Resolution and Association

The following separation is frozen:

```text
identity resolution
  -> listing association
```

The repository does not establish whether these are separate operations or one
atomic catalog transaction. That decision is:

```text
OPEN — operation boundary and atomicity.
```

Association must never create canonical IDs or substitute platform identifiers
for canonical identity.

## 7. Association Preconditions

The following constraints are frozen:

- unresolved Product identity cannot produce an authoritative association;
- unresolved Variant identity cannot be attached to an arbitrary Variant;
- Product and Variant approval requirements follow the catalog governance
  contract;
- provenance must be available for the identity decision.

The exact required approval state, evidence threshold, listing validity, and
whether both Product and Variant must be resolved are:

```text
OPEN — authoritative association preconditions.
```

## 8. Unresolved Listings

When a listing has no resolved Product, it must remain unassociated. It must
not silently become a catalog entity or attach to an arbitrary Product.

When Product is resolved but Variant is unresolved, the listing must not be
silently attached to an arbitrary Variant.

Whether unresolved listings are rejected, deferred, held for governance, or
represented by a pending association is:

```text
OPEN — unresolved listing handling.
```

## 9. Reassignment

The repository does not define what happens when a listing previously
associated with Product/Variant A is later resolved to B.

```text
OPEN — reassignment, correction, supersession, and history semantics.
```

No implementation may silently rewrite the association or generate a new
listing identity.

## 10. Historical Observations

`ListingObservation` captures a listing at a point in time. The repository does
not define whether historical observations retain the association effective at
capture time or inherit a later current association.

```text
OPEN — historical association semantics.
```

Price, availability, and offer history must not be silently rewritten by an
association correction.

## 11. Cross-Platform Semantics

Platform-specific listings may be associated with the same canonical Product
or Variant only through governed Product Intelligence identity resolution:

```text
Platform A listing -> canonical entity
Platform B listing -> same canonical entity
```

This does not merge listing identities. Platform IDs remain platform-scoped and
cannot become canonical IDs. Cross-platform association evidence and equality
remain governed by the Product and Variant identity contracts.

## 12. Replay and Idempotency

The following rules are frozen:

- replaying the same PlatformListing must not create a duplicate listing;
- replaying the same ListingObservation must not create a duplicate logical
  observation;
- replaying the same normalized observation must not create duplicate
  association effects;
- capture timestamps and worker metadata must not change listing identity;
- association replay must preserve canonical identity and provenance.

Exact duplicate storage and conflicting association results are:

```text
OPEN — listing and association conflict/idempotency semantics.
```

## 13. Provenance

Any future association must preserve the chain:

```text
observation_id
  -> PlatformListing
  -> canonical Product
  -> canonical ProductVariant, when resolved
```

The explainability record must retain or reference:

- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform and platform identifiers;
- source listing identity;
- canonical IDs when assigned.

The Evidence Registry remains the provenance authority. No second evidence
system is introduced.

## 14. Candidate Snapshot Eligibility

The existing governance contract requires approved, internally consistent
canonical entities for `CandidateCatalogSnapshot`.

Whether a listing association is additionally required before an otherwise
approved Product or Variant enters a snapshot is:

```text
OPEN — listing association snapshot eligibility.
```

The snapshot remains a derived view and is not a listing registry.

## 15. Listing Lifecycle

The repository does not define a lifecycle model for PlatformListing. Existing
Product/Variant lifecycle fields cannot be silently applied to listings.

The following are **OPEN**:

- active/inactive semantics;
- removal or discontinuation;
- deprecation or supersession;
- persistence of inactive listings;
- historical addressability;
- effect on associated observations and snapshots.

## 16. Explicit Non-Goals

This contract does not implement or authorize:

- listing registries;
- association services;
- Product/ProductVariant creation;
- canonical ID generation;
- listing persistence;
- observation history storage;
- catalog snapshot construction;
- candidate generation or matching;
- changes to ingestion or evidence registries.

## 17. Remaining Open Decisions

Before association implementation, the following must be frozen:

1. Association target shape: Product, Variant, both, or separate structure.
2. Association owner and persistence authority.
3. Identity-resolution versus association atomicity.
4. Association approval and evidence preconditions.
5. Unresolved listing handling.
6. Reassignment and correction semantics.
7. Historical observation association semantics.
8. Listing and association replay/conflict behavior.
9. Snapshot eligibility requirements.
10. Listing lifecycle and historical retention.
