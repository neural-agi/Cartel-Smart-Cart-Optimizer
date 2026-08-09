# Parser Provenance Propagation Amendment

**Status:** Frozen contract amendment  
**Scope:** Parser provenance from acquisition through the Product Intelligence handoff

## Problem

`ListingObservation.parser_version` is required by Product Intelligence. The
parser version was already owned by the Blinkit bridge as `blinkit-parser-v1`,
but it was lost when normalized observations were produced.

Parser version and normalization version are distinct provenance values:

- `parser_version` identifies platform parser semantics;
- `normalization_version` identifies normalization semantics.

Neither value may be substituted for the other.

## Ownership and Authoritative Source

The platform parser owns `parser_version`. For Blinkit, the stable source-
controlled value is `blinkit-parser-v1`. It is explicit, deterministic, and
contains no runtime, deployment, machine, timestamp, or repository metadata.

The parser output boundary carries the value in `RawExtractionResult`. The
Blinkit parser bridge copies that value into `ParsedRetailObservationBatch`.
The batch is authoritative for the parser version consumed by normalization.

## Propagation Path

```text
Blinkit parser implementation
  -> RawExtractionResult.parser_version
  -> ParsedRetailObservationBatch.parser_version
  -> NormalizedObservation.parser_version
  -> Product Intelligence handoff
  -> ListingObservation.parser_version
```

Downstream components must consume the carried value. They must not inspect
parser code, package metadata, filenames, git state, or runtime state to
reconstruct it.

## Contract Fields

`RawExtractionResult.parser_version` is a non-empty parser-semantic version
owned by the parser boundary. Existing Blinkit output uses the explicit stable
value `blinkit-parser-v1`.

`ParsedRetailObservationBatch.parser_version` remains the batch identity input
and preserves the parser version used to interpret the raw artifact.

`NormalizedObservation.parser_version` is a required immutable provenance field.
It is copied from the parsed batch and is not a normalization policy field.

## Identity Implications

The existing `NormalizedObservationIdentityBuilder` identity inputs remain
unchanged. Parser version is provenance, not a new observation-defining input.

Changing parser version therefore does not introduce a second identity
algorithm or alter the frozen observation identity rule. The parsed batch
identity continues to distinguish parser versions through its existing
artifact-plus-parser-version rule.

## Replay

Replay of the same artifact with the same parser version preserves the exact
parser version through every contract boundary. A parser semantics change must
publish a new parser version; it must never be represented as the previous
version.

No runtime metadata participates in replay identity or provenance.

## Product Intelligence Handoff

The future Product Intelligence adapter maps:

```text
NormalizedObservation.parser_version
    -> ListingObservation.parser_version
```

It performs no inference and does not use `normalization_version`.

The adapter remains responsible only for deterministic handoff construction;
Product Intelligence remains responsible for canonical product identity,
matching, review, and assertions.

## Compatibility Implications

The artifact contract is unchanged. `RawArtifactReference` does not own parser
semantics and does not gain a parser-version field.

Existing `ParsedRetailObservationBatch` parser-version behavior is preserved.
`NormalizedObservation` gains only the required immutable provenance field;
its identity algorithm, completeness, raw artifact reference, and normalization
semantics are unchanged.

Existing Product Intelligence models and behavior are unchanged.

## Slice 6B Boundary

Slice 6B may now construct a valid `ListingObservation` parser version without
reaching backward into Blinkit-specific code:

```text
registered NormalizedObservation
  -> deterministic Product Intelligence handoff
```

This amendment does not implement that adapter or invoke the Product
Intelligence orchestrator.

## Frozen Decisions

1. Parser implementations own parser-version values.
2. Blinkit’s current parser version is `blinkit-parser-v1`.
3. Raw extraction, parsed batch, and normalized observation contracts carry
   parser provenance forward.
4. Parser and normalization versions are distinct and non-interchangeable.
5. Parser version is excluded from the existing normalized observation ID.
6. Replay preserves parser version exactly.
7. Product Intelligence consumes parser provenance; it does not reconstruct or
   own it.
