# Canonical Catalog Identity Contract Amendment

**Status:** Slice 7A boundary freeze with explicit open decisions  
**Scope:** Canonical Product/ProductVariant catalog boundary only

## Motivation

The ingestion pipeline now produces trustworthy, immutable normalized
observations. Product Intelligence candidate generation requires governed
canonical `Product` and `ProductVariant` objects, but the repository has no
production catalog, identity service, repository, registry, or executable
mapping from normalized observations to canonical entities.

This amendment records the boundaries that are already established and
identifies the remaining decisions that must be frozen before catalog
implementation. It does not create catalog entities or alter Product
Intelligence behavior.

## Canonical Identity Ownership

Canonical identity belongs to Product Intelligence and its catalog-governance
boundary. Ingestion owns observation identity and provenance only.

No existing executable service currently creates or assigns:

- `canonical_product_id`;
- `canonical_variant_id`.

Candidate generation consumes those IDs but does not create them. Matching,
review, and assertion services consume canonical entities and do not establish
their initial catalog identity.

## Identity Distinctions

These identities are distinct and must never be substituted for one another:

```text
observation_id
!= platform_listing_id
!= canonical_product_id
!= canonical_variant_id
```

- `observation_id` identifies one immutable normalized observation.
- `platform_listing_id` identifies a platform-native listing and is currently
  mapped from `NormalizedObservation.source_record_id` at the Product
  Intelligence handoff.
- `canonical_product_id` identifies a governed platform-independent product
  family.
- `canonical_variant_id` identifies a governed purchasable configuration and
  must reference its parent canonical product.

The existing observation identity algorithm is unchanged.

## Product Identity Semantics

The existing `Product` model contains canonical display, brand, product type,
category, identity attributes, lifecycle, revision, and evidence fields. The
repository does not define which subset establishes product identity, nor does
it define whether identity is deterministic from attributes, externally
assigned, curated, or reviewed.

`normalized_name` is not sufficient by itself to establish a canonical Product
identity. A platform listing is not a canonical Product identity.

## Variant Identity Semantics

The existing `ProductVariant` model requires a canonical variant ID, parent
product ID, variant identity attributes, pack configuration, lifecycle, catalog
revision, and evidence. The repository does not define the identity inputs or
the authority that decides whether two observations refer to the same
variant.

Quantity text must not be treated as a canonical variant identity rule without
an explicit governed policy. Product and variant identity remain separate
decisions.

## Observation Mapping Boundary

The established boundary is:

```text
NormalizedObservation
  -> governed canonical identity resolution
  -> Product/ProductVariant and platform-listing association
```

No executable mapping currently exists. The resolver must not be placed in the
parser, normalizer, observation registry, or candidate generator.

## Product Creation and Resolution

The repository does not establish what happens when an observation has no
matching canonical catalog entity. No automatic Product or ProductVariant
creation is authorized by the current architecture.

The following alternatives remain behavior-affecting and unresolved:

- resolve only against a pre-existing governed catalog;
- create a pending/unreviewed entity;
- queue the observation for human identity resolution;
- resolve through an external catalog;
- another explicitly governed process.

No implementation may choose among these alternatives implicitly.

## Platform Listing Association

`PlatformListing` and `ListingObservation` remain platform-native records. The
6B handoff can construct them, but no existing service associates them with a
canonical Product or ProductVariant.

The future catalog boundary must explicitly record whether association is:

1. part of canonical identity resolution; or
2. a separate listing-association operation after identity resolution.

It must preserve the relationship:

```text
observation
  -> platform listing
  -> canonical product
  -> canonical variant, when resolved
```

## Provenance Requirements

Any future canonical identity or association record must retain or reference
the provenance needed to explain the decision:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers;
- associated platform listing and observation values.

The existing Evidence Registry remains the evidence authority. No second
evidence model or provenance system is introduced.

## Catalog Lifecycle and Persistence

The repository does not define a production catalog persistence mechanism. It
contains no ProductRepository, ProductVariantRepository, CatalogRepository,
ProductRegistry, VariantRegistry, or catalog seed store.

The lifecycle of canonical entities is also not frozen. Existing models expose
revision, lifecycle, evidence, and assertion-related fields, but the repository
does not establish the authoritative rules for creation, revision, correction,
deprecation, review, approval, or restart durability.

`CandidateCatalogSnapshot` is an in-memory immutable view supplied directly to
candidate generation. It is not a catalog store and has no defined production
source yet.

## CandidateCatalogSnapshot Boundary

Candidate generation must eventually consume a snapshot derived from an
authoritative governed catalog source. The source may not be inferred from the
current in-memory fixture container.

The future snapshot boundary must define:

- which approved Products and ProductVariants are included;
- how parent-product relationships are validated;
- catalog revision consistency;
- deterministic ordering;
- refresh/rebuild behavior;
- behavior when no catalog entities exist.

## Product Intelligence Ownership

Product Intelligence owns:

- canonical Product identity;
- canonical ProductVariant identity;
- catalog governance;
- candidate generation;
- product and variant matching;
- review and assertion decisions already represented by existing services.

Ingestion owns:

- acquisition;
- parsing;
- normalization;
- observation identity;
- observation and evidence provenance.

