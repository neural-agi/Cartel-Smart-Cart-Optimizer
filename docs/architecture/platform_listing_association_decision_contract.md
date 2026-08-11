# Platform Listing Association Decision Contract

**Status:** Slice 7I-E contract with approved MVP decisions and deferred extensions  
**Scope:** Association of platform listings and observations with canonical entities

## 1. Scope

This contract covers:

```text
PlatformListing + ListingObservation
  -> resolved canonical identity
  -> canonical Product/ProductVariant association
```

It consumes identity outcomes and does not define Product or Variant identity,
ID assignment, persistence, governance, or snapshot construction.

## 2. Listing Identity

The stable PlatformListing identity is:

```text
(platform, platform_listing_id)
```

`source_record_id` is carried into `platform_listing_id` by the existing
handoff, but remains a source identifier. URLs, artifact paths, timestamps,
source references, and runtime metadata do not define listing identity.

```text
PlatformListing identity
!= ListingObservation identity
!= observation_id
!= canonical_product_id
!= canonical_variant_id
```

`ListingObservation` is an observation of a listing at a capture time and must
remain independently addressable. The repository does not define a separate
ListingObservation identity algorithm.

## 3. Association Target

Existing Product Intelligence models contain no association record or field
that establishes whether a listing targets Product, ProductVariant, both, or a
separate structure.

```text
OPEN — association target shape.
```

No implementation may omit a Variant relationship or invent a field on an
existing model to resolve this gap.

## 4. Association Owner

Ingestion constructs platform-native listings and observations but does not
attach them to canonical entities. Candidate generation, ProductMatcher,
VariantMatcher, ObservationRegistry, and EvidenceRegistry do not establish
listing association ownership.

The association belongs conceptually at the governed Product Intelligence
catalog boundary, but no concrete production owner exists.

```text
OPEN — concrete association authority and persistence owner.
```

## 5. Identity Resolution Boundary

The architectural separation is:

```text
Product/Variant identity resolution
  -> listing association
```

Listing association must consume resolved canonical identities and must not
determine identity, generate IDs, or substitute platform identifiers for
canonical IDs. Whether resolution and association are separate operations or
one atomic catalog operation is unresolved.

```text
OPEN — resolution/association operation boundary and atomicity.
```

## 6. Association Preconditions

The following fail-closed constraints are established:

- unresolved Product identity cannot produce an authoritative association;
- unresolved Variant identity cannot attach a listing to an arbitrary Variant;
- provenance for the identity decision must remain available;
- Product and Variant governance requirements, when defined, apply before an
  association is authoritative.

The exact required identity states, approval states, evidence threshold, and
listing validity requirements are:

```text
OPEN — authoritative association preconditions.
```

## 7. Product versus Variant Association

The repository does not establish whether Product association alone is
sufficient or whether an authoritative association must include both Product
and ProductVariant.

```text
OPEN — Product versus ProductVariant association requirement.
```

An implementation must not infer the target from grocery-domain assumptions or
from the presence of a `canonical_product_id` on ProductVariant.

## 8. Unresolved Listings

When Product identity is unresolved, the listing remains unassociated. When
Product identity is resolved but Variant identity is unresolved, the listing
must not attach to an arbitrary Variant. No placeholder Product, Variant, or
canonical ID may be created by association.

The resulting action, including rejection, deferral, governance review, or
pending association representation, is:

```text
OPEN — unresolved listing governance.
```

## 9. Reassignment

The repository does not define behavior when a listing associated with Product
or Variant A later resolves to B. Correction, reassignment, supersession, and
whether a new association revision is required are all unresolved.

```text
OPEN — listing reassignment and correction semantics.
```

No implementation may silently rewrite an association or create a new listing
identity.

## 10. Historical ListingObservations

`ListingObservation` records capture price, availability, offer, parser, source
artifact, and capture-time data for a platform listing. The repository does not
define whether a historical observation retains the association effective at
capture time or follows the listing's current association.

```text
OPEN — historical association semantics.
```

Association correction must not silently rewrite historical observation data.

## 11. Cross-Platform Semantics

