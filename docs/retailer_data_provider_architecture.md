# Retailer Data Provider Boundary

Cartel treats retailer data acquisition as an evidence boundary. A provider
returns location-scoped raw evidence and a typed outcome; it does not create a
canonical product or make a listing searchable. The existing parser, immutable
artifact store, observation registry, exact canonical resolver, listing
association registry, and consumer search remain the only governed path.

## Provider contract

Each provider has a stable `provider_id` and an `acquisition_method`:
`official_api`, `authorized_browser`, `authorized_third_party`, or
`operator_evidence`. It receives a `RetailerAcquisitionRequest` containing the
retailer, the existing `ScrapeJob`, and a required non-global `LocationScope`.
The scope must identify a locality, postal code, or coordinate pair and must
match `ScrapeJob.capture_context.location_scope`.

A successful result carries an existing `AcquisitionResult` plus provider ID,
method, scope, capture time, content digest (created by the existing artifact
store), and evidence quality. Raw evidence remains immutable and auditable.
The normalized observation retains retailer product/listing identifiers,
variant/group/store identifiers when supplied by the provider, source URL,
capture time, parser/version metadata, and the raw artifact reference. Missing
fields remain missing; they are never inferred from a title, price, or array
position.

Typed outcomes are `success`, `unavailable`, `unauthorized`, `access_denied`,
`rate_limited`, `timeout`, `provider_error`, `invalid_response`,
`insufficient_evidence`, and `location_unavailable`. Failure results carry no
retailer evidence. Blinkit 403/429 remains fail-closed; this boundary does not
retry, use a browser fallback, rotate proxies, solve challenges, or harvest
sessions.

## Governance path

```text
provider + LocationScope
  -> RetailerAcquisitionResult
  -> AcquisitionResult / immutable raw artifact
  -> existing parser + normalizer
  -> observation registry
  -> exact canonical Product/Variant resolver
  -> governed listing association
  -> consumer search
```

Provider evidence may establish a retailer observation, but only the existing
identity contract can associate it with a canonical Product/Variant. An
unresolved or ambiguous identity remains out of consumer search. Replaying the
same job and payload uses the existing content-addressed artifact and
observation identities, so it cannot create a second fact.

## Configuration and operator probe

`RETAILER_DATA_PROVIDER_MODE` defaults to `unavailable`. Setting it to
`quickcommerce` explicitly selects the documented QuickCommerce `/v1/search`
adapter for Blinkit data. It sends only `q`, explicit `lat`/`lon`, and
`platform=BlinkIt`, authenticated with `X-API-Key`. The key is read from
`QUICKCOMMERCE_API_KEY` and is never included in diagnostics or evidence.
Setting it to `blinkit` explicitly selects the existing native adapter, whose
access-control behavior remains fail-closed. There is no silent fallback from
an unavailable provider to direct Blinkit.

The bounded operator entry point is:

```sh
set -eu
PYTHONPATH=backend python3 scripts/query_retailer_provider.py \
  --provider quickcommerce --platform BlinkIt \
  --location <location-scope> \
  --lat <explicit-latitude> --lon <explicit-longitude> \
  --query "<one-product-query>"
```

Until a concrete authorized adapter is installed, this returns
`provider_not_configured`, performs no network request, and writes no catalog
data. It prints only a sanitized outcome and scope. QuickCommerce mode
requires `QUICKCOMMERCE_API_BASE_URL` and `QUICKCOMMERCE_API_KEY`; it makes
one read-only search request and does not ingest or modify catalog data.

## Future Blinkit provider requirement

The first authorized Blinkit provider must supply, for each capture: retailer
identity, location/PIN scope, stable retailer product/listing identity, native
product URL where available, variant/group/store identity where available,
observed price and availability as facts (not checkout totals), capture time,
provider/parser versions, and sanitized raw evidence. It must document
authorization, rate limits, location semantics, retention, and response schema.
It must never provide credentials, cookies, payment data, or unverifiable
identity. No provider is configured by this document and no live request is
made by the architecture.
