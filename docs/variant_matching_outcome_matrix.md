# Cartel Variant Matching Outcome Matrix

This document provides deterministic validation scenarios for Variant Matching.

It uses only concepts already defined in:

- `docs/variant_matching_architecture.md`
- `docs/variant_matching_implementation_spec.md`
- `docs/variant_evidence_extraction_spec.md`
- `docs/variant_quantity_normalization_contract.md`

No new concepts, algorithms, or architecture are introduced here.

Assumption:

- quantity normalization has already produced structured pack evidence where possible
- product context has already passed validation unless a scenario explicitly tests product-context failure

---

## 1. Mapped Scenarios

### Mapped 1

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk`
3. Quantity text: `500 ml`
4. Candidate variants: `Amul Taaza Milk, 500 ml`
5. Expected outcome: `mapped`
6. Why: explicit single-unit pack evidence matches the only candidate exactly.

### Mapped 2

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk Toned`
3. Quantity text: `1 L`
4. Candidate variants: `Amul Taaza Milk, 1 L`
5. Expected outcome: `mapped`
6. Why: product context is plausible and the pack evidence exactly matches the candidate.

### Mapped 3

1. Product context: `Britannia Bread`
2. Listing title: `Britannia Whole Wheat Bread`
3. Quantity text: `400 g`
4. Candidate variants: `Britannia Whole Wheat Bread, 400 g`
5. Expected outcome: `mapped`
6. Why: the candidate pack and product context align without contradiction.

### Mapped 4

1. Product context: `Coca-Cola Soft Drink`
2. Listing title: `Coca-Cola Soft Drink Pack of 2`
3. Quantity text: `Pack of 2`
4. Candidate variants: `Coca-Cola Soft Drink, multipack of 2`
5. Expected outcome: `mapped`
6. Why: explicit multipack evidence matches the candidate pack kind and count.

### Mapped 5

1. Product context: `Lay's Chips`
2. Listing title: `Lay's Magic Masala Chips`
3. Quantity text: `50 g`
4. Candidate variants: `Lay's Magic Masala Chips, 50 g`
5. Expected outcome: `mapped`
6. Why: exact pack evidence and variant identity align.

## 2. Ambiguous Scenarios

### Ambiguous 1

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk`
3. Quantity text: `1 L`
4. Candidate variants: `Amul Taaza Milk, 1 L pouch`; `Amul Taaza Milk, 1 L carton`
5. Expected outcome: `ambiguous`
6. Why: pack size matches, but packaging form does not resolve the tie.

### Ambiguous 2

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk`
3. Quantity text: `Pack of 2`
4. Candidate variants: `Amul Taaza Milk, pack of 2`; `Amul Taaza Milk, pack of 2 special pack`
5. Expected outcome: `ambiguous`
6. Why: the quantity is sufficient for a multipack, but the candidates remain tied.

### Ambiguous 3

1. Product context: `Britannia Bread`
2. Listing title: `Britannia Bread`
3. Quantity text: `400 g`
4. Candidate variants: `Britannia Bread, 400 g`; `Britannia Bread, 400 g value pack`
5. Expected outcome: `ambiguous`
6. Why: pack evidence is incomplete for exact variant separation.

### Ambiguous 4

1. Product context: `Colgate Toothpaste`
2. Listing title: `Colgate Toothpaste`
3. Quantity text: `2 x 50 g`
4. Candidate variants: `Colgate Toothpaste, multipack 2 x 50 g`; `Colgate Toothpaste, bundle 2 x 50 g`
5. Expected outcome: `ambiguous`
6. Why: the pack is clearly a multipack, but candidates remain materially tied.

### Ambiguous 5

1. Product context: `Kellogg's Cereal`
2. Listing title: `Kellogg's Cereal`
3. Quantity text: `Combo Pack`
4. Candidate variants: `Kellogg's Cereal, combo pack A`; `Kellogg's Cereal, combo pack B`
5. Expected outcome: `ambiguous`
6. Why: combo semantics are present, but component detail is insufficient to choose.

## 3. Unresolved Scenarios

