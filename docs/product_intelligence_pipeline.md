# Product Intelligence Pipeline

## Purpose

This document defines how Cartel should transform raw extracted grocery listings into canonical product intelligence while preserving evidence, uncertainty, and provenance.

The pipeline is intentionally staged. Cartel should not jump directly from raw listing text to a canonical product match, because product identity, pack structure, and listing observations are different kinds of facts.

Current domain targets:

- `Product`
- `ProductVariant`
- `PlatformListing`
- `ListingObservation`

The pipeline below explains how raw extracted data should eventually produce and update those entities.

## 1. End-To-End Workflow

### Starting Point: Raw Extracted Product

Example raw extracted record:

- title: `Amul Taaza Toned Milk`
- quantity: `500 ml`
- displayed price: `₹31`
- reference price: maybe present as another visual price
- offer text: maybe present
- availability signal: maybe `ADD`

This record is not yet canonical product intelligence. It is a platform-shaped observation.

### Stage A: Raw Listing Intake

Purpose:

- accept raw extraction output without interpretation beyond source bookkeeping
- preserve the extracted card-level fields exactly as observed

Inputs:

- raw extracted product dictionaries
- extraction metadata
- source artifact metadata

Outputs:

- candidate `PlatformListing` input
- candidate `ListingObservation` input
- immutable evidence bundle

Why this stage exists:

- raw extracted data is the first stable handoff from scraping to product intelligence
- it separates raw evidence from later interpretation

### Stage B: Listing Identity Construction

Purpose:

- decide whether the extracted record represents a distinct platform-native listing identity
- group repeated observations of the same platform item under one `PlatformListing`

Inputs:

- raw title
- raw quantity text
- raw category text
- platform
- listing URL or platform listing identifier if available

Outputs:

- `PlatformListing`

Why this stage exists:

- the same listing may appear multiple times over time with different prices or offers
- platform-native identity must be stable before canonical matching occurs

### Stage C: Observation Capture

Purpose:

- store the volatile commercial state attached to a `PlatformListing`
- keep each render or capture as an append-only observation

Inputs:

- raw displayed price
- raw reference price text
- offer text
- availability signal
- capture timestamp
- parser version
- source artifact reference
- capture context reference

Outputs:

- `ListingObservation`

Why this stage exists:

- pricing and availability are observations, not product identity
- every render can be historically useful even when later interpretations change

### Stage D: Candidate Generation

Purpose:

- generate plausible canonical product and variant candidates for a listing
- avoid committing to a match too early

Inputs:

- `PlatformListing`
- listing observation evidence
- raw title tokens
- raw quantity text
- raw category text
- platform-derived hints

Outputs:

- candidate `Product` set
- candidate `ProductVariant` set
- candidate explanations or reason fragments

Why this stage exists:

- exact canonical identity is rarely obvious from a single platform card
- the system needs a bounded candidate set before any match decision

### Stage E: Product Match Evaluation

Purpose:

- decide whether the listing belongs to a canonical `Product`
- preserve uncertainty when the answer is not reliable

Inputs:

- candidate products
- raw listing evidence
- structured attributes already known about candidate products

Outputs:

- accepted product link, or unresolved/ambiguous state
- review flag when confidence is insufficient
- match evidence and reasoning artifacts

Why this stage exists:

- product identity is broader than pack size, but still must be explainable
- the system needs to separate "likely same family" from "certain canonical identity"

### Stage F: Variant Match Evaluation

Purpose:

- decide whether the listing belongs to a specific `ProductVariant`
- preserve pack structure, quantity semantics, and ambiguity

Inputs:

- accepted or provisional `Product`
- candidate variants
- quantity evidence
- packaging evidence
- pack composition evidence

Outputs:

- accepted variant link, or unresolved/ambiguous state
- variant review flag when needed
- variant match evidence and reasoning artifacts

Why this stage exists:

- `500 ml`, `1 L`, `Pack of 2`, and `2 x 750 ml` are not interchangeable by default
- a listing can share a product family while still being a different purchasable unit

