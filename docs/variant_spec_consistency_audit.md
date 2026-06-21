# Variant Spec Consistency Audit

## Scope

Audited documents:

- `variant_matching_architecture.md`
- `variant_matching_implementation_spec.md`
- `outcome_boundary_clarification.md`
- `variant_quantity_normalization_contract.md`
- `variant_product_context_matrix.md`
- `variant_pathological_scenarios.md`
- `candidate_pool_coverage_governance.md`
- `pack_equivalence_governance.md`
- `product_context_freshness_governance.md`
- `coverage_qualification_contract.md`
- `coverage_validation_contract.md`
- `freshness_lineage_model.md`
- `freshness_classification_contract.md`
- `upstream_failure_governance.md`
- `decision_audit_contract.md`

## Audit Result

The documents are now internally consistent for prototype implementation planning.

The remaining concerns are governance dependencies, not logical contradictions in the matcher contract.

## Resolved Issues

### 1. Candidate coverage sufficiency was undefined

- Source document: `variant_matching_implementation_spec.md`
- Conflicting section: rejection rules and outcome decision flow
- Issue: `sufficiently representative` was used without an authoritative definition
- Resolution: `coverage_qualification_contract.md` and `coverage_validation_contract.md` now define how `representative` is earned and validated, while `candidate_pool_coverage_governance.md` reserves `rejected` for validated `representative` pools only

### 2. Candidate-set failure could be mistaken for rejection

- Source document: `variant_matching_implementation_spec.md`
- Conflicting section: rejection rules and outcome notes
- Issue: the spec had to distinguish disproved candidates from incomplete coverage
- Resolution: candidate-set failure collapses to `unresolved`; only validated representative pools may yield `rejected`

### 3. Candidate contradiction was too easy to misread as conflict

- Source document: `outcome_boundary_clarification.md`
- Conflicting section: conflict vs rejection boundaries
- Issue: a bad or incomplete candidate pool could appear to justify `conflicting`
- Resolution: candidate contradiction only removes candidates; conflict is reserved for evidence or product-context incompatibility

### 4. Product-family ambiguity risked leaking into Variant Matching

- Source document: `variant_product_context_matrix.md`
- Conflicting section: ambiguous and unresolved rows
- Issue: product-family uncertainty could be interpreted as a Variant Matching responsibility
- Resolution: `variant_boundary_review.md` and the matrix notes assign product-family ambiguity to Product Matching

### 5. Pack equivalence was not separated from exact variant identity

- Source document: `variant_matching_architecture.md`
- Conflicting section: pack semantics and exact identity
- Issue: downstream equivalence could be mistaken for matcher identity
- Resolution: `pack_equivalence_governance.md` states equivalence may not replace exact identity

### 6. Freshness behavior was not governed by lineage

- Source document: `variant_matching_implementation_spec.md`
- Conflicting section: product context handling
- Issue: stale context needed a governed lifecycle, not a time heuristic
- Resolution: `product_context_freshness_governance.md` defines `fresh`, `stale-compatible`, `stale-unresolved`, `stale-conflicting`, `invalid`, and `missing`

### 7. Quantity comparison needed explicit dimension governance

- Source document: `variant_quantity_normalization_contract.md`
- Conflicting section: measurement dimension guidance
- Issue: comparison rules had to state which dimensions may and may not be compared
- Resolution: volume, mass, count, unit-based consumer goods, and unknown are now governed explicitly

## Remaining Assumptions

These are not contradictions, but they are dependencies that the implementation must consume from upstream components:

- candidate coverage state must be supplied by Candidate Generation
- freshness state must be supplied by the product-context layer
- quantity normalization must be performed before Variant Matching consumes pack evidence

## Conclusion

No unresolved deterministic contradiction remains inside the current spec set.

The contract is coherent for prototype implementation, provided upstream components honor the governed coverage and freshness declarations.
