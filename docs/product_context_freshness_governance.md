# Product Context Freshness Governance

## Purpose

Variant Matching must know when an upstream product context is current enough to use, stale but still usable, stale and unsafe, or outright invalid.
Freshness is governed by lineage and catalog state, not by time alone.
`freshness_classification_contract.md` defines how the states are assigned.
`freshness_lineage_model.md` defines the lineage inputs that make those states computable.

## Ownership

- Product Intelligence / assertion lineage owns freshness state production.
- Variant Matching consumes freshness state and does not recompute it.
- Review may override or correct freshness classifications later, but not during matching.

## Freshness States

### `fresh`

Meaning:

- The product context is the current authoritative context for the listing class being evaluated.
- No superseding catalog assertion invalidates it.

Matcher behavior:

- Fully usable.

### `stale-compatible`

Meaning:

- The context has been superseded or aged, but the upstream revision is still compatible with the current listing evidence.
- Examples include catalog renames, presentation changes, or benign lifecycle movement that does not change pack identity.

Matcher behavior:

- Usable as supporting context.
- May support `mapped`, `ambiguous`, or `unresolved`.
- Must not be treated as evidence of contradiction by itself.

### `stale-unresolved`

Meaning:

- The context is not current enough to support a definitive variant decision, but it does not directly contradict the evidence.
- It may be too broad, too old, or too weakly linked to the current listing to resolve exact variant identity.

Matcher behavior:

- Variant Matching must return `unresolved` unless another independently valid evidence source resolves the case.

### `stale-conflicting`

Meaning:

- The context points to a superseding or incompatible product state that contradicts the listing evidence.
- The contradiction is about product-context validity, not candidate count.

Matcher behavior:

- Variant Matching must return `conflicting`.

### `invalid`

Meaning:

- The context cannot be trusted because it is malformed, missing required lineage, or internally inconsistent.

Matcher behavior:

- Usually `unresolved`.
- May become `conflicting` only if the invalidity itself is a direct contradiction with trusted evidence.

### `missing`

Meaning:

- No product context is available.

Matcher behavior:

- `unresolved` unless the evidence bundle itself is conflicting.

## What Makes Context Stale

Staleness is caused by lineage changes, not by a clock.

Examples:

- a product was renamed but remains the same exact variant
- a product family was split into distinct products
- a product family was merged into a broader canonical entry
- the packaging revision changed
- the formulation or size changed
- the item became discontinued but remains historically relevant
- a newer assertion superseded the older context

## When Stale Context Remains Usable

Stale context remains usable when:

- the pack identity implied by the stale context still matches the listing evidence
- the stale context does not contradict the listing evidence
- the stale context still anchors the candidate pool to the right product family or variant family

## When Stale Context Becomes Unresolved

Stale context becomes `unresolved` when:

- it is too broad to separate candidates
- it is older than the current evidence lineage but not contradictory
- it cannot safely support exact variant identity
- it lacks the lineage detail needed to decide pack identity

## When Stale Context Becomes Conflicting

Stale context becomes `conflicting` when:

- the evidence bundle proves a different pack identity
- the stale context asserts a superseded packaging state that cannot coexist with the current listing evidence
- the stale context is incompatible with the known canonical product state for that evidence

## Decision Matrix

| Context state | Listing evidence relationship | Matcher result |
| --- | --- | --- |
| fresh | compatible | usable |
| fresh | contradictory | conflicting |
| stale-compatible | compatible | usable |
| stale-compatible | insufficient | unresolved or mapped depending on other evidence |
| stale-unresolved | non-contradictory | unresolved |
| stale-conflicting | contradictory | conflicting |
| invalid | non-contradictory | unresolved |
| invalid | contradictory | conflicting |
| missing | any non-contradictory case | unresolved |

## Cross-Domain Examples

### FMCG

- `Amul Taaza 1 L` context renamed from an older catalog title but pack identity unchanged -> `stale-compatible`
- `Amul Taaza 1 L` context points to `500 ml` while listing shows `1 L` -> `stale-conflicting`

### Electronics

- `AA battery pack of 4` context remains usable after title revision -> `stale-compatible`
- `battery pack of 4` context superseded by `battery pack of 2` while listing shows `pack of 4` -> `stale-conflicting`

### Packaging Revision

- `soap 200 g` packaging refreshed from old label artwork but quantity and pack identity unchanged -> `stale-compatible`
- `soap 200 g` context superseded by `soap 150 g` while listing shows `200 g` -> `stale-conflicting`

### Discontinued Variants

- a discontinued variant may remain usable historically if the listing evidence still points to that exact variant family and no contradiction exists
- once the current evidence proves a different pack identity, the old context becomes `stale-conflicting`

## Key Principle

Freshness is a governed validity property of product context.
Variant Matching consumes that property; it does not infer it from age or recency.