### Stage G: Canonical Assertion Update

Purpose:

- persist the canonical product-intelligence view
- version the decision rather than overwrite history

Inputs:

- accepted product link or review outcome
- accepted variant link or review outcome
- evidence references
- decision metadata

Outputs:

- updated `Product`
- updated `ProductVariant`
- traceable mapping state

Why this stage exists:

- canonical identity must remain revisioned and auditable
- later matching improvements must be able to revise earlier decisions safely

## 2. Candidate Generation Design

Candidate generation should be broad, cheap, and conservative. It should prefer recall over precision at this stage, because the later match stages and review workflow are responsible for correctness.

### Candidate Sources

Candidates should be generated from:

- brand tokens
- product family tokens
- category hints
- identity-critical attributes
- quantity and pack signals
- known aliases and prior mapping history

### Candidate Types

#### Exact Candidates

When the raw title or structured extraction strongly resembles a known canonical record, the listing should surface an exact candidate.

Examples:

- same brand
- same product family
- same pack configuration
- same variant-defining attributes

#### Brand Candidates

If the brand is strong but the rest of the identity is noisy, the system should generate all canonical products or variants under that brand within the observed category.

This is useful when:

- titles are inconsistent
- categories are noisy
- quantity is embedded in the title

#### Attribute Candidates

If a listing has strong identity attributes such as `toned`, `full cream`, `whole wheat`, `magic masala`, or `keratin smooth`, the candidate pool should include canonical entities with the same attribute pattern even when the title wording varies.

#### Category Candidates

Category is a weak but useful broad filter. It should reduce search space, not define identity.

Examples:

- milk-like candidates for milk listings
- bread-like candidates for bread listings
- shampoo-like candidates for shampoo listings

### Candidate Ranking Inputs

Candidate ranking should eventually consider:

- exact token overlap
- brand agreement
- category agreement
- attribute agreement
- pack structure agreement
- historical mapping consistency

This document does not define scoring logic. It only defines what evidence should be available to future scoring.

## 3. Product Matching Stage

The product matching stage decides whether a listing belongs to a `Product`.

### Matching Question

The question here is not "does this exact pack match?". The question is:

> Is this listing the same stable product family or formulation?

### Inputs

- raw title evidence
- brand evidence
- category evidence
- known product identity attributes
- historical mapping evidence
- parser/extraction provenance

### Outputs

- `mapped`
- `unresolved`
- `ambiguous`
- `rejected`

### Decision Principles

- prefer explainability over aggressive automation
- preserve uncertainty rather than forcing a guess
- keep candidate evidence attached to the decision
- avoid overwriting the raw listing if a later correction occurs

### Likely Failure Modes

- collapsing distinct formulations because they share a brand
- treating marketing copy as identity
- over-trusting short or noisy titles
- merging product families that differ only subtly but materially

### False Positive Risks

- `Toned Milk` mapped as `Full Cream Milk`
- `Whole Wheat Bread` mapped as plain white bread
- `Magic Masala` chips mapped as a generic salted variant

### False Negative Risks

- genuine brand or spelling variation causing missed links
- titles with truncated identity tokens
- listings where pack wording obscures the underlying product family

## 4. Variant Matching Stage

The variant matching stage decides whether a listing belongs to a `ProductVariant`.

### Matching Question

The question here is:

> Is this the same consumer-distinct purchasable configuration?

### Variant Identity Signals

Relevant signals include:

- quantity text
- pack kind
- consumer unit count
- packaging form
- multipack wording
- combo composition
- variant-defining attributes tied to the pack

### Examples

- `500 ml` should not be treated as the same variant as `1 L`
- `Pack of 2` should not be flattened into a single-unit variant
- `2 x 750 ml` should preserve multipack semantics even if the total content is known

### Inputs

- candidate product link
- pack configuration evidence
- raw quantity text
- title-derived quantity hints
- component descriptions for combos

### Outputs

- matched variant
- ambiguous variant
- unresolved variant
- review request

