# Variant Candidate Evaluation Contract v2

Status: revision

This document supersedes the retention and support ambiguity left open in `variant_candidate_evaluation_contract.md`.
It freezes the deterministic behavior of candidate evaluation before implementation.

## 1. Candidate Evaluation Boundary

### Inputs

The evaluator consumes only governed inputs:

- `VariantMatchRequest`
- `VariantGovernanceContext`
- canonical candidate pool supplied by upstream candidate generation

### Outputs

The evaluator returns a `CandidateEvaluationResult` containing:

- `candidate_ids_considered`
- `viable_candidate_ids`
- `eliminated_candidate_ids`
- `ambiguous_candidate_ids`
- `selected_variant_id`
- `all_candidates_disproved`
- `rationale`
- `rejection_rationale`

### Ownership

Candidate evaluation owns:

- deterministic candidate elimination
- deterministic candidate retention
- survivor selection when allowed by contract
- serialization of candidate-evaluation outcome state

Candidate evaluation does not own:

- coverage qualification
- coverage validation
- freshness classification
- lineage construction
- quantity normalization
- candidate generation
- product matching
- persistence
- audit storage

## 2. Candidate State Model

Only two candidate states exist at the evaluation layer:

### retained

A candidate is retained when:

- it is not eliminated by any firing rule
- it remains eligible for downstream survivor selection or ambiguity reporting

Retention is a logical state, not a separate persisted artifact.

### eliminated

A candidate is eliminated when:

- any deterministic elimination rule applies
- the candidate is removed from the viable set for the remainder of evaluation

Elimination is terminal for the current evaluation run.

## 3. Exact Minimum Support Matrix

### Support classes

Candidate support is classified deterministically into four classes:

- `exact`
- `partial`
- `none`
- `contradicted`

These are evaluation classifications only. They are not confidence scores.

### Support class meaning

- `exact`: the candidate is directly supported by governed evidence and is not contradicted
- `partial`: the candidate is plausibly supported by governed evidence, but the exact-support floor is not met
- `none`: the candidate is neither supported nor contradicted by governed evidence
- `contradicted`: the candidate is directly incompatible with governed evidence

### Minimum support floor

`selected_variant_id` requires the exact-support floor:

- at least one retained candidate with `exact` support
- no competing retained candidate with `exact` support
- no contradiction that invalidates the chosen candidate

Partial support is never sufficient to assign `selected_variant_id`.
None support is never sufficient to assign `selected_variant_id`.

### Support matrix

Within candidate evaluation, invalid coverage always yields `unresolved` unless a higher-priority upstream matcher stage has already produced `conflicting`.

| Remaining retained candidate distribution | Required coverage state | Result |
| --- | --- | --- |
| zero retained candidates | representative coverage | `rejected` |
| zero retained candidates | partial / unknown / invalid coverage | `unresolved` |
| one or more retained candidates | invalid coverage | `unresolved` |
| exactly one retained candidate with `exact` support | any non-invalid coverage state | `mapped` with `selected_variant_id` |
| exactly one retained candidate with `partial` support | any coverage state | `unresolved` |
| exactly one retained candidate with `none` support | any coverage state | `unresolved` |
| two or more retained candidates, exactly one candidate with `exact` support | any non-invalid coverage state | `mapped` with `selected_variant_id` |
| two or more retained candidates, two or more candidates with `exact` support | any non-invalid coverage state | `ambiguous` |
| two or more retained candidates, zero candidates with `exact` support | representative coverage | `ambiguous` |
| two or more retained candidates, zero candidates with `exact` support | partial / unknown / invalid coverage | `unresolved` |

### Support interpretation rule

The exact-support floor is the only floor that permits selection.
All lower support classes can preserve ambiguity or unresolved status, but they can never force a selected variant.

## 4. Exact Rule Firing Order

Rules fire in the following fixed order. Later rules may only observe the output of earlier rules.

### CE-01 Canonical candidate ordering

The evaluator receives candidates in governed pool order.
Duplicate candidate identifiers are removed while preserving first occurrence.
This produces `candidate_ids_considered`.

### CE-02 Direct contradiction elimination

Any candidate directly contradicted by governed inputs is eliminated.

### CE-03 Exact-support classification

Each non-eliminated candidate is classified for exact support.

### CE-04 Partial-support classification

Each non-eliminated candidate that did not reach exact support is classified for partial support or none.

### CE-05 Minimum-support gate

Candidates without at least partial support remain retained only if they have not been contradicted.
Candidates with contradiction are eliminated and may not re-enter the viable set.