### Unresolved 1

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk`
3. Quantity text: `null`
4. Candidate variants: `Amul Taaza Milk, 500 ml`; `Amul Taaza Milk, 1 L`
5. Expected outcome: `unresolved`
6. Why: there is not enough pack evidence to select a variant.

### Unresolved 2

1. Product context: `Britannia Bread`
2. Listing title: `Britannia Bread`
3. Quantity text: `Value Pack`
4. Candidate variants: `Britannia Bread, 400 g`; `Britannia Bread, 450 g`
5. Expected outcome: `unresolved`
6. Why: the raw quantity text does not establish a pack configuration.

### Unresolved 3

1. Product context: `Rice`
2. Listing title: `Basmati Rice`
3. Quantity text: `Family Pack`
4. Candidate variants: `Basmati Rice, 1 kg`; `Basmati Rice, 5 kg`
5. Expected outcome: `unresolved`
6. Why: the evidence is too generic to identify the exact variant.

### Unresolved 4

1. Product context: `Shampoo`
2. Listing title: `Keratin Smooth Shampoo`
3. Quantity text: `null`
4. Candidate variants: `Keratin Smooth Shampoo, 180 ml`; `Keratin Smooth Shampoo, 340 ml`
5. Expected outcome: `unresolved`
6. Why: product context is plausible, but pack identity is absent.

### Unresolved 5

1. Product context: `Chips`
2. Listing title: `Magic Masala Chips`
3. Quantity text: `null`
4. Candidate variants: `Magic Masala Chips, 50 g`; `Magic Masala Chips, 70 g`
5. Expected outcome: `unresolved`
6. Why: no pack evidence exists to support a defensible variant mapping.

### Unresolved 6

1. Product context: `Milk`
2. Listing title: `Milk`
3. Quantity text: `2 L`
4. Candidate variants: `500 ml`; `1 L`
5. Expected outcome: `unresolved`
6. Why: the evaluated candidate set is incomplete, so the matcher must not convert candidate-set failure into rejection.

## 4. Conflicting Scenarios

### Conflicting 1

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk 1 L`
3. Quantity text: `500 ml`
4. Candidate variants: `Amul Taaza Milk, 500 ml`; `Amul Taaza Milk, 1 L`
5. Expected outcome: `conflicting`
6. Why: title and quantity text disagree materially.

### Conflicting 2

1. Product context: `Coca-Cola Soft Drink`
2. Listing title: `Coca-Cola Soft Drink Pack of 2`
3. Quantity text: `1 unit`
4. Candidate variants: `Coca-Cola Soft Drink, multipack of 2`
5. Expected outcome: `conflicting`
6. Why: explicit pack count contradicts the quantity text.

### Conflicting 3

1. Product context: `Lay's Chips`
2. Listing title: `Lay's Chips 50 g`
3. Quantity text: `2 x 50 g`
4. Candidate variants: `Lay's Chips, 50 g`
5. Expected outcome: `conflicting`
6. Why: the listing advertises a multipack while the candidate is single-unit.

### Conflicting 4

1. Product context: `Kellogg's Cereal`
2. Listing title: `Kellogg's Cereal Combo Pack`
3. Quantity text: `500 g`
4. Candidate variants: `Kellogg's Cereal, single unit 500 g`
5. Expected outcome: `conflicting`
6. Why: combo semantics conflict with single-unit candidate interpretation.

### Conflicting 5

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk`
3. Quantity text: `1 L`
4. Candidate variants: `Amul Taaza Milk, 500 ml`
5. Expected outcome: `conflicting`
6. Why: the candidate is incompatible with the explicit quantity evidence.

## 5. Rejected Scenarios

Assumption:

- these rows assume the candidate pool coverage state is `representative`, so the evidence can legitimately disprove the evaluated set rather than merely expose incomplete coverage.

### Rejected 1

1. Product context: `Amul Taaza Milk`
2. Listing title: `Amul Taaza Milk`
3. Quantity text: `1 L`
4. Candidate variants: `Amul Taaza Milk, 500 ml`
5. Expected outcome: `rejected`
6. Why: the candidate does not match the explicit quantity evidence.

### Rejected 2

1. Product context: `Britannia Bread`
2. Listing title: `Britannia Bread`
3. Quantity text: `400 g`
4. Candidate variants: `Britannia Bread, 200 g`
5. Expected outcome: `rejected`
6. Why: the candidate pack size is incompatible with the observed pack evidence.

### Rejected 3

1. Product context: `Coca-Cola Soft Drink`
2. Listing title: `Coca-Cola Soft Drink`
3. Quantity text: `Pack of 2`
4. Candidate variants: `Coca-Cola Soft Drink, single unit`
5. Expected outcome: `rejected`
6. Why: the candidate requires a single-unit interpretation that the evidence does not support.

### Rejected 4

1. Product context: `Lay's Chips`
2. Listing title: `Lay's Chips`
3. Quantity text: `2 x 50 g`
4. Candidate variants: `Lay's Chips, 50 g`
5. Expected outcome: `rejected`
6. Why: the candidate is incompatible with the explicit multipack evidence.

### Rejected 5

1. Product context: `Shampoo`
2. Listing title: `Keratin Smooth Shampoo`
3. Quantity text: `340 ml`
4. Candidate variants: `Keratin Smooth Shampoo, 180 ml`
5. Expected outcome: `rejected`
6. Why: the candidate pack size is specifically ruled out by the evidence.

## 6. Validation Notes

- Mapped means one candidate is justified.
- Ambiguous means several candidates remain materially tied.
- Unresolved means evidence is insufficient.
- Conflicting means the evidence itself is incompatible.
- Rejected means a specific candidate is ruled out.

The matrix is intended to validate implementation behavior before code is written.
