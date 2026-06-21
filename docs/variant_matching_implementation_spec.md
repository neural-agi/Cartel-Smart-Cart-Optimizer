# Cartel Variant Matching Implementation Specification

This document translates `docs/variant_matching_architecture.md` into implementation guidance.
It does not add architecture, algorithms, or new concepts.

## 1. Exact Request Contract

Use the existing `VariantMatchRequest` contract from `backend/app/product_intelligence/matching/types.py`.

### Fields

- `platform_listing: PlatformListing`
- `listing_observation: ListingObservation`
- `evidence_references: list[EvidenceReference]`
- `product: Product | None`
- `variant_candidates: list[ProductVariant]`

### Required Interpretation

- `platform_listing` and `listing_observation` are the primary evidence inputs.
- `evidence_references` carries provenance into the matcher.
- `product` is the upstream product context. Variant matching depends on it, but the request may still be constructed with `None` when upstream product matching has not yet produced a usable context.
- `variant_candidates` is the bounded candidate pool from candidate generation.

### Product Context Handling

The matcher must treat `product` as a validated upstream context, not as a hint.

- Missing product context -> `unresolved`
- Invalid product context -> `unresolved` unless the context itself conflicts with the evidence, in which case `conflicting`
- Conflicting product context -> `conflicting`
- Stale product context -> governed by `product_context_freshness_governance.md`, `freshness_classification_contract.md`, and `freshness_lineage_model.md`; usable only if the freshness state is `fresh` or `stale-compatible`, otherwise `unresolved` for `stale-unresolved` or `conflicting` for `stale-conflicting`
- Multiple plausible product contexts upstream -> `unresolved`; product-family ambiguity belongs to Product Matching

The matcher must not infer freshness from timestamps, and it must not reinterpret product-family ambiguity as a variant decision.

### Request Requirements

- Preserve raw evidence references unchanged.
- Preserve parser/version/provenance references unchanged.
- Do not infer pack truth from price, offer, or availability.
- Do not add variant-specific fields to the request contract.

## 2. Exact Response Contract

Use the existing `VariantMatchResponse` contract from `backend/app/product_intelligence/matching/types.py`.

### Fields

- `outcome: MatchOutcome`
- `selected_variant: ProductVariant | None`
- `rationale: list[str]`

### Required Interpretation

- `outcome` is one of: `mapped`, `unresolved`, `ambiguous`, `conflicting`, `rejected`.
- `selected_variant` is set only when `outcome == mapped`.
- `rationale` must explain the decision deterministically.

### Response Requirements

- Always return a response object.
- Never mutate the request objects.
- Never return a hidden confidence score.
- Never use the response to rewrite evidence.

## 3. Deterministic Signals

Variant matching may use only pack-relevant signals defined by the architecture.

### Allowed Signals

- product context from upstream product matching
- raw quantity text
- pack kind
- consumer unit count
- content per consumer unit
- total declared content, only as supporting evidence
- packaging form when materially relevant
- combo / assortment component structure
- variant-level identity attributes
- provenance-backed historical variant evidence

### Explicitly Disallowed Signals

- displayed price
- reference price / MRP-like display
- offer text
- discount labels
- membership price presentation
- availability state
- `ADD` / UI controls
- search rank
- session state
- delivery location
- checkout outcomes

## 4. Signal Priority Order

Use the following precedence order when evaluating a candidate variant.

1. Product context
2. Explicit pack kind
3. Explicit consumer unit count
4. Explicit content per consumer unit
5. Explicit total declared content, only if it does not erase pack semantics
6. Packaging form when materially relevant
7. Combo / assortment component structure
8. Variant-level identity attributes
9. Historical evidence with compatible provenance
10. Contradictions

### Priority Rules

- Exact pack evidence outranks inferred pack evidence.
- Explicit count outranks implied count.
- Pack structure outranks total content when the two conflict.
- Combo or assortment evidence outranks scalar quantity simplification.
- Contradiction blocks acceptance even if other signals are strong.

## 5. Conflict Rules

Return `conflicting` only when the evidence bundle or product context is internally incompatible.

### Conflict Conditions

- raw title and quantity text disagree materially
- quantity field and candidate pack configuration disagree materially
- combo evidence is being collapsed into a single-unit interpretation
- multipack evidence is being flattened into a single-unit interpretation
- trusted prior evidence conflicts with current pack evidence
- product context is incompatible with the listing evidence

### Not A Conflict

A bad or incomplete candidate pool is not a conflict.

Candidate contradiction is normal and must not produce `conflicting` by itself.
It only removes candidates from consideration.

### Conflict Handling

