• # Scrape Job Contract Amendment

  Status: Frozen contract amendment
  Applies to:

  - docs/architecture/real_data_ingestion_rfc.md
  - docs/architecture/scrape_job_lifecycle_rfc.md

  This amendment freezes only the implementation-blocking vocabulary and contract schemas. It does not alter the existing architecture or lifecycle semantics.

  ## 1. Platform

  The canonical Platform vocabulary is:

  - BLINKIT
  - ZEPTO
  - INSTAMART
  - BIGBASKET
  - FLIPKART_MINUTES

  Platform values are stable identity-bearing values. Their serialized form is the uppercase enum name.

  Future platforms require an additive enum extension and corresponding adapter, parser, and fixture support. Existing platform values must never be renamed or reinterpreted.

  ## 2. CaptureType

  The canonical CaptureType vocabulary is:

  - SEARCH_RESULTS
  - PRODUCT_DETAIL
  - CART
  - CHECKOUT
  - DELIVERY_SLOTS

  SEARCH_RESULTS represents a platform search or listing capture.

  - Producer: scheduler, API, or replay request
  - Consumer: scraper adapter, parser, normalizer

  PRODUCT_DETAIL represents one product-detail capture.

  - Producer: scheduler, API, or replay request
  - Consumer: scraper adapter, parser, normalizer

  CART represents a retailer cart-state capture.

  - Producer: scheduler, API, or replay request
  - Consumer: scraper adapter, parser, normalizer

  CHECKOUT represents a checkout-state capture, including applied checkout-visible benefits and charges.

  - Producer: scheduler, API, or replay request
  - Consumer: scraper adapter, parser, normalizer, Cost Intelligence

  DELIVERY_SLOTS represents delivery-slot availability capture.

  - Producer: scheduler, API, or replay request
  - Consumer: scraper adapter, parser, normalizer

  Capture types are mutually exclusive for one ScrapeJob. A job must declare exactly one capture type.

  ## 3. FailureCategory

  The canonical FailureCategory vocabulary is:

  - NETWORK_ERROR
  - REQUEST_TIMEOUT
  - BROWSER_TIMEOUT
  - HTTP_403
  - CAPTCHA_OR_ANTI_BOT
  - HTTP_404
  - PARSER_RUNTIME_FAILURE
  - PARSER_LAYOUT_CHANGE
  - MISSING_REQUIRED_FIELDS
  - MALFORMED_HTML_OR_JSON
  - NORMALIZATION_RUNTIME_FAILURE
  - NORMALIZATION_CONTRACT_FAILURE
  - STORAGE_FAILURE
  - OBSERVATION_REGISTRATION_FAILURE
  - PIPELINE_PUBLICATION_FAILURE
  - WORKER_CRASH
  - QUEUE_LEASE_EXPIRY
  - CANCELLATION
  - MALFORMED_REQUEST
  - UNSUPPORTED_PLATFORM
  - UNSUPPORTED_CAPTURE_TYPE
  - EMPTY_RESULTS_WITH_COMPLETENESS_EVIDENCE
  - EMPTY_RESULTS_WITHOUT_COMPLETENESS_EVIDENCE
  - EXPIRED_QUEUED_JOB
  - EXPIRED_RUNNING_LEASE

  The following categories are retryable within the frozen maximum-attempt policy:

  - NETWORK_ERROR
  - REQUEST_TIMEOUT
  - BROWSER_TIMEOUT
  - PARSER_RUNTIME_FAILURE
  - NORMALIZATION_RUNTIME_FAILURE
  - STORAGE_FAILURE
  - OBSERVATION_REGISTRATION_FAILURE
  - PIPELINE_PUBLICATION_FAILURE
  - WORKER_CRASH
  - QUEUE_LEASE_EXPIRY
  - EXPIRED_RUNNING_LEASE

  The following categories are terminal and non-retryable:

  - HTTP_403
  - CAPTCHA_OR_ANTI_BOT
  - HTTP_404
  - PARSER_LAYOUT_CHANGE
  - MISSING_REQUIRED_FIELDS
  - MALFORMED_HTML_OR_JSON
  - NORMALIZATION_CONTRACT_FAILURE
  - CANCELLATION
  - MALFORMED_REQUEST
  - UNSUPPORTED_PLATFORM
  - UNSUPPORTED_CAPTURE_TYPE
  - EMPTY_RESULTS_WITHOUT_COMPLETENESS_EVIDENCE
  - EXPIRED_QUEUED_JOB

  EMPTY_RESULTS_WITH_COMPLETENESS_EVIDENCE is a successful terminal observation condition and is not a failure requiring retry or dead-lettering.

  All failure artifacts are replayable when the required source artifact or diagnostic input was preserved. Replayability does not make a failure retryable.

  Retryable failures are dead-letter eligible after the maximum attempt count is exhausted. Terminal failures are dead-letter eligible when the lifecycle contract routes them to dead-letter handling.
  Cancellation is not dead-lettered unless an external lifecycle policy explicitly records it as an operator failure.

  ## 4. AttemptOutcome

  The canonical AttemptOutcome vocabulary is:

  - SUCCEEDED
  - RETRY_SCHEDULED
  - FAILED
  - BLOCKED
  - INVALID
  - CANCELLED
  - EXPIRED
  - DEAD_LETTERED

  SUCCEEDED is emitted when the attempt completes its required stages and produces a valid terminal result.

  RETRY_SCHEDULED is emitted when the attempt fails with a retryable category and another attempt is permitted.

  FAILED is emitted when the attempt reaches terminal failure without being blocked, invalid, cancelled, expired, or dead-lettered.

  BLOCKED is emitted for access blocks, CAPTCHA, or equivalent anti-bot conditions.

  INVALID is emitted for malformed or unsupported contracts that cannot be executed.

  CANCELLED is emitted when cancellation terminates the attempt.

  EXPIRED is emitted when a queued job or running lease expires according to lifecycle rules.

  DEAD_LETTERED is emitted when retry exhaustion or terminal failure routes the job to dead-letter handling.

  ## 5. DownstreamMode

  The canonical DownstreamMode vocabulary is:

  - NONE
  - PRODUCT_INTELLIGENCE
  - COST_INTELLIGENCE
  - CART_OPTIMIZATION
  - FULL_PIPELINE

  NONE means no downstream pipeline event is requested.

  PRODUCT_INTELLIGENCE requests publication to Product Intelligence after normalized observation registration.

  COST_INTELLIGENCE requests publication to Cost Intelligence after the required canonical observation is registered.

  CART_OPTIMIZATION requests publication to Cart Optimization after all required upstream outputs exist.

  FULL_PIPELINE requests publication through Product Intelligence, Cost Intelligence, and Cart Optimization in the repository’s established dependency order.

  Downstream mode is immutable and participates in ScrapeJob identity. It does not alter scraper, parser, or normalization semantics.

  ## 6. Contract Schemas

  All contracts in this amendment are immutable. Collections use canonical ordered tuples. Mapping-like request data uses canonical key ordering and rejects duplicate keys.

  ### CaptureContext

   Field                    Type                                    Required    Identity    Producer            Consumer
  ━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   country_code             non-empty string                             yes         yes    API or scheduler    scraper, observation, replay
  ───────────────────────  ──────────────────────────────────────  ──────────  ──────────  ──────────────────  ─────────────────────────────────────────
   currency_code            non-empty string                             yes         yes    API or scheduler    scraper, observation, Cost Intelligence
  ───────────────────────  ──────────────────────────────────────  ──────────  ──────────  ──────────────────  ─────────────────────────────────────────
   locale                   non-empty string                             yes         yes    API or scheduler    scraper, parser, normalizer
  ───────────────────────  ──────────────────────────────────────  ──────────  ──────────  ──────────────────  ─────────────────────────────────────────
   location_scope           non-empty string                             yes         yes    API or scheduler    scraper, observation, replay
  ───────────────────────  ──────────────────────────────────────  ──────────  ──────────  ──────────────────  ─────────────────────────────────────────
   session_scope            non-empty string                             yes         yes    API or scheduler    scraper, session manager
  ───────────────────────  ──────────────────────────────────────  ──────────  ──────────  ──────────────────  ─────────────────────────────────────────
   additional_parameters    canonical tuple of key/value strings          no         yes    API or scheduler    scraper adapter

  All fields are immutable. session_scope is an explicit identity input; it does not authorize hidden account or repository lookup.

  ### RequestParameters

   Field     Type                                                Required    Identity    Producer            Consumer
  ━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   values    canonical tuple of unique key/value string pairs         yes         yes    API or scheduler    scraper adapter, parser declaration, replay

  Keys are unique, non-empty strings. Pairs are serialized in lexicographic key order. Request parameters contain only explicit capture inputs and never runtime metadata.

  ### RawArtifactReference

   Field                Type                Required    Identity    Producer                     Consumer
  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━
   artifact_id          non-empty string         yes         yes    scraper/artifact registry    parser, replay, audit
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   job_id               non-empty string         yes         yes    worker                       parser, replay, audit
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   attempt_id           non-empty string         yes         yes    worker                       parser, replay, audit
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   platform             Platform                 yes         yes    scraper                      parser, replay
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   capture_type         CaptureType              yes         yes    scraper                      parser, replay
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   content_digest       non-empty string         yes         yes    artifact registry            replay, audit
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   storage_reference    non-empty string         yes          no    artifact storage             parser, replay
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   content_type         non-empty string         yes          no    scraper                      parser
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   capture_timestamp    datetime                 yes          no    scraper                      audit only
  ───────────────────  ──────────────────  ──────────  ──────────  ───────────────────────────  ───────────────────────
   source_reference     non-empty string         yes          no    scraper                      parser, audit

  storage_reference, timestamps, and source metadata are operational or provenance fields. They do not alter artifact identity.

  ### JobFailure

   Field                 Type                                Required    Identity    Producer                                       Consumer
  ━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   category              FailureCategory                          yes          no    worker or stage owner                          retry policy, lifecycle, audit
  ────────────────────  ──────────────────────────────────  ──────────  ──────────  ─────────────────────────────────────────────  ────────────────────────────────
   message               non-empty safe diagnostic string         yes          no    failing stage                                  diagnostics, audit
  ────────────────────  ──────────────────────────────────  ──────────  ──────────  ─────────────────────────────────────────────  ────────────────────────────────
   source_reference      non-empty string or None                  no          no    failing stage                                  diagnostics, replay
  ────────────────────  ──────────────────────────────────  ──────────  ──────────  ─────────────────────────────────────────────  ────────────────────────────────
   artifact_reference    RawArtifactReference or None              no          no    scraper/parser                                 replay, audit
  ────────────────────  ──────────────────────────────────  ──────────  ──────────  ─────────────────────────────────────────────  ────────────────────────────────
   attempt_id            non-empty string                         yes          no    worker                                         lifecycle, audit
  ────────────────────  ──────────────────────────────────  ──────────  ──────────  ─────────────────────────────────────────────  ────────────────────────────────
   retryable             boolean                                  yes          no    derived from frozen category classification    retry policy, audit

  retryable must agree with the frozen FailureCategory classification. A caller may not override category semantics.

  ### JobCancellation

   Field           Type                Required    Identity    Producer                       Consumer
  ━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━
   reason          non-empty string         yes          no    API, scheduler, or operator    lifecycle, audit
  ──────────────  ──────────────────  ──────────  ──────────  ─────────────────────────────  ──────────────────
   requested_by    non-empty string         yes          no    cancellation requester         lifecycle, audit
  ──────────────  ──────────────────  ──────────  ──────────  ─────────────────────────────  ──────────────────
   requested_at    datetime                 yes          no    cancellation boundary          audit only
  ──────────────  ──────────────────  ──────────  ──────────  ─────────────────────────────  ──────────────────
   job_id          non-empty string         yes          no    lifecycle owner                lifecycle, audit

  Cancellation metadata is operational and audit-only. It never participates in job identity.

  ### LifecycleTransition

   Field                   Type                        Required    Identity    Producer              Consumer
  ━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━
   job_id                  non-empty string                 yes          no    lifecycle owner       lifecycle, audit
  ──────────────────────  ──────────────────────────  ──────────  ──────────  ────────────────────  ──────────────────
   previous_state          JobState or None                 yes          no    lifecycle owner       lifecycle, audit
  ──────────────────────  ──────────────────────────  ──────────  ──────────  ────────────────────  ──────────────────
   current_state           JobState                         yes          no    lifecycle owner       lifecycle, API
  ──────────────────────  ──────────────────────────  ──────────  ──────────  ────────────────────  ──────────────────
   reason                  non-empty string                 yes          no    lifecycle owner       audit
  ──────────────────────  ──────────────────────────  ──────────  ──────────  ────────────────────  ──────────────────
   attempt_number          positive integer or None          no          no    worker                audit
  ──────────────────────  ──────────────────────────  ──────────  ──────────  ────────────────────  ──────────────────
   failure                 JobFailure or None                no          no    worker/stage owner    lifecycle, audit
  ──────────────────────  ──────────────────────────  ──────────  ──────────  ────────────────────  ──────────────────
   cancellation            JobCancellation or None           no          no    cancellation owner    lifecycle, audit
  ──────────────────────  ──────────────────────────  ──────────  ──────────  ────────────────────  ──────────────────
   transition_timestamp    datetime                         yes          no    lifecycle owner       audit only

  A transition is structurally invalid when its state-specific payload is inconsistent, such as a cancellation payload without CANCEL_REQUESTED or CANCELLED, or a failure payload without a failure state.

  ### ScrapeJob

  The immutable job fields are:

   Field                           Type                    Required    Identity
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━
   job_id                          deterministic string     derived         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   platform                        Platform                     yes         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   capture_type                    CaptureType                  yes         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   request_parameters              RequestParameters            yes         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   capture_context                 CaptureContext               yes         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   parser_policy_version           non-empty string             yes         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   normalization_policy_version    non-empty string             yes         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   downstream_mode                 DownstreamMode               yes         yes
  ──────────────────────────────  ──────────────────────  ──────────  ──────────
   job_contract_version            non-empty string             yes         yes

  job_id is derived from the canonical serialization of all identity-bearing fields. Lifecycle state, attempts, timestamps, worker metadata, queue metadata, and diagnostics are not fields of job identity.

  ### ScrapeAttempt

   Field                  Type                                                 Required    Identity    Producer              Consumer
  ━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━
   job_id                 non-empty string                                          yes         yes    worker                lifecycle, audit
  ─────────────────────  ─────────────────────────────────────────  ────────────────────  ──────────  ────────────────────  ───────────────────────
   attempt_number         positive integer                                          yes         yes    worker                retry policy, audit
  ─────────────────────  ─────────────────────────────────────────  ────────────────────  ──────────  ────────────────────  ───────────────────────
   attempt_id             job_id + ":" + attempt_number                         derived         yes    identity generator    lifecycle, audit
  ─────────────────────  ─────────────────────────────────────────  ────────────────────  ──────────  ────────────────────  ───────────────────────
   outcome                AttemptOutcome                             yes when finalized          no    worker                lifecycle, audit
  ─────────────────────  ─────────────────────────────────────────  ────────────────────  ──────────  ────────────────────  ───────────────────────
   failure                JobFailure or None                                         no          no    worker/stage owner    retry, audit
  ─────────────────────  ─────────────────────────────────────────  ────────────────────  ──────────  ────────────────────  ───────────────────────
   artifact_references    canonical tuple of RawArtifactReference                    no          no    scraper               parser, replay, audit
  ─────────────────────  ─────────────────────────────────────────  ────────────────────  ──────────  ────────────────────  ───────────────────────
   started_at             datetime                                                  yes          no    worker                audit only
  ─────────────────────  ─────────────────────────────────────────  ────────────────────  ──────────  ────────────────────  ───────────────────────
   finished_at            datetime or None                                           no          no    worker                audit only

  Attempt identity is exactly job_id plus the 1-based attempt number. Attempts are immutable once finalized.

  ## 7. ReplayReference

  ReplayReference is immutable.

   Field                           Type                                 Required            Identity    Producer           Consumer
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━
   replay_id                       deterministic string                  derived                 yes    replay boundary    replay, audit
  ──────────────────────────────  ───────────────────────────────────  ──────────  ──────────────────  ─────────────────  ──────────────────────────
   original_job_id                 non-empty string                          yes                 yes    replay request     replay
  ──────────────────────────────  ───────────────────────────────────  ──────────  ──────────────────  ─────────────────  ──────────────────────────
   artifact_reference              RawArtifactReference or None               no    yes when present    replay request     parser/normalizer replay
  ──────────────────────────────  ───────────────────────────────────  ──────────  ──────────────────  ─────────────────  ──────────────────────────
   replay_target                   explicit target vocabulary string         yes                 yes    replay request     replay executor
  ──────────────────────────────  ───────────────────────────────────  ──────────  ──────────────────  ─────────────────  ──────────────────────────
   parser_policy_version           non-empty string or None                   no    yes when present    replay request     parser replay
  ──────────────────────────────  ───────────────────────────────────  ──────────  ──────────────────  ─────────────────  ──────────────────────────
   normalization_policy_version    non-empty string or None                   no    yes when present    replay request     normalizer replay
  ──────────────────────────────  ───────────────────────────────────  ──────────  ──────────────────  ─────────────────  ──────────────────────────
   downstream_mode                 DownstreamMode or None                     no    yes when present    replay request     downstream replay

  replay_id is derived only from the original job identity, selected replay target, selected artifact identity, and explicitly selected policy versions.

  Replay does not create a new scrape attempt and does not mutate the original job.

  Stable across replay:

  - original job_id;
  - original immutable job fields;
  - referenced artifact identity;
  - selected parser and normalization policy versions;
  - deterministic downstream outputs when governed inputs and versions match.

  Different across replay:

  - replay_id;
  - replay execution metadata;
  - timestamps;
  - worker identity;
  - trace and correlation identifiers;
  - environment diagnostics.

  ## 8. Contract Freeze

  The following decisions are now frozen:

  - canonical supported platform vocabulary;
  - canonical capture-type vocabulary;
  - canonical failure-category vocabulary;
  - canonical attempt-outcome vocabulary;
  - canonical downstream-mode vocabulary;
  - immutable field sets for all contract models;
  - identity-bearing versus operational fields;
  - canonical ordering for request parameter pairs and artifact references;
  - deterministic ScrapeJob.job_id inputs;
  - deterministic ScrapeAttempt.attempt_id inputs;
  - deterministic ReplayReference.replay_id inputs;
  - failure-category retryability classification;
  - attempt outcome emission rules;
  - replay stability rules;
  - cancellation and failure metadata boundaries;
  - absence of clocks, UUIDs, worker state, queue position, and runtime ordering from domain identities.

  Implementation Slice 1 may begin immediately after this amendment. No implementation policy remains unspecified for the immutable contract layer.