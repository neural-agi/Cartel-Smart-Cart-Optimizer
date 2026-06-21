# Candidate Pool Coverage Governance

## Purpose

Variant Matching must never infer candidate-pool sufficiency from pool size, candidate diversity, or matching outcome alone.
Coverage is a governed upstream declaration. The matcher consumes it and does not guess.
`coverage_qualification_contract.md` defines how the declaration is earned.
`coverage_validation_contract.md` defines how the declaration is independently checked.

## Ownership

- Candidate Generation owns candidate pool construction and coverage declaration.
- Variant Matching consumes the declared coverage state.
- Review and Assertions may later audit coverage declarations, but they do not redefine them during matching.

## Coverage State Model

Coverage is a property of the candidate pool as a whole.

### `unknown`

Meaning:

- No authoritative coverage declaration is available.
- The pool may be usable for positive mapping or ambiguity detection, but not for negative rejection.

Matcher behavior:

- May return `mapped`, `ambiguous`, or `unresolved` if the evidence supports those outcomes.
- Must not return `rejected` based on this pool.

### `partial`

Meaning:

- The pool is known to cover only a subset of plausible candidates.
- The generator intentionally stopped early, applied a narrow filter, or otherwise did not attempt exhaustive recall for the evidence class.

Matcher behavior:

- May return `mapped`, `ambiguous`, or `unresolved`.
- Must not return `rejected`.

### `representative`

Meaning:

- The pool is declared broad enough to support negative reasoning for the evaluated evidence class.
- The generator has applied the expected recall-oriented search for that scope.
- The declaration is only trustworthy after `coverage_validation_contract.md` accepts it as valid.
- Coverage does not mean exhaustive completeness across the entire catalog; it means the pool is suitable for concluding that all currently plausible candidates have been disproved.

Matcher behavior:

- May return `mapped`, `ambiguous`, `unresolved`, or `rejected`.
- `rejected` is allowed only when:
  - the evidence bundle is internally consistent,
  - every candidate in the pool is explicitly disproved, and
  - no other candidate remains viable under the declared evidence class.

### `invalid`

Meaning:

- The coverage declaration is malformed, contradictory, or missing required fields.
- The matcher cannot trust the pool for negative reasoning.

Matcher behavior:

- Treat as `unresolved` unless evidence or context independently proves `conflicting`.
- Must not return `rejected`.

## Required Matcher Behavior

1. Candidate coverage state is evaluated before rejection is considered.
2. Candidate-set failure always collapses to `unresolved`.
3. `rejected` requires `representative` coverage.
4. Candidate contradiction alone never produces `conflicting`.
5. Coverage state never upgrades a weak evidence bundle into a match.

## Deterministic Classification Rules

### Rejection Allowed

Rejection is allowed only when all of the following are true:

- coverage state is `representative`
- the evidence bundle is internally consistent
- every candidate is explicitly disproved
- there is no unresolved product-context contradiction that would require upstream handling

### Rejection Must Collapse to Unresolved

Rejection must collapse to `unresolved` when any of the following are true:

- coverage state is `unknown`
- coverage state is `partial`
- coverage state is `invalid`
- candidate generation says the pool is incomplete for the evidence class
- the generator cannot assert that the pool is representative
- a candidate-set failure is caused by missing coverage rather than contrary evidence

## Validation Examples

1. `Milk / 2 L` with candidates `500 ml`, `1 L`, coverage `representative`, and evidence that explicitly contradicts both candidates -> `rejected`.
2. `Milk / 2 L` with candidates `500 ml`, `1 L`, coverage `partial`, and both candidates disproved -> `unresolved`, not `rejected`.
3. `Milk / 1 L` with one exact candidate and coverage `unknown` -> may still be `mapped`; coverage blocks only negative rejection.
4. `Bread / pack of 6` with several plausible packs and coverage `representative`, but one pack remains tied -> `ambiguous`.
5. `Shampoo / 180 ml` with malformed coverage metadata -> `unresolved` unless the evidence bundle itself is conflicting.

## Pathological Examples

1. A one-item candidate pool labeled `representative` but generated from a narrow brand-only filter. The label is invalid if the evidence class still allows other plausible variants.
2. A large pool of unrelated candidates marked `partial`. Size does not authorize rejection.
3. A pool with two disproved candidates and one missing plausible candidate family. Outcome is `unresolved`.
4. A pool with no candidates and coverage `representative`. Outcome is `unresolved`, because the request cannot support rejection without a candidate set.
5. A pool where the generator cannot explain coverage but the matcher prefers a negative answer. Outcome remains `unresolved`.

## Key Principle

Variant Matching must never guess whether coverage is sufficient.
Coverage sufficiency is an upstream contract, not an inference.
