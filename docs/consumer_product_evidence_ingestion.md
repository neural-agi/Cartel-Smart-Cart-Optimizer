# Consumer Product Evidence Ingestion

Consumer search reads the existing Product Intelligence catalog, canonical listing associations, and immutable normalized observation registry. It does not search retailer pages at request time and does not infer canonical identity from a product name.

## Explicit operator flow

Acquisition is never run at application startup. To acquire Blinkit search evidence, invoke the existing coordinator-backed command explicitly:

```sh
set -eu
PYTHONPATH=backend python3 scripts/acquire_mvp_observations.py milk \
  --location Gurugram --lat 28.413333 --lon 77.072833
```

The command persists the raw artifact and normalized observations through the existing Blinkit acquisition adapter, `LocalIngestionWorker`, parser/bridge, normalizer, observation registry, and deterministic canonical listing resolver. An observation that cannot match an already established active Product and complete Variant remains unresolved; acquisition does not create a canonical identity from its title.

Review unresolved observations using the existing operator queue:

```sh
set -eu
PYTHONPATH=backend python3 scripts/export_catalog_review_queue.py \
  --output /tmp/cartel-catalog-review.json
```

After a human has reviewed the underlying retained retailer evidence and supplied a governed canonical Product, ProductVariant, and listing association, import the explicit manifest:

```sh
set -eu
PYTHONPATH=backend python3 scripts/import_catalog_manifest.py /path/to/reviewed-catalog-manifest.json
```

The import is an operator action. Repeating an identical import is idempotent; conflicting canonical records are rejected. Associations must reference an already registered observation and match its platform and `source_record_id` exactly.

## Importing a locally captured retailer artifact

When live acquisition is unavailable, an operator may import a legitimately captured **sanitized** Blinkit search or product-detail HTML artifact. This command makes no network requests. It uses the existing Blinkit parser/bridge, normalizer, immutable artifact store, observation registry, and exact canonical resolver. It does not create canonical identity from a title.

The sidecar manifest and payload must be separate local files in the same directory. Required fields are:

- `schema_version: 1`, `retailer: "BLINKIT"`, and `sanitized_capture: true`;
- the actual HTTPS Blinkit source URL and timezone-aware capture timestamp;
- `capture_type` (`SEARCH_RESULTS` or `PRODUCT_DETAIL`), `content_type: "text/html"`, and the capture `location_scope`;
- a relative `payload_file` and the lowercase SHA-256 digest of its exact UTF-8 bytes;
- observed capture coverage (`evaluation_scope`, page count, pagination state, termination reason); search captures also require the observed query.

The HTML must be a sanitized page/product evidence fragment containing the actual retailer ID, validated `/prn/.../prid/<id>` product link, observed title, and observed variant/pack text for every parsed product. Price and availability are preserved only when the source exposes them; absence is not filled in. Do not include cookies, authorization/session data, payment details, or unrelated page state. The importer enforces a 10 MiB limit and rejects mismatched digests, unsupported URLs, missing identifiers/variant text, and ambiguous duplicate retailer IDs before persistence.

Example structure only; these values and the matching HTML are synthetic, the digest is intentionally invalid, and this example must **never** be imported or inserted into the production catalog:

```json
{
  "schema_version": 1,
  "retailer": "BLINKIT",
  "sanitized_capture": true,
  "source_reference": "https://example.invalid/s/?q=synthetic-item",
  "captured_at": "2026-01-01T12:00:00+05:30",
  "capture_type": "SEARCH_RESULTS",
  "content_type": "text/html",
  "payload_file": "capture.html",
  "payload_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "location_scope": "synthetic example only",
  "query": "synthetic-item",
  "coverage": {
    "evaluation_scope": "synthetic example only",
    "pages_evaluated": 1,
    "pagination_complete": null,
    "termination_reason": "synthetic example only"
  }
}
```

Invoke explicitly after placing a real, admissible manifest and its sanitized HTML together:

```sh
set -eu
PYTHONPATH=backend python3 scripts/import_retailer_evidence.py /path/to/evidence.json
```

The import is content-addressed and repeatable: identical manifest and payload resolve to the same job/artifact/observation identities, and existing registries enforce idempotency/conflict rejection. If exact established Product and complete Variant identity keys do not match, the observation is registered as unresolved; no association or canonical entity is fabricated. Review it with `scripts/export_catalog_review_queue.py`, then use the existing reviewed `CatalogPopulationManifest` workflow. It becomes consumer-searchable only after a governed Product/Variant and exact listing association are present and consumer evidence checks pass.

## Evidence required for consumer search

A result is eligible only when all of these hold:

- canonical Product identity is established and active;
- the Variant belongs to that Product, is established and active, and has a complete pack configuration;
- a persisted CanonicalListingAssociation references that exact Product, Variant, platform, listing key, and observation;
- the normalized observation exists, matches the association's platform, and retains its RawArtifactReference;
- for the currently supported consumer retailer, the source reference is HTTPS on Blinkit's `blinkit.com` host (fixture/demo/`.invalid` evidence is excluded);
- capture time, parser/normalizer versions, native retailer product ID/URL when observed, sanitized source path (query strings removed), artifact digest, and evidence references are returned as provenance.

`platform_listing_id` is Cartel's association key derived from the ingestion source record. It is not the Blinkit `retailer_product_id`. `source_index` is parser-local and must never be promoted to retailer identity. The native retailer product ID and product URL remain separate optional identifiers on the observation.

When multiple eligible observations exist for one native retailer product ID, search exposes only the unique latest capture. Equal-time ambiguity or conflicting canonical mappings suppress the result. List mutation rechecks that the selected observation is still that current observation. No observation-age cutoff currently exists; the exact capture time is shown and must not be described as fresh solely because it is registered.

Displayed price and availability are observation facts only. They are not checkout quotes, and this ingestion path does not create cart state, checkout evidence, or effective cost.

## Existing data status

The checked-in `data/product_intelligence` sample catalog and associations are explicitly demo-seeded and are not returned by consumer search. The older `data/cleaned/blinkit` exports are not sufficient for promotion: they lack the registered immutable raw artifact and native retailer product ID/URL, and their referenced raw source is not present in this repository. Do not import them as live evidence.

If retailer access, browser readiness, or required browser runtime is unavailable, acquisition fails without creating a successful observation. No fixture or demo provider is available through the production consumer path.