Neither side may absorb the other side's identity decisions.

## Classification

**C. Canonical identity/catalog contract is missing and must be frozen.**

There are also multiple missing implementation boundaries, but no conflicting
identity owners were found.

## Open Contract Decisions

The following decisions must be frozen before implementation:

1. Canonical Product identity inputs and equality semantics.
2. Canonical ProductVariant identity inputs and equality semantics.
3. Authority for assigning canonical IDs.
4. Behavior for an observation with no existing canonical match.
5. Whether new entities may be pending/unreviewed or require human/external
   resolution before entering the catalog.
6. Whether platform-listing association is part of identity resolution or a
   separate boundary.
7. Catalog creation, revision, correction, review, approval, and deprecation
   lifecycle.
8. Catalog persistence and restart durability.
9. Authoritative catalog source for `CandidateCatalogSnapshot`.
10. Snapshot rebuild, ordering, and catalog-revision semantics.

These are intentionally open. No Product or ProductVariant implementation can
be compliant until they are resolved.

## Proposed Next Slice

**Slice 7A — Canonical Catalog Identity Contract Freeze**

This slice should resolve the open decisions above without creating catalog
entities or selecting infrastructure unless the architecture explicitly does
so.

After that, implementation can be split into governed canonical catalog
storage/population, listing association, and deterministic snapshot assembly.

## Slice 7A Frozen Rules

The following rules are frozen because they are established by the existing
models and architecture:

1. Product Intelligence owns canonical Product and ProductVariant identity.
   Ingestion and observation registration never assign canonical IDs.
2. `observation_id`, `platform_listing_id`, `canonical_product_id`, and
   `canonical_variant_id` are separate identities.
3. `NormalizedObservation` is an input to identity resolution, not a Product or
   ProductVariant.
4. A platform listing may be represented before canonical resolution. The
   existing 6B handoff creates platform-native listing/observation inputs but
   does not attach them to a canonical entity.
5. Canonical entities and listing associations must retain the established
   observation and evidence provenance chain.
6. `CandidateCatalogSnapshot` is a derived in-memory view and is never the
   authoritative catalog.
7. A snapshot may contain only approved, internally consistent canonical
   Products and ProductVariants from the authoritative catalog source.
8. Snapshot construction is a separate boundary from identity resolution and
   candidate generation.
9. Replay must not create duplicate canonical entities or change canonical
   identity because capture timestamps or runtime metadata changed.
10. Cross-platform observations may resolve to one canonical Product or Variant
    only through the Product Intelligence identity-resolution boundary. A
    platform identifier can never serve as a canonical ID.

## Decision Status

| Decision | Status | Frozen rule or required follow-up |
|---|---|---|
| Product identity inputs/equality | **OPEN** | Existing models do not define whether identity is based on attributes, curated mapping, external identity, or review. Requires a Product Identity Contract. |
| Variant identity inputs/equality | **OPEN** | Existing pack and attribute fields do not define equality or safe derivation. Requires a Variant Identity Contract. |
| Canonical ID authority | **OPEN** | No service or external authority exists in the repository. No ID strategy may be implemented yet. |
| Unresolved observation behavior | **OPEN** | The repository does not choose rejection, pending entity, human review, or external resolution. |
| Review/approval eligibility | **PARTIALLY FROZEN** | Only approved, internally consistent entities may enter a candidate snapshot. The authority and workflow that create approval remain open. Existing match review is not catalog approval. |
| Listing association | **OPEN** | The repository does not decide whether association is atomic with identity resolution or a separate operation. Historical movement semantics are also open. |
| Catalog lifecycle | **PARTIALLY FROZEN** | Existing lifecycle/revision fields must be preserved; no creation, correction, deprecation, deletion, or approval workflow is defined. |
| Persistence/lifecycle | **OPEN** | No authoritative persistence boundary exists. Infrastructure selection is deferred. |
| Snapshot source | **FROZEN** | An authoritative governed catalog source supplies approved entities to a deterministic snapshot builder; `CandidateCatalogSnapshot` is only the derived view. |
| Snapshot semantics | **PARTIALLY FROZEN** | Include approved entities with valid parent relationships and deterministic ordering. Revision consistency, rebuild trigger, empty-catalog behavior, and exact ordering key remain open. |

## Required Follow-up Contracts

The unresolved decisions cannot be safely implemented from the current
repository. Before catalog code is written, the following focused contracts
are required:

1. Product identity and canonical ID authority.
2. Variant identity and parent-product resolution.
3. Unresolved-observation and catalog-approval lifecycle.
4. Platform-listing association and historical reassignment.
5. Catalog persistence and revision lifecycle.
6. Deterministic snapshot build and catalog revision semantics.

These contracts must preserve the frozen ownership and identity distinctions
above. They must not turn ingestion observations into canonical entities by
default.

## Explicit Non-Goals

This amendment does not implement:

- Product or ProductVariant creation;
- canonical ID generation;
- catalog persistence;
- product or variant registries;
- listing association;
- CandidateCatalogSnapshot population;
- candidate generation or matching;
- Product Intelligence execution;
- changes to ingestion, evidence, or observation contracts.