- preserve all evidence references
- keep the contradiction visible in rationale
- do not silently choose the more convenient candidate

## 6. Rejection Rules

Return `rejected` only when the evidence explicitly disproves every candidate in the request and the candidate pool is declared `representative` under `candidate_pool_coverage_governance.md` and validated under `coverage_validation_contract.md`.

### Rejection Conditions

- candidate pack size does not match explicit quantity evidence
- candidate pack kind does not match explicit pack evidence
- candidate requires a single-unit interpretation that the evidence does not support
- the candidate pool is `unknown`, `partial`, or `invalid`
- candidate requires a combo interpretation that the evidence does not support
- candidate is contradicted by stronger pack evidence
- all candidates are explicitly ruled out by pack evidence
- the candidate pool is not obviously incomplete

### Rejection Scope

- Rejection is a request-level outcome.
- Candidate-specific reasoning still appears in rationale.
- If any candidate remains viable, use `mapped`, `ambiguous`, or `unresolved` instead.
- If every candidate is disproved but candidate coverage is incomplete or suspect, use `unresolved`.

## 7. Ambiguity Rules

Return `ambiguous` when more than one candidate remains materially plausible.

### Ambiguity Conditions

- multiple variants match the same pack evidence equally well
- quantity is sufficient to narrow the pack family but not the exact variant
- packaging form is missing but materially distinguishes candidate variants
- pack evidence is partial but not contradictory
- product context is plausible but does not separate tied candidates

### Ambiguity Handling

- keep all tied candidates visible
- do not break ties by incidental ordering
- do not promote a tied candidate to mapped status

## 8. Outcome Decision Tree

Use this decision flow in order.

1. If evidence contains material contradictions about pack identity or product context, return `conflicting`.
2. If there are no `variant_candidates`, return `unresolved`.
3. If `product` is missing or invalid and no candidate can be evaluated defensibly, return `unresolved`.
4. Rank candidates using the signal priority order.
5. If exactly one candidate remains viable and it meets the minimum pack evidence bar, return `mapped`.
6. If two or more candidates remain viable and materially tied, return `ambiguous`.
7. If zero candidates remain viable because candidate coverage is incomplete or suspect, return `unresolved`.
8. If zero candidates remain viable because the evidence explicitly disproves every candidate and the pool is `representative`, return `rejected`.

### Outcome Notes

- `mapped` means one exact pack configuration is justified.
- `ambiguous` means multiple exact pack configurations remain plausible.
- `unresolved` means no defensible variant mapping exists from the current evidence.
- `conflicting` means evidence itself is incompatible.
- `rejected` means the entire candidate set is ruled out by explicit contrary evidence.
- `unresolved` also covers candidate-set failure, where the pool is too narrow to conclude rejection.

## 9. Candidate Ranking Strategy

Rank candidates deterministically using the same precedence order above.

### Ranking Inputs

- pack kind match
- unit count match
- content-per-unit match
- packaging form match
- component structure match
- variant-level identity attribute match
- historical evidence compatibility

### Ranking Rules

- Prefer exact pack match over partial pack match.
- Prefer explicit evidence over inferred evidence.
- Prefer candidates whose pack structure matches the listing without reinterpretation.
- Prefer candidates whose component structure matches exactly for combos and assortments.
- If candidates remain tied after all allowed signals, keep the result ambiguous.

### Ranking Constraint

Ranking may order candidates for explanation and review, but it must not introduce a hidden scoring model.

## 10. Required Rationale Fields

The rationale is a list of strings. It must be deterministic and sufficient for review.

### Required Contents

- request context summary
- whether product context was present
- candidate count
- signal comparison summary
- selected candidate identifier when mapped
- why the selected candidate won
- why tied candidates remained tied
- why a candidate was rejected
- why evidence was conflicting, if applicable
- why the result was unresolved, if applicable

### Rationale Rules

- Include missing evidence explicitly.
- Include contradictory evidence explicitly.
- Keep rationale stable for the same inputs.
- Do not depend on nondeterministic iteration order.
- Do not use pricing, offers, or availability in rationale as decision reasons.

## 11. Variant Evidence And Product Reasoning

Variant evidence can be exposed to review and future matching systems as supporting context when product identity remains uncertain.

Implementation should preserve that context in rationale and evidence references.

This does not change the primary boundary:

- variant matching depends on product matching
- variant evidence may support later product reasoning
- variant evidence does not replace product matching

## 12. Implementation Boundary

Do not add:

- normalization logic
- fuzzy matching
- embeddings
- ML ranking
- confidence scoring
- APIs
- repositories
- databases
- review execution
- assertions

The matcher should remain a deterministic consumer of request evidence and candidate variants.
