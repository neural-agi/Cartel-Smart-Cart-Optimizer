# Product Intelligence Candidate Generation

## Purpose

Candidate generation is the first recall-oriented step in Cartel's product-intelligence pipeline. Its job is to produce a bounded set of plausible canonical `Product` and `ProductVariant` candidates from platform evidence before any matching or review decision is made.

This layer is deterministic and intentionally conservative. It does not establish identity, score confidence, normalize attributes, or decide mapping. It only expands the search space for downstream matching.

## Architectural Position

The candidate generator sits between evidence preparation and product matching.

It consumes:

- `PlatformListing`
- `ListingObservation`
- evidence references
- a canonical catalog snapshot supplied by the service

It produces:

- candidate products
- candidate variants
- rationale fragments for downstream matching

## Evidence Used

The implemented service uses only the approved light-weight signals:

- brand token overlap
- product family token overlap
- category overlap
- quantity hints

No fuzzy matching library, embeddings, ML model, or LLM is used.

## Strategy

Candidate generation is recall-first.

That means:

- keep plausible candidates even when evidence is weak
- prefer a broader candidate pool over a narrow one
- do not prune aggressively at this stage
- leave final correctness to product and variant matching

The generator uses deterministic tokenization and overlap counts to rank candidates. The ranking is not a confidence score and does not decide identity. It only orders the candidate pool so downstream matchers can inspect the most plausible options first.

## Service Behavior

The concrete service is in-memory and catalog-driven:

- it receives a catalog snapshot at construction time
- it reads the incoming listing evidence
- it tokenizes brand, family, category, and quantity hints
- it calculates deterministic overlap signals
- it returns ordered candidate pools plus rationale

This keeps the implementation aligned with the approved architecture while remaining easy to rewire into a later persistence-backed catalog source.

## Rationale Structure

The response includes human-readable rationale that records:

- platform
- raw title
- candidate pool size
- quantity hints, when present
- the fact that ranking favors recall over precision
- one concise signal summary per ranked candidate, limited to the top entries

This rationale is meant for downstream matching, review, and audit tooling.

## Demo Usage

A small script at `scripts/demo_candidate_generation.py` demonstrates the service against mock canonical products and platform listings.

## Future Integration Points

This layer is deliberately narrow so it can later be extended without redesign:

- catalog retrieval can move from in-memory snapshots to a registry or repository
- ranking can be refined with additional deterministic signals
- matching can consume the returned candidate pool without changing the service contract
- review can display the generated rationale as part of an audit bundle

## Uncertainty Notes

The approved architecture defines candidate generation as recall-oriented and evidence-driven, but it does not prescribe a universal catalog source. This implementation therefore treats the canonical catalog as an injected snapshot. That keeps the service deterministic and avoids introducing persistence concerns into the candidate generation boundary.
