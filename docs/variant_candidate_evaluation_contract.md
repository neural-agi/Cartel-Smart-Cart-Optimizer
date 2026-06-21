# Cartel Variant Candidate Evaluation Contract

This document freezes the deterministic behavior of Candidate Evaluation before implementation.

It does not define matching outcomes, coverage qualification, freshness classification, normalization, candidate generation, audit storage, or review behavior.

The evaluator is a narrow internal boundary inside Variant Matching. It consumes governed inputs and produces a deterministic candidate-evaluation result for the variant matcher service.

---

## 1. Candidate Evaluation Boundary

### Purpose

Candidate Evaluation deterministically compares governed candidate variants against governed request evidence and classifies each candidate as either retained or eliminated.

### Inputs

Candidate Evaluation must consume only the following governed inputs:

- `VariantMatchRequest`
- `VariantGovernanceContext`

The request may contain:

- `platform_listing`
- `listing_observation`
- `evidence_references`
- `product`
- `variant_candidates`

The governance context may contain:

- `coverage_validation`
- `freshness`
- `upstream_failures`
- `normalized_pack_evidence`

### Outputs

Candidate Evaluation must produce:

- `CandidateEvaluationResult`

### Ownership

Candidate Evaluation owns:

- deterministic candidate comparison
- candidate retention and elimination
- tie detection among surviving candidates
- survivor designation only when the survivor meets the minimum support bar
- candidate-level rationale serialization

### Non-Ownership

Candidate Evaluation must not own:

- coverage qualification
- coverage validation
- freshness classification
- lineage construction
- quantity normalization
- candidate generation
- persistence
- audit storage
- review workflow
- assertions
- product-family resolution
- pack-evidence invention
- heuristic ranking
- fuzzy matching
- embeddings
- ML
- external API calls

---

## 2. Candidate State Model

Candidate Evaluation uses exactly two canonical candidate states.

### `retained`

A candidate is `retained` when the governed evidence does not eliminate it under the deterministic rule set.

Meaning:

- the candidate remains viable for downstream selection
- the candidate is still in the considered solution set
- the candidate has not been disproved by governed evidence

### `eliminated`

A candidate is `eliminated` when a deterministic rule directly disproves it under the governed evidence.

Meaning:

- the candidate is removed from the viable set
- the elimination reason must be recorded
- the elimination must be reproducible from the same inputs and rule definitions

Candidate state is always computed from governed inputs only.

---

## 3. Candidate Elimination Record

Every eliminated candidate must be serializable into a canonical machine-readable elimination record.

### Required Fields

- `candidate_id`
- `rule_id`
- `rule_name`
- `evidence_reference`
- `elimination_reason`
- `timestamp`

### Field Semantics

- `candidate_id`: stable identifier of the eliminated `ProductVariant`
- `rule_id`: stable identifier of the deterministic rule that fired
- `rule_name`: human-readable name for the rule
- `evidence_reference`: the specific governed evidence reference or references that supported elimination
- `elimination_reason`: concise deterministic explanation of why the rule eliminated the candidate
- `timestamp`: the time the elimination record was produced

### Timestamp Requirements

- timestamp must be recorded in UTC
- timestamp must be emitted at decision time
- timestamp must not change after creation
- timestamp must not be used as a decision input

### Determinism Requirements

Two engineers examining the same evidence, governed inputs, and rule definitions must produce identical elimination records except for the wall-clock timestamp value.

All non-time fields must be identical.

The elimination record must not depend on:

- set iteration order
- nondeterministic candidate ordering
- external mutable state
- hidden scoring
- incidental processing order

---

## 4. Candidate Retention Record

Every retained candidate must be serializable into a canonical machine-readable retention record.

### Required Fields

- `candidate_id`
- `rule_id`
- `rule_name`
- `evidence_reference`
- `retention_reason`
- `timestamp`

### Field Semantics

- `candidate_id`: stable identifier of the retained `ProductVariant`
- `rule_id`: stable identifier of the deterministic rule that preserved the candidate
- `rule_name`: human-readable name for the rule
- `evidence_reference`: the specific governed evidence reference or references that supported retention
- `retention_reason`: concise deterministic explanation of why the rule preserved the candidate
- `timestamp`: the time the retention record was produced

### Timestamp Requirements

- timestamp must be recorded in UTC
- timestamp must be emitted at decision time
- timestamp must not change after creation
- timestamp must not influence candidate retention

### Determinism Requirements

Two engineers examining the same evidence, governed inputs, and rule definitions must produce identical retention records except for the wall-clock timestamp value.

All non-time fields must be identical.

The retention record must not depend on:

- set iteration order
- nondeterministic candidate ordering
- external mutable state
- hidden scoring
- incidental processing order

---

## 5. Candidate Evaluation Result Contract

Candidate Evaluation must return a `CandidateEvaluationResult` with the following exact semantics.

### `candidate_ids_considered`

The complete ordered list of candidate identifiers evaluated by the candidate evaluator.

Rules:

- must include every candidate supplied to evaluation
- must preserve deterministic order
- must not omit eliminated candidates
- must not reorder candidates nondeterministically

### `viable_candidate_ids`

The ordered list of candidate identifiers that remain retained after deterministic evaluation.

Rules:

- must be a subset of `candidate_ids_considered`
- must include only retained candidates
- must preserve deterministic order

### `eliminated_candidate_ids`

The ordered list of candidate identifiers that were deterministically eliminated.

Rules:

- must be a subset of `candidate_ids_considered`
- must include only eliminated candidates
- must preserve deterministic order

### `ambiguous_candidate_ids`

