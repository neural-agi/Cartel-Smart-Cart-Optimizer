# Variant Governance Review

## Authority Map

Exactly one owner is assigned to each governance classification.

| Governance classification | Owner |
| --- | --- |
| Coverage qualification | Candidate Generation |
| Coverage validation | Variant Matching preflight validation |
| Freshness classification | Assertion / context freshness classifier |
| Lineage construction | Assertion / context lineage service |
| Audit generation | Decision audit service |

## Boundary Rules

- Coverage qualification is upstream and write-oriented.
- Coverage validation is downstream and read-only.
- Lineage construction is upstream and write-oriented.
- Freshness classification is downstream and read-only.
- Audit generation is append-only and read-only with respect to decision inputs.

## Dependency Flow

1. Candidate Generation emits a coverage declaration.
2. Variant Matching preflight validates the declaration.
3. Assertion / lineage service emits lineage records.
4. Freshness classifier assigns a freshness state from the lineage snapshot.
5. Variant Matching consumes candidate pool, coverage state, and freshness state.
6. Decision audit records the final outcome.

## Hidden Governance Loop Check

### Coverage Depends On Freshness?

No.

Coverage qualification uses candidate-generation execution trace only.

### Freshness Depends On Coverage?

No.

Freshness classification uses lineage and listing evidence only.

### Validation Depends On Itself?

No.

Coverage validation reads declaration and trace; it does not read matcher outcome.

### Lineage Depends On Freshness?

No.

Lineage construction records revision history; it does not ask freshness to justify itself.

### Freshness Depends On Lineage Classification Outputs?

No.

Freshness classification reads lineage records; it does not depend on prior freshness labels.

## Undefined Authority Check

No classification is ownerless.
No classification has multiple owners.

## Governance Principles

- downstream consumers may downgrade a declaration, but they may not upgrade it
- absence of evidence is not evidence of representative coverage
- absence of lineage is not freshness
- audit records are for traceability, not decision repair

## Conclusion

The governance layer now has single-owner responsibilities and no circular authority path.
