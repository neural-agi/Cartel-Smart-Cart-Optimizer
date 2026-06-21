# Cartel Variant Quantity Normalization Contract

This document defines the ownership boundary between raw quantity input, quantity normalization, and Variant Matching.

It does not define conversion algorithms or matching logic.

## 1. Pipeline Contract

```text
Input Layer
  -> Normalization Layer
  -> Variant Matcher
```

### Input Layer

The input layer provides raw quantity evidence, including:

- quantity text from the listing
- quantity text embedded in the title
- source artifact reference
- parser version
- capture context reference

The input layer does not promise canonical units.

### Normalization Layer

The normalization layer owns:

- unit alias resolution
- spacing and punctuation canonicalization
- quantity count extraction
- pack configuration assembly
- measurement canonicalization within a known unit family

### Variant Matcher

The matcher consumes normalized pack evidence and decides whether the listing maps to a canonical `ProductVariant`.

The matcher does not perform quantity normalization itself.

## 2. Matcher Assumptions

The Variant Matcher may assume:

- raw quantity text has been preserved
- known unit aliases have already been canonicalized
- explicit count expressions have already been parsed
- pack kind, count, and measurement fields are already structured when the normalization layer could determine them
- unknowns are represented explicitly as null or unknown status, not as inferred facts

The matcher may not assume:

- that all quantity spellings are already semantically identical unless normalization asserted that equivalence
- that total content can erase pack structure
- that a scalar quantity implies single-unit packaging
- that packaging form is known if it was not explicitly normalized
- that unknown units can be compared with known units as if they were equivalent

## 3. Normalized Quantity Representation

The normalized representation must preserve the same pack evidence concepts used by the canonical schema:

- `pack_kind`
- `consumer_unit_count`
- `content_per_consumer_unit`
- `total_declared_content`
- `packaging_form`
- `component_set`
- `pack_configuration_status`

### Representation Rules

- `500 ml` and `1 L` are normalized as single-unit pack evidence with explicit volume measurements.
- `2 x 500 ml` is normalized as multipack evidence with explicit count and per-unit content.
- `Pack of 2` is normalized as multipack evidence with explicit count and partial pack information.
- `Combo Pack` is normalized as combo or assortment evidence with partial or explicit component structure.
- `1L`, `1 L`, `1 litre`, `1 liter`, `1000ml`, and `1000 ml` are all normalized into equivalent structured quantity evidence when the unit family is known and the normalization layer can safely resolve them.

The matcher should only rely on the normalized representation, not on the raw spellings.

## 4. Measurement Dimension Governance

Quantity normalization must assign each measurement to a governed dimension before Variant Matching consumes it.

### Governed Dimensions

- `volume`
- `mass`
- `count`
- `unit_based_consumer_goods`
- `unknown`

### Dimension Meaning

- `volume` covers liquid or volumetric quantities such as `ml`, `l`, `liter`, and `litre`.
- `mass` covers weight quantities such as `mg`, `g`, `kg`, and other explicitly mass-based units.
- `count` covers explicit item counts such as `2`, `pack of 6`, `pcs`, `pieces`, and other count-based expressions.
- `unit_based_consumer_goods` covers consumer units expressed as discrete sellable units rather than mass or volume when the unit itself is the commercial measure.
- `unknown` means the unit family cannot be safely classified.

### Comparison Rules

The matcher may compare only within the same governed dimension.

- volume may compare with volume
- mass may compare with mass
- count may compare with count
- unit_based_consumer_goods may compare only with unit_based_consumer_goods when the normalized unit family is the same

### Never Compare

The matcher must never compare:

- volume with mass
- volume with count
- volume with unit_based_consumer_goods
- mass with count
- mass with unit_based_consumer_goods
- count with unit_based_consumer_goods unless normalization has already resolved them into the same governed count family
- any known dimension with `unknown`

### Unknown Dimension Handling

If a quantity cannot be assigned a governed dimension:

- preserve the raw quantity text
- preserve the unknown unit token
- mark the pack configuration as `unknown` or `requires_review`
- do not use the value as a positive match signal

## 5. Normalization Invariants

The normalization layer must preserve these invariants:

1. Raw quantity text remains referenceable.
2. The same raw quantity input produces the same normalized output.
3. Pack structure is not flattened into a scalar quantity.
4. Multipacks remain multipacks even when total content can be derived.
5. Combos and assortments remain structurally distinct from homogeneous packs.
6. Unknown quantity semantics remain explicit.
7. Normalization never invents pack facts that were not supported by the input.

## 6. Failure Handling

If normalization cannot safely resolve the quantity text, it must not fabricate a canonical pack.

### Required Failure States

- `unknown`
- `partial`
- `requires_review`

### Handling Rules

- `unknown` means the text cannot be interpreted safely.
- `partial` means some pack facts are known, but not enough to fully specify the pack.
- `requires_review` means the text is materially ambiguous or contradictory.

When normalization fails:

- preserve the raw quantity text
- preserve the unresolved status
- allow Variant Matching to return `unresolved`, `ambiguous`, or `conflicting` as appropriate

## 7. Unknown-Unit Handling

Unknown-unit handling is explicit.

If the quantity text contains a unit that cannot be mapped to a known unit family:

- the raw unit token is preserved
- the measurement dimension is `unknown`
- the pack configuration status is `unknown` or `requires_review`
- the matcher must not assume equivalence with a known unit family

Unknown units are evidence of uncertainty, not evidence of equivalence.

## 8. What The Matcher May Assume About Normalized Input

The matcher may assume normalized quantity evidence is already organized into:

- explicit count
- explicit per-unit content when known
- explicit total content when safely derivable
- explicit pack kind or unknown pack kind
- explicit packaging form when material
- explicit component structure when present

The matcher may then compare candidates deterministically against those fields.

## 9. What The Matcher May Not Assume

The matcher may not assume:

- quantity normalization resolved every ambiguity
- unit conversion answers substitute for pack semantics
- a known total content implies exact variant identity
- a known pack count implies a single product variant
- any missing quantity field can be inferred from price or offer behavior

## 10. Boundary Summary

- Input Layer preserves raw quantity evidence.
- Normalization Layer owns canonical quantity interpretation.
- Variant Matcher consumes normalized pack evidence only.

This separation prevents raw spelling variation from becoming matching logic.
