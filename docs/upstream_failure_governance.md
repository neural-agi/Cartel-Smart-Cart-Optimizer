# Upstream Failure Governance

## Purpose

Variant Matching must have deterministic behavior when upstream dependencies fail, return partial data, or disagree.

## Owner

- **Failure governance owner:** Variant Matching consumer boundary

The matcher does not repair upstream failures.
It records them, classifies them, and returns the governed outcome.

## Covered Dependencies

- Candidate Generation
- Coverage Qualification
- Coverage Validation
- Freshness Classification
- Freshness Lineage
- Quantity Normalization

## Failure State Rules

For every upstream dependency, the following states must be handled deterministically:

### Missing

The dependency produced no usable record.

Matcher behavior:

- return `unresolved` unless the evidence bundle itself is conflicting
- preserve the missing dependency in rationale
- never treat missing data as proof of rejection

### Invalid

The dependency produced a malformed or internally contradictory record.

Matcher behavior:

- return `unresolved` unless the invalidity itself directly contradicts trusted evidence, in which case `conflicting`
- preserve the invalid dependency in rationale
- never use invalid data to support `rejected`

### Contradictory

The dependency disagrees with another trusted record for the same scope.

Matcher behavior:

- if the contradiction is about pack identity or product context, return `conflicting`
- otherwise return `unresolved` and mark the dependency for audit escalation

### Timeout

The dependency did not complete within the allowed execution window.

Matcher behavior:

- return `unresolved`
- record the timeout in rationale
- prohibit rejection if the failed dependency is coverage-related

### Partial

The dependency returned incomplete but usable data.

Matcher behavior:

- may still allow `mapped` or `ambiguous` if the remaining evidence is sufficient
- must block `rejected` when the partial dependency is coverage-related or freshness-related
- must never be upgraded silently to complete

## Dependency-Specific Behavior

### Candidate Generation

- missing -> `unresolved`
- invalid -> `unresolved`
- contradictory -> `unresolved`
- timeout -> `unresolved`
- partial -> candidate-set failure, which is `unresolved`

### Coverage Qualification

- missing -> `unknown`
- invalid -> `invalid`
- contradictory -> `invalid`
- timeout -> `unknown`
- partial -> `partial`

### Coverage Validation

- missing -> `unverifiable`
- invalid -> `invalid`
- contradictory -> `contradictory`
- timeout -> `unverifiable`
- partial -> `unverifiable`

### Freshness Classification

- missing -> `missing`
- invalid -> `invalid`
- contradictory -> `stale-conflicting`
- timeout -> `stale-unresolved`
- partial -> `stale-unresolved`

### Freshness Lineage

- missing -> freshness cannot be computed; downstream treats the context as `missing`
- invalid -> freshness cannot be trusted; downstream treats the context as `invalid`
- contradictory -> freshness cannot be trusted; downstream treats the context as `stale-conflicting`
- timeout -> freshness cannot be computed; downstream treats the context as `stale-unresolved`
- partial -> freshness cannot be fully computed; downstream treats the context as `stale-unresolved`

### Quantity Normalization

- missing -> `unresolved`
- invalid -> `unresolved` unless direct contradiction is proven, then `conflicting`
- contradictory -> `conflicting`
- timeout -> `unresolved`
- partial -> `unresolved`

## Required Escalation Behavior

Each failure must be recorded for the relevant upstream owner:

- Candidate Generation failures -> candidate generation audit/retry
- Coverage qualification failures -> candidate generation audit/retry
- Coverage validation failures -> coverage validation audit
- Freshness classification failures -> freshness lineage audit
- Freshness lineage failures -> lineage construction audit
- Quantity normalization failures -> normalization audit

Escalation must not change the current matcher outcome.

## Required Rationale Behavior

The matcher rationale must always include:

- the failing dependency name
- the failure state
- whether the failure blocked rejection
- whether the failure caused unresolved or conflicting
- the upstream record id if available

## Deterministic Downstream Behavior

- Missing coverage or missing freshness never authorizes rejection.
- Invalid coverage or invalid lineage never authorizes rejection.
- Timeout never authorizes rejection.
- Partial data never authorizes silent promotion to representative or fresh.

## Failure Examples

1. Candidate Generation timed out -> `unresolved`.
2. Coverage declaration missing -> `unresolved` with coverage state `unknown`.
3. Freshness lineage contradictory -> `stale-conflicting`.
4. Quantity normalization malformed -> `unresolved` unless the malformation directly contradicts trusted pack evidence.
5. Coverage validation contradictory -> coverage treated as invalid; rejection blocked.
