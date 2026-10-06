# Consumer Product Evidence Ingestion

Canonical catalog population is operator-governed. The current implemented
boundary accepts source records from Open Food Facts, stores immutable raw
evidence with provenance and digest metadata, and creates a reviewable
candidate. It does not promote retailer listings or observations into
canonical identity.

A candidate must be explicitly approved before admission. The approval carries
an operator decision reference; the final admission payload supplies the
canonical Product and ProductVariant IDs and all identity-critical attributes.
The existing catalog service validates established identity status, approved
category, complete pack configuration, and parent Product/Variant integrity.

Malformed records, missing product name/brand/quantity/GTIN, malformed
quantities, provider failures, duplicate conflicting artifacts, and missing or
mismatched approvals fail closed. Re-ingesting the same provider record and
source revision is idempotent.

No Open Food Facts records are automatically seeded by application startup, and
no synthetic source data is included in production composition. Retailer
association and consumer search continue to use the existing governed catalog
and observation paths after an operator has admitted canonical entities.

Still unresolved are source-policy approval, a reviewed real seed in the target
deployment data store, and any retailer association for which no admissible
observation exists.
