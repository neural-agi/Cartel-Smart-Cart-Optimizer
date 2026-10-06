# Retailer Acquisition Job

Retailer acquisition uses the existing `ScrapeJob`, lifecycle store, attempt
allocation, artifact store, and `JobExecutionCoordinator`. The helper
`build_retailer_acquisition_job` creates a bounded Blinkit search job with
deterministic job identity. The existing lifecycle store provides replay-safe
attempt identities and a maximum of three attempts; no second queue or worker
system is introduced.

The execution path is:

```text
ScrapeJob
  -> existing worker claim/lifecycle
  -> Blinkit acquisition
  -> existing raw artifact store
  -> Blinkit parser/bridge
  -> RetailerObservation adapter
  -> immutable retailer observation store
  -> normalized observation registry
```

Retailer acquisition jobs carry `retailer_only=true`. They still use the
existing normalization and observation-registration lifecycle, but skip the
existing canonical matching and automatic association stage. Association is a
separate governed operation requiring an existing canonical ProductVariant.

Artifact publication and retailer observation persistence happen before the
worker reports success. Acquisition, parser, storage, and missing-listing-ID
failures therefore produce failed attempts rather than successful empty data.
The existing scraper retry and access-denied classification remains in force;
blocking responses are not converted into empty success.

The job identity is distinct from observation identity. Replaying the same
`ScrapeJob` reuses the same deterministic job identity, while observations are
historical snapshots keyed by listing, timestamp, and source payload digest.
This preserves at-least-once worker safety without collapsing different
observed timestamps.

No provider credentials, cookies, raw session state, or raw provider payloads
are placed in the job record. Existing structured logging is retained; this
repository does not currently expose a separate bounded metrics registry for
retailer acquisition.
