# Cartel Variant Spec Consistency Review

This review audits the current variant-related specification set for contradictions, duplicate rules, undefined terms, overlapping outcomes, and undocumented assumptions.

Reviewed documents:

- `docs/variant_matching_architecture.md`
- `docs/variant_matching_implementation_spec.md`
- `docs/variant_evidence_extraction_spec.md`
- `docs/variant_matching_outcome_matrix.md`
- `docs/variant_product_context_matrix.md`
- `docs/variant_quantity_normalization_contract.md`
- `docs/variant_pathological_scenarios.md`
- `docs/outcome_boundary_clarification.md`
- `docs/candidate_pool_coverage_governance.md`
- `docs/pack_equivalence_governance.md`
- `docs/product_context_freshness_governance.md`

## Issues And Resolutions

| Issue | Source document | Conflicting section | Issue description | Recommended resolution |
| --- | --- | --- | --- | --- |
| 1 | `variant_matching_architecture.md` and `variant_matching_implementation_spec.md` | Outcome definitions / rejection rules | `rejected` and `conflicting` were both usable for a candidate ruled out by pack evidence, which made implementation non-deterministic. | Use `docs/outcome_boundary_clarification.md`: `conflicting` is evidence-incompatible, `rejected` is a clean negative outcome for an internally consistent evidence bundle that disproves every candidate. |
| 2 | `variant_matching_implementation_spec.md` | Request contract / product context handling | The request contract allowed `product: Product | None`, but the downstream behavior for missing, invalid, stale, and multiple plausible product contexts was not specified. | Treat product context as a validated upstream input and use `docs/variant_product_context_matrix.md` for outcome behavior. |
| 3 | `variant_evidence_extraction_spec.md` | Required evidence fields | `evidence_confidence_state` was introduced without being defined in the approved architecture or implementation spec. | Remove the field. Keep `pack_configuration_status` and interpretation notes only. |
| 4 | `variant_evidence_extraction_spec.md` and `variant_quantity_normalization_contract.md` | Quantity interpretation / normalization boundary | Extraction and normalization responsibilities overlapped. The extractor was describing quantity equivalence even though normalization owns that boundary. | Restrict extraction to raw quantity preservation and structured pack evidence assembly. Move unit alias resolution and canonicalization to the normalization contract. |
| 5 | `variant_matching_outcome_matrix.md` | Scenario assumptions | The matrix did not state that it assumes normalized pack evidence and a validated product context unless the scenario is testing those failures. | Add explicit assumptions at the top of the matrix. |
| 6 | `variant_matching_architecture.md` and `product_matching_architecture.md` | Outcome states | Earlier draft language could have been read as implying `product_mapped_variant_unresolved` as a separate variant outcome. It remains a product-matching decision detail, not a sixth variant-matching outcome. | Keep it descriptive only in product-matching contexts. Final variant response outcomes remain the five `MatchOutcome` values. |
| 7 | `variant_matching_implementation_spec.md` | Rejection rules / decision tree | Rejection was previously described as candidate-specific, which conflicted with the request-level response contract. | Define `rejected` as a request-level outcome that applies when every candidate is explicitly disproved by consistent evidence. |
| 8 | `variant_matching_architecture.md` and `variant_matching_implementation_spec.md` | Variant evidence and product reasoning | Variant evidence may support product reasoning, but the boundary was not always stated sharply enough. | Keep the distinction explicit: variant evidence may be surfaced to review and future product reasoning, but it does not replace product matching as the primary decision layer. |
| 9 | `outcome_boundary_clarification.md` and `variant_matching_implementation_spec.md` | Candidate-set failure vs true rejection | The matcher must distinguish an incomplete candidate pool from a genuinely disproved candidate pool. Without that distinction, `rejected` would be overused. | Use `unresolved` when candidate coverage is incomplete or suspect; use `rejected` only when the evidence explicitly disproves every candidate in a pool whose coverage state is `representative`. |
| 10 | `variant_product_context_matrix.md` and `variant_boundary_review.md` | Product-family vs pack ambiguity | Earlier examples blurred product-family ambiguity with pack ambiguity. That would make Variant Matching a second Product Matcher. | Keep product-family ambiguity upstream in Product Matching; keep Variant Matching limited to pack ambiguity and pack-level conflict. |

## Result

After the above resolutions, the variant specification set is internally consistent for prototype implementation planning.

The remaining work before broad rollout is governance and implementation validation, not further architecture design.
