# Cartel Variant Matching Architecture

## Purpose And Scope

This document defines how Cartel should decide whether a platform listing maps to a canonical `ProductVariant`.

It is a design review, not an implementation. It builds on the approved product-intelligence docs and on the current canonical schema and domain models:

- `docs/research_analysis.md`
- `docs/canonical_product_schema.md`
- `docs/product_intelligence_design.md`
- `docs/product_intelligence_pipeline.md`
- `docs/product_intelligence_components.md`
- `docs/product_matching_architecture.md`

The central rule is that variant matching answers a narrower question than product matching:

> Given an already plausible product family/formulation, does this listing represent the same consumer-distinct purchasable configuration?

Variant matching must preserve pack semantics, quantity semantics, and uncertainty. It must not flatten pack structure into a scalar quantity just because totals look equivalent.

The exact boundary between outcomes is defined in `docs/outcome_boundary_clarification.md`. This document describes the architecture; the boundary document defines the deterministic classification rules used by implementation.

---

## 1. Purpose Of Variant Matching

Variant matching exists to identify the exact purchasable configuration of a product once the product family/formulation is already known or plausibly known.

This layer is needed because listings that belong to the same `Product` can still be commercially distinct:

- `500 ml` vs `1 L`
- single unit vs `Pack of 2`
- single homogeneous pack vs combo pack
- `2 x 500 ml` vs `1 L`

Without variant matching, Cartel can know that two listings are about the same product family but still fail to know whether they are exact comparison targets. That would make price comparison, cart optimization, and offer interpretation unreliable.

Variant matching therefore:

- distinguishes exact pack configurations
- preserves multipack and combo semantics
- prevents false equivalence between packs with the same total content
- provides the exact canonical unit for future price comparison and cost reasoning

---

## 2. Inputs

Variant matching should consume only evidence that is relevant to pack identity and consumer-distinct configuration.

### Required Inputs

- `Product` context from product matching
- `PlatformListing`
- `ListingObservation`
- evidence bundle from the Evidence Registry
- candidate `ProductVariant` set from candidate generation

### Useful Evidence Inputs

- raw title
- raw quantity text
- raw category text
- listing URL when available
- platform listing identifier
- parser version
- capture timestamp
- source artifact reference
- capture context reference
- variant candidate pack configuration
- variant candidate identity attributes
- historical variant evidence, when exposed through the evidence bundle

### Input Boundaries

Variant matching should not infer pack truth from:

- displayed price
- reference price
- offer text
- availability state
- session state
- search rank

Those are observations or commerce signals, not pack identity evidence.

---

## 3. Outputs

Variant matching should return a structured decision object suitable for downstream review and assertion handling.

### Required Outputs

- `ProductVariantMatchResponse`
- `MatchOutcome`
- selected `ProductVariant` when mapping is justified
- rationale explaining the decision

### Recommended Decision Shape

The response should make explicit:

- the evaluated product context
- the candidate set considered
- the chosen candidate, if any
- the outcome state
- the evidence basis for the decision
- why a candidate was not accepted, if applicable

### Output States

The variant matcher must support:

- `mapped`
- `ambiguous`
- `unresolved`
- `conflicting`
- `rejected`

These states should be aligned with the existing product matching contract so review and assertions can treat them consistently.

---

## 4. Allowed Signals

Variant matching should use only signals that help determine the exact purchasable configuration.

### Allowed Signals

- quantity text
- pack kind
- consumer unit count
- per-unit content
- total declared content, only when it does not erase pack semantics
- packaging form when materially relevant
- combo or assortment component structure
- variant-level identity attributes when they distinguish sellable configurations
- product context from upstream product matching
- historical evidence when it is provenance-backed and still applicable

### Allowed Interpretation

Variant matching may use quantity evidence in structured form, but only as pack evidence, not as a generic size similarity hint.

Examples of allowed interpretation:

- `1 L` and `1000 ml` may be equivalent wording if pack semantics are clear
- `Pack of 2` is different from a single unit
- `2 x 500 ml` is not automatically the same as `1 L`
- combo composition must be preserved as a structure, not reduced to total content

