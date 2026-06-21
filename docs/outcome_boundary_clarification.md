# Cartel Outcome Boundary Clarification

This document defines deterministic boundaries between Variant Matching outcomes.

It exists to remove overlap between:

- `conflicting` and `rejected`
- `ambiguous` and `unresolved`
- `unresolved` and `rejected`
- `ambiguous` and `conflicting`
- `unresolved` and `conflicting`

The rules below are implementation-facing. They do not change architecture.

## 1. Global Decision Order

A single Variant Matching request must resolve to exactly one outcome.

Use this order:

In this document, `representative` means a coverage declaration that was earned under `coverage_qualification_contract.md` and accepted under `coverage_validation_contract.md`.

1. `conflicting` if the evidence bundle or product context is internally incompatible.
2. `ambiguous` if two or more candidates remain viable and materially tied.
3. `mapped` if exactly one candidate remains viable and meets the minimum support bar.
4. `rejected` if every candidate is explicitly disproved by consistent evidence and the candidate pool is declared `representative` under `candidate_pool_coverage_governance.md`.
5. `unresolved` if no candidate is defensible because evidence is insufficient or candidate coverage is incomplete.

Notes:

- `conflicting` is an evidence-integrity outcome.
- `ambiguous` is a tie outcome.
- `mapped` is a positive acceptance outcome.
- `rejected` is a clean negative outcome.
- `unresolved` is an insufficient-information outcome.

Candidate-level rejection may still happen internally, but the final request outcome must follow the order above.

## 2. Contradiction Types And Outcome Mapping

### Evidence Contradiction

Definition:

- raw evidence is internally incompatible
- example: title and quantity text disagree materially

Possible outcome:

- `conflicting` only

### Product-Context Contradiction

Definition:

- the supplied product context is incompatible with the listing evidence
- example: product context says one family, while the listing evidence clearly points to another

Possible outcome:

- `conflicting` only

### Candidate Contradiction

Definition:

- one or more candidates do not fit the evidence
- example: `500 ml` candidate against explicit `1 L` evidence

Possible outcomes:

- `mapped`
- `ambiguous`
- `rejected`
- `unresolved`

Candidate contradiction must never produce `conflicting` by itself.

---

## 3. Conflicting vs Rejected

### Deciding Principle

- `conflicting` means the evidence itself cannot be made consistent.
- `rejected` means the evidence is internally consistent, but it explicitly disproves every candidate in a pool whose coverage state is `representative`.

### Escalation Rules

- `conflicting` goes to review because the source evidence must be inspected.
- `rejected` does not require review unless review policy requires sample validation.

### Examples

1. Title: `Amul Taaza Milk 1 L`
   Quantity: `500 ml`
   Candidate: `Amul Taaza Milk, 500 ml`
   Outcome: `conflicting`
   Why: title and quantity disagree materially.

2. Title: `Amul Taaza Milk`
   Quantity: `1 L`
   Candidate: `Amul Taaza Milk, 500 ml`
   Outcome: `rejected`
   Why: evidence is consistent, but the candidate is explicitly ruled out by the observed quantity.

3. Title: `Coca-Cola Soft Drink Pack of 2`
   Quantity: `Pack of 2`
   Candidate: `Coca-Cola Soft Drink, single unit`
   Outcome: `rejected`
   Why: the pack evidence cleanly disproves the single-unit candidate.

---

## 4. Ambiguous vs Unresolved

### Deciding Principle

- `ambiguous` means at least two candidates remain viable after deterministic filtering.
- `unresolved` means fewer than two viable candidates remain and the matcher cannot justify a unique mapping.

### Escalation Rules

- `ambiguous` goes to review because a human can inspect the tied candidates.
- `unresolved` goes to evidence capture, recapture, or broader candidate generation unless policy says otherwise.

### Examples

1. Title: `Amul Taaza Milk`
   Quantity: `1 L`
   Candidates: `1 L pouch`, `1 L carton`
   Outcome: `ambiguous`
   Why: pack size is sufficient, but packaging form leaves two viable options.

2. Title: `Amul Taaza Milk`
   Quantity: `null`
   Candidates: `500 ml`, `1 L`
   Outcome: `unresolved`
   Why: there is not enough pack evidence to keep more than one candidate viable.

3. Title: `Kellogg's Cereal`
   Quantity: `Combo Pack`
   Candidates: `combo pack A`, `combo pack B`
   Outcome: `ambiguous`
   Why: combo semantics are explicit, but the component detail does not separate the tie.

---

## 5. Unresolved vs Rejected

### Deciding Principle

