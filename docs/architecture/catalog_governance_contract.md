# Catalog Governance Contract

**Status:** Slice 7D contract freeze with explicit open decisions  
**Scope:** Canonical Product/ProductVariant governance and unresolved identity

## 1. Scope

This contract defines governance boundaries after Product and Variant identity
resolution:

```text
identity resolution
  -> catalog governance
  -> approved catalog entities
  -> CandidateCatalogSnapshot
```

It does not implement lifecycle state, entity creation, persistence, review
queues, or snapshot construction.

## 2. Ownership

Canonical catalog governance belongs to the Product Intelligence catalog
boundary. Ingestion owns normalized observations and provenance, not catalog
entities.

No executable catalog-governance service or entity-creation authority exists in
the repository.

## 3. Unresolved Product Identity

The system must distinguish an observation whose Product identity is resolved
from one whose Product identity is not resolved.

An unresolved observation must not silently become a canonical Product and must
not be admitted to an approved candidate snapshot.

The behavior after unresolved identity is **OPEN**:

```text
OPEN — reject, defer, create a pending entity, human resolution, or external resolution
```

No pending Product may be assumed merely because the Product model contains
status fields.

## 4. Unresolved Variant Identity

A Variant depends on a governed parent Product. If Product identity is
unresolved, Variant identity is unresolved.

If Product identity is resolved but Variant identity is not, the observation
must not silently attach to an arbitrary Variant or create a canonical Variant.

The handling of unresolved Variant identity is **OPEN**:

```text
OPEN — reject, defer, pending variant, human resolution, or external resolution
```

## 5. Entity Creation Authority

Product Intelligence owns the authority boundary for canonical entity
governance, but the concrete creator is **OPEN**.

The repository contains no ProductRepository, VariantRegistry, CatalogService,
catalog database, external catalog adapter, or deterministic canonical-ID
authority. No implementation may create entities or generate IDs until this
authority is frozen.

Identity resolution, entity creation, and approval remain separate decisions.

## 6. Approval Authority

The existing `ReviewQueueManager` is Product Intelligence match review. It is
used for unresolved, ambiguous, conflicting, or rejected matching outcomes and
does not establish canonical catalog approval.

No canonical catalog approval authority or workflow exists. Therefore:

```text
OPEN — catalog approval authority and approval workflow
```

Match review must not be treated as catalog approval without a later contract.

## 7. Candidate Snapshot Eligibility

The following rule is frozen from the canonical catalog boundary amendment:

Only approved, internally consistent canonical Products and ProductVariants
may enter `CandidateCatalogSnapshot`.

Pending, unresolved, or rejected entities are not eligible. Deprecated or
superseded eligibility is **OPEN** because the repository does not define their
snapshot visibility semantics.

The snapshot remains a derived view and is never the source of truth.

## 8. Product and Variant Governance Dependency

Governance follows the parent relationship:

```text
Product governance
  -> Variant governance
```

A Variant cannot be approved or admitted to an approved snapshot without a
valid governed parent Product.

Whether a Variant may exist in a pending state beneath an approved Product,
whether Product rejection cascades to Variants, and whether Variant approval is
independent are **OPEN**.

## 9. Revision Semantics

Existing `catalog_revision`, lifecycle, evidence, and effective-period fields
are metadata available to a future governance boundary. The repository does
not define whether a change is a revision, correction, or new canonical
identity.

Therefore:

```text
OPEN — revision versus identity-change semantics
```

No implementation may infer that every attribute change creates a new entity
or that every change is merely a revision.

## 10. Correction and Deprecation

The Product and ProductVariant models expose lifecycle values, but no governed
transition rules, correction workflow, historical-retention rule, or
deprecation policy are implemented.

The following are **OPEN**:

- correction authority;
- revision history and supersession;
- deprecation eligibility;
- historical visibility;
- deletion policy;
- effect of deprecation on platform listings and snapshots.

No deletion or mutation behavior is authorized by this contract.

## 11. Replay and Idempotency

The following boundary rules are frozen:

- Replaying the same observation must not create duplicate canonical entities.
- Runtime metadata, capture timestamps, worker IDs, and storage paths must not
  change canonical identity.
- Repeated evidence must remain provenance, not become a new entity.
- A platform-specific identifier must never become a canonical Product or
  Variant ID.

The exact replay result for pending, corrected, deprecated, or revised catalog
entities is **OPEN**.

## 12. Provenance

Every governance decision must remain explainable through:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers;
- platform listing identity;
- canonical Product identity when resolved;
- canonical Variant identity when resolved.

The existing Evidence Registry remains the provenance authority. No second
evidence system is introduced.

## 13. ReviewQueueManager Relationship

The existing `ReviewQueueManager` is classified as:

**B. Product Intelligence match/review only.**

It manages review cases produced by matching outcomes and can support review
resolution for those cases. It is not a canonical catalog approval service,
does not assign canonical IDs, and does not define entity lifecycle.

## 14. Pending Entity Policy

Pending entity behavior is **OPEN**.

The presence of identity-status fields does not authorize creating:

- `Product(status=PENDING)`;
- `ProductVariant(status=PENDING)`;
- canonical IDs for unresolved observations.

Visibility, persistence, approval, and promotion of pending entities require a
later governance contract.

## 15. External Resolution Boundary

No external catalog authority exists in the repository. External resolution is
not implemented or assumed.

If later selected, it requires a separate contract defining authority,
identity mapping, evidence, failure behavior, replay, and approval. Until then,
external resolution remains:

```text
OPEN — external catalog resolution is not available
```

## 16. Explicit Non-Goals

This contract does not implement or authorize:

- Product or ProductVariant creation;
- canonical ID generation;
- catalog persistence;
- approval or review workflow;
- pending entity lifecycle;
- listing association;
- CandidateCatalogSnapshot population;
- candidate generation or matching;
- changes to ingestion or evidence registries.

## 17. Remaining Open Decisions

Before catalog governance implementation, the following must be frozen:

1. Entity creation authority.
2. Unresolved Product behavior.
3. Unresolved Variant behavior.
4. Catalog approval authority and workflow.
5. Pending entity policy and snapshot visibility.
6. Product-to-Variant approval dependency and cascading behavior.
7. Revision, correction, supersession, and deprecation semantics.
8. Persistence and historical retention.
9. Replay behavior for governed lifecycle states.
10. External resolution, if permitted.

These decisions must preserve Product/Variant ownership and must not move
catalog governance into ingestion.