### Pack Semantics Are First-Class

The matcher should treat these as structurally meaningful:

- single unit
- multipack
- combo
- assortment
- unknown pack structure

This is necessary because the pack structure can change price comparison meaning even when the underlying product is the same.

---

## 5. Disallowed Signals

Variant matching must not use signals that are commercially relevant but not identity-defining.

### Disallowed Signals

- displayed selling price
- reference price or MRP-like display
- discount labels
- offer text
- coupon text
- membership price presentation
- stock or availability state
- `ADD` or similar UI controls
- cart checkout outcome
- location-specific delivery charges
- payment method effects
- session-specific browsing artifacts

### Why These Are Disallowed

These fields vary across time, location, session, and eligibility. They do not define which consumer-distinct pack is being offered.

Using them in variant matching would create two risks:

1. false confidence from pricing/offer coincidence
2. hidden coupling between product identity and commercial context

Variant matching should remain about pack identity, not commercial attractiveness.

---

## 6. Decision Policy

Variant matching should be deterministic, explainable, and conservative.

### Core Policy

1. Prefer exact pack evidence over inferred pack evidence.
2. Prefer structured quantity interpretation over title-only hints.
3. Preserve multipack and combo semantics.
4. Refuse to collapse ambiguous pack structures into a single-unit variant.
5. Accept only when the evidence is sufficient to justify a specific canonical variant.

### Decision Order

A practical decision order is:

1. Verify that a plausible `Product` context exists.
2. Compare the listing's pack evidence against candidate variant pack configurations.
3. Check whether the listing and candidate agree on pack kind, count, and content semantics.
4. Check whether quantity wording resolves to the same pack configuration.
5. Check for contradictory pack evidence.
6. Decide among mapped, ambiguous, unresolved, conflicting, or rejected.

### Deterministic Rule Shape

The matcher should remain deterministic by using ordered comparison rules rather than opaque scoring:

- exact pack match outranks inferred pack match
- explicit pack count outranks implied count
- explicit homogeneous single-unit evidence outranks ambiguous total-content interpretation
- combo/component evidence outranks scalar quantity matching
- contradictory pack evidence blocks acceptance

This does not mean the matcher must be simplistic. It means the decision rationale must be reproducible.

---

## 7. Outcome Definitions

Variant matching should use the same outcome vocabulary as product matching, but with pack semantics as the deciding factor.

### `mapped`

Returned when a single `ProductVariant` is the best supported exact pack match and no conflicting pack evidence blocks acceptance.

Meaning:

- product context is sufficient
- pack structure is sufficiently explicit
- candidate variant and listing agree on consumer-distinct configuration

### `ambiguous`

Returned when more than one candidate variant remains materially plausible under the available pack evidence.

Meaning:

- the product is plausible
- pack evidence is insufficient to separate nearby variants
- the system should not guess

### `unresolved`

Returned when pack evidence is too weak to support any variant mapping.

Meaning:

- the product context may exist
- the listing does not establish a defensible exact pack
- the correct behavior is to preserve the evidence and wait for better input

### `conflicting`

Returned when pack evidence or trusted prior evidence points to incompatible variant identities.

Meaning:

- title and quantity disagree materially
- pack count disagrees with the candidate
- combo semantics conflict with a single-unit interpretation
- a trusted prior mapping is no longer consistent with the evidence

### `rejected`

Returned when the evidence explicitly disproves the entire candidate set while the evidence bundle itself remains internally consistent and the candidate pool is declared `representative` under `candidate_pool_coverage_governance.md`.

Meaning:

- every candidate in the request is explicitly ruled out
- rejection is a request-level outcome, not a per-candidate label
- if the candidate pool is plainly incomplete, the correct outcome is `unresolved` instead of `rejected`

---

## 8. Examples For Each Outcome

The examples below are illustrative, not implementation rules.

### Mapped

**Listing evidence**