### CE-06 Unique-survivor selection

If exactly one retained candidate has exact support and no competing retained candidate has exact support, that candidate becomes `selected_variant_id`.

### CE-07 Ambiguity formation

If more than one retained candidate remains and no unique exact-support survivor exists, the retained candidate identifiers are emitted in deterministic order as `ambiguous_candidate_ids`.

### CE-08 Outcome fallback

If no retained candidates remain:

- `rejected` only when every considered candidate was eliminated and the governed coverage state authorizes rejection
- otherwise `unresolved`

## 5. Retention Serialization Rules

Retention records are eliminated entirely from the contract.

There is no standalone `CandidateRetentionRecord`.

Retention is serialized implicitly through:

- `viable_candidate_ids`
- `ambiguous_candidate_ids`
- `selected_variant_id`
- `rationale`

This avoids duplicate canonical state for retained candidates and keeps the contract deterministic.

### Retention serialization rule

The retained set is the ordered contents of `viable_candidate_ids` minus any selected identifier.

If the retained set is empty, no retention artifact is emitted.

## 6. Candidate Elimination Record

Elimination records remain the canonical per-candidate machine-readable artifact.

Each elimination record must include:

- `candidate_id`
- `rule_id`
- `rule_name`
- `evidence_reference`
- `elimination_reason`
- `timestamp`

The same governed inputs must always produce the same elimination record for the same eliminated candidate.

## 7. Candidate Evaluation Result Contract

### candidate_ids_considered

Ordered candidate identifiers after canonicalization and duplicate removal.

### viable_candidate_ids

Ordered identifiers for candidates that were not eliminated.

### eliminated_candidate_ids

Ordered identifiers for candidates that were eliminated.

### ambiguous_candidate_ids

Ordered identifiers for retained candidates when no unique exact-support survivor exists.

### selected_variant_id

The single retained candidate identifier selected by the exact-support floor.
This field is null unless CE-06 succeeds.

### all_candidates_disproved

True only when every considered candidate is eliminated.
This field does not by itself authorize `rejected`.

### rationale

Deterministic narrative explaining:

- which rules fired
- which candidates were retained
- which candidates were eliminated
- why a unique survivor was or was not selected

### rejection_rationale

Deterministic narrative emitted only when `rejected` is reached.
Null otherwise.

## 8. Survivor Selection Contract

`selected_variant_id` may be assigned only when all of the following are true:

1. exactly one retained candidate has `exact` support
2. no other retained candidate has `exact` support
3. the candidate is not contradicted
4. governed inputs do not force `ambiguous`, `rejected`, or `unresolved` earlier in the rule order

### Single-survivor behavior

If a single retained candidate reaches the exact-support floor, it is selected.

### Insufficient-support behavior

If no retained candidate reaches the exact-support floor:

- the result is `ambiguous` only when multiple retained candidates remain tied under deterministic rule order
- otherwise the result is `unresolved`

## 9. Ambiguity Contract

`ambiguous_candidate_ids` is populated when:

- more than one candidate remains retained
- no unique exact-support survivor exists

### Ordering guarantees

`ambiguous_candidate_ids` preserves deterministic candidate pool order after elimination.

### Tie handling

Ties are not broken by hidden heuristics.
The presence of a tie is itself the result.

## 10. Rule Execution Contract

### Elimination ordering

Elimination rules execute before any survivor selection rule.
Once a candidate is eliminated, later rules cannot restore it.

### Replay requirements

Given:

- identical request inputs
- identical governed inputs
- identical candidate pool
- identical rule definitions

two implementations must produce identical:

- `candidate_ids_considered`
- `viable_candidate_ids`
- `eliminated_candidate_ids`
- `ambiguous_candidate_ids`
- `selected_variant_id`
- `all_candidates_disproved`
- serialized elimination records
- `rationale`
- `rejection_rationale`

## 11. Audit Compatibility

The following artifacts must be preserved for audit compatibility:

- candidate evaluation result
- elimination records
- rule identifiers
- evidence references
- deterministic candidate order

No separate retention artifact is required for auditability because retention is fully reconstructed from the evaluation result and elimination records.

## 12. Final Determinism Clause

Given identical request inputs, identical governed inputs, identical candidate pool, and identical rule definitions, two independent implementations must produce identical retained candidates, identical eliminated candidates, identical `selected_variant_id`, identical `ambiguous_candidate_ids`, identical `all_candidates_disproved` state, and identical serialized elimination artifacts.