### Likely Ambiguities

- quantity in title versus quantity field
- `1 L` versus `1000 ml`
- `2 x 500 ml` versus `1 L`
- combo packs that look similar to multipacks
- packs where the quantity is absent or partially hidden

### Variant Matching Rule of Thumb

Variant matching should be stricter than product matching. A product family can be correct while the pack is still wrong. The pipeline must allow that state.

## 5. Human Review Strategy

Future matching will not be perfect. The pipeline should therefore route uncertain cases into review rather than silently deciding.

### Review Triggers

Review should be triggered when:

- the product match is ambiguous
- the variant match is ambiguous
- pack structure cannot be confidently interpreted
- candidate evidence conflicts
- parser output appears inconsistent with source card shape
- historical mappings disagree with a new capture

### Confidence Thresholds

This document does not define numeric thresholds. It defines the policy:

- high-confidence exact matches can auto-accept
- low-confidence or conflicting matches should not auto-accept
- ambiguous matches should remain unresolved until reviewed

### Review Workflow

1. capture raw evidence
2. generate candidates
3. rank candidates
4. flag uncertain matches
5. present evidence and reasoning for human review
6. store reviewer decision with revision metadata
7. preserve the previous state as history

### Auditability Requirements

The review path must always preserve:

- original raw title
- raw quantity text
- raw category text
- parser version
- capture timestamp
- source artifact reference
- candidate set considered
- decision outcome
- reviewer action or system action

The goal is explainability, not just correctness.

## 6. Evidence Preservation Strategy

Evidence should survive every stage.

### Evidence That Must Never Be Discarded

- raw title
- raw quantity text
- raw category text
- visible displayed price
- reference price text
- offer text
- availability signal
- source artifact reference
- capture timestamp
- parser version
- capture context reference
- platform identifier
- platform listing identifier when available

### Evidence That Should Be Preserved Through Matching

- extraction provenance
- observation provenance
- candidate generation rationale
- match decision rationale
- review action and reviewer identity when available

### Evidence Boundary

Canonical records should reference evidence; they should not replace it.

This matters because:

- parsing rules may improve later
- a listing may be reinterpreted later
- a match decision may be corrected later
- different capture contexts may expose different facts

## 7. Future Compatibility

### Normalization

The pipeline creates a place for normalization without forcing it early.

Normalization can later:

- standardize quantity expressions
- standardize brand aliases
- standardize attribute names
- preserve raw forms alongside derived forms

### Matching

The pipeline is explicitly candidate-driven and reviewable, so later matching can improve without changing the raw evidence model.

### Cross-Platform Comparison

By separating listing observations from canonical product identity, Cartel can later compare:

- like-for-like products
- like-for-like variants
- pack-equivalent but not identical alternatives

### Cost Intelligence

Cost intelligence needs a stable product and variant reference before it can interpret checkout cost, offers, or fee behavior.

This pipeline supplies that stable reference without mixing in pricing semantics too early.

### Cart Optimization

Optimization requires:

- canonical product and variant references
- platform listing links
- observation history
- uncertainty states

The pipeline keeps those ingredients separate so optimization can reason over them later.

## 8. Risks And Design Constraints

### Major Risks

- forcing a match too early
- collapsing pack structure into a scalar quantity
- treating observed price as product identity
- losing provenance during reinterpretation
- hiding uncertainty from operators

### Hard Constraints

- raw data remains evidence
- canonical identity is revisioned
- unresolved is a valid state
- matching and normalization remain separate concerns
- product family and variant are different questions

## Bottom Line

Raw extracted grocery listings should become canonical product intelligence through a staged process:

1. ingest raw extraction evidence
2. form or reuse a platform listing identity
3. capture append-only observations
4. generate candidates
5. evaluate product membership
6. evaluate variant membership
7. persist a revisioned canonical assertion
8. route uncertain cases to review

This is the minimum architecture needed to convert noisy retail evidence into a trustworthy product-intelligence foundation without losing provenance, pack semantics, or uncertainty.
