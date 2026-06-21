# Pack Equivalence Governance

## Purpose

This document defines where exact variant identity ends and where any later equivalence policy may begin.
The Variant Matcher only decides exact variant identity. It does not apply category-specific equivalence policy.

## Core Rule

Equivalent commercial usefulness is not the same as exact variant identity.

Variant Matching may not replace exact variant identity with:

- operational equivalence
- category equivalence
- commercial substitutability
- downstream catalog policy

## Definitions

### Exact Variant Identity

Two listings have the same exact variant only when their governed pack semantics match exactly.

Examples:

- `500 ml` matches `500 ml`
- `1 L` matches `1 L`
- `2 x 500 ml` matches `2 x 500 ml`
- `Pack of 6` matches `Pack of 6` when the governed pack interpretation is identical

### Operational Equivalence

Operational equivalence means the listings may be treated similarly for a later business purpose, such as shopping assistance or substitution guidance.

This is not a matcher outcome.

### Category Equivalence

Category equivalence means a later policy says two different pack forms are acceptable as a category-specific comparison or substitution rule.

This is not a matcher outcome.

## What Variant Matching May Use

Variant Matching may use only exact pack evidence and governed quantity normalization results.

It may use:

- normalized quantity representation
- pack kind
- explicit count
- explicit unit content
- evidence consistency

It may not use:

- category-specific equivalence tables
- replacement rules
- consumer substitution policy
- operational convenience

## Can Equivalence Replace Exact Variant Identity?

No.

Equivalence may never replace exact variant identity inside Variant Matching.
If two pack forms are not exactly the same under the governed quantity contract, Variant Matching may not map them as the same variant by invoking equivalence.

## Outcome Impact

Category or operational equivalence may influence only future layers, such as:

- comparison UX
- substitution ranking
- cart optimization
- human review guidance

Those later layers may observe the exact-identity result from Variant Matching, but they may not rewrite it.

## Examples

1. `2 x 500 ml` vs `1 L`
   - Exact variant identity: no
   - Operational equivalence: maybe later
   - Variant Matching outcome: not mapped by equivalence

2. `Pack of 12 batteries` vs `12 single batteries`
   - Exact variant identity: not guaranteed
   - Category equivalence: may exist later in downstream policy
   - Variant Matching outcome: unchanged by equivalence

3. `Pack of 100 pens` vs `10 packs of 10 pens`
   - Exact variant identity: no
   - Category equivalence: may be defined later for analysis
   - Variant Matching outcome: not mapped by equivalence

4. `Tissues 100 sheets` vs `Tissues 2 x 50 sheets`
   - Exact variant identity: only if governed pack semantics say so
   - Category equivalence: downstream only

5. `Eggs 12 count` vs `Eggs dozen`
   - Exact variant identity: only if normalization makes them the same governed count form
   - Category equivalence: downstream only

## Future Extension Path

Future category-specific equivalence rules may be introduced without changing Variant Matching behavior by placing them in a downstream policy layer that consumes the exact-identity outcome and attaches optional guidance for comparison or substitution.

That future layer may:

- annotate comparisons
- guide user-facing equivalence views
- support cart optimization heuristics

It may not alter the matcher's exact outcome.
