# Product Intelligence Component Architecture

## Purpose

This document defines the software components responsible for transforming raw grocery observations into canonical product intelligence.

It does not define algorithms, storage technology, APIs, background jobs, or matching logic. It defines responsibilities, ownership boundaries, interactions, and failure containment.

The approved pipeline remains:

Raw Listing
-> PlatformListing
-> ListingObservation
-> Candidate Generation
-> Product Match Evaluation
-> Variant Match Evaluation
-> Canonical Assertion Update
-> Review

The purpose of this architecture is to assign each of those stages to explicit software components with minimal overlap.

## 1. Component Inventory

The product-intelligence layer should be organized around these major components:

1. `Listing Intake Coordinator`
2. `Listing Identity Resolver`
3. `Observation Assembler`
4. `Evidence Registry`
5. `Candidate Generator`
6. `Product Matcher`
7. `Variant Matcher`
8. `Assertion Manager`
9. `Review Queue Manager`
10. `Decision Audit Recorder`

These names are intentionally descriptive. Future implementation can rename them, but the ownership boundaries should remain.

### Why This Split

- intake and identity construction are different from matching
- evidence ownership must not be hidden inside matchers
- product matching and variant matching are separate questions
- review and audit must remain independent from automatic decision-making
- canonical assertion updates must be isolated from candidate generation and matching

## 2. Responsibility Matrix

### Listing Intake Coordinator

Responsibility:

- accept raw extracted listing records from the extraction layer
- validate that required observation inputs are present
- prepare handoff payloads for listing identity and observation assembly

Inputs:

- raw extracted product data
- extraction metadata
- source artifact metadata
- capture context metadata

Outputs:

- intake payload for `Listing Identity Resolver`
- intake payload for `Observation Assembler`
- evidence registration request for `Evidence Registry`

May access:

- raw extracted listing fields
- parser version
- source artifact identifiers
- capture timestamp and context

Must not own:

- canonical product identity
- candidate sets
- match decisions
- review state

### Listing Identity Resolver

Responsibility:

- determine or construct the platform-native `PlatformListing`
- keep repeated observations of the same platform item tied to one listing identity

Inputs:

- platform
- platform listing identifier when available
- listing URL
- raw title
- raw quantity text
- raw category text

Outputs:

- `PlatformListing`
- listing identity status for downstream use

May access:

- platform-native identifiers
- raw listing presentation fields
- prior platform listing identities

Must not own:

- prices
- offers
- availability observations
- canonical product or variant assertions

### Observation Assembler

Responsibility:

- construct append-only `ListingObservation` records
- attach volatile commercial facts to a `PlatformListing`

Inputs:

- listing identity from `Listing Identity Resolver`
- displayed price
- reference price text
- offer text
- availability signal
- parser version
- capture timestamp
- source artifact reference
- capture context reference

Outputs:

- `ListingObservation`

May access:

- raw observation fields
- capture and provenance metadata

Must not own:

- canonical product identity
- product variant identity
- candidate selection
- review decisions

### Evidence Registry

Responsibility:

- maintain durable evidence references used throughout the product-intelligence layer
- ensure canonical assertions and decisions point back to stable evidence identifiers

Inputs:

- source artifact metadata
- extraction metadata
- listing identity references
- observation references
- decision evidence references

Outputs:

- stable evidence references
- evidence bundles for matchers and review

May access:

- raw evidence identifiers
- provenance metadata
- decision evidence linkage

Must not own:

- matching outcomes
- business decisions
- canonical product content

### Candidate Generator

Responsibility:

- generate plausible canonical `Product` and `ProductVariant` candidates from listing evidence
- provide a bounded search space for match evaluation

Inputs:

- `PlatformListing`
- `ListingObservation` evidence
- raw title
- raw quantity text
- raw category text
- existing canonical catalog metadata

Outputs:

- product candidate set
- variant candidate set
- candidate rationale fragments

May access:

- canonical brand references
- canonical categories
- canonical product and variant attributes
- historical mapping signals

Must not own:

- final mapping status
- review queue state
- canonical record revisioning

### Product Matcher

Responsibility:

- evaluate whether the listing belongs to a canonical `Product`
- preserve ambiguity when product identity is uncertain

Inputs:

- `PlatformListing`
- `ListingObservation`
- evidence bundle
- product candidate set

Outputs:

- product match decision
- unresolved or ambiguous state
- rationale for the decision
- review trigger when needed

May access:

- canonical product attributes
- candidate rationale
- historical product-level mapping evidence

Must not own:

- variant decisions
- canonical assertion updates
- review finalization

### Variant Matcher

Responsibility:

- evaluate whether the listing belongs to a canonical `ProductVariant`
- preserve pack semantics and quantity ambiguity

