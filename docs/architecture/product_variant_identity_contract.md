# ProductVariant Identity Contract

**Status:** Slice 7C contract freeze with explicit open decisions  
**Scope:** Canonical ProductVariant identity and `canonical_variant_id` authority only

## 1. Scope

This contract defines the boundary:

```text
governed Product identity
  -> ProductVariant identity resolution
  -> canonical_variant_id
```

It does not implement variant resolution, Product creation, catalog
persistence, listing association, snapshot construction, or matching.

## 2. Ownership

Canonical ProductVariant identity is owned by the governed Product Intelligence
catalog boundary. Ingestion owns observations and provenance only.

No executable variant identity resolver or canonical variant ID authority exists
in the repository.

## 3. Product Dependency

A ProductVariant belongs to exactly one canonical Product through
`ProductVariant.canonical_product_id`.

Variant identity is evaluated within its governed parent Product. Variant
attributes are not globally sufficient to identify a variant across products.

If the parent Product is unresolved, the Variant must remain unresolved. The
variant boundary must not bypass Product identity resolution or attach an
observation to an arbitrary parent.

## 4. Variant Identity Definition

A canonical ProductVariant represents a governed purchasable configuration
within one canonical Product. It is not equivalent to:

- a normalized observation;
- a platform listing or source record;
- a quantity string alone;
- a platform-specific variant identifier.

The repository does not define the authoritative identity key for deciding
whether two observed configurations are the same canonical variant.

## 5. Variant Field Classification

| Field | Classification | Identity status |
|---|---|---|
| `canonical_variant_id` | canonical identifier | Assigned identifier, not an input by itself |
| `canonical_product_id` | parent relationship | Required identity scope and parent dependency |
| `variant_identity_status` | governance/lifecycle | Excluded |
| `variant_identity_attributes` | canonical variant data | Potential identity input, equality OPEN |
| `pack_configuration` | canonical configuration | Potential identity input, equivalence OPEN |
| `lifecycle_status` | lifecycle | Excluded |
| `catalog_revision` | revision/version | Excluded from stable identity |
| `evidence_references` | provenance | Excluded from stable identity |
| `effective_period_start` | temporal validity | Excluded |
| `effective_period_end` | temporal validity | Excluded |

The repository does not establish whether descriptive or packaging fields are
identity-defining, nor how they are canonicalized.

## 6. Pack and Quantity Semantics

The existing model represents pack configuration through `PackConfiguration`,
`Measurement`, `PackComponent`, dimensions, units, consumer-unit count, and
declared content. Existing normalization preserves textual quantities but does
not define general physical equivalence.

Therefore this contract freezes only these restrictions:

- quantity text alone is not a canonical variant ID;
- platform listing IDs and source record IDs are not variant identity;
- no unit conversion is implied;
- no pack equivalence is implied;
- `500 ml` and `0.5 L` must not be treated as equal without an explicit
  governed unit policy;
- `2 x 500 ml` and `1 x 1 L` must not be treated as equal without an explicit
  governed pack-equivalence policy.

Exact pack and quantity identity semantics are **OPEN**.

## 7. Equality Semantics

The rule for:

```text
Variant A == Variant B
```

within the same governed Product is **OPEN**.

No implementation may use token overlap, title similarity, platform IDs, or
quantity text alone as variant equality.

## 8. Canonical ID Authority

Product Intelligence owns the canonical variant authority boundary, but the
concrete assignment authority is **OPEN**.

No existing service, external catalog authority, deterministic identity
builder, or repository is established as the assigning component. This
contract does not authorize UUIDs, random IDs, timestamps, observation IDs,
listing IDs, or storage paths.

## 9. ID Stability

`canonical_variant_id` must remain stable for the lifetime of one governed
variant identity. Capture timestamps, runtime metadata, worker IDs, evidence
storage paths, and platform identifiers must not alter variant identity.

Whether a pack, measurement, identity attribute, or parent-product correction
constitutes a new variant identity rather than a revision is **OPEN**.

## 10. Replay Semantics

The following rules are frozen:

- Replaying an identical normalized observation must not create a duplicate
  canonical variant by default.
- Repeated observations across capture times must not change variant identity
  because of time metadata.
- Observations from different platforms may resolve to one canonical variant
  only through the governed Product Intelligence boundary.
- Platform-specific identifiers can never become `canonical_variant_id`.

The exact replay result when catalog attributes change is **OPEN**.

## 11. Cross-Platform Semantics

The intended relationship is:

```text
Platform A variant observation
  + Platform B variant observation
  -> one governed ProductVariant under one canonical Product
```

This is a Product Intelligence identity-resolution decision. It is not a merge
of platform IDs and is not performed by ingestion, the observation registry,
or the existing deterministic matcher without a governed canonical catalog.

Cross-platform evidence thresholds and equality rules are **OPEN**.

## 12. Provenance

Every variant identity decision must remain explainable through:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers;
- source listing identity;
- parent `canonical_product_id`.

The existing Evidence Registry remains the provenance authority. No second
evidence system is introduced.

## 13. Unresolved Variant Identity

The contract distinguishes:

- variant identity resolved;
- variant identity not resolved.

When the parent Product is unresolved, the Variant is unresolved. An
observation must not silently create a ProductVariant or attach to an arbitrary
existing variant.

Pending, rejected, human-reviewed, or externally resolved behavior is **OPEN**
and belongs to the later catalog-governance contract.

## 14. Revision Semantics

`catalog_revision` is revision metadata, not a stable variant identity input.
Evidence updates, lifecycle updates, validity periods, and descriptive changes
must not automatically change `canonical_variant_id`.

The repository does not define when a configuration change is an identity
change, who approves it, or how historical revisions are retained. Those rules
are **OPEN**.

## 15. Explicit Non-Goals

This contract does not implement or authorize:

- ProductVariant creation;
- canonical variant ID generation;
- Product identity resolution;
- pack or unit conversion;
- variant repositories or registries;
- platform listing association;
- catalog persistence;
- CandidateCatalogSnapshot population;
- candidate generation or matching;
- review workflow implementation;
- Product Intelligence execution.

## 16. Remaining Open Decisions

Before variant implementation, the following must be resolved:

1. Exact variant identity inputs and equality semantics.
2. Pack and quantity canonicalization/equivalence policy.
3. Canonical variant ID assignment authority and stable-ID policy.
4. Identity-change versus revision rules.
5. Unresolved and approval behavior.
6. Cross-platform variant evidence and resolution semantics.

These decisions must preserve the parent Product dependency and must not move
variant identity into ingestion.
