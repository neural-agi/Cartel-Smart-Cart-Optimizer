# Product Intelligence Implementation Plan

## Purpose

This plan translates the approved product-intelligence architecture into implementation order. It stays within the existing design boundary established in:

- `docs/research_analysis.md`
- `docs/canonical_product_schema.md`
- `docs/product_intelligence_design.md`
- `docs/product_intelligence_pipeline.md`
- `docs/product_intelligence_components.md`
- `docs/product_matching_architecture.md`

It does not introduce new components or new matching behavior.

## Implementation Order

### 1. Evidence Package

Implement `backend/app/product_intelligence/evidence/` first.

Why first:

- every downstream stage depends on durable evidence references
- the architecture requires provenance to survive matching and review
- the storage model is content-addressed and append-only at the record level, so identical registration payloads should reuse the same durable record instead of creating redundant duplicates

Dependencies unlocked:

- candidate generation inputs
- match request envelopes
- review case bundles

### 2. Candidate Generation Package

Implement `backend/app/product_intelligence/candidate_generation/` second.

Why second:

- the approved pipeline requires bounded candidates before any match decision
- candidate contracts shape the inputs to product and variant matching

Dependencies unlocked:

- product matching requests
- variant matching requests
- review case payloads

### 3. Matching Package

Implement `backend/app/product_intelligence/matching/` third.

Why third:

- the architecture splits product and variant matching into separate decisions
- matching is the first place where canonical assertions become possible

Dependencies unlocked:

- review triggering
- assertion update requests
- mapping state transitions

### 4. Review Package

Implement `backend/app/product_intelligence/review/` fourth.

Why fourth:

- the approved architecture treats unresolved and ambiguous outcomes as first-class
- review cases need candidate, evidence, and match context already defined

Dependencies unlocked:

- human review workflow contracts
- auditable decision outcomes

### 5. Assertion Package

Implement `backend/app/product_intelligence/assertions/` last among the new packages.

Why last:

- assertions should only consume approved match or review outcomes
- this package must not define any matching behavior itself

Dependencies unlocked:

- canonical update orchestration
- versioned assertion handoff
- future persistence integration

## Dependency Graph

```text
evidence
  -> candidate_generation
    -> matching
      -> review
        -> assertions
```

Supporting flow:

```text
models
  -> evidence / candidate_generation / matching / review / assertions
```

## Future Milestones

### Milestone 1: Package-Level Interfaces

Create and stabilize the abstract contracts and request/response models.

Outcome:

- implementation boundaries are explicit
- future services can be added without redesigning the package layout

### Milestone 2: Internal Orchestrators

Add concrete orchestrator classes that wire the interfaces together.

Outcome:

- the pipeline can be executed without embedding logic in API handlers or storage layers

### Milestone 3: Persistence Adapters

Add storage adapters for evidence, match outcomes, review cases, and assertions.

Outcome:

- the system can retain history and replay decisions

### Milestone 4: Platform-Specific Implementations

Implement concrete adapters for Blinkit first, then additional platforms.

Outcome:

- the package contracts remain stable while platform-specific behavior evolves

### Milestone 5: Review and Reprocessing Tools

Add review tooling and controlled reprocessing over retained evidence.

Outcome:

- ambiguous or corrected cases can be revisited without changing the core contracts

## Uncertainty Notes

The approved documentation defines the architectural split clearly, but it does not prescribe exact class names, method names, or whether future concrete implementations will be synchronous or asynchronous internally. This plan therefore keeps the interfaces minimal and defers behavioral detail to later implementation phases.