Inputs:

- accepted or provisional product match
- variant candidate set
- pack evidence
- quantity evidence
- listing and observation evidence

Outputs:

- variant match decision
- unresolved or ambiguous state
- rationale for the decision
- review trigger when needed

May access:

- canonical variant pack configuration
- variant identity attributes
- historical variant-level mapping evidence

Must not own:

- product-level identity resolution rules
- canonical record revisioning
- review finalization

### Assertion Manager

Responsibility:

- convert accepted decisions into revisioned canonical assertions
- update mapping state without overwriting raw listing or observation history

Inputs:

- product match decision
- variant match decision
- evidence references
- review outcome when applicable

Outputs:

- canonical assertion update request
- mapping state update
- revised `Product` or `ProductVariant` references when needed

May access:

- canonical domain models
- prior assertion history
- evidence references
- approved review outcomes

Must not own:

- candidate generation
- automatic match scoring policy
- review queue lifecycle

### Review Queue Manager

Responsibility:

- manage ambiguous or conflicting cases that require human review
- enforce a visible review lifecycle instead of silent fallback behavior

Inputs:

- review triggers from matchers
- evidence bundle
- candidate sets
- decision rationale

Outputs:

- queued review case
- review status transitions
- resolved review outcome

May access:

- unresolved or conflicting decision records
- evidence references
- candidate explanations

Must not own:

- raw observation creation
- candidate generation rules
- canonical product definitions outside approved review outcomes

### Decision Audit Recorder

Responsibility:

- preserve the full audit trail for automated and reviewed decisions
- ensure every mapping outcome is explainable later

Inputs:

- candidate sets
- matcher outputs
- review actions
- assertion updates
- evidence references

Outputs:

- decision audit record
- rationale history
- reviewer history

May access:

- all non-destructive decision metadata
- evidence references
- review lifecycle state

Must not own:

- catalog identity fields
- listing observations
- candidate generation logic

## 3. Component Interaction Flow

The interaction flow should be:

1. `Listing Intake Coordinator` receives raw extracted listing data.
2. `Evidence Registry` creates or confirms durable evidence references for source artifacts, extraction metadata, and capture context.
3. `Listing Identity Resolver` creates or reuses the `PlatformListing`.
4. `Observation Assembler` creates the `ListingObservation`.
5. `Candidate Generator` receives the listing, observation, and evidence bundle and returns product and variant candidates.
6. `Product Matcher` evaluates product identity first.
7. `Variant Matcher` runs only after product-level evaluation has produced an accepted or provisional product context.
8. `Decision Audit Recorder` records candidate sets, matcher outcomes, rationale, and triggers.
9. `Review Queue Manager` receives ambiguous or conflicting cases.
10. `Assertion Manager` applies only accepted automated decisions or approved review outcomes to canonical assertions.
11. `Decision Audit Recorder` records the final assertion update and outcome.

### Why Product Match Must Precede Variant Match

Variant matching depends on product-family context. Without that context, the system can overfit to pack size and miss formulation differences, or collapse distinct products that happen to share similar quantities.

### Why Assertion Update Must Be Last

Canonical identity is the most durable layer. It should be updated only after:

- listing identity is stable
- observation evidence is preserved
- candidate search is complete
- ambiguity has either been resolved automatically or routed to review

## 4. Ownership Boundaries

### Component Boundaries That Must Stay Hard

- `PlatformListing` ownership belongs with `Listing Identity Resolver`
- `ListingObservation` ownership belongs with `Observation Assembler`
- evidence reference ownership belongs with `Evidence Registry`
- candidate ownership belongs with `Candidate Generator`
- product decision ownership belongs with `Product Matcher`
- variant decision ownership belongs with `Variant Matcher`
- review lifecycle ownership belongs with `Review Queue Manager`
- canonical assertion ownership belongs with `Assertion Manager`
- audit trail ownership belongs with `Decision Audit Recorder`

### Boundaries That Must Not Blur

- matchers must not silently rewrite evidence
- assertion updates must not bypass audit recording
- review must not mutate raw listing evidence
- evidence registration must not embed matching assumptions
- candidate generation must not self-approve final matches

This separation is what keeps the system explainable.

## 5. Evidence Ownership

Evidence is a first-class concern, not a byproduct.

### Evidence Registry Owns

- durable evidence references
- linkage between source artifacts and downstream decision consumers
- provenance bundle assembly for match and review stages

### Decision Audit Recorder Owns

- candidate history
- decision rationale
- automated decision traces
- reviewer actions and final outcomes

### Matchers Own Only Temporary Decision Outputs

The matchers may produce rationale, ambiguity markers, and candidate preferences, but they must not become the durable owners of provenance. Durable provenance belongs outside them.

