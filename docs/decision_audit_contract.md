# Decision Audit Contract

## Purpose

Every Variant Matching outcome must be reproducible from its audit record.

## Owner

- **Audit generation owner:** Decision audit service for the Product Intelligence matching path

The audit record is append-only.
It records what happened.
It does not influence what should happen.

## Common Audit Fields

Every final outcome must record:

- audit id
- decision id
- matcher version
- rule document references
- request hash
- evidence reference list
- candidate ids considered
- candidate ids eliminated
- selected candidate id when present
- coverage declaration id
- coverage validation result
- freshness classification result
- lineage root id
- lineage revision ids
- rationale
- timestamp
- upstream failure states

## Outcome-Specific Audit Requirements

### `mapped`

Required:

- selected variant id
- winning rule path
- why the candidate won
- why other candidates lost
- validated coverage reference
- freshness reference used

### `ambiguous`

Required:

- tied candidate ids
- tie criteria
- why the tie could not be broken
- coverage reference
- freshness reference

### `unresolved`

Required:

- missing or insufficient dependency summary
- reason the pool could not support a definitive variant decision
- which upstream dependency blocked resolution
- coverage reference if present
- freshness reference if present

### `conflicting`

Required:

- exact contradiction source
- evidence references showing the contradiction
- product-context or pack-identity conflict summary
- coverage reference
- freshness reference

### `rejected`

Required:

- complete list of candidates disproved
- explicit negative evidence for each disproved candidate
- proof that coverage was `representative`
- proof that coverage was validated or that validation did not fail
- freshness reference
- reason rejection was preferred over unresolved

## Reproducibility Guarantees

Given the same:

- request input
- evidence bundle
- candidate set
- coverage declaration
- coverage validation result
- freshness classification
- lineage snapshot
- rule document versions

the audit record must reproduce the same outcome and rationale.

## Required Rule References

The audit record must reference the governing rules that fired:

- outcome boundary rule
- coverage qualification rule
- coverage validation rule
- freshness classification rule
- lineage validation rule
- upstream failure rule

## Required Coverage References

The audit record must preserve:

- coverage state
- coverage declaration id
- coverage validation result
- coverage scope id

## Required Freshness References

The audit record must preserve:

- freshness state
- lineage root id
- lineage revision ids
- supersession ids where present

## Required Evidence References

The audit record must preserve:

- raw listing evidence
- quantity evidence
- source artifact reference
- parser version
- capture context reference
- candidate evidence references

## Questions The Audit Record Must Answer

- Why did this happen?
- What evidence was used?
- Which candidates were considered?
- Which candidates were eliminated?
- Which rule fired?
- Which coverage state was used?
- Which freshness state was used?

## Validation Invariants

- the audit record must not omit a chosen outcome
- the audit record must not rely on nondeterministic ordering
- the audit record must not depend on mutable external state after creation
- the audit record must not rewrite upstream records
- the audit record must not hide unresolved dependencies

## Examples

1. Mapped result includes selected variant, eliminated alternatives, and the exact rule path.
2. Ambiguous result includes every tied candidate and the reason the tie remained.
3. Unresolved result includes the missing or partial upstream dependency.
4. Conflicting result includes the contradiction source and the conflicting evidence refs.
5. Rejected result includes every disproved candidate plus the proof of representative coverage.
