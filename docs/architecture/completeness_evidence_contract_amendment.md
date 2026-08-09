# Completeness Evidence Contract Amendment

Status: Frozen contract amendment

Applies to:

- `docs/architecture/real_data_ingestion_rfc.md`
- `docs/architecture/scrape_job_lifecycle_rfc.md`
- `docs/architecture/scrape_job_contract_amendment.md`
- `docs/architecture/parsed_normalized_observation_contract_amendment.md`

This amendment resolves only the contradiction between empty extraction results
and `ObservationCompleteness`. It does not redesign the ingestion pipeline and
does not change Product Intelligence, Cost Intelligence, Cart Optimization, or
artifact storage ownership.

## 1. Ownership Boundary

Completeness evidence originates at the acquisition/scraper boundary.

The scraper knows which declared request scope it evaluated and whether its
pagination or capture termination condition proves that scope was exhausted.
The parser may preserve this metadata but must not infer it from the number of
parsed products.

`RawExtractionResult` is the existing handoff from the Blinkit parser to later
ingestion stages. It therefore gains explicit acquisition-supplied completeness
metadata. No separate worker or registry lookup is required.

The parser bridge consumes this metadata and maps it to the already frozen
`ObservationCompleteness` value object.

## 2. Declared Evaluation Scope

Every ingestion-compliant retail extraction must carry:

| Field | Type | Required | Identity | Producer | Meaning |
|---|---|---:|---:|---|---|
| `evaluation_scope` | non-empty string | yes | yes | acquisition/scraper boundary | Stable opaque identifier for the requested retail scope |

For a search capture, the scope is the declared search request plus its explicit
capture context, including query, platform, location, locale, and session scope.
The acquisition boundary derives this value from governed request/context inputs;
it must not contain timestamps, filesystem paths, worker IDs, queue positions, or
random values.

The scope identifier is not a catalog-coverage claim by itself. It identifies
what the scraper was asked to evaluate.

## 3. Capture Coverage Metadata

Every ingestion-compliant `RawExtractionResult` must carry immutable
`capture_coverage` metadata:

| Field | Type | Required | Identity | Producer | Meaning |
|---|---|---:|---:|---|---|
| `evaluation_scope` | non-empty string | yes | yes | acquisition/scraper boundary | Must equal the enclosing extraction scope |
| `pages_evaluated` | positive integer | yes | yes | acquisition/scraper boundary | Number of pages or equivalent result segments actually evaluated |
| `pagination_complete` | boolean or `None` | yes | yes | acquisition/scraper boundary | Whether the scraper has explicit evidence that no further scope pages remain |
| `termination_reason` | non-empty stable string | yes | yes | acquisition/scraper boundary | Deterministic reason capture stopped, such as `exhausted`, `no_next_page`, or `blocked` |

`CaptureCoverage` is immutable. `pagination_complete=True` is permitted only
when the scraper observed the platform's explicit completion condition. The
absence of a next-page control, a zero product count, a parser loop ending, or a
successful HTTP response is not sufficient by itself.

`pagination_complete=False` means the declared scope was not exhausted. `None`
means the scraper cannot determine whether more scope remains. The value is not
filled by the parser or bridge.

## 4. Empty Extraction Semantics

An extraction with zero products maps as follows:

| Condition | Completeness |
|---|---|
| Declared scope present and `pagination_complete=True` with explicit completion evidence | `EMPTY` |
| Declared scope present and `pagination_complete=False` | `PARTIAL` |
| Declared scope present, non-empty result, and `pagination_complete=None` | `UNKNOWN` |

`product_count == 0` is never sufficient evidence for `EMPTY` or `COMPLETE`.

An empty result with `pagination_complete=None` is not a valid successful
observation batch. The parser bridge must fail closed because the lifecycle RFC
classifies empty results without completeness evidence as a terminal ingestion
failure. It must not assign `UNKNOWN` to make the batch structurally fit.

