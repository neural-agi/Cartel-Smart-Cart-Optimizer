# Retailer Data Provider and Canonical Association

Retailer acquisition is isolated from canonical identity:

```text
retailer adapter
  -> RetailerObservation
  -> immutable observation persistence
  -> explicit association
  -> existing canonical ProductVariant
```

`RetailerObservation` preserves provider and retailer listing identity,
observed commercial state, location/session context when available, source
artifact reference, payload digest, parser/schema versions, and evidence
references. It does not contain a canonical Product or ProductVariant ID.

The first adapter, `BlinkitRetailerDataProvider`, wraps the existing Blinkit
parser output. It does not add browser behavior, infer identity, or provide
fallback prices or availability. Missing listing IDs or source artifacts fail
closed.

`FilesystemRetailerObservationStore` is append-only by observation identity.
Repeated identical observations are idempotent; a changed payload under the
same observation identity is rejected. Multiple observations for the same
listing remain historical records and are ordered by observed timestamp.

`GovernedRetailerAssociationService` requires an existing canonical variant and
its parent Product before registering an association. The association registry
retains the existing deterministic conflict checks. Uncertain matches must not
be passed to this service; they remain unresolved or review work. Retailer
observations can associate with canonical entities, but retailer observations
can never create canonical entities.

Freshness is explicit on observations through `freshness_at(max_age=...)`.
There is no hidden business freshness duration: callers must provide the
configured age appropriate to their use case. Historical observations remain
available for audit but must not be treated as current after the freshness
window expires.

Consumer search uses the governed catalog and association registry. It reads
the established normalized-observation registry first and can also read an
explicitly associated observation from `FilesystemRetailerObservationStore`.
No unassociated retailer output is exposed. Search callers may provide
`max_age_seconds`; stale retailer observations are excluded under that
caller-owned policy, while historical records remain immutable. Checkout,
optimization, and browser acquisition remain separate boundaries.
