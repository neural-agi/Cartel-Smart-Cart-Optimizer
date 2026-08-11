# Variant Identity Decision Contract

**Status:** Slice 7I-B contract with approved MVP decisions and deferred extensions  
**Scope:** Canonical ProductVariant identity and `canonical_variant_id` authority

## 1. Scope

This contract covers:

```text
governed Product identity
  -> Variant identity decision
  -> canonical_variant_id authority
```

It does not define Variant creation, approval, pending entities, persistence,
catalog revisions, listing association, snapshots, candidate generation, or
matching.

## 2. Parent Product Dependency

A ProductVariant belongs to exactly one governed canonical Product through
`canonical_product_id`.

Variant identity is scoped within the parent Product. A Variant cannot be
treated as belonging to multiple canonical Products.

If Product identity or `canonical_product_id` is unresolved, Variant identity
is unresolved. Variant resolution must not bypass Product identity resolution
or invent a parent.

## 3. Variant Identity Inputs

The existing ProductVariant model provides potential variant evidence through:

- `canonical_product_id`;
- `variant_identity_attributes`;
- `pack_configuration`;
- pack measurements, units, counts, and components represented inside that
  configuration.

The repository does not establish the exact identity key over those fields.

## 4. Field Classification

| Field or source | Classification |
|---|---|
| `canonical_variant_id` | Canonical identifier, not an identity input by itself |
| `canonical_product_id` | Parent identity scope and required dependency |
| `variant_identity_attributes` | Potential identity evidence; exact equality governed by MVP decision |
| `pack_configuration` | Potential identity evidence; equivalence governed by MVP decision |
| `variant_identity_status` | Governance/identity-resolution state; excluded from identity |
| `lifecycle_status` | Lifecycle only |
| `catalog_revision` | Revision metadata, not stable identity |
| `evidence_references` | Provenance only |
| `effective_period_start/end` | Temporal validity only |
| platform listing/source IDs | Source identity only; excluded |
| observation timestamps and artifact metadata | Acquisition provenance; excluded |

## 5. Pack and Quantity Semantics

The repository represents pack and quantity information through typed model
structures, but does not establish unit conversion or commercial pack
equivalence.

The following are explicitly not equivalent by this contract:

- `500 ml` and `0.5 L`;
- `2 x 500 ml` and `1 x 1 L`;
- a six-pack and a single item;
- `100 g x 2` and `200 g`;
- a family pack and another package size.

No conversion, mathematical equivalence, or quantity-text comparison may
establish Variant identity without a later governed policy.

## 6. Variant Equality

The canonical equality rule for the MVP is:

```text
Variant A == Variant B iff both resolve to the same owner-defined governed
Variant identity key within the same governed Product scope.
```

The exact field set inside that governed key is an owner decision. No
implementation may infer equality from matcher scores, token overlap, title
similarity, platform IDs, source record IDs, observation IDs, or quantity text
alone.

## 7. Product Versus Variant

Product identity and Variant identity are separate:

```text
Product identity != Variant identity
```

An observation may provide evidence for both decisions, but a commercial
attribute becomes Variant-defining only under an explicit governed rule. A
Variant change must not silently change Product identity.

## 8. Canonical Variant ID Authority

Product Intelligence owns the eventual Variant identity boundary. For the MVP,
`canonical_variant_id` is assigned by a manually curated or otherwise
externally governed stable ID authority chosen by the owner.

No implementation may invent a deterministic Variant ID generator.

This contract authorizes no UUID, random value, hash, parent-ID concatenation,
platform listing ID, source record ID, observation ID, timestamp, or runtime
metadata as a canonical Variant ID.

## 9. ID Stability

The following invariants are frozen:

- a governed Variant identity must retain one stable canonical ID;
- repeated observations and replays must not change identity because capture or
  runtime metadata changed;
- platform-specific IDs cannot become canonical IDs;
- multiple platform observations may converge only through governed Product
  Intelligence resolution;
- a Variant cannot have multiple canonical parents.

The mechanism guaranteeing stability is the owner-defined governed identity key
and its assigned canonical ID authority.

## 10. Identity Versus Revision

These concepts remain distinct:

```text
canonical_variant_id != catalog revision != observation_id
```

For the MVP, identity is distinct from revision metadata. A change in
pack/quantity structure, descriptive attributes, lifecycle, or provenance does
not by itself redefine the governed Variant identity key; revision handling is
deferred to the later catalog persistence contract.

## 11. Unresolved, Ambiguous, and Conflicting Outcomes

The identity boundary must conceptually distinguish:

- **RESOLVED:** one governed Variant under one governed Product is identified;
- **UNRESOLVED:** evidence is insufficient;
- **CONFLICTING:** evidence supports incompatible Variant conclusions.

If the parent Product is unresolved, Variant identity is unresolved. If Product
is resolved but Variant evidence is ambiguous, no arbitrary Variant may be
selected.

The governance action after these outcomes is outside this slice and remains
deferred to the later governance contract.

## 12. Replay Semantics

The following principles are frozen:

- replaying the same observation must not create a duplicate Variant identity;
- repeatedly observing the same governed Variant must not change its identity;
- capture timestamps, artifact paths, workers, and runtime ordering are not
  identity inputs;
- repeated pack/quantity observations do not establish equivalence by
  themselves;
- cross-platform observations may converge only through governed resolution.

Conflict resolution for replayed or revised evidence is deferred to the later
governance and persistence contracts.

## 13. Cross-Platform Semantics

Platform A and Platform B listing or source IDs remain platform-scoped. They
must never become `canonical_variant_id`.

Two platform observations may resolve to one canonical Variant only through the
governed Product Intelligence identity boundary and within the same canonical
Product scope.

No cross-platform matching algorithm is defined here.

## 14. Provenance

Every Variant identity decision must be explainable through:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform and platform identifiers;
- platform listing identity;
- parent `canonical_product_id`.

The Evidence Registry remains the provenance authority. No second evidence
mechanism is introduced.

## 15. Product Dependency Invariant

A canonical Variant cannot be treated as belonging to multiple canonical
Products. A Variant identity decision without a governed parent Product is not
resolved.

No reassignment, merge, split, or historical-parent behavior is defined here;
those belong to later governance and association contracts.

## 16. Explicit Non-Goals

This contract does not implement or authorize:

- Product or ProductVariant creation;
- canonical Variant ID generation;
- Product identity equality or Product ID authority;
- Variant approval or pending state;
- persistence or catalog revision;
- listing association;
- snapshots;
- candidate generation or matching;
- changes to ingestion or evidence registries.

## Approved MVP Decisions

- Variant identity uses exact governed attributes within the resolved parent
  Product.
- No implicit unit conversion or commercial pack equivalence is permitted.
- `canonical_variant_id` is assigned manually or by an external governed
  authority and remains stable for the governed identity.

## 17. Remaining Open Decisions

The following MVP decisions are approved. Deferred extensions are:

1. Detailed identity-change versus revision semantics.
2. Replay conflict behavior beyond fail-closed handling.
3. Cross-platform evidence/convergence workflow.
4. Governance action after unresolved or conflicting identity.

These decisions must preserve the parent Product dependency and must not move
Variant identity into ingestion.
