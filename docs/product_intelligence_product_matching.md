# Product Intelligence Product Matching

## Purpose

Product matching is the deterministic step that decides whether a platform listing belongs to a canonical `Product`.

It sits after candidate generation and before any variant reasoning, review workflow, or canonical assertion update. The goal is not to score similarity in the abstract. The goal is to make an evidence-backed product-family decision that can be explained, audited, or refused.

## Inputs

The matcher consumes:

- `PlatformListing`
- `ListingObservation`
- evidence references
- candidate `Product` objects produced by candidate generation

## Outputs

The matcher returns:

- `ProductMatchResponse`
- `MatchOutcome`
- selected `Product` when a mapping is justified
- rationale explaining the decision

## Decision Policy

The implementation is deterministic and evidence-driven.

It uses only approved signals from the architecture:

- brand agreement
- product-family agreement
- category agreement
- identity-attribute agreement
- historical evidence when supplied through the candidate set and evidence references

It does not use:

- embeddings
- fuzzy string libraries
- LLMs
- vector search
- hidden confidence scoring formulas

## Outcome Handling

The matcher supports the approved outcome set:

- `mapped`
- `ambiguous`
- `unresolved`
- `conflicting`
- `rejected`

### Mapped

Returned when a single product candidate has the strongest deterministic support and no conflicting evidence blocks the decision.

### Ambiguous

Returned when multiple product candidates remain materially tied under the same deterministic signals.

### Unresolved

Returned when no candidate has enough product-family support to justify a mapping.

### Conflicting

Returned when listing evidence and candidate evidence point toward incompatible identities.

### Rejected

Returned when the best candidate still fails the minimum evidence bar for product-family membership.

## Rationale Format

The rationale is intentionally explicit. It records:

- the request context
- the selected candidate, when one is chosen
- overlap counts for each deterministic signal
- why the decision mapped, tied, conflicted, or was rejected

This makes the matcher suitable for downstream review and assertion layers without hiding why a decision was made.

## Architectural Boundary

This implementation does not perform:

- variant matching
- review workflow execution
- assertion updates

Those remain separate components in the approved architecture.

## Demo

A small demonstration script is provided at `scripts/demo_product_matching.py`.