The ordered list of retained candidate identifiers that remain materially tied after deterministic evaluation.

Rules:

- must be a subset of `viable_candidate_ids`
- must contain only surviving candidates that remain tied under the rule set
- must preserve deterministic order

### `selected_variant_id`

The identifier of the unique surviving candidate only when the minimum support bar is met.

Rules:

- must be `None` unless a single candidate survives and meets the minimum support bar
- must equal the sole value in `viable_candidate_ids` when populated
- must not be populated for ties
- must not be populated for insufficient support

### `all_candidates_disproved`

Boolean flag indicating whether every evaluated candidate was eliminated by deterministic rules.

Rules:

- must be `True` only when `viable_candidate_ids` is empty
- must be `False` when at least one candidate is retained
- must not depend on coverage sufficiency
- must not encode matcher outcome directly

### `rationale`

Deterministic human-readable rationale strings for the overall candidate evaluation result.

Rules:

- must explain rule firings and elimination/retention decisions
- must preserve deterministic ordering
- must include the evidence basis for decisions
- must not use heuristic language
- must not use price, offer, or availability as decision reasons

### `rejection_rationale`

Deterministic rationale strings specifically explaining why all candidates were disproved when `all_candidates_disproved` is `True`.

Rules:

- must be populated only when all candidates are disproved
- must explain the elimination basis for the evaluated set
- must remain distinct from generic rationale

---

## 6. Survivor Selection Contract

Candidate Evaluation may select a survivor only under strictly deterministic conditions.

### Minimum Support Bar

A candidate may be selected only when all of the following are true:

1. exactly one candidate remains in `viable_candidate_ids`
2. the surviving candidate is not contradicted by governed evidence
3. the surviving candidate satisfies the applicable exact-support rule set for the evidence class
4. no other candidate remains materially tied with the survivor
5. no blocking upstream contradiction exists in the governed inputs

### Single-Survivor Behavior

If exactly one candidate remains viable:

- return that candidate in `selected_variant_id` only if the minimum support bar is met
- otherwise preserve the candidate in `viable_candidate_ids` and leave `selected_variant_id` unset

### Insufficient-Support Behavior

If a single candidate remains but the evidence does not satisfy the minimum support bar:

- the candidate remains retained
- `selected_variant_id` must be `None`
- the candidate evaluator must not invent support

Selection must never be based on incidental candidate ordering or hidden preference.

---

## 7. Ambiguity Contract

Ambiguity exists only among retained candidates.

### When `ambiguous_candidate_ids` Is Populated

`ambiguous_candidate_ids` must be populated when:

- two or more retained candidates remain materially tied
- the tie cannot be broken by deterministic rule order
- the evaluator cannot justify a unique survivor

### Tie Representation

Tie members must be listed explicitly and deterministically.

Rules:

- only retained candidates may appear
- all tied candidates must be included
- no eliminated candidate may appear
- ordering must be deterministic

### Ordering Guarantees

The order of `ambiguous_candidate_ids` must be stable for identical inputs and identical rules.

### Determinism Requirements

Ambiguity must not be inferred from:

- pool size alone
- incidental ordering
- randomness
- hidden scoring
- non-governed evidence

Ambiguity must be represented only by deterministic tie membership.

---

## 8. Rule Execution Contract

Candidate Evaluation must execute rules deterministically.

### Rule Firing Order

Rules must fire in a fixed, documented order.

The evaluator must:

1. inspect each candidate under the same rule sequence
2. apply elimination rules before survivor selection
3. preserve the deterministic order of candidates and rule outcomes
4. record every fired rule that changes candidate state

### Elimination Ordering

Elimination ordering must be deterministic.

Rules:

- candidates are processed in a stable order
- when multiple rules can eliminate a candidate, the first applicable rule in the fixed order must determine the recorded elimination reason
- the same candidate must not produce multiple contradictory elimination records

### Tie Handling

When multiple retained candidates remain tied:

- retain all tied candidates
- populate `ambiguous_candidate_ids`
- do not choose a survivor

### Replay Requirements

Given the same governed inputs and the same rule definitions, replay must reconstruct:

- identical retained candidates
- identical eliminated candidates
- identical ambiguous candidate set
- identical selected survivor decision
- identical all-candidates-disproved state

The evaluator must not depend on mutable state outside the request and governance context.

---

## 9. Audit Compatibility

Candidate Evaluation artifacts must be preserved in the variant decision trace and audit record.

### Required Trace Preservation

`VariantDecisionTrace` must preserve:

- candidate_ids_considered
- candidate_ids_eliminated
- selected_variant_id when present
- rule references used by candidate evaluation
- decision path
- rationale

### Required Audit Preservation

`VariantDecisionAuditRecord` must preserve:

- candidate_ids_considered
- candidate_ids_eliminated
- selected_candidate_id when present
- decision id
- rule document references
- rationale
- upstream failure states relevant to candidate evaluation

### Audit Compatibility Rules

- candidate evaluation artifacts must be replayable from the audit record plus governed inputs
- audit records must not require access to hidden internal state
- audit records must not rely on nondeterministic candidate ordering
- audit records must not collapse eliminated and retained candidates into an opaque score

---

## 10. Final Determinism Clause

Given identical request inputs, identical governed inputs, identical candidate pool, and identical rule definitions, two independent implementations must produce:

- identical retained candidates
- identical eliminated candidates
- identical selected_variant_id
- identical ambiguous_candidate_ids
- identical all_candidates_disproved state
- identical serialized candidate evaluation artifacts

Any implementation that can produce a different result under the same inputs is non-compliant with this contract.

