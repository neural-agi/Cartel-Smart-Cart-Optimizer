# Freshness Lineage Model

## Purpose

Freshness classification needs a governed lineage model.
This document defines the lineage structure that makes freshness computable.

## Owner

- **Lineage construction owner:** Assertion / context lineage service

## Definition Of Lineage

Lineage is the ordered revision history for a canonical product context.
It records how one authoritative context replaces, supersedes, renames, splits, merges, or retires another.

Lineage is not freshness.
Freshness is computed from lineage.

## Participating Entities

The lineage model may include revision records for:

- canonical product context
- canonical product revision
- product variant revision
- assertion revision
- retired context record

## Revision Relationships

### Revision

A revision is a new record that updates the authoritative view of a context.

### Supersession

Supersession is the explicit relationship that says one revision replaces another as the authoritative context for a scope.

### Parentage

Parentage links a revision to the record it evolved from.

## Allowed Revision Types

- rename
- packaging revision
- pack-size revision
- formulation revision
- category migration
- split
- merge
- discontinuation
- supersession

## Minimum Lineage Representation

Freshness cannot be computed unless the lineage record contains:

- `lineage_root_id`
- `revision_id`
- `revision_type`
- `parent_revision_id` or `supersedes_revision_id`
- `scope_descriptor`
- `evidence_references`
- `source_artifact_references`
- `authoritative_status`
- `revision_timestamp` or equivalent ordered revision marker

## Validation Rules

1. Every revision must belong to exactly one lineage root.
2. Every revision must have a stable revision id.
3. Every revision must have an evidence reference.
4. Every revision must have a parent or supersedes link, except the root.
5. The lineage graph must not contain cycles.
6. The authoritative head for a scope must be identifiable.
7. Two active heads for the same exact scope invalidate the lineage for freshness computation.
8. A split or merge must be explicitly marked; it may not be implied.

## Supersession Rules

- A superseding revision replaces the prior authoritative revision for its scope.
- A retired revision remains historically visible.
- A retired revision may still be used as stale-compatible evidence if the freshness classifier allows it.
- A retired revision may not silently become current again without a new revision record.

## Revisions And Evidence

Each revision must cite the evidence that caused it:

- raw listing evidence
- source artifact reference
- parser version
- capture context reference
- review or assertion reference when present

## Examples

1. `Amul Taaza 1 L` renamed from an older title but same pack -> rename revision.
2. `Amul Taaza 1 L` replaced by `Amul Taaza 1.5 L` -> pack-size revision and supersession.
3. `Bread` split into `white bread` and `whole wheat bread` -> split revision.
4. `Pack of 6` merged into `combo pack` with explicit branch metadata -> merge revision.
5. Discontinued variant retained for audit history -> retired revision.

## Determinism Note

Two engineers must be able to reconstruct the same lineage graph from the same revision records.
If they cannot, the lineage model is incomplete.

Lineage construction never depends on freshness classification.
