# Variant Support Signal Matrix

Status: frozen

This document freezes exact-support derivation at the signal level for candidate evaluation.
It is the signal-layer companion to:

- `variant_candidate_evaluation_contract_v2.md`
- `variant_candidate_evaluation_classification_freeze.md`

## 1. Purpose

Exact support is derived only from governed signals that directly substantiate a candidate variant.
This document defines which signals may contribute to exact support and how they are interpreted.

## 2. Signal Classes

Only the following signal classes are permitted for exact-support derivation:

### 2.1 Direct pack evidence

Pack evidence normalized upstream from governed quantity text.

Examples:

- exact pack count
- exact quantity unit
- exact quantity magnitude
- exact composite pack structure when explicitly represented

### 2.2 Direct product-context evidence

Governed product context that identifies the candidate family without ambiguity.

Examples:

- exact product reference
- valid product lineage reference
- governed product identity state that is not ambiguous or conflicting

### 2.3 Direct listing evidence

Evidence observed on the listing itself that exactly matches the candidate without inference.

Examples:

- exact listing title token alignment
- exact listing quantity alignment
- exact listing pack alignment

## 3. Exact-Support Derivation Rules

Exact support is present only when all required signals align without contradiction.

### ES-01 Direct pack match

The candidate's governed pack identity must match direct pack evidence.

### ES-02 Direct product-context match

The candidate's governed product context must be valid and compatible.

### ES-03 No direct contradiction

No signal may directly contradict the candidate.

### ES-04 No inferential dependency

Exact support may not depend on:

- absence of better candidates
- candidate pool completeness
- heuristics
- fuzzy similarity
- confidence scores
- embedding similarity
- ML output

### ES-05 No normalization invention

Exact support may not invent pack meaning, unit meaning, or product identity.
It may only consume already governed normalization output.

## 4. Support Matrix

| Direct pack evidence | Direct product-context evidence | Direct listing evidence | Exact support |
| --- | --- | --- | --- |
| present and matching | present and valid | present and matching | exact |
| present and matching | present and valid | absent | exact only if direct listing evidence is not required by the upstream contract |
| present and matching | ambiguous | present and matching | not exact |
| present and matching | conflicting | present and matching | not exact |
| present and conflicting | any | any | not exact |
| absent | any | any | not exact |
| present but approximate | any | any | not exact |
| present and matching | invalid | any | not exact |

## 5. Signal Priority Order

Signals are evaluated in the following fixed order:

1. direct contradiction checks
2. direct pack evidence
3. direct product-context evidence
4. direct listing evidence
5. exact-support assignment

Later signals may not override earlier contradiction.

## 6. Allowed Exact-Support Inputs

The following are allowed inputs to exact-support derivation:

- `VariantMatchRequest`
- `VariantGovernanceContext`
- normalized pack evidence from governance
- governed product context
- governed candidate identity

## 7. Disallowed Exact-Support Inputs

The following must never be used to derive exact support:

- candidate generation score
- candidate pool size
- number of eliminated candidates
- absence of alternatives
- freshness score
- coverage score
- review outcome
- persistence metadata
- runtime ordering artifacts not governed by the contract
- heuristic similarity

## 8. Determinism Requirements

Given identical governed inputs and identical candidate identity, two implementations must assign the same exact-support classification.

Exact support must be:

- reproducible
- replayable
- order-independent except for canonical candidate ordering
- non-probabilistic

## 9. Contract Boundary

This document freezes signal-level derivation only.
It does not authorize selection.
It does not define survivor selection.
It does not define ambiguity.
It does not define rejection.

Those behaviors remain governed exclusively by the candidate-evaluation contract and outcome governance documents.