Platform A and Platform B listings may converge on the same canonical Product
or Variant only through the governed Product/Variant identity boundary:

```text
Platform A listing -> canonical entity
Platform B listing -> same canonical entity
```

Their platform-scoped identities remain distinct. Platform listing IDs,
observation IDs, and source IDs can never become canonical IDs.

Cross-platform matching and identity resolution are outside this contract.

## 12. Replay and Idempotency

The following principles are frozen:

- replaying a PlatformListing must not create a duplicate logical listing;
- replaying a ListingObservation must not create a duplicate logical
  observation;
- replaying the same normalized observation must not duplicate association
  effects;
- capture timestamps and worker metadata must not change listing identity;
- replay preserves canonical identity and provenance.

Exact duplicate, conflict, and replay-after-catalog-revision results are:

```text
OPEN — association replay and conflict semantics.
```

No storage-specific upsert or overwrite behavior is authorized.

## 13. Listing Lifecycle

`PlatformListing` has no lifecycle field. `ListingObservation` is an append-only
observation model, but the repository does not define listing lifecycle states
or their effects.

The following remain open:

- active, inactive, discontinued, removed, deprecated, or superseded meaning;
- persistence and historical addressability of inactive listings;
- effect on observations and associations;
- effect on CandidateCatalogSnapshot eligibility.

```text
OPEN — listing lifecycle and retention semantics.
```

## 14. Catalog Revision Relationship

No listing-association revision or effective-period model is established. It is
therefore unresolved whether an association is current-state only, bound to a
catalog revision, or effective over an interval.

```text
OPEN — listing association revision semantics.
```

Association must not invent revision numbers or mutate canonical identity.

## 15. Snapshot Relationship

The frozen catalog boundary remains:

```text
Authoritative Catalog
  -> deterministic snapshot builder
  -> CandidateCatalogSnapshot
```

`CandidateCatalogSnapshot` currently contains canonical Products and Variants,
not PlatformListing or ListingObservation objects. The repository therefore
does not establish whether listing association is required for snapshot
eligibility.

```text
OPEN — listing-association requirement for snapshot eligibility.
```

Association does not populate or construct the snapshot.

## 16. Provenance

Any future association must preserve or reference:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform and platform listing identity;
- canonical Product and Variant IDs when assigned.

The chain remains:

```text
observation_id
  -> PlatformListing
  -> canonical Product
  -> canonical ProductVariant, when resolved
```

The Evidence Registry remains the provenance authority. No second evidence
system is introduced.

## 17. Identity and Persistence Boundaries

This contract consumes Product and Variant identity outcomes from their
dedicated decision contracts. It does not redefine equality or ID strategy.

It also does not define catalog persistence, repositories, transactions,
revision storage, or write semantics. Those decisions remain governed by the
canonical catalog persistence contracts.

## 18. Explicit Non-Goals

This contract does not implement or authorize:

- a ListingRegistry or association service;
- Product/ProductVariant creation or canonical ID generation;
- listing or catalog persistence;
- Product/Variant identity resolution or cross-platform matching;
- lifecycle or reassignment workflow;
- CandidateCatalogSnapshot construction;
- candidate generation, matching, APIs, or frontend behavior.

## Approved MVP Decisions

- An authoritative MVP listing association requires both canonical Product and
  canonical ProductVariant.
- Unresolved or conflicting identity remains unassociated and requires manual
  resolution.
- Reassignment, historical association rewriting, advanced lifecycle, and
  association revision history are deferred; unsupported cases fail closed.

## 19. Remaining Open Decisions

Before listing association implementation, the following require product,
business, or architecture decisions:

1. Association target shape.
2. Concrete association owner and persistence authority.
3. Resolution/association atomicity.
4. Identity, approval, evidence, and listing-validity preconditions.
5. Unresolved listing action.
6. Reassignment, correction, and supersession semantics.
7. Historical ListingObservation association semantics.
8. Replay, duplicate, and conflict results.
9. Listing lifecycle and retention.
10. Association revision/effective-period semantics.
11. Listing-association requirement for snapshot eligibility.

No implementation may resolve these decisions implicitly.
