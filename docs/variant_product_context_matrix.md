# Cartel Variant Product Context Matrix

This matrix validates how Variant Matching behaves when the upstream `product` context is missing, invalid, stale, conflicting, or multiply plausible.

It uses only concepts already defined in the variant architecture, implementation spec, boundary clarification, and quantity normalization contract.

## Mapped Scenarios

| # | Product context | Listing title | Quantity text | Candidate variants | Expected outcome | Why |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Current valid Product: `Amul Taaza Toned Milk` | `Amul Taaza Toned Milk` | `500 ml` | `Amul Taaza Toned Milk, 500 ml` | mapped | Product context is valid and the variant match is exact. |
| 2 | Stale but still compatible Product revision: `Britannia Whole Wheat Bread` | `Britannia Whole Wheat Bread` | `400 g` | `Britannia Whole Wheat Bread, 400 g` | mapped | The stale context does not contradict current evidence. |
| 3 | Valid Product with alias label: `Lay's Magic Masala Chips` | `Lay's Magic Masala Chips` | `50 g` | `Lay's Magic Masala Chips, 50 g` | mapped | Alias handling does not change the canonical product context. |
| 4 | Valid Product from prior review: `Coca-Cola Soft Drink` | `Coca-Cola Soft Drink Pack of 2` | `Pack of 2` | `Coca-Cola Soft Drink, multipack of 2` | mapped | Product context is valid and the pack evidence is exact. |
| 5 | Valid Product context with title noise: `Keratin Smooth Shampoo` | `Keratin Smooth Shampoo for dry hair` | `340 ml` | `Keratin Smooth Shampoo, 340 ml` | mapped | Title noise does not invalidate a correct product context. |

## Unresolved Scenarios

| # | Product context | Listing title | Quantity text | Candidate variants | Expected outcome | Why |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Missing product context: `null` | `Amul Taaza Milk` | `500 ml` | `500 ml`, `1 L` | unresolved | Variant matching depends on product context and cannot fabricate one. |
| 2 | Invalid product context: malformed Product missing mandatory identity fields | `Amul Taaza Milk` | `1 L` | `Amul Taaza Milk, 1 L` | unresolved | The supplied context is unusable, but not inherently contradictory. |
| 3 | Stale product context with no defensible candidate | `Amul Taaza Milk` | `null` | `500 ml`, `1 L` | unresolved | The context does not supply enough current pack evidence. |
| 4 | Multiple plausible upstream product contexts, none committed | `Britannia Bread` | `400 g` | `Whole Wheat Bread`, `White Bread` | unresolved | Upstream product selection has not resolved a usable context. Product Matching owns this ambiguity. |
| 5 | Over-broad product context: `Milk` | `Amul Taaza Milk` | `null` | `Amul Taaza Milk, 500 ml`, `Amul Taaza Milk, 1 L` | unresolved | The context is too generic to support a defensible variant decision. Product Matching owns the family resolution. |

## Ambiguous Scenarios

| # | Product context | Listing title | Quantity text | Candidate variants | Expected outcome | Why |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Valid Product context: `Amul Taaza Milk` | `Amul Taaza Milk` | `1 L` | `1 L pouch`, `1 L carton` | ambiguous | The product is known, but packaging form leaves a tie. |
| 2 | Stale context compatible with current evidence: `Amul Taaza Milk` | `Amul Taaza Milk` | `Pack of 2` | `pack of 2`, `pack of 2 special pack` | ambiguous | The product context is usable, but the variants remain materially tied. |
| 3 | Valid Product context: `Britannia Bread` | `Britannia Bread` | `400 g` | `400 g loaf`, `400 g sliced pack` | ambiguous | The product is known, but packaging form leaves a tie. |
| 4 | Valid Product context: `Coca-Cola Soft Drink` | `Coca-Cola Soft Drink` | `2 x 500 ml` | `2 x 500 ml bottle`, `2 x 500 ml can pack` | ambiguous | The product is known, but component packaging leaves a tie. |
| 5 | Valid Product context with shared pack evidence: `Keratin Smooth Shampoo` | `Keratin Smooth Shampoo` | `340 ml` | `340 ml pouch`, `340 ml bottle` | ambiguous | The pack is known, but packaging form does not resolve the tie. |

## Conflicting Scenarios

| # | Product context | Listing title | Quantity text | Candidate variants | Expected outcome | Why |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Valid Product context: `Amul Taaza Toned Milk` | `Amul Taaza Milk 1 L` | `500 ml` | `500 ml`, `1 L` | conflicting | The product context and listing evidence disagree materially. |
| 2 | Stale product context contradicted by current evidence: `Toned Milk` | `Full Cream Milk` | `1 L` | `1 L full cream`, `1 L toned` | conflicting | The stale context no longer matches the current evidence. |
| 3 | Brand/category mismatch in product context: `Lay's Chips` | `Britannia Bread 400 g` | `400 g` | `Britannia Bread, 400 g` | conflicting | The supplied product context is incompatible with the observed listing. |
| 4 | Product context says 500 ml-only family | `Amul Taaza Milk` | `1 L` | `500 ml`, `1 L` | conflicting | The context and quantity evidence cannot both be true for the same pack. |
| 5 | Multiple plausible upstream contexts are mutually incompatible | `Milk` | `1 L` | `Amul Taaza Milk, 1 L`, `Amul Gold Milk, 1 L` | conflicting | The upstream product state itself cannot be reconciled with the evidence. |

## Rejected Scenarios

| # | Product context | Listing title | Quantity text | Candidate variants | Expected outcome | Why |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Valid Product context: `Amul Taaza Toned Milk` | `Amul Taaza Toned Milk` | `1 L` | `Amul Taaza Toned Milk, 500 ml` | rejected | The supplied candidate is explicitly disproved by the quantity evidence. |
| 2 | Stale context that is now superseded: `Britannia Whole Wheat Bread` | `Britannia Whole Wheat Bread` | `200 g` | `400 g` | rejected | The stale context has been ruled out by explicit pack evidence. |
| 3 | Valid Product context: `Coca-Cola Soft Drink` | `Coca-Cola Soft Drink` | `Pack of 2` | `single unit` | rejected | The only supplied candidate is contradicted by the pack evidence. |
| 4 | Valid Product context: `Lay's Chips` | `Lay's Chips` | `2 x 50 g` | `50 g single unit` | rejected | The candidate is explicitly incompatible with the multipack evidence. |
| 5 | Valid Product context: `Keratin Smooth Shampoo` | `Keratin Smooth Shampoo` | `340 ml` | `180 ml` | rejected | The entire candidate set is ruled out by explicit contrary evidence. |

## Notes

- Missing product context should not be silently substituted.
- Invalid product context should not be coerced into a plausible context.
- Stale product context may still be usable if it does not conflict with current evidence.
- Multiple plausible product contexts should remain visible rather than being collapsed.
- Product context conflicts must be escalated before pack reasoning can be trusted.
- Product-family ambiguity belongs to Product Matching, not Variant Matching.
