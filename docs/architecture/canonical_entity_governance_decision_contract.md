# Canonical Entity Governance Decision Contract

**Status:** Slice 7I-C contract with approved MVP decisions and deferred extensions  
**Scope:** Identity outcome to canonical entity creation and governance

## 1. Scope

This contract covers:

```text
identity outcome
  -> canonical entity creation decision
  -> governance/approval eligibility
```

It consumes Product and Variant identity outcomes from their dedicated
contracts. It does not redefine identity equality or ID strategy, and does not
implement creation, approval, persistence, listing association, or snapshots.

## 2. Identity-to-Creation Boundary

Identity resolution and entity creation are distinct:

```text
RESOLVED identity
  -> creation may be considered

UNRESOLVED or CONFLICTING identity
  -> creation is forbidden
```

An observation is not a canonical entity. A resolved identity alone does not
authorize creation; creation authority and governance preconditions remain
separate.

## 3. Product Creation Preconditions

The existing Product model requires canonical ID, brand, product type, display
name, category, identity attributes, lifecycle, revision, and provenance data.

The following constraints are frozen:

- a NormalizedObservation is not sufficient authorization by itself;
- Product identity must be `RESOLVED` under the Product identity contract;
- unresolved or conflicting identity cannot create a Product;
- required Product fields must be valid before creation.

The exact evidence threshold, creator, approval prerequisite, and handling of
missing descriptive fields are:

```text
OPEN — Product creation preconditions.
```

## 4. Variant Creation Preconditions

The existing ProductVariant model requires a canonical Variant ID, parent
Product ID, variant identity attributes, pack configuration, lifecycle,
revision, and provenance.

The following constraints are frozen:

- Variant identity must be `RESOLVED` under the Variant identity contract;
- a governed parent Product must exist conceptually;
- unresolved or conflicting Variant identity cannot create a Variant;
- Variant creation cannot bypass Product identity resolution;
- a Variant cannot belong to multiple Products.

Whether the parent must be approved before Variant creation, and the exact
Variant evidence threshold, are:

```text
OPEN — ProductVariant creation preconditions.
```

## 5. Creation Authority

No production Product or ProductVariant creation authority exists. Existing
constructors are test fixtures, not catalog services.

```text
OPEN — canonical entity creation authority.
```

No repository, registry, external source, or service is authorized by this
contract to create entities.

## 6. ID Assignment Relationship

Identity resolution, ID assignment, creation, and approval remain separate:

```text
identity resolution
  -> ID assignment authority
  -> entity creation
  -> approval
```

This contract does not choose or change Product/Variant ID authority. The
dedicated identity decision contracts leave those policies open.

## 7. Approval Authority

The repository has no canonical catalog approval authority.

`ReviewQueueManager` is Product Intelligence match review. It is not catalog
approval, entity creation, or canonical ID assignment. `AssertionManager`
applies Product Intelligence assertions and is not catalog approval.

```text
OPEN — canonical catalog approval authority and workflow.
```

## 8. Creation Versus Approval Ordering

The conceptual distinction is frozen:

```text
identity resolution
  -> creation
  -> approval
  -> snapshot eligibility
```

The repository does not establish whether creation requires prior approval,
whether an unapproved entity may exist, or who transitions it to approved:

```text
OPEN — creation/approval ordering.
```

Creation must not be treated as approval by default.

## 9. Unresolved Identity Behavior

For unresolved or conflicting Product identity:

- no Product may be created;
- no placeholder ID may be assigned;
- no arbitrary existing Product may be selected.

For resolved Product with unresolved or conflicting Variant identity:

- no Variant may be created;
- no placeholder ID may be assigned;
- no arbitrary existing Variant may be selected.

Whether the observation is rejected, deferred, reviewed, externally resolved,
or represented by another governed result is:

```text
OPEN — unresolved identity governance action.
```

## 10. Pending Entity Policy

No pending Product or Variant policy is established. Status fields in the
models do not authorize creating pending entities.

```text
OPEN — pending entity creation, persistence, visibility, and promotion.
```

Pending entities must not be assumed visible to matching or eligible for
CandidateCatalogSnapshot.

## 11. Snapshot Eligibility Prerequisite

The existing catalog contracts establish only this prerequisite:

```text
approved + internally consistent canonical entity
  -> eligible for CandidateCatalogSnapshot consideration
```

The precise meaning of approved and internally consistent remains open. This
contract does not redefine snapshot construction or ordering.

## 12. Product/Variant Governance Dependency

Governance follows the parent relationship:

```text
Product governance
  -> Variant governance
```

A Variant cannot be governed independently of its parent Product identity.

Whether a Variant may be pending under an approved Product, whether Product
rejection/deprecation cascades, and whether Variant approval is independent
are:

```text
OPEN — Product/Variant governance dependency details.
```

## 13. Replay and Idempotency

The following principles are frozen:

- the same resolved Product identity must not create duplicate canonical
  Products;
- the same resolved Variant identity must not create duplicate canonical
  Variants;
- replaying an observation must not create a new entity solely because runtime
  metadata changed;
- repeated evidence remains provenance;
- platform and observation IDs cannot become canonical IDs.

Exact return/no-op/conflict semantics for repeated creation requests remain:

```text
OPEN — entity creation replay/idempotency behavior.
```

## 14. Conflict Behavior

The repository does not define handling for:

- one identity assigned multiple canonical IDs;
- one ID receiving conflicting identity data;
- conflicting Product identity evidence;
- conflicting Variant evidence;
- one Variant identity under multiple Products.

```text
OPEN — governance conflict policy.
```

No implementation may silently overwrite, merge, or reparent entities.

## 15. Provenance

Creation and governance decisions must preserve or reference:

- `observation_id`;
- `RawArtifactReference`;
- `EvidenceReference`;
- `ObservationFieldReference`;
- parser version;
- normalization version;
- platform identifiers;
- platform listing identity;
- canonical Product ID when assigned;
- canonical Variant ID when assigned.

The Evidence Registry remains the provenance authority. No second evidence
system is introduced.

## 16. Explicit Non-Goals

This contract does not implement or authorize:

- Product or ProductVariant creation;
- ID generation;
- approval service or review workflow;
- pending entities;
- persistence;
- catalog revisions;
- listing association;
- CandidateCatalogSnapshot construction;
- candidate generation or matching;
- changes to ingestion or evidence registries.

## Approved MVP Decisions

- The MVP uses a manually curated, pre-approved catalog.
- Unresolved or conflicting identity remains uncreated and unassociated;
  manual resolution is required.
- Automatic creation, pending entities, and automated approval workflows are
  outside the MVP.
- Only canonically identified, approved, active, parent-consistent entities
  are eligible for a future snapshot.
- Duplicate or conflicting canonical state fails closed.

## 17. Remaining Open Decisions

Before entity governance implementation, the following require product/business
decisions:

1. Product creation authority and evidence threshold.
2. Variant creation authority and evidence threshold.
3. Parent approval prerequisite for Variant creation.
4. Canonical approval authority and lifecycle.
5. Creation/approval ordering.
6. Unresolved identity action.
7. Pending entity policy.
8. Product/Variant cascading governance behavior.
9. Creation replay/idempotency results.
10. Conflict resolution policy.

No implementation may resolve these decisions implicitly.
