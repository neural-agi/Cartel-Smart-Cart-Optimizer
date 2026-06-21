# Cartel Variant Pathological Scenarios

This matrix stress-tests Variant Matching under messy, contradictory, and partially parsed inputs.

It does not add new architecture. It uses only the concepts already defined in the variant docs and the quantity normalization contract.

## Scenarios

| # | Product context | Listing title | Quantity text | Candidate variants | Expected outcome | Why |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Amul Taaza Milk` | `Amul Taaza Milk 1 L` | `500 ml` | `500 ml`, `1 L` | conflicting | Title and quantity disagree materially. |
| 2 | `Amul Taaza Milk` | `Amul Taaza Milk 500 ml` | `1 L` | `500 ml`, `1 L` | conflicting | Quantity field contradicts the title and candidate pack. |
| 3 | `Britannia Bread` | `Britannia Bread Pack of 2` | `1 unit` | `Pack of 2` | conflicting | The pack count is explicit and incompatible with the quantity text. |
| 4 | `Lay's Chips` | `Lay's Chips Combo Pack` | `50 g` | `single unit 50 g` | conflicting | Combo semantics cannot be collapsed into a single-unit candidate. |
| 5 | `Coca-Cola Soft Drink` | `Coca-Cola Soft Drink 2 x 500 ml` | `1 L` | `1 L single unit` | conflicting | The pack structure and single-unit interpretation are incompatible. |
| 6 | `Amul Taaza Milk` | `Amul Taaza Milk` | `2 x 500 ml` | `1 L single unit` | unresolved | The explicit multipack evidence may rule out the candidate, but the pool is too narrow to conclude true rejection. |
| 7 | `Britannia Bread` | `Britannia Bread` | `Pack of 6` | `single unit` | unresolved | The count evidence may rule out the candidate, but the pool coverage state is not `representative`. |
| 8 | `Shampoo` | `Keratin Smooth Shampoo` | `Combo Pack` | `single unit 340 ml` | unresolved | The candidate is likely wrong, but candidate coverage is incomplete. |
| 9 | `Snack Mix` | `Snack Mix` | `2 x 50 g` | `50 g single unit` | unresolved | Multipack evidence suggests failure of the candidate pool, not a true rejection. |
| 10 | `Milk` | `Milk` | `Pack of 2` | `1 L single unit` | unresolved | The pack-of-N evidence is insufficient to conclude true rejection from a narrow pool. |
| 11 | `Amul Taaza Milk` | `Amul Taaza Milk` | `null` | `500 ml`, `1 L` | unresolved | There is no pack evidence at all. |
| 12 | `Bread` | `Bread` | `~1 L` | `400 g`, `500 g` | unresolved | The quantity text is malformed and not safely interpretable. |
| 13 | `Rice` | `Basmati Rice` | `1Lx2` | `2 x 1 L`, `1 L single unit` | unresolved | The raw quantity text is partially parsed but not safely normalized yet. |
| 14 | `Shampoo` | `Keratin Smooth Shampoo` | `Value Pack` | `180 ml`, `340 ml` | unresolved | The pack semantics are unknown. |
| 15 | `Chips` | `Magic Masala Chips` | `12 oz` | `50 g`, `70 g` | unresolved | The unit is unknown to the normalization layer. |
| 16 | `Amul Taaza Milk` | `Amul Taaza Milk` | `Pack of 6` | `Pack of 6`, `Pack of 6 special` | ambiguous | The count is clear, but the candidates remain tied. |
| 17 | `Bread` | `Whole Wheat Bread` | `400 g` | `400 g pouch`, `400 g pouch duplicate` | ambiguous | Duplicate candidates remain materially tied. |
| 18 | `Cereal` | `Cereal` | `1 kg` | `1 kg box`, `1 kg pouch` | ambiguous | Identical quantity with different packaging forms leaves a tie. |
| 19 | `Milk` | `Amul Taaza Milk` | `1 L` | `1 L pouch`, `1 L carton` | ambiguous | Packaging form is missing and both candidates remain viable. |
| 20 | `Shampoo` | `Keratin Smooth Shampoo` | `340 ml` | `340 ml bottle`, `340 ml bottle duplicate` | ambiguous | Two identical candidates remain equally plausible. |
| 21 | `Milk` | `Amul Taaza Milk 1 L` | `500 ml` | `500 ml`, `1 L` | conflicting | The evidence bundle is internally contradictory. |
| 22 | `Bread` | `Britannia Bread Combo Pack` | `Pack of 2` | `single unit`, `multipack of 2` | conflicting | The title, quantity, and candidate set contain incompatible pack facts. |
| 23 | `Snack Mix` | `Snack Mix 2 x` | `50 g` | `2 x 50 g`, `50 g single unit` | unresolved | The pack expression is partially parsed and not safe to decide from. |
| 24 | `Coca-Cola Soft Drink` | `Coca-Cola Soft Drink` | `1 L` | `500 ml`, `500 ml duplicate` | unresolved | Every supplied candidate is wrong, but the candidate pool is incomplete. |
| 25 | `Shampoo` | `Keratin Smooth Shampoo` | `Combo Pack` | `1 L single unit`, `180 ml single unit` | conflicting | The combo semantics conflict with every candidate interpretation. |

## Coverage Notes

This matrix explicitly covers:

- title quantity conflicts
- quantity field conflicts
- combo vs single-unit conflicts
- multipack vs single-unit conflicts
- missing quantity text
- contradictory evidence bundles
- partially parsed evidence
- malformed quantity text
- pack-of-N without unit quantity
- unknown pack semantics
- duplicated candidate variants
- identical pack quantities with different packaging forms
- candidate-set failure from incomplete variant coverage

The purpose of the matrix is to force the implementation to prove boundary behavior before any matcher code is written.
