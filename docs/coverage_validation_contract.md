# Coverage Validation Contract

## Purpose

This contract defines how downstream systems independently validate a coverage declaration before trusting it for negative reasoning.

## Owner

- **Coverage validation owner:** Variant Matching preflight validation

The validator is read-only.
It does not qualify coverage.
It does not alter candidate generation output.

## Inputs

Validation consumes:

- the declared coverage state
- the coverage declaration record
- the candidate-generation trace
- the scope descriptor
- the source attempt log
- the search-space limits
- the candidate pool summary

## Validation Procedure

1. Verify the declaration id and trace id match.
2. Verify required metadata fields exist and are well formed.
3. Verify the scope descriptor matches the trace.
4. Verify every declared source channel has a recorded outcome.
5. Verify the declared state is consistent with the trace evidence.
6. Verify no contradictory declaration exists for the same scope and trace.
7. Assign the validation result.

## Validation Results

### `valid`

The declaration is internally consistent and supported by trace evidence.

### `unverifiable`

The declaration cannot be proven from available trace evidence.

Examples:

- the trace is missing
- the trace was truncated
- the storage layer lost part of the generation record

### `invalid`

The declaration is malformed or contradicted by its own trace.

Examples:

- required fields are missing
- the trace shows an omitted required source
- the trace contradicts the claimed coverage state

### `contradictory`

Multiple coverage declarations for the same scope cannot both be true.

Examples:

- one declaration says `representative`
- another declaration for the same scope and trace says `partial`

## Deterministic Downstream Behavior

- `valid + representative` may be used for negative rejection.
- `valid + partial` may not be used for rejection.
- `valid + unknown` may not be used for rejection.
- `unverifiable` downgrades to `unknown` for downstream negative reasoning.
- `invalid` downgrades to `invalid` for downstream negative reasoning and may not support rejection.
- `contradictory` downgrades to `invalid` for downstream negative reasoning and may not support rejection.

Downstream systems must never treat an unverifiable declaration as representative.

## Failure Handling

### Missing Declaration

If the declaration is missing, validation result is `unverifiable`.

### Invalid Declaration

If the declaration is malformed, validation result is `invalid`.

### Contradictory Declaration

If two declarations conflict, the conservative result is `contradictory`, which downstream systems treat as invalid.

### Timeout During Validation

If validation cannot complete because trace retrieval times out, the result is `unverifiable`.

### Partial Trace

If only part of the generation trace is available, the result is `unverifiable` unless the available portion already proves invalidity.

## Required Validation Rationale

The validation rationale must state:

- which declaration was checked
- which trace was checked
- which metadata fields were missing or contradictory
- why the result is valid, unverifiable, invalid, or contradictory
- whether rejection remains permitted downstream

## Validation Invariants

- validation never upgrades a declaration to a stronger state than the trace supports
- validation never depends on matcher outcome
- validation never depends on freshness
- validation never depends on product matching
- validation never rewrites the declaration
- validation never feeds back into coverage qualification

## Examples

1. Declaration and trace align exactly -> `valid`.
2. Declaration exists but trace is missing -> `unverifiable`.
3. Trace shows a required source omitted -> `invalid`.
4. Two declarations for the same scope disagree -> `contradictory`.
5. Trace retrieval times out -> `unverifiable`.

## Determinism Note

Given the same declaration, the same trace, and the same validation rules, two engineers must produce the same validation result.
