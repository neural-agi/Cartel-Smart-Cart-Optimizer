# Canonical Source Provider Contract

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
