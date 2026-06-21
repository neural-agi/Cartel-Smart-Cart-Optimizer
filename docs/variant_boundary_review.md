# Cartel Variant Boundary Review

This short review records the separation between Product Matching and Variant Matching.

## Boundary Rule

- Product Matching owns product-family ambiguity.
- Variant Matching owns pack ambiguity.

## Practical Meaning

Variant Matching may only decide after a plausible `Product` context exists.

It may:

- accept a pack-level mapping
- reject a pack-level candidate
- return ambiguous when pack candidates are tied
- return unresolved when pack evidence or product context is insufficient
- return conflicting when the evidence bundle or product context is internally incompatible

It may not:

- choose between two different product families
- resolve `Whole Wheat Bread` versus `White Bread`
- resolve `Amul Taaza Milk` versus `Amul Gold Milk`
- become a second product matcher under the guise of pack reasoning

## Matrix Implication

Any scenario that asks Variant Matching to choose between product families must be treated as upstream Product Matching work or as unresolved product context, not as a variant ambiguity.

The `docs/variant_product_context_matrix.md` file has been revised to reflect that boundary.