- title: `Amul Taaza Toned Milk`
- quantity text: `1 L`
- category: `milk`

**Candidate variants**

- `Amul Taaza Toned Milk, 500 ml`
- `Amul Taaza Toned Milk, 1 L`

**Expected outcome**

- `mapped` to `Amul Taaza Toned Milk, 1 L`

**Why**

- product family is already plausible
- pack evidence explicitly matches the `1 L` variant
- there is no contradictory pack signal

### Ambiguous

**Listing evidence**

- title: `Amul Taaza Toned Milk`
- quantity text: `1 L`
- category: `milk`

**Candidate variants**

- `Amul Taaza Toned Milk, 1 L pouch`
- `Amul Taaza Toned Milk, 1 L carton`

**Expected outcome**

- `ambiguous`

**Why**

- the quantity is sufficient for a 1 L pack
- but packaging form is still materially different and not resolved
- the system should not guess pouch versus carton without evidence

### Unresolved

**Listing evidence**

- title: `Amul Taaza Toned Milk`
- quantity text: `null`
- category: `milk`

**Candidate variants**

- `Amul Taaza Toned Milk, 500 ml`
- `Amul Taaza Toned Milk, 1 L`

**Expected outcome**

- `unresolved`

**Why**

- the product family may be plausible
- but there is not enough pack evidence to select a specific variant
- if the candidate pool is plainly incomplete, the correct outcome is still `unresolved`, not `rejected`

### Conflicting

**Listing evidence**

- title: `Amul Taaza Toned Milk 1 L`
- quantity text: `500 ml`
- category: `milk`

**Candidate variants**

- `Amul Taaza Toned Milk, 500 ml`
- `Amul Taaza Toned Milk, 1 L`

**Expected outcome**

- `conflicting`

**Why**

- the title and quantity field disagree materially
- the evidence bundle contains incompatible pack facts
- the matcher should not silently choose the more convenient interpretation

### Rejected

**Listing evidence**

- title: `Amul Taaza Toned Milk`
- quantity text: `1 L`
- category: `milk`

**Candidate variants**

- `Amul Taaza Toned Milk, 500 ml`

**Expected outcome**

- `rejected` for the request, assuming the evaluated candidate pool is `representative`

**Why**

- the candidate is specifically incompatible with the observed pack size
- rejection here is the request-level outcome because the only supplied candidate is disproved

---

## 9. Deterministic Matching Strategy

Variant matching should be deterministic in the same way product matching is deterministic: same inputs, same decision, same rationale.

### Strategy Principles

- use explicit comparison rules
- preserve order of precedence
- separate exact evidence from inferred evidence
- do not let quantity totals erase pack structure
- do not use commercial signals as pack identity signals

### Recommended Comparison Order

1. Compare product context.
2. Compare pack kind.
3. Compare consumer unit count.
4. Compare content per consumer unit.
5. Compare total declared content only as supporting evidence.
6. Compare packaging form when material.
7. Compare component structure for combos and assortments.
8. Compare any variant-level identity attributes.
9. Detect contradictions and ties.

### Deterministic Tie Handling

If two candidates remain equally plausible after the allowed comparison order:

- return `ambiguous`
- keep both candidates in the response
- preserve the rationale for later review

The matcher should not resolve ties through hidden heuristics, incidental ordering, or price-based convenience.

---

## 10. How Variant Matching Differs From Product Matching

Product matching and variant matching are related but not interchangeable.

### Product Matching

Product matching answers:

> Is this the same stable product family or formulation?

It focuses on:

- brand
- product family
- category
- identity-critical formulation attributes

### Variant Matching

Variant matching answers:

> Is this the same consumer-distinct purchasable configuration?

It focuses on:

- pack kind
- pack count
- unit content
- packaging form
- combo composition

### Key Difference

Product matching can succeed even when variant matching fails.

Example:

- `Amul Taaza Toned Milk` may be a correct product match
- but `500 ml` versus `1 L` still requires a separate variant decision

This separation matters because:

