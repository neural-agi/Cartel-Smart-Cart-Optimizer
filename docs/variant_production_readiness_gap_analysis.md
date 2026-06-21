# Variant Production Readiness Gap Analysis

## Scope

This analysis classifies the remaining governance areas for Variant Matching after the current specification hardening pass.

The goal is not to repeat the design. The goal is to state, bluntly, what is still safe for prototype work and what still blocks production readiness.

## Classification Key

- Prototype Safe: acceptable for controlled implementation experiments.
- Production Blocker: must be resolved before production use.
- Future Governance Requirement: not blocking a prototype, but required before broad rollout.
- Future Optimization: useful later, but not required to stabilize the current contract.

## Findings

### Candidate Pool Coverage Governance

Classification: Production Blocker

Reason:

- rejection depends on whether the candidate pool coverage state is `representative`
- without a governed coverage state, two engineers can still disagree on whether `rejected` is legal
- candidate-set failure would remain ambiguous without an authoritative upstream declaration

### Product Context Freshness Governance

Classification: Production Blocker

Reason:

- Variant Matching must know when upstream product context is stale-but-usable versus stale-and-conflicting
- without a freshness contract, stale lineage cases will diverge in implementation
- freshness cannot be inferred safely from timestamps alone

### Pack Equivalence Governance

Classification: Future Governance Requirement

Reason:

- exact identity is now deterministic
- equivalence policy is intentionally out of scope for Variant Matching
- future category-specific equivalence may be valuable, but it must remain downstream policy

### Quantity Normalization Governance

Classification: Prototype Safe

Reason:

- the quantity normalization ownership and contract are already resolved
- the matcher can consume the governed normalized quantity boundary without inventing new rules

### Product-Context Boundary Separation

Classification: Prototype Safe

Reason:

- the boundary between Product Matching and Variant Matching is already explicit
- variant matching is not allowed to become a second product matcher

### Candidate-Set Failure vs Rejection

Classification: Prototype Safe

Reason:

- the current governance documents already separate incomplete coverage from true negative rejection
- the implementation can follow this rule deterministically once coverage state is supplied

### Review Exposure of Variant Evidence

Classification: Future Optimization

Reason:

- review visibility is important for explainability
- it does not change the core deterministic outcome contract

## Overall Assessment

Variant Matching is not production-ready yet.

The specification is sufficient for controlled prototype implementation, but not for production deployment because the matcher still depends on upstream governance for:

- candidate coverage sufficiency
- freshness classification
- quantity normalization boundaries

## Explicit Blockers

1. Candidate coverage must be declared, not inferred.
2. Product context freshness must be governed, not guessed.

## Non-Blockers

- downstream pack equivalence policy
- review visibility improvements
- operational equivalence policy
- quantity normalization ownership
- later confidence ranking refinements

## Conclusion

The current documentation closes the known matcher-level ambiguity for a prototype implementation.

Production readiness is still blocked until the governed candidate coverage and freshness contracts are enforced by the system that supplies Variant Matching.
