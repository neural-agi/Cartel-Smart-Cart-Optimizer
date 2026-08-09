# Product Intelligence Ingestion Handoff Contract Amendment

**Status:** Frozen contract amendment  
**Scope:** Slice 6A handoff; implementation follows in Slice 6B

## Motivation

The ingestion architecture ends its normalization path at:

```text
NormalizedObservation -> Observation Registry -> Product Intelligence
```

Product Intelligence currently consumes `PlatformListing`,
`ListingObservation`, `EvidenceBundle`, and
`ProductIntelligencePipelineRequest`; it does not consume
`NormalizedObservation` directly. This amendment freezes the deterministic
mapping boundary without changing Product Intelligence models or behavior.

## Handoff Responsibility

The future handoff adapter maps one registered `NormalizedObservation` into
Product Intelligence-native input structures. It preserves ingestion identity,
completeness, and provenance, but makes no product or variant decision.

The adapter does not normalize, scrape, store artifacts, register evidence,
generate candidates, match products, resolve variants, apply assertions, or
invoke Cost Intelligence.

## Frozen Mapping

### PlatformListing

| Product Intelligence field | Source | Rule |
|---|---|---|
| `platform` | `NormalizedObservation.platform` | Serialize using the existing platform value. |
| `platform_listing_id` | `NormalizedObservation.source_record_id` | Preserve exactly; no new listing ID is generated. |
| `raw_title` | `NormalizedObservation.normalized_name` | Use the normalized name exactly. If it is `None`, fail closed; do not substitute an identifier, category, or placeholder. |
| `raw_quantity_text` | `NormalizedObservation.normalized_quantity` | Preserve the nullable normalized representation. |
| `raw_category_text` | `NormalizedObservation.normalized_category` | Preserve the nullable normalized representation. |
| `listing_url` | none | Leave `None`; no URL is invented from artifact or source metadata. |
| `mapping_status` | Product Intelligence default | Leave unresolved; the handoff does not assert canonical mapping. |

The adapter never creates `canonical_product_id` or
`canonical_variant_id`.

### ListingObservation

| Product Intelligence field | Source | Rule |
|---|---|---|
| `platform_listing_id` | `NormalizedObservation.source_record_id` | Must equal the corresponding `PlatformListing` identifier. |
| `displayed_price` | `NormalizedObservation.observed_price_text` | Preserve as observed text; no numeric or currency conversion. |
| `reference_price` | `NormalizedObservation.observed_mrp_text` | Preserve as observed text; no canonical-MRP assertion. |
| `offer_text` | `NormalizedObservation.observed_offer_text` | Preserve verbatim after normalization; no discount calculation. |
| `availability_signal` | `NormalizedObservation.availability_signal` | Preserve as a signal only; no inventory assertion. |
| `capture_timestamp` | `NormalizedObservation.raw_artifact_reference.capture_timestamp` | Use acquisition time exactly; never use handoff or registry time. |
| `source_artifact_reference` | `NormalizedObservation.raw_artifact_reference.artifact_id` | Use the durable artifact identity, never a filesystem path or local source path. |
| `capture_context_reference` | none | Leave `None` unless an existing future caller supplies a separately governed context reference. |
| `parser_version` | see Open Contract Decision | It must not be replaced with `normalization_version`. |

## Artifact and Provenance Handoff

`source_artifact_reference` is the durable artifact ID string required by the
existing `ListingObservation` model. The complete `RawArtifactReference` is
preserved in the handoff envelope alongside the Product Intelligence-native
models; it is not collapsed or discarded.

The envelope also preserves the exact `EvidenceReference` tuple and
`ObservationFieldReference` tuple from `NormalizedObservation`. Existing
`EvidenceReference` and `EvidenceBundle` types are reused. No second evidence
model is introduced and no filesystem path becomes provenance.

The handoff therefore retains:

```text
NormalizedObservation
  -> RawArtifactReference
  -> EvidenceReference / ObservationFieldReference
  -> PlatformListing / ListingObservation / EvidenceBundle
```

## Completeness

Completeness is retained explicitly in the handoff envelope as the original
`ObservationCompleteness` value. It is never discarded or upgraded.

- `COMPLETE`: may produce a Product Intelligence input.
- `PARTIAL`: may produce a Product Intelligence input only while retaining
  `PARTIAL` in the envelope; it must never be represented as complete coverage.
- `UNKNOWN`: may produce a Product Intelligence input only while retaining
  `UNKNOWN` in the envelope; it must never be represented as complete coverage.
- `EMPTY`: produces no fabricated `PlatformListing` or `ListingObservation`.
  The empty handoff remains an explicit empty result with its completeness and
  provenance preserved.

The existing Product Intelligence models do not own ingestion completeness, so
the handoff envelope carries this field without modifying those models.

## Handoff Identity and Replay

`NormalizedObservation.observation_id` remains the upstream identity. The
handoff creates no second ingestion identity and does not use Product or
Variant IDs, timestamps, filesystem paths, database IDs, or runtime ordering.

Equivalent normalized input produces deterministic equivalent listing,
observation, and evidence input values. Runtime time is not read or generated
by the adapter. `normalization_version` is preserved as ingestion provenance;
it is not relabeled as parser version.

## Invocation Ownership

The adapter only constructs the deterministic handoff envelope and the
Product Intelligence-native request inputs. It does not invoke
`DeterministicProductIntelligenceOrchestrator`.

A separate downstream integration boundary owns orchestrator invocation and
its Product Intelligence lifecycle/result. This preserves dependency direction
and keeps data mapping separate from matching and assertion orchestration.

## Error Semantics

The future adapter fails closed when:

- the input is not a valid `NormalizedObservation`;
- `normalized_name` is absent, because `PlatformListing.raw_title` is required;
- required source identity fields are invalid;
- parser provenance is unavailable as described below;
- an unsupported platform cannot be represented by the existing Product
  Intelligence input vocabulary.

Nullable quantity, category, price, MRP, offer, and availability values remain
nullable. They are not fabricated. Product Intelligence decision outcomes are
not adapter errors.

## Slice 6B Boundary

After this amendment, Slice 6B owns only:

```text
registered NormalizedObservation
  -> deterministic handoff envelope
  -> PlatformListing / ListingObservation / EvidenceBundle inputs
```

Slice 6B does not modify existing Product Intelligence models, invoke the
orchestrator, create canonical identities, or add API behavior.

## Compatibility Implications

No existing model is changed by this amendment. The future implementation must
use the existing `PlatformListing`, `ListingObservation`, `EvidenceBundle`,
`EvidenceReference`, and `ProductIntelligencePipelineRequest` models rather
than defining duplicates.

## Open Contract Decisions

### Parser provenance field

`ListingObservation.parser_version` is required. The current
`NormalizedObservation` exposes `normalization_version`, but neither it nor
`RawArtifactReference` carries the parser version. Existing
`EvidenceReference` also has no parser-version field.

Therefore parser version cannot be recovered deterministically at the
normalized-observation boundary. It MUST NOT be replaced with
`normalization_version`, inferred from runtime/package metadata, or guessed
from evidence.

Before Slice 6B implementation, the architecture must decide which existing
boundary carries the original parser version through normalization and
registration. Until that decision is materialized, a compliant adapter cannot
construct a valid `ListingObservation`.

All other handoff decisions required by Slice 6B are frozen above.
