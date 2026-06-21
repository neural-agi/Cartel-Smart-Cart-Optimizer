# Cartel Variant Evidence Extraction Specification

This document defines how raw quantity text is converted into deterministic pack evidence for Variant Matching.

It does not define algorithms, matching logic, normalization policy, or new architecture.

The purpose is to standardize the structured evidence that Variant Matching consumes.

## 1. Scope

Variant evidence extraction is the interpretation of raw quantity text into structured pack evidence.

It applies to evidence such as:

- `500 ml`
- `1 L`
- `2 x 500 ml`
- `Pack of 2`
- `Combo Pack`

The extractor should preserve raw text and produce structured evidence without collapsing pack semantics.

## 2. Evidence Goals

The structured pack evidence must:

- preserve provenance
- preserve raw quantity text
- preserve uncertainty when pack semantics are incomplete
- distinguish single-unit, multipack, combo, assortment, and unknown structures
- remain deterministic for the same raw input

Quantity normalization and unit alias resolution are not owned by this document.
This document only defines the structured evidence shape that normalization and variant matching consume.

## 3. Structured Pack Evidence Representation

The evidence representation should be compatible with the current canonical schema concepts:

- `PackKind`
- `QuantityValue`
- `Measurement`
- `PackComponent`
- `PackConfiguration`

### Required Evidence Fields

- `raw_quantity_text: str | None`
- `pack_kind: PackKind`
- `consumer_unit_count: int | None`
- `content_per_consumer_unit: Measurement | None`
- `total_declared_content: Measurement | None`
- `packaging_form: str | None`
- `component_set: list[PackComponent]`
- `pack_configuration_status: str`
- `source_text_preserved: bool`
- `interpretation_notes: list[str]`

## 4. Deterministic Interpretation Rules

### Single Unit Quantity

Examples:

- `500 ml`
- `1 L`
- `5 kg`

Interpretation:

- `pack_kind = single_unit`
- `consumer_unit_count = 1`
- `content_per_consumer_unit = structured measurement`
- `total_declared_content = same as content_per_consumer_unit`
- `pack_configuration_status = complete` when unit and amount are explicit

### Multipack With Explicit Per-Unit Quantity

Examples:

- `2 x 500 ml`
- `3 x 100 g`

Interpretation:

- `pack_kind = multipack`
- `consumer_unit_count = explicit count`
- `content_per_consumer_unit = explicit unit measurement`
- `total_declared_content = derived total when arithmetic is safe and unambiguous`
- `pack_configuration_status = complete` when both count and per-unit content are explicit

### Pack Of N

Examples:

- `Pack of 2`
- `Pack of 6`

Interpretation:

- `pack_kind = multipack`
- `consumer_unit_count = explicit count`
- `content_per_consumer_unit = null`
- `total_declared_content = null`
- `pack_configuration_status = partial`

### Combo Pack

Examples:

- `Combo Pack`
- `Combo`
- `Assorted Pack`

Interpretation:

- `pack_kind = combo` or `assortment` when explicitly indicated
- `consumer_unit_count = null` unless explicitly stated
- `component_set` should contain component entries only when component contents are explicit
- `pack_configuration_status = partial` unless full component structure is explicit

### Mixed Or Ambiguous Quantity Text

Examples:

- `Value Pack`
- `Family Pack`
- `Best of 3`
- `Save More`

Interpretation:

- `pack_kind = unknown` unless explicit pack semantics exist
- `pack_configuration_status = unknown` or `requires_review`
- preserve the raw text without forcing a false pack assertion

## 5. Mandatory Preservation Rules

The extractor must always preserve:

- raw quantity text
- raw title context when quantity is embedded there
- provenance reference to the source artifact
- parser version
- capture timestamp

The extractor must not:

- drop the original quantity text
- reduce multipacks to a scalar quantity only
- convert combos into a single content number unless the evidence explicitly supports that
- infer packaging form from quantity alone when it is not explicit

## 6. Supported Pack Semantics

### `single_unit`

Use when the evidence describes one consumer unit with a single declared content value.

### `multipack`

Use when the evidence describes multiple consumer units of the same item or the same pack structure.

### `combo`

Use when the evidence describes a bundle of different items or a mixed commercial set.

### `assortment`

Use when the evidence describes a mixed selection that should not be collapsed into a single homogeneous unit.

### `unknown`

Use when the evidence does not support a reliable pack interpretation.

## 7. Derived Total Content

Derived total content is allowed only when:

- count is explicit
- per-unit content is explicit
- arithmetic is unambiguous

Derived total content must not erase the original pack structure.

Example:

- `2 x 500 ml` may carry `total_declared_content = 1000 ml`
- but it must still remain `multipack`

## 8. Pack Configuration Status

### `complete`

All major pack facts are explicit.

### `partial`

Some pack facts are explicit, but not enough to fully specify the pack.

### `unknown`

Pack semantics are not reliable enough to assert more.

### `requires_review`

The evidence is contradictory or materially ambiguous.

## 9. Normalization Boundary

This extractor does not decide whether `1L`, `1 L`, `1 litre`, `1 liter`, `1000ml`, and `1000 ml` are equivalent.

That equivalence is owned by the quantity normalization contract.

The extractor only preserves the raw quantity text and emits structured pack evidence that downstream normalization can complete or leave unresolved.

## 10. Interpretation Notes

Interpretation notes should record:

- why a pack kind was chosen
- whether total content was derived or directly observed
- whether pack semantics were partial
- whether evidence needs review

These notes are for downstream Variant Matching and review.

## 11. Validation Invariants

- The same raw quantity text must always produce the same structured evidence.
- Raw text must remain referenceable.
- Pack structure must remain visible.
- Multipack and combo semantics must not be flattened.
- Ambiguity must remain explicit rather than silently resolved.
