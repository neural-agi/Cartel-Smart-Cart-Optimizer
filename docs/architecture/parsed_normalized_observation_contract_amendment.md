# Parsed and Normalized Observation Contract Amendment

Status: Frozen contract amendment

Applies to:

- `docs/architecture/real_data_ingestion_rfc.md`
- `docs/architecture/scrape_job_lifecycle_rfc.md`
- `docs/architecture/scrape_job_contract_amendment.md`
- `docs/architecture/artifact_storage_contract_amendment.md`

This amendment fills only the executable-contract gaps for parsed and normalized
observations. It does not change scraper, worker, queue, scheduler, artifact
storage, Product Intelligence, Cost Intelligence, or Cart Optimization ownership.

## 1. Scope and Relationship to Slice 1

Slice 1 owns the immutable job, attempt, artifact, lifecycle, and replay
contracts. This amendment adds the parser and normalizer result contracts that
consume those values.

The ingestion flow is:

```text
RawArtifactReference
  -> ParsedRetailObservationBatch
  -> ParsedRetailObservation
  -> NormalizedObservation
  -> observation registry
```

`ParsedRetailObservation` is platform-native parser output. `NormalizedObservation`
is platform-independent observation data. Neither model is Product Intelligence
and neither model asserts canonical `Product` or `ProductVariant` identity.

## 2. Shared Rules

All contracts in this amendment are immutable frozen value objects. Collections
are tuples. Mapping-like values are tuples of unique key/value pairs in
lexicographic key order. Empty tuples are valid where the field is optional.

All string values are UTF-8 strings and must be non-empty when required. `None`
means the value was not available or could not be determined from the governed
input. It must not be replaced with a guessed value.

The following are never identity inputs for these contracts:

- timestamps;
- UUIDs;
- worker or queue metadata;
- filesystem paths, including `source_path`;
- runtime ordering or object identity.

## 3. Field-Level Source Reference

The existing Product Intelligence `EvidenceReference` remains the durable
evidence vocabulary and retains its existing `(source_type, source_id)` identity
semantics. It is not replaced or redefined by this amendment.

The parser/normalizer boundary adds the following immutable wrapper for field
location:

| Field | Type | Required | Identity | Meaning |
|---|---|---:|---:|---|
| `evidence_reference` | `EvidenceReference` | yes | yes through its source identity | Durable artifact/evidence identity |
| `locator` | non-empty string | yes | yes | Stable field locator supplied by the parser, such as a raw field name, source index path, selector, or byte/line locator |

The wrapper is named `ObservationFieldReference`. `locator` is descriptive of
the source location; it does not become a filesystem path or storage API.
Equality is structural after evidence identity and locator are compared. Field
references are preserved in first-seen tuple order and duplicate exact pairs are
rejected.

## 4. Completeness

`ObservationCompleteness` is an immutable value object with:

| Field | Type | Required | Identity | Meaning |
|---|---|---:|---:|---|
| `state` | `CompletenessState` | yes | yes | `COMPLETE`, `PARTIAL`, `EMPTY`, or `UNKNOWN` |
| `scope_reference` | non-empty string or `None` | no | yes when present | Explicit scope whose coverage is being described |
| `basis` | non-empty string | yes | yes | Deterministic parser/normalizer evidence supporting the state |
| `missing_scope` | tuple of non-empty strings | no | yes | Canonically ordered scope portions not covered; required for `PARTIAL` |

`COMPLETE` means the declared scope was evaluated and no governed records are
missing. `PARTIAL` means the scope is known but only part was captured.
`EMPTY` means zero records were observed and explicit evidence proves that the
declared scope was evaluated. `UNKNOWN` means completeness cannot be established.

Rules:

- `COMPLETE` requires `scope_reference` and an empty `missing_scope`.
- `PARTIAL` requires `scope_reference` and non-empty `missing_scope`.
- `EMPTY` requires `scope_reference` and an empty observation collection at the
  enclosing batch.
- `UNKNOWN` requires a non-empty `basis` explaining why completeness is unknown.
- An empty batch is valid only with `EMPTY` or `COMPLETE` completeness. It is
  never implicitly complete.
- A non-empty batch may be `COMPLETE`, `PARTIAL`, or `UNKNOWN`, but never
  `EMPTY`.

