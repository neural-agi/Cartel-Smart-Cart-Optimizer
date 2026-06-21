# Variant Candidate Evaluation Classification Freeze

Status: frozen

This document freezes three remaining candidate-evaluation contracts before implementation:

1. Exact Support Classification Matrix
2. Direct Contradiction Classification Matrix
3. Canonical Candidate Ordering Contract

It is intended to remove any remaining interpretive freedom from candidate evaluation.

## 1. Exact Support Classification Matrix

### Purpose

Exact support determines whether a retained candidate may be selected as `selected_variant_id`.
Exact support is deterministic and binary at the candidate level.

### Exact support definition

A candidate is `exact` only when all of the following are true:

1. The candidate is not directly contradicted by governed inputs.
2. The candidate is supported by governed evidence that matches the candidate's governed pack identity.
3. The support is not merely inferential or approximate.
4. No other candidate has a stronger claim under the exact-support floor.

### Exact support matrix

| Candidate state | Product context | Coverage state | Freshness state | Result |
| --- | --- | --- | --- | --- |
| directly contradicted | any | any | any | not exact |
| not contradicted, direct governed pack evidence matches candidate exactly | valid or stale-compatible | representative or partial | fresh / stale-compatible | exact |
| not contradicted, direct governed pack evidence matches candidate exactly | valid or stale-compatible | invalid / unknown | fresh / stale-compatible | exact support may be computed, but selection is not authorized if upstream governance forbids it |
| not contradicted, support is only approximate, inferred, or partial | any | any | any | not exact |
| not contradicted, support relies on unresolved product identity | any | any | any | not exact |
| not contradicted, support relies on incompatible pack semantics | any | any | any | not exact |

### Exact support rule

Exact support is assigned only by direct, governed evidence matching the candidate identity.
It is never inferred from candidate generation, pool shape, or absence of alternatives.

### Exact support invariants

- exact support is candidate-specific
- exact support is deterministic
- exact support does not imply selection
- exact support does not override contradiction

## 2. Direct Contradiction Classification Matrix

### Purpose

Direct contradiction determines whether a candidate must be eliminated before any survivor selection.

### Direct contradiction definition

A candidate is directly contradicted when governed inputs establish that the candidate cannot be the listed variant.

Direct contradiction is stronger than partial support, stronger than ambiguity, and stronger than exact support.

### Direct contradiction matrix

| Evidence condition | Product context condition | Coverage condition | Result |
| --- | --- | --- | --- |
| candidate pack identity conflicts with governed pack evidence | any | any | contradicted |
| candidate quantity semantics conflict with governed normalized pack evidence | any | any | contradicted |
| candidate unit kind conflicts with governed normalized unit evidence | any | any | contradicted |
| candidate requires a product context that is invalid for the request | invalid or conflicting | any | contradicted only if the contradiction is explicit and governed |
| candidate is incompatible with a stale-conflicting freshness classification | any | any | contradicted |
| candidate lacks support | any | any | not contradicted |
| candidate is merely unproven | any | any | not contradicted |
| candidate pool is incomplete | any | any | not contradicted |

### Direct contradiction rule

Direct contradiction may only arise from evidence or governed context that positively rules the candidate out.
Lack of evidence is not contradiction.
Incomplete candidate coverage is not contradiction.
Candidate existence is not contradiction.

### Direct contradiction invariants

- contradiction is terminal for the candidate in the current evaluation run
- contradiction is deterministic
- contradiction does not require confidence scoring
- contradiction does not require heuristic inference

## 3. Canonical Candidate Ordering Contract

### Purpose

Canonical ordering ensures that every downstream serialization and audit artifact is replayable.

### Ordering source

The canonical order is the upstream governed candidate pool order after duplicate removal.

### Ordering rule

1. Receive candidate identifiers in governed pool order.
2. Remove duplicate candidate identifiers.
3. Preserve first occurrence.
4. Emit the resulting ordered list as `candidate_ids_considered`.

### Ordering invariants

- ordering is stable
- ordering is deterministic
- ordering is replayable
- ordering does not depend on runtime hash order
- ordering does not depend on set semantics
- ordering does not depend on candidate score

### Ordering scope

Canonical ordering applies to:

- `candidate_ids_considered`
- `viable_candidate_ids`
- `eliminated_candidate_ids`
- `ambiguous_candidate_ids`
- elimination record emission order

### Ordering exclusions

Canonical ordering does not depend on:

- quantity normalization
- freshness classification
- coverage qualification
- candidate confidence
- matching heuristics
- any external storage order

## 4. Contract Interaction

The three frozen contracts interact as follows:

1. Canonical candidate ordering establishes the deterministic evaluation sequence.
2. Direct contradiction classification runs against that order and removes eliminated candidates.
3. Exact support classification runs only on non-eliminated candidates.

If a candidate is directly contradicted, it cannot be exact.
If a candidate is exact, it is still not selected unless the full candidate-evaluation contract authorizes selection.

## 5. Determinism Clause

Given identical governed inputs and identical candidate pool order, two independent implementations must produce:

- identical `candidate_ids_considered`
- identical direct contradiction outcomes
- identical exact-support outcomes
- identical elimination order
- identical selection eligibility

No implementation may introduce a hidden tie-breaker or secondary ordering rule.