## 5. Partial Extraction Semantics

An extraction maps to `PARTIAL` when the scraper has explicit scope but did not
evaluate the whole scope, including when:

- a next page or continuation is known to exist;
- the capture stopped at a deterministic page limit;
- a transient acquisition boundary ended capture after some pages;
- the platform reported an incomplete result window.

`PARTIAL` requires a non-empty deterministic `missing_scope` description in the
`ObservationCompleteness` value. The parser must not claim which products are
missing; it preserves only the scope-level explanation supplied by acquisition.

## 6. Complete Extraction Semantics

An extraction maps to `COMPLETE` only when:

- `evaluation_scope` is present;
- `pagination_complete=True`;
- the termination condition is explicit and recorded in `termination_reason`;
- no failure or blocked condition ended capture.

For a complete scope with zero products, the result maps to `EMPTY`, not
`COMPLETE`. `COMPLETE` is reserved for a non-empty result set whose declared
scope was exhausted.

## 7. Unknown and Failure Semantics

`pagination_complete=None` maps to `UNKNOWN` only for a non-empty extraction
that is otherwise a valid result but whose coverage cannot be established.

An access block, CAPTCHA, malformed acquisition response, or parser failure is
not represented as an empty or partial product result. It remains the applicable
frozen failure category and does not produce a successful observation batch.

## 8. Required RawExtractionResult Fields

For the ingestion-compliant contract, `RawExtractionResult` must expose:

- existing `platform`, `query`, `source_path`, `extracted_at`, `product_count`,
  and `products` fields;
- `capture_coverage: CaptureCoverage`;
- `evaluation_scope`, either as the top-level non-empty field or exactly equal to
  `capture_coverage.evaluation_scope`.

The canonical representation is one top-level `evaluation_scope` plus one
`capture_coverage` object. Duplicate or conflicting scope values are invalid.

Legacy parser output that omits these fields may remain constructible for local
parser compatibility, but it is not ingestion-compliant. The Slice 3 bridge
must reject it rather than infer completeness.

## 9. Identity Rules

`ParsedRetailObservationBatch.batch_id` remains exactly the identity frozen by
the parsed/normalized amendment: raw artifact identity plus parser version.
Coverage metadata does not alter `batch_id`.

`evaluation_scope`, `capture_coverage`, and the resulting
`ObservationCompleteness` fields participate in normalized observation identity
and in serialized batch content. This ensures that a replay with different
evaluated scope or pagination evidence cannot reuse the same normalized
observation semantics while preserving the stable identity of the parser result
for one artifact and parser version.

The following never participate in identity:

- `source_path`;
- `extracted_at`;
- timestamps of any kind;
- worker/runtime metadata;
- queue position;
- object identity;
- payload formatting or local filesystem location.

Product values, warnings, and parser diagnostics remain content/provenance data;
they do not alter `ParsedRetailObservationBatch.batch_id`, which remains based
on raw artifact identity and parser version only. Completeness is preserved in
the batch content and downstream observation identity.

## 10. Replay Semantics

Replay must preserve the original `evaluation_scope` and `capture_coverage`
values from the governed extraction result. Replaying the same raw artifact
with the same parser version and the same coverage metadata produces the same
completeness state and downstream observation semantics.

Replaying with changed coverage metadata is a different governed input. It may
produce different completeness and observation outputs even when the raw
payload is unchanged; operational timestamps and source paths alone never cause
such a change.

## 11. Compatibility Note

This amendment supplies the missing acquisition metadata and makes explicit that
the existing fail-closed treatment of empty results without completeness
evidence remains in force. It does not weaken the parsed/normalized empty-batch
contract. All other parsed, normalized, evidence, artifact, and identity rules
remain unchanged.

## 12. Open Contract Decisions

None for the Slice 3 completeness boundary. The acquisition boundary must now
provide the explicit scope and capture coverage metadata defined here.