### Evidence That Must Survive All Stages

- raw title
- raw quantity text
- raw category text
- platform and platform listing identifier
- listing URL when available
- displayed price
- reference price text
- offer text
- availability signal
- parser version
- source artifact reference
- capture timestamp
- capture context reference
- candidate sets considered
- decision rationale
- review outcome when applicable

## 6. Review Architecture

Review must be treated as part of the architecture, not as a manual patch around weak automation.

### Review Queue Ownership

`Review Queue Manager` owns:

- review case creation
- case status transitions
- reviewer assignment model in the future
- case resolution state

### Review Triggers

Review should be triggered when:

- product match is ambiguous
- variant match is ambiguous
- quantity or pack structure is incomplete
- candidate evidence conflicts
- historical mappings conflict with new evidence
- parser output appears suspicious relative to prior evidence

### Review Lifecycle

The review lifecycle should support at least:

- `queued`
- `in_review`
- `approved`
- `rejected`
- `needs_more_evidence`
- `superseded`

### Review Outcomes

Review can result in:

- accept product and variant mapping
- accept product but leave variant unresolved
- reject proposed mapping
- create or request a new canonical product
- create or request a new canonical variant
- mark the case for reprocessing once better evidence exists

### Explainability Requirement

Every review case should display:

- original raw listing evidence
- observation evidence
- candidate options
- automated rationale
- prior mapping history when relevant

The reviewer should never be asked to trust a black box output without evidence context.

## 7. Failure Isolation

The architecture should degrade safely when parts of the product-intelligence pipeline fail.

### Bad Extraction

Containment:

- `Listing Intake Coordinator` should reject incomplete records or mark them as intake failures
- no canonical assertion should be attempted
- raw evidence should still remain referenceable for reprocessing

### Ambiguous Match

Containment:

- `Product Matcher` or `Variant Matcher` emits unresolved or ambiguous outcomes
- `Review Queue Manager` receives the case
- `Assertion Manager` does nothing until the case is resolved

### Conflicting Evidence

Containment:

- conflicting evidence is preserved, not collapsed
- `Decision Audit Recorder` stores the conflict context
- `Review Queue Manager` handles the resolution path

### Parser Regression

Containment:

- observations continue to retain parser version and source artifact references
- suspect cases can be isolated by parser version
- canonical assertions remain revisioned instead of being silently rewritten

### Partial Pipeline Failure

Containment:

- listing identity and observation capture may succeed even if candidate generation or matching fails
- evidence remains reusable when the failed component is fixed later

This is the correct failure mode: preserve evidence, stop unsafe assertion updates, and allow reprocessing.

## 8. Future Extension Compatibility

### Normalization

Normalization can later be introduced between `Observation Assembler` and `Candidate Generator`, or as a supporting dependency of `Candidate Generator`, without changing the rest of the ownership model.

### Matching Improvements

Improved heuristics or ML-based reranking can later be introduced inside `Candidate Generator`, `Product Matcher`, or `Variant Matcher` without changing evidence ownership, review, or assertion boundaries.

### Confidence Scoring

Confidence scoring can later enrich matcher outputs, but it should remain advisory to `Assertion Manager` and `Review Queue Manager`, not a replacement for auditability.

### Multi-Platform Expansion

The architecture already separates platform-native listing identity and observation handling from canonical catalog assertions. That allows new platforms to enter through the same intake, listing, and observation boundaries.

### Cost Intelligence

Cost intelligence can later consume:

- canonical `ProductVariant` references
- `PlatformListing`
- `ListingObservation`

without needing to know how candidate generation or matching was implemented.

### Cart Optimization

Cart optimization can later depend on stable canonical mapping states and observation history without becoming coupled to review workflows or evidence registration internals.

## 9. Recommended Packaging Direction

This document does not prescribe implementation files, but the component boundaries imply three internal subdomains inside product intelligence:

- observation-facing components
- decision-facing components
- audit and review components

That split is preferable to one large orchestrator module because:

- observation handling and canonical assertion handling evolve at different rates
- matching logic will grow faster than listing/observation modeling
- review and audit need to remain independently understandable

## Bottom Line

Cartel's product-intelligence architecture should be built around ten explicit components:

- `Listing Intake Coordinator`
- `Listing Identity Resolver`
- `Observation Assembler`
- `Evidence Registry`
- `Candidate Generator`
- `Product Matcher`
- `Variant Matcher`
- `Assertion Manager`
- `Review Queue Manager`
- `Decision Audit Recorder`

This split keeps raw evidence, platform-native identity, canonical identity, decision-making, review, and audit trails separate. That is the critical architectural property. It allows Cartel to improve matching over time, expand to multiple platforms, and add cost and optimization layers later without losing provenance or making canonical assertions opaque.