Completeness is preserved downstream. It does not assert catalog coverage,
product availability, or Product Intelligence matching success.

## 5. Parser Version

The exact field name is `parser_version`.

| Field | Type | Required | Owner | Identity |
|---|---|---:|---|---:|
| `parser_version` | non-empty stable version string | yes on `ParsedRetailObservationBatch` | platform parser | yes |

The value is declared by the parser implementation and identifies parser
semantics, not execution time. It must be stable for a given parser contract and
must change when parser interpretation changes. Timestamps, deployment IDs,
worker IDs, and runtime configuration do not form part of the version.

## 6. ParsedRetailObservation

`ParsedRetailObservation` is the immutable platform-parser output consumed only
by normalization and replay.

| Field | Type | Required | Identity | Meaning |
|---|---|---:|---:|---|
| `source_record_id` | non-empty string | yes | yes | Stable record identifier within the parsed artifact, normally the parser's source index or platform record ID |
| `platform` | `Platform` | yes | yes | Platform declared by the parser |
| `raw_title` | non-empty string or `None` | no | no | Title text as observed |
| `raw_quantity` | non-empty string or `None` | no | no | Quantity/pack text as observed |
| `raw_category` | non-empty string or `None` | no | no | Category text as observed |
| `platform_identifiers` | canonical tuple of unique string pairs | no | yes | Platform-native IDs only; never canonical Product IDs |
| `raw_price_text` | non-empty string or `None` | no | no | Displayed price text; never a verified payable amount |
| `raw_mrp_text` | non-empty string or `None` | no | no | MRP text, without a trust assertion |
| `offer_text` | non-empty string or `None` | no | no | Offer text as observed |
| `availability_signal` | non-empty string or `None` | no | no | Platform/UI availability signal only |
| `field_references` | tuple of `ObservationFieldReference` | yes | yes | Field-level provenance for populated and explicitly missing parsed fields |

`platform_identifiers` keys are unique and canonically ordered. The parser may
preserve ambiguous or unavailable values as `None` or raw text. No field is a
canonical product assertion, final monetary value, verified discount, or
guaranteed inventory fact.

## 7. ParsedRetailObservationBatch

`ParsedRetailObservationBatch` is the immutable parser result for one raw
artifact and one parser version.

| Field | Type | Required | Identity | Meaning |
|---|---|---:|---:|---|
| `batch_id` | deterministic string | derived | yes | Identity generated from `raw_artifact_reference.artifact_id` and `parser_version` |
| `raw_artifact_reference` | `RawArtifactReference` | yes | yes through `artifact_id` | Durable source artifact supplied by acquisition/job boundary |
| `parser_version` | non-empty stable version string | yes | yes | Parser semantics used for this result |
| `observations` | tuple of `ParsedRetailObservation` | yes | content, not batch identity | Parser records in deterministic source order |
| `warnings` | tuple of non-empty strings | yes | no | Parser diagnostics preserved in emission order |
| `completeness` | `ObservationCompleteness` | yes | yes | Explicit result coverage state |

Observations are ordered by the parser-declared source order. The parser must
provide a unique `source_record_id`; duplicate IDs are invalid. Warnings remain
ordered and are not used to alter batch identity.

`batch_id` is generated only from the canonical pair:

```text
raw_artifact_identity = raw_artifact_reference.artifact_id
parser_version
```

The raw artifact payload, storage reference, source path, timestamps, observation
values, warnings, and runtime metadata do not participate in `batch_id`.

## 8. NormalizedObservation

`NormalizedObservation` is the immutable platform-independent observation passed
to the observation registry and Product Intelligence ingestion.