- `unresolved` means evidence is insufficient and does not explicitly disprove the candidate set.
- `rejected` means the evidence explicitly disproves every candidate in a pool whose coverage state is `representative`.

### Escalation Rules

- `unresolved` goes to better evidence or broader candidate generation.
- `rejected` is a clean negative decision and should not be converted into review noise unless policy requires it.

### Examples

1. Title: `Amul Taaza Milk`
   Quantity: `null`
   Candidates: `500 ml`, `1 L`
   Outcome: `unresolved`
   Why: there is no explicit pack evidence to disprove or support the candidates.

2. Title: `Britannia Bread`
   Quantity: `400 g`
   Candidate: `200 g`
   Outcome: `rejected`
   Why: the candidate is explicitly ruled out by the pack size.

3. Title: `Lay's Chips`
   Quantity: `2 x 50 g`
   Candidate: `50 g single unit`
   Outcome: `rejected`
   Why: the multipack evidence disproves the single-unit candidate.

### Candidate-Set Failure Versus True Rejection

### Deciding Principle

- `candidate-set failure` means every evaluated candidate is wrong, but the matcher cannot trust the pool as `representative`.
- `true rejection` means the evidence explicitly disproves every evaluated candidate and the pool coverage state is `representative`.

### Escalation Rules

- candidate-set failure -> `unresolved`
- true rejection -> `rejected`

### Examples

1. Title: `2 L Milk`
   Quantity: `2 L`
   Candidates: `500 ml`, `1 L`
   Outcome: `unresolved`
   Why: every evaluated candidate is wrong, but the pool is obviously incomplete.

2. Title: `Pack of 2`
   Quantity: `Pack of 2`
   Candidates: `single unit`, `3-pack`
   Outcome: `unresolved`
   Why: the evaluated candidate pool is too narrow to conclude true rejection.

3. Title: `Amul Taaza Milk`
   Quantity: `1 L`
   Candidates: `500 ml`, `1 L`, `2 x 500 ml`
   Outcome: `rejected`
   Why: the evidence explicitly disproves the evaluated candidate set and the pool coverage state is `representative`.

---

## 6. Ambiguous vs Conflicting

### Deciding Principle

- `ambiguous` means the evidence is internally consistent but not decisive.
- `conflicting` means the evidence contains incompatible facts and cannot be treated as a simple tie.

### Escalation Rules

- `ambiguous` goes to review as a tie.
- `conflicting` goes to review as an evidence-quality problem.

### Examples

1. Title: `Amul Taaza Milk`
   Quantity: `1 L`
   Candidates: `1 L pouch`, `1 L carton`
   Outcome: `ambiguous`
   Why: the evidence is consistent and only the packaging form is unresolved.

2. Title: `Amul Taaza Milk 1 L`
   Quantity: `500 ml`
   Candidates: `500 ml`, `1 L`
   Outcome: `conflicting`
   Why: the source fields disagree materially.

3. Title: `Coca-Cola Soft Drink Pack of 2`
   Quantity: `Pack of 2`
   Candidates: `single unit`, `multipack of 2`
   Outcome: `conflicting`
   Why: the candidate set contains a candidate that is directly contradicted by the pack evidence.

---

## 7. Unresolved vs Conflicting

### Deciding Principle

- `unresolved` means the matcher does not have enough evidence to separate candidates.
- `conflicting` means the evidence contains a contradiction that makes the request unsafe to resolve by candidate ranking.

### Escalation Rules

- `unresolved` should trigger evidence acquisition, recapture, or broader candidate generation.
- `conflicting` should trigger review of the source artifact and parser output.

### Examples

1. Title: `Keratin Smooth Shampoo`
   Quantity: `null`
   Candidates: `180 ml`, `340 ml`
   Outcome: `unresolved`
   Why: evidence is incomplete, but not contradictory.

2. Title: `Keratin Smooth Shampoo 340 ml`
   Quantity: `180 ml`
   Candidates: `180 ml`, `340 ml`
   Outcome: `conflicting`
   Why: title and quantity disagree materially.

3. Title: `Value Pack`
   Quantity: `~1L`
   Candidates: `1 L`, `2 x 500 ml`
   Outcome: `unresolved`
   Why: the quantity text is too weak to establish a pack contradiction or a unique pack.

---

## 8. Exhaustiveness Rule

Every valid request must land in exactly one of the five outcomes.

The implementation should therefore treat these conditions as mutually exclusive:

- incompatible evidence -> `conflicting`
- multiple viable candidates -> `ambiguous`
- exactly one viable candidate with enough support -> `mapped`
- zero viable candidates with explicit disproval -> `rejected`
- zero viable candidates with insufficient evidence -> `unresolved`

This is the final boundary contract for Variant Matching.
