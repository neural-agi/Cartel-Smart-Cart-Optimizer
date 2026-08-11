# Product Identity Decision Contract

**Status:** Slice 7I-A contract with approved MVP decisions and deferred extensions  
**Scope:** Canonical Product identity and `canonical_product_id` authority only

## 1. Scope

This contract covers:

```text
identity evidence
  -> canonical Product identity decision
  -> canonical_product_id authority
```

It does not define Product creation, approval, pending entities, persistence,
catalog revisions, Variant identity, listing association, or snapshots.

## 2. Product Identity Inputs

The existing Product model provides the following possible identity evidence:

- `brand_reference`;
- `product_type`;
- `canonical_display_name`;
- `canonical_category_reference`;
- `identity_attributes`.

The repository does not establish the exact identity key or equality function
over these fields.

`NormalizedObservation` may provide evidence for a future identity decision
through its normalized values, platform identifiers, source listing identity,
and provenance. It is not a Product and must not be transformed directly into
one by ingestion.

## 3. Field Classification

| Product field or source | Classification |
|---|---|
| `canonical_product_id` | Canonical identifier, not an identity input by itself |
| `brand_reference` | Potential identity evidence; exact role OPEN |
| `product_type` | Potential identity evidence; exact role OPEN |
| `canonical_display_name` | Potential identity evidence; exact role OPEN |
| `canonical_category_reference` | Potential identity evidence; exact role OPEN |
| `identity_attributes` | Potential identity evidence; exact equality OPEN |
| `descriptive_attributes` | Descriptive only unless a later decision promotes a field |
| `product_identity_status` | Governance/identity-resolution state; not identity input |
| `lifecycle_status` | Lifecycle only |
| `catalog_revision` | Revision metadata, not stable identity |
| `evidence_references` | Provenance only |
| `effective_period_start/end` | Temporal validity only |
| platform/listing IDs | Source identity only; not canonical Product identity |
| observation timestamps and artifact metadata | Operational/acquisition provenance; not identity |

No field classification above authorizes automatic Product creation.

## 4. Product Equality

The canonical equality rule for the MVP is:

```text
Product A == Product B iff both resolve to the same owner-defined governed
Product identity key over explicitly selected normalized attributes.
```

The exact field set inside that governed key is an owner decision. No
implementation may infer equality from name similarity, token overlap,
category alone, platform identifiers, or quantity text.

Identity equality is distinct from:

- equality of descriptive attributes;
- equality of evidence or observations;
- catalog revision equality;
- Product Intelligence match scores.

## 5. Ambiguity and Identity Outcomes

The identity boundary must conceptually distinguish:

- **RESOLVED:** evidence identifies one governed canonical Product;
- **UNRESOLVED:** evidence is insufficient to establish identity;
- **CONFLICTING:** evidence supports incompatible identity conclusions.

These are conceptual outcomes only. No implementation enums or lifecycle
actions are introduced by this contract.

The action after `UNRESOLVED` or `CONFLICTING` is outside this slice and remains
governed by the later catalog governance contract.

## 6. Canonical Product ID Authority

Product Intelligence owns the eventual canonical identity boundary. For the
MVP, `canonical_product_id` is assigned by a manually curated or otherwise
externally governed stable ID authority chosen by the owner.

The repository contains no established deterministic ID generator for Product
identity, and no implementation may invent one.

This contract authorizes none of the following strategies:

- UUID or random IDs;
- hashes of names or attributes;
- platform listing IDs;
- source record IDs;
- observation IDs;
- timestamps, paths, worker IDs, or runtime values.

## 7. ID Stability

The following invariants are frozen:

- a canonical Product identity must retain one stable `canonical_product_id`;
- repeated observations of the same governed Product must not create a new
  identity because capture metadata changed;
- platform-specific IDs never become canonical IDs;
- replay order and worker/runtime metadata never define Product identity;
- observations from multiple platforms may converge only through the governed
  Product identity boundary.

The mechanism that guarantees stability is the owner-defined governed identity
key and its assigned canonical ID authority.

## 8. Identity Versus Revision

These concepts remain distinct:

```text
canonical_product_id != catalog revision != observation_id
```

Evidence updates, descriptive changes, lifecycle changes, and capture changes
must not be assumed to change Product identity. The repository does not define
which attribute changes constitute a new identity versus a revision.

For the MVP, identity is distinct from revision metadata. A change in
descriptive, lifecycle, or provenance fields does not by itself redefine the
governed Product identity key; revision handling is deferred to the later
catalog persistence contract.

## 9. Replay Semantics

The following principles are frozen:

- replaying the same observation must not create a duplicate Product identity;
- observing the same governed Product at another capture time must not alter
  identity;
- observing the same governed Product on another platform may converge to the
  same canonical Product through Product Intelligence;
- artifact paths, worker metadata, and runtime ordering are excluded from
  identity.

Exact behavior when evidence is ambiguous, conflicting, or associated with a
changed catalog revision remains deferred to the later governance and
persistence contracts.

## 10. Cross-Platform Semantics

Platform A and Platform B identifiers remain source identities. They may refer
to one canonical Product only after a governed Product identity decision.

No cross-platform matching algorithm is defined by this contract.

## 11. Provenance

Every Product identity decision must be explainable through the existing chain:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform and platform identifiers;
- platform listing identity.

The Evidence Registry remains the provenance authority. No second evidence
mechanism is introduced.

## 12. Explicit Non-Goals

This contract does not implement or authorize:

- Product creation;
- canonical Product ID generation;
- Product approval or pending state;
- persistence or catalog revisions;
- Variant identity or Variant IDs;
- listing association;
- snapshot construction;
- candidate generation or matching;
- changes to ingestion or evidence registries.

## Approved MVP Decisions

- Product identity uses an owner-defined governed identity key over explicitly
  selected normalized attributes.
- Name-only inference and platform-ID inference are prohibited.
- `canonical_product_id` is assigned manually or by an external governed
  authority and remains stable for the governed identity.

## 13. Remaining Open Decisions

The following MVP decisions are approved. Deferred extensions are:

1. Detailed identity-change versus revision semantics.
2. Conflict handling beyond fail-closed unresolved identity.
3. Stability mechanics across catalog revisions.

These decisions must be resolved without moving canonical identity into
ingestion or substituting platform identities.