| Field | Type | Required | Identity | Meaning |
|---|---|---:|---:|---|
| `observation_id` | deterministic string | derived | yes | Identity generated from the immutable observation-defining fields below |
| `platform` | `Platform` | yes | yes | Source platform retained after normalization |
| `source_record_id` | non-empty string | yes | yes | Parsed source record retained for traceability |
| `raw_artifact_reference` | `RawArtifactReference` | yes | yes through `artifact_id` | Original immutable source evidence |
| `normalized_name` | non-empty string or `None` | no | yes when present | Platform-independent normalized display text, not canonical product identity |
| `normalized_quantity` | non-empty string or `None` | no | yes when present | Platform-independent quantity representation without unsupported conversion |
| `normalized_category` | non-empty string or `None` | no | yes when present | Platform-independent category label, not a canonical category assertion |
| `platform_identifiers` | canonical tuple of unique string pairs | no | yes | Platform-native identifiers retained without canonical mapping |
| `observed_price_text` | non-empty string or `None` | no | yes when present | Normalized representation of observed price text, not money |
| `observed_mrp_text` | non-empty string or `None` | no | yes when present | Normalized representation of observed MRP text, without trust semantics |
| `observed_offer_text` | non-empty string or `None` | no | yes when present | Normalized offer text, not a verified discount |
| `availability_signal` | non-empty string or `None` | no | yes when present | Normalized availability signal, not guaranteed inventory |
| `evidence_references` | tuple of `EvidenceReference` | yes | yes | Durable provenance in first-seen order, exact duplicates rejected |
| `field_references` | tuple of `ObservationFieldReference` | yes | yes | Field-level provenance |
| `completeness` | `ObservationCompleteness` | yes | yes | Completeness inherited from the normalized result scope |
| `normalization_version` | non-empty stable version string | yes | yes | Normalization semantics used for this value |

`observation_id` is generated from platform, source record ID, raw artifact ID,
all normalized observation-defining values, platform identifiers, completeness,
and normalization version. It excludes timestamps, storage references,
filesystem paths, worker metadata, and presentation formatting.

This model must not contain canonical Product or ProductVariant identifiers,
verified discount values, final payable cost, or guaranteed inventory state.
Those decisions remain owned by downstream Product Intelligence and Cost
Intelligence contracts.

## 9. Normalization Version

The exact field name is `normalization_version`.

It is a required, non-empty stable version string owned by the normalizer and
included in `NormalizedObservation.observation_id`. It identifies normalization
semantics, not a runtime execution. A semantic normalization change requires a
new version. It is preserved for replay and audit.

## 10. RawArtifactReference Relationship

`RawArtifactReference` is produced by the scraper/artifact registry boundary.
The parser consumes it and may read its payload through the `ArtifactStore`
abstraction. The parser does not create or alter `artifact_id`, `job_id`,
`attempt_id`, `content_digest`, or `storage_reference`.

`source_path` from an upstream parser or extraction result is acquisition-local
metadata only. It is never copied into domain identity or used as a durable
artifact reference. `ArtifactStore` does not generate artifact, job, or attempt
identities.

## 11. Deterministic Serialization

All models use the repository's frozen Pydantic serialization conventions:

- frozen models;
- enum values serialized using their canonical values;
- tuples serialized in their declared canonical order;
- mapping-like tuples sorted by key;
- no timestamps or runtime metadata in identity payloads;
- identity payloads serialized with sorted keys, stable separators, and UTF-8
  encoding before hashing.

Serialization of a complete model may include provenance, warnings, and audit
metadata. Identity generation must use only the explicitly listed identity
fields and must not hash an unrestricted full model dump.

## 12. Compatibility and Replay

Replaying the same raw artifact with the same parser version produces the same
`ParsedRetailObservationBatch.batch_id`. Replaying with a different parser
version produces a different batch identity even when the artifact is unchanged.

Replaying normalization with the same normalized inputs and normalization version
produces the same `NormalizedObservation.observation_id`. Changing normalization
semantics requires a new normalization version and therefore a new observation
identity.

Raw artifact identity remains stable across parser and normalization replay.
Operational timestamps, worker identity, queue position, and local source paths
may differ without changing domain identity.

## 13. Implementation Impact on Slice 3

Slice 3 may now implement a Blinkit bridge that:

1. consumes an existing `RawExtractionResult` plus a supplied
   `RawArtifactReference`;
2. declares an explicit stable `parser_version`;
3. emits `ParsedRetailObservation` records preserving raw strings and field
   references;
4. emits `ParsedRetailObservationBatch` with explicit completeness;
5. optionally emits `NormalizedObservation` only through a separately governed
   normalizer boundary.

The bridge must not derive durable identity from `source_path`, invent final
prices, infer stock guarantees, or trigger downstream intelligence.

## 14. Open Contract Decisions

None. The decisions required to implement the parsed and normalized observation
contracts are frozen by this amendment.
