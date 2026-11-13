# Canonical Source Provider Contract

This boundary describes independent sources of canonical Product and
ProductVariant evidence. It does not authorize retailer observations to become
canonical evidence and it does not imply that any particular source beyond the
one described below is configured today.

## Provider result

A configured provider may return an immutable, content-addressed evidence
record containing:

- `provider_id` and source name;
- source record identifier and source revision;
- capture timestamp and effective timestamp, when supplied;
- canonical brand/manufacturer;
- canonical product name and product type;
- approved taxonomy/category reference;
- identity-critical product and variant attributes;
- GTIN/EAN when explicitly supplied by the source;
- structured packaging: pack kind, consumer-unit count, content per unit,
  total declared content, unit, dimension, content basis, and packaging form;
- source URL or durable artifact reference;
- field-level provenance and evidence quality.

Missing or conflicting fields remain unresolved. A provider result must never
be converted directly into a catalog row.

## Governance boundary

The result enters the existing operator manifest workflow. The workflow must
validate complete established Product/Variant records, evidence references,
approved category, active lifecycle, catalog revision, and complete structured
pack identity before persistence. A retailer observation is only compared by
the existing exact resolver after the canonical records exist.

GTIN is corroborating identity evidence, not a universal requirement and not a
substitute for product, variant, or pack identity. One GTIN cannot be reused
for incompatible variants; missing GTIN remains valid when the other governed
identity evidence is complete.

## Open Food Facts adapter

Cartel canonical identity is admitted only through an explicit canonical-source
evidence and governance boundary. Retailer observations remain evidence for
matching and association; they cannot create Products or ProductVariants.

The first source adapter is `OpenFoodFactsProvider`. It retrieves one source
record, preserves the raw response as a source-isolated
`CanonicalEvidenceArtifact`, and normalizes only claims that are present in the
response. The adapter does not assign Cartel canonical IDs and does not mutate
the catalog.

The application flow is:

```text
Open Food Facts
  -> CanonicalEvidenceArtifact
  -> CanonicalEvidenceCandidate
  -> explicit operator approval
  -> explicit Product/ProductVariant admission
  -> FilesystemAuthoritativeCatalog
```

Artifact identity includes the source record, source revision, and content
digest. Repeated retrieval of the same source revision and bytes is idempotent;
changed bytes under the same artifact identity fail closed. Review decisions
are persisted separately from source artifacts. Admission requires a matching
approval reference and explicit canonical entities satisfying the existing
catalog validation rules.

The CLI `scripts/ingest_canonical_evidence.py` performs ingestion only and
leaves candidates pending. It is not a consumer endpoint and does not
auto-approve or auto-populate the catalog. A production seed still requires an
operator to verify source records and submit an approved admission payload.

Open Food Facts source policy, field licensing, and redistribution decisions
remain deployment/legal-owner responsibilities; raw source payloads stay in the
source-isolated evidence area and are not exposed by consumer APIs.

## Current status

`OpenFoodFactsProvider` is the only canonical-source adapter in this
repository. No retailer observation, including the real QuickCommerce/Blinkit
observation for retailer product `19512`, is sufficient by itself to establish
the canonical Amul Taaza 500 ml Product/Variant. Blinkit consumer search remains
disabled by commercial policy; no Blinkit canonical-source access is configured
or implied.
