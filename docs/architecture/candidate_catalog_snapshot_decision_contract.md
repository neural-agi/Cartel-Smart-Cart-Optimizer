# Candidate Catalog Snapshot Decision Contract

**Status:** Slice 7I-F contract with approved MVP decisions and deferred extensions  
**Scope:** Governed catalog state to deterministic `CandidateCatalogSnapshot`

## 1. Scope

This contract covers:

```text
authoritative catalog
  -> snapshot builder
  -> CandidateCatalogSnapshot
  -> candidate generation
```

It does not define catalog persistence, entity identity, creation, approval,
listing association, or candidate ranking.

## 2. Authoritative Input

`CandidateCatalogSnapshot` is an immutable in-memory container of Product and
ProductVariant tuples. It is a derived view, not a source of truth. No
production catalog repository, service, external source, or snapshot builder
exists in the repository.

```text
OPEN — authoritative snapshot input source and builder ownership.
```

The future builder must read governed authoritative catalog state, not
ObservationRegistry, EvidenceRegistry, ingestion output, PlatformListing,
CandidateGeneration output, or test fixtures.

## 3. Product Eligibility

Only approved, internally consistent canonical Products may be included. This
is the existing governance boundary, but the repository defines no concrete
approval value or complete eligibility predicate.

```text
OPEN — Product approval and eligibility predicate.
```

Unresolved or unapproved Products must not be treated as eligible by default.

## 4. Variant Eligibility

An included Variant must have a governed parent Product and a resolved Variant
identity. An orphaned Variant cannot be internally consistent. The repository
does not establish whether the parent must be approved, how deprecated or
superseded states are filtered, or whether other lifecycle conditions apply.

```text
OPEN — Variant approval and eligibility predicate.
```

## 5. Parent Consistency

Every snapshot Variant must reference exactly one eligible Product through
`canonical_product_id`, and that Product must be present in the same coherent
eligible view.

The response to an orphaned or conflicting Variant is not defined:

```text
OPEN — exclude, reject, quarantine, or fail-whole snapshot behavior.
```

The builder must not silently attach a Variant to another Product.

## 6. Snapshot Ordering

The repository defines no ordering key for Products or Variants in the
snapshot. Candidate generation ordering is not a snapshot ordering contract.

```text
OPEN — deterministic Product and Variant ordering.
```

Insertion order, database order, timestamps, runtime metadata, and filesystem
paths are not implicit ordering policies.

## 7. Snapshot Identity

No stable snapshot identity, build identifier, content identity, or version
field exists. Snapshot identity must remain distinct from catalog revision,
canonical IDs, and observation identity.

```text
OPEN — snapshot identity.
```

No timestamp, UUID, process ID, worker ID, or path may be invented as identity.

## 8. Catalog Revision Binding

Product and Variant expose `catalog_revision`, but the repository does not
establish whether one snapshot must represent exactly one revision, whether
revision is externally supplied, or whether it participates in snapshot
identity.

```text
OPEN — snapshot/catalog revision relationship.
```

Mixed revisions must not be silently accepted once a consistency policy is
defined.

## 9. Duplicate and Conflict Handling

The repository defines no behavior for duplicate Product or Variant IDs,
duplicate identities, conflicting Product content, conflicting Variant
parents, or conflicting revisions.

```text
OPEN — duplicate and conflict semantics.
```

The builder must not silently deduplicate, overwrite, merge, or choose a
winner.

## 10. Empty Catalog Semantics

The candidate-generation path can represent an empty in-memory snapshot. The
repository does not establish whether an empty authoritative catalog is valid,
a special state, or a build failure.

```text
OPEN — authoritative empty-catalog behavior.
```

No placeholder catalog entities may be fabricated.

## 11. Snapshot Consistency and Atomicity

The intended snapshot represents one coherent authoritative catalog state, but
no transaction, revision, lock, or consistent-read mechanism exists.

```text
OPEN — snapshot consistency and atomicity boundary.
```

The builder must not claim atomicity or accept mixed Product/Variant state by
assumption.

## 12. Rebuild Semantics

For identical authoritative catalog state, a future builder must produce
equivalent Product/Variant contents and, once ordering is frozen, deterministic
ordering. The repository does not establish whether equivalent builds share
identity or create distinct snapshot instances.

```text
OPEN — rebuild and snapshot-identity semantics.
```

Rebuilding must not mutate canonical entity identity.

## 13. Replay and Catalog Changes

Snapshot content is determined by authoritative catalog state, not ingestion
runtime metadata. Replaying observations does not itself populate the snapshot
or create canonical entities.

Behavior after approval changes, corrections, deprecation, supersession, or a
catalog revision is not defined.

```text
OPEN — replay against changed catalog state.
```

## 14. Listing Association Relationship

The executable snapshot container contains Products and ProductVariants, not
PlatformListing or ListingObservation values. Listing association is therefore
a separate boundary and is not represented in snapshot identity or contents.

Whether an eligible Product or Variant must have an associated listing before
snapshot inclusion is:

```text
OPEN — listing-association eligibility requirement.
```

No listing fields may be invented in the snapshot.

## 15. Candidate Generation Boundary

The boundary remains:

```text
CandidateCatalogSnapshot
  -> CandidateGenerationRequest
  -> DeterministicCandidateGenerationService
```

Snapshot construction must not create entities, resolve identity, associate
listings, rank candidates, match products or variants, or mutate catalog state.

## 16. Provenance and Traceability

Snapshot construction must preserve canonical entity provenance already carried
by Products and Variants, including:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform and listing identifiers;
- canonical Product and Variant IDs;
- catalog revision when defined.

The Evidence Registry remains the provenance authority. No second evidence
system is introduced.

## 17. Test Fixture Boundary

Product, ProductVariant, and CandidateCatalogSnapshot instances created in
tests are fixtures only. They are not authoritative catalog state, seed data,
persistence, or production snapshot-builder output.

## 18. Explicit Non-Goals

This contract does not implement or authorize:

- SnapshotBuilder;
- catalog persistence or a catalog source;
- Product/ProductVariant creation or ID generation;
- approval or governance;
- listing association;
- CandidateCatalogSnapshot modification or population;
- candidate generation, matching, APIs, or frontend behavior.

## Approved MVP Decisions

- Eligible Products and Variants are canonically identified, approved, active,
  and internally parent-consistent.
- Products are sorted by `canonical_product_id`; Variants by
  `canonical_variant_id`.
- Duplicate or conflicting canonical input fails closed.
- An empty authoritative catalog is valid and produces an empty
  `CandidateCatalogSnapshot`.

## 19. Remaining Open Decisions

Before snapshot construction, the following require product, business, or
architecture decisions:

1. Authoritative catalog source and builder ownership.
2. Product eligibility predicate.
3. Variant eligibility predicate.
4. Parent inconsistency handling.
5. Deterministic ordering.
6. Snapshot identity.
7. Catalog revision binding.
8. Duplicate and conflict behavior.
9. Empty-catalog behavior.
10. Atomicity and consistency mechanism.
11. Rebuild identity semantics.
12. Replay behavior across catalog changes.
13. Listing-association eligibility requirement.

No implementation may resolve these decisions implicitly.
