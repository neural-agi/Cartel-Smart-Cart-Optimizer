# Product Identity Contract

**Status:** Slice 7B contract freeze with explicit open decisions  
**Scope:** Canonical Product identity and `canonical_product_id` authority only

## 1. Scope

This contract defines the boundary between an ingestion observation and
canonical Product identity:

```text
NormalizedObservation
  -> Product identity resolution
  -> canonical_product_id
```

It does not define ProductVariant identity, catalog persistence, platform
listing association, snapshot construction, candidate generation, or review
lifecycle.

## 2. Ownership

Canonical Product identity is owned by the governed Product Intelligence
catalog boundary. Ingestion owns `observation_id`, normalization, and source
provenance only.

The repository contains no executable Product identity resolver and no existing
component that assigns `canonical_product_id`.

## 3. Product Identity Definition

A canonical Product represents a platform-independent product family. It is
not equivalent to:

- a normalized observation;
- a platform listing;
- a listing observation;
- a product name string;
- a platform-specific identifier.

The repository does not currently define the authoritative identity key that
determines whether two observations represent the same Product.

## 4. Product Field Classification

The existing Product model fields are classified as follows:

| Field | Classification | Identity status |
|---|---|---|
| `canonical_product_id` | canonical identifier | Assigned identifier, not an identity input by itself |
| `product_identity_status` | governance/lifecycle | Excluded |
| `brand_reference` | canonical product data | Potential identity input, exact role OPEN |
| `product_type` | canonical product data | Potential identity input, exact role OPEN |
| `canonical_display_name` | canonical product data | Potential descriptive or identity input, exact role OPEN |
| `identity_attributes` | canonical product data | Potential identity input, exact equality OPEN |
| `descriptive_attributes` | descriptive data | Excluded unless a future contract explicitly promotes a field |
| `canonical_category_reference` | taxonomy data | Potential identity input, exact role OPEN |
| `lifecycle_status` | lifecycle | Excluded |
| `catalog_revision` | revision/version | Excluded from stable identity |
| `evidence_references` | provenance | Excluded from stable identity |
| `effective_period_start` | temporal validity | Excluded from stable identity |
| `effective_period_end` | temporal validity | Excluded from stable identity |

`NormalizedObservation.normalized_name` is not sufficient by itself to
establish Product identity. `platform_identifiers`, `source_record_id`,
`platform_listing_id`, artifact IDs, timestamps, and storage references are
also not Product identity inputs.

## 5. Equality Semantics

The exact rule for:

```text
Product A == Product B
```

is **OPEN**.

The repository does not establish whether equality is based on exact canonical
attributes, governed curated mapping, external catalog identity, or another
mechanism. No implementation may infer equality from name, category, brand,
quantity, or token overlap alone.

## 6. Canonical ID Authority

Product Intelligence owns the authority boundary for assigning
`canonical_product_id`, but the concrete authority is **OPEN**.

No existing service, deterministic identity builder, external catalog adapter,
or repository is established as the assigning authority. This contract does
not authorize UUIDs, random IDs, timestamp-derived IDs, platform IDs, or a new
hash algorithm.

## 7. Identity and ID Generation

Product identity determination and identifier assignment are separate
responsibilities:

```text
identity decision -> assigning authority -> canonical_product_id
```

`canonical_product_id` must be stable for the lifetime of a canonical Product
identity. The rule for assigning the same ID to the same identity across
replays and catalog revisions remains OPEN until the authority and identity
inputs are frozen.

## 8. Replay Semantics

The following boundary rules are frozen:

- Replaying the same `NormalizedObservation` must not create a second Product
  identity by default.
- Capture timestamps, worker IDs, runtime metadata, artifact storage paths,
  and queue state must not change Product identity.
- A platform-specific identifier must not become a canonical Product ID.
- An observation from another platform may resolve to an existing canonical
  Product only through the governed Product Intelligence identity boundary.

Whether a replay or a changed descriptive observation creates a new catalog
revision, updates an existing Product, or requires review is **OPEN**.

## 9. Cross-Platform Semantics

The intended ownership boundary permits:

```text
Platform A observation + Platform B observation
  -> one governed canonical Product
```

This is an identity-resolution decision, not a platform-ID merge. Cross-
platform matching rules and evidence thresholds are not defined by the current
repository and remain **OPEN**.

## 10. Provenance Requirements

Every Product identity decision must remain explainable through the existing
ingestion provenance chain, including where applicable:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers;
- source listing identity.

The existing Evidence Registry remains the provenance authority. This contract
does not create another evidence system.

## 11. Unresolved Identity Behavior

The resolver must distinguish at least:

- identity resolved;
- identity not resolved.

An unresolved observation must not silently become a new canonical Product and
must not be admitted to an approved candidate snapshot as though identity were
established.

The subsequent behavior of unresolved observations, including rejection,
pending state, human review, or external resolution, is **OPEN** and belongs to
the later catalog governance contract.

## 12. Revision Semantics

`catalog_revision` is revision metadata, not a Product identity input. Evidence,
descriptive changes, lifecycle changes, and validity periods must not alter
stable identity merely because their values change.

The repository does not define when a change is a revision versus an identity
change, who approves it, or whether historical revisions are append-only. Those
rules are **OPEN**.

## 13. Explicit Non-Goals

This contract does not implement or authorize:

- Product creation;
- ProductVariant creation;
- canonical ID generation;
- automatic observation-to-Product mapping;
- product repositories or registries;
- catalog persistence;
- listing association;
- CandidateCatalogSnapshot population;
- candidate generation or matching;
- review workflow implementation;
- Product Intelligence execution.

## 14. Remaining Open Decisions

The following must be resolved before Product identity implementation:

1. Exact Product identity inputs and equality semantics.
2. Canonical ID assignment authority and stable-ID algorithm, if any.
3. Behavior for observations with no existing canonical match.
4. Approval/review requirements for canonical identity.
5. Revision versus identity-change rules.
6. Cross-platform identity evidence and resolution semantics.

The next contract should resolve these items without changing ingestion
observation identity or moving canonical decisions into ingestion.