- product-level identity is broader than pack-level identity
- variant-level identity is required for exact comparison and cart planning
- a correct product match should not be over-extended into a false variant match

### Important Edge Case

Variant evidence can sometimes help disambiguate product identity when product evidence alone is weak.

Example:

- `Amul Taaza Milk 500 ml` may point toward one product family
- `Amul Taaza Milk 1 L` may point toward a different product family when those sizes are not shared across catalog items

In cases like this, pack evidence is still handled as variant evidence first, but it may also be exposed to review and future matching systems as supporting context for product identity.

The boundary should remain:

- variant matching depends on product matching
- variant evidence may support product review or later product reasoning
- variant evidence does not replace product matching as the primary decision layer

---

## 11. Integration With Other Components

Variant matching should fit into the approved product-intelligence architecture without taking ownership of adjacent responsibilities.

### Evidence Registry

Variant matching consumes evidence bundles from the Evidence Registry.

It depends on:

- source artifact references
- parser version
- capture context reference
- capture timestamps
- durable provenance links

It must not own the registry or mutate evidence records.

### Candidate Generation

Candidate generation should produce the candidate variant pool.

Variant matching consumes that pool and decides among the candidates.

The boundary is:

- candidate generation widens recall
- variant matching narrows to one outcome or refuses to guess

### Product Matching

Product matching should happen before variant matching.

Variant matching depends on the product context because pack identity only makes sense once the product family/formulation is plausible.

Variant matching must not re-open product identity except to detect a contradiction severe enough to mark the case as conflicting.

### Review

Review should receive:

- ambiguous outcomes
- unresolved outcomes
- conflicting outcomes
- rejected candidates where human validation is needed

Review should see the pack evidence, not a hidden summary.

### Assertions

Assertions should only be updated after a variant decision is accepted or explicitly reviewed.

Variant matching should feed the assertion layer with:

- selected variant
- rationale
- evidence references
- outcome state

It must not directly rewrite canonical records.

---

## 12. Architectural Risks

Variant matching has several foreseeable risks that should shape later implementation.

### Risk 1: Flattening Pack Semantics

The biggest risk is treating `2 x 500 ml` and `1 L` as interchangeable because the totals look similar.

This would damage:

- exact price comparison
- offer interpretation
- cart optimization
- review trust

### Risk 2: Using Quantity As A Weak Proxy For Identity

Quantity helps distinguish variants, but it should not replace product identity.

If quantity is allowed to drive product identity, the architecture will start confusing pack size with product family.

### Risk 3: Over-reliance On Title Text

Retail titles are noisy. If variant matching depends too much on raw title text, the matcher will become brittle across platforms and parser versions.

### Risk 4: Packaging Ambiguity

Pouch, bottle, carton, sachet, jar, and combo semantics may be omitted or inconsistently presented.

If packaging form is treated as always mandatory, the system will produce too many false unresolved states.

If packaging form is ignored, the system will collapse materially different variants.

### Risk 5: Hidden Coupling To Commerce Signals

Price, offer, and availability are tempting fallback signals because they are visible.

They must remain outside variant identity or the system will create decisions that are unstable across time and location.

### Risk 6: Incomplete Candidate Coverage

If candidate generation misses the true variant, the matcher may look deterministic while actually operating on an incomplete search space.

This is why the candidate set and rationale must remain visible.

### Risk 7: Unclear Review Escalation

If the boundary between `ambiguous`, `unresolved`, and `conflicting` is not crisp, review will either be overused or underused.

The architecture should therefore keep these outcomes distinct and auditable.

---

## Bottom Line

Variant matching is the exact-pack decision layer.

It should:

1. consume an already plausible product context
2. use only pack-relevant evidence
3. preserve multipacks and combos as first-class structures
4. refuse to flatten uncertain quantity semantics
5. return one of `mapped`, `ambiguous`, `unresolved`, `conflicting`, or `rejected`
6. pass only accepted or reviewed outcomes into assertion updates

This keeps Cartel’s product-intelligence stack explainable and prevents the system from confusing a consumer product family with a consumer purchase configuration.
