• # RFC: Scrape Job Lifecycle for Cartel

  Status: Frozen lifecycle contract
  Depends on: docs/architecture/real_data_ingestion_rfc.md
  Scope: ScrapeJob lifecycle only

  ## 1. Purpose

  A ScrapeJob represents one deterministic request to acquire platform data from a retailer under an explicit capture contract.

  A ScrapeJob is not:

  - a worker;
  - a scrape attempt;
  - a raw artifact;
  - a parser run;
  - a normalization run;
  - a downstream Product Intelligence or Cost Intelligence pipeline execution;
  - a scheduler request.

  A ScrapeJob owns the lifecycle of one ingestion request from creation through terminal completion, failure, cancellation, expiry, or dead-lettering.

  The job defines:

  - what platform is being scraped;
  - what capture type is requested;
  - which canonical request parameters apply;
  - which capture context applies;
  - which parser and normalization policy versions are required;
  - whether downstream pipeline publication is requested.

  A worker executes a job.
  An attempt records one bounded execution of a job.
  A raw artifact records acquired source material.
  Parser and normalizer runs are stage outputs inside an attempt.
  A scheduler request is an upstream instruction that may create or reuse a job.

  Job request fields are immutable. Lifecycle state changes are append-only state records.

  ## 2. Job Identity

  ### Identity Inputs

  ScrapeJob.job_id is deterministic and derived from the canonical serialization of:

  - platform;
  - capture_type;
  - canonical request_parameters;
  - canonical capture_context;
  - parser_policy_version;
  - normalization_policy_version;
  - downstream_mode;
  - job_contract_version.

  ### Idempotency Key

  The canonical idempotency key is the same identity payload used to derive job_id.

  An API or scheduler may provide a client idempotency key, but it does not replace the canonical job identity. If supplied, it is operational metadata only.

  Submitting the same identity payload must return the same job identity.

  ### Immutable Fields

  Immutable job fields:

  - job_id;
  - platform;
  - capture_type;
  - request_parameters;
  - capture_context;
  - parser_policy_version;
  - normalization_policy_version;
  - downstream_mode;
  - job_contract_version;
  - canonical idempotency payload.

  ### Mutable Fields

  Mutable lifecycle data is represented as append-only events or state records:

  - current state;
  - attempt count;
  - assigned worker;
  - queue metadata;
  - lifecycle timestamps;
  - retry schedule;
  - terminal failure;
  - cancellation request metadata;
  - operational diagnostics.

  Mutable lifecycle data must never change job identity.

  ### Equality Semantics

  Two ScrapeJob objects are the same domain job if their deterministic job_id values are equal.

  Runtime metadata differences do not affect domain equality.

  ### Values That Must Not Participate In Identity

  The following must never participate in job_id or idempotency identity:

  - timestamps;
  - UUIDs;
  - worker id;
  - retry count;
  - queue position;
  - runtime ordering;
  - attempt id;
  - lease id;
  - trace id;
  - correlation id;
  - API request id;
  - insertion order;
  - storage path generated at runtime.

  ## 3. Job State Machine

  ### Canonical States

  The canonical lifecycle states are:

  - CREATED
  - QUEUED
  - DEQUEUED
  - ACQUIRING
  - ARTIFACT_CAPTURED
  - PARSING
  - PARSED
  - NORMALIZING
  - NORMALIZED
  - REGISTERING_OBSERVATION
  - REGISTERED
  - PUBLISHING_PIPELINE_EVENT
  - COMPLETED
  - RETRY_SCHEDULED
  - CANCEL_REQUESTED
  - CANCELLED
  - EXPIRED
  - DEAD_LETTERED
  - FAILED
  - BLOCKED
  - INVALID

  The broader ingestion RFC uses summary states such as running and succeeded. This lifecycle contract replaces those summaries with explicit stage states. APIs may expose summarized views, but workers must
  use these canonical states.

  ### State Definitions

   State                        Owner                Terminal                                                                        Retry Eligible    Meaning
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   CREATED                      scheduler/API              No                                                                                    No    Job identity exists but has not entered a queue.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   QUEUED                       queue                      No                                                                                    No    Job is available for worker delivery.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   DEQUEUED                     queue/worker               No                                                                                   Yes    Worker has leased the job but acquisition has not
                                                                                                                                                       started.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   ACQUIRING                    worker/scraper             No                                                                                   Yes    Scraper is fetching source data.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   ARTIFACT_CAPTURED            worker/scraper             No                                                                       Stage-dependent    Raw artifact has been captured and preserved or
                                                                                                                                                       referenced.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   PARSING                      worker/parser              No    Yes for parser-runtime failure, no for layout contract failure after max attempts.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   PARSED                       worker/parser              No                                                                       Stage-dependent    Parser emitted a parsed observation batch or explicit
                                                                                                                                                       partial parse.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   NORMALIZING                  worker/normalizer          No                Yes for transient normalizer runtime failure, no for contract failure.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   NORMALIZED                   worker/normalizer          No                                                                       Stage-dependent    Normalized observation contract exists.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   REGISTERING_OBSERVATION      worker/registry            No                                           Yes for transient storage/registry failure.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   REGISTERED                   registry/worker            No                                                                       Stage-dependent    Observation and evidence registration succeeded.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   PUBLISHING_PIPELINE_EVENT    worker                     No                                          Yes for transient queue publication failure.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   COMPLETED                    worker                    Yes                                                                                    No    All required stages finished successfully.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   RETRY_SCHEDULED              worker/queue               No                                                                   No until retry time    Retry is scheduled deterministically.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   CANCEL_REQUESTED             API/scheduler              No                                                                                    No    Cancellation has been requested but not yet acknowledged
                                                                                                                                                       by worker.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   CANCELLED                    worker                    Yes                                                                                    No    Job stopped at a valid cancellation boundary.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   EXPIRED                      scheduler/queue           Yes                                                                                    No    Job exceeded allowed age before completion or dequeue.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   DEAD_LETTERED                worker/queue              Yes                                                                                    No    Retryable or diagnosable failure exhausted policy or
                                                                                                                                                       requires operator action.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   FAILED                       worker                    Yes                                                                                    No    Non-retryable execution failure that is not blocked,
                                                                                                                                                       invalid, cancelled, or dead-lettered.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   BLOCKED                      scraper/worker            Yes                                                                                    No    Access was blocked by CAPTCHA, anti-bot, 403, or
                                                                                                                                                       equivalent.
  ───────────────────────────  ───────────────────  ──────────  ────────────────────────────────────────────────────────────────────────────────────  ───────────────────────────────────────────────────────────
   INVALID                      scheduler/worker          Yes                                                                                    No    Job contract or request is malformed or unsupported.

  ### Transition Table

   From                         Allowed To                                                                              Forbidden To
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   CREATED                      QUEUED, INVALID, CANCEL_REQUESTED, EXPIRED                                              Any execution state, terminal success
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   QUEUED                       DEQUEUED, CANCEL_REQUESTED, EXPIRED                                                     Parser/normalizer states, COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   DEQUEUED                     ACQUIRING, RETRY_SCHEDULED, CANCEL_REQUESTED, FAILED, INVALID, EXPIRED                  PARSED, NORMALIZED, COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   ACQUIRING                    ARTIFACT_CAPTURED, RETRY_SCHEDULED, BLOCKED, FAILED, CANCEL_REQUESTED, DEAD_LETTERED    PARSED, REGISTERED, COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   ARTIFACT_CAPTURED            PARSING, CANCEL_REQUESTED, FAILED, DEAD_LETTERED                                        NORMALIZED, COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   PARSING                      PARSED, RETRY_SCHEDULED, FAILED, DEAD_LETTERED, CANCEL_REQUESTED                        REGISTERED, COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   PARSED                       NORMALIZING, CANCEL_REQUESTED, FAILED, DEAD_LETTERED                                    REGISTERED, COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   NORMALIZING                  NORMALIZED, RETRY_SCHEDULED, FAILED, DEAD_LETTERED, CANCEL_REQUESTED                    COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   NORMALIZED                   REGISTERING_OBSERVATION, CANCEL_REQUESTED, FAILED, DEAD_LETTERED                        COMPLETED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   REGISTERING_OBSERVATION      REGISTERED, RETRY_SCHEDULED, FAILED, DEAD_LETTERED, CANCEL_REQUESTED                    COMPLETED without REGISTERED
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   REGISTERED                   PUBLISHING_PIPELINE_EVENT, COMPLETED, CANCEL_REQUESTED                                  acquisition/parser states
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   PUBLISHING_PIPELINE_EVENT    COMPLETED, RETRY_SCHEDULED, FAILED, DEAD_LETTERED                                       acquisition/parser states
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   RETRY_SCHEDULED              QUEUED, DEAD_LETTERED, CANCEL_REQUESTED, EXPIRED                                        stage execution states directly
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   CANCEL_REQUESTED             CANCELLED, current in-flight stage if worker has not acknowledged yet                   COMPLETED unless cancellation was requested after completion
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   COMPLETED                    none                                                                                    all
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   CANCELLED                    none                                                                                    all
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   EXPIRED                      none                                                                                    all
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   DEAD_LETTERED                none                                                                                    all
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   FAILED                       none                                                                                    all
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   BLOCKED                      none                                                                                    all
  ───────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────  ──────────────────────────────────────────────────────────────
   INVALID                      none                                                                                    all

  ### Transition Rules

  Invalid transitions fail closed.

  A job must not skip stage states when the skipped stage is required by its capture type.

  A job may move from REGISTERED directly to COMPLETED only when downstream_mode does not require pipeline event publication.

  A job must not enter COMPLETED unless all required stage outputs exist and are structurally valid.

  Terminal states are immutable.

  ## 4. Attempts

  ### Attempt Identity

  A ScrapeAttempt is one bounded execution of a job by a worker.

  Attempt identity is deterministic within a job:

  attempt_id = job_id + ":" + attempt_number

  attempt_number is 1-based.

  ### Job And Attempt Relationship

  A job may have zero or more attempts.

  A job has zero attempts while in CREATED or QUEUED.

  A new attempt begins when a worker transitions the job from QUEUED to DEQUEUED.

  ### Maximum Attempts

  The frozen default maximum is:

  max_attempts = 3

  This means one initial attempt plus at most two retries.

  A platform-specific policy may reduce max attempts but must not increase it unless the policy version is explicitly part of the job identity.

  ### Retry Counting

  Retry count is derived from completed failed attempts:

  retry_count = attempt_number - 1

  Retry count is lifecycle metadata and never participates in job identity.

  ### Retry Ownership

  The worker classifies attempt failure.

  The retry policy decides whether another attempt is permitted.

  The queue owns making the retry visible at the scheduled time.

  ### Attempt Immutability

  Attempts are immutable once finalized.

  An in-progress attempt may accumulate stage events. Once the attempt reaches success, retry scheduling, cancellation, dead-letter, blocked, invalid, expired, or failure, its record is closed.

  ## 5. Retry Policy

  ### Deterministic Backoff

  Backoff is deterministic and has no jitter.

  For retry attempt n, where n is the next 1-based attempt number:

  delay_seconds = min(300, 30 * 2^(n - 2))

  So:

  - attempt 2 is delayed by 30 seconds;
  - attempt 3 is delayed by 60 seconds.

  No fourth attempt exists under the default policy.

  Backoff scheduling time is operational metadata. Replay compares the policy decision and delay value, not wall-clock execution time.

  ### Failure Categories

   Failure Type                                                           Retry                    Backoff        Terminal                                Dead Letter    Final State If Not Retried
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Network error                                        Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Request timeout                                      Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Browser timeout                                      Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   HTTP 403                                                                  No                         No             Yes                                         No    BLOCKED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   CAPTCHA / anti-bot challenge                                              No                         No             Yes                                         No    BLOCKED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Parser runtime failure                               Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Parser layout change                                                      No                         No             Yes                                        Yes    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Missing required parse fields                                             No                         No             Yes    Yes if downstream cannot accept partial    DEAD_LETTERED or FAILED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Malformed HTML/JSON                                            No by default                         No             Yes                                        Yes    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Normalization runtime failure                        Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Normalization contract failure                                            No                         No             Yes                                        Yes    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Worker crash                                            Yes via lease expiry    Queue visibility policy    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Queue lease expiry                                   Yes, until max attempts         Queue lease policy    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Cancellation                                                              No                         No             Yes                                         No    CANCELLED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Malformed request                                                         No                         No             Yes                                         No    INVALID
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Unsupported platform                                                      No                         No             Yes                                         No    INVALID
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Unsupported capture type                                                  No                         No             Yes                                         No    INVALID
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Layout change                                                             No                         No             Yes                                        Yes    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Storage failure                                      Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Observation registration failure                     Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Pipeline event publication failure                   Yes, until max attempts                        Yes    No initially                     Yes after max attempts    DEAD_LETTERED
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Empty results with explicit completeness evidence                         No                         No     Yes success                                         No    Continue pipeline
  ───────────────────────────────────────────────────  ─────────────────────────  ─────────────────────────  ──────────────  ─────────────────────────────────────────  ────────────────────────────
   Empty results without completeness evidence                               No                         No             Yes                                        Yes    DEAD_LETTERED

  ### Retry Requirements

  Retry must preserve:

  - same job_id;
  - same immutable job request fields;
  - same idempotency identity;
  - previous attempt records;
  - previous raw artifacts and diagnostics where captured.

  Retry must create:

  - a new attempt_id;
  - a new attempt record;
  - new operational lifecycle timestamps;
  - new artifact references if acquisition occurs again.

  Retry must not overwrite prior attempt outputs.

  ## 6. Queue Semantics

  This contract defines logical queue behavior only. It does not assume Redis, Postgres, SQS, local memory, or any specific queue implementation.

  ### Enqueue

  Enqueue accepts a valid ScrapeJob.

  If an equivalent job already exists, enqueue returns the existing job identity and state.

  Enqueue must not create duplicate domain jobs for identical identity payloads.

  ### Dequeue

  Dequeue leases one queued job to one worker.

  The worker must transition the job to DEQUEUED before executing acquisition.

  ### Visibility And Leases

  A dequeued job is invisible to other workers until:

  - acknowledged;
  - failed and retry-scheduled;
  - cancelled;
  - terminal;
  - the lease expires.

  Lease expiry is treated as recoverable worker failure.

  ### Acknowledgement

  A worker acknowledges a job only after transitioning it to a valid terminal state or retry-scheduled state.

  Acknowledgement does not mean success. It means the queue may stop delivering that lease instance.

  ### Duplicate Delivery

  Queue implementations may deliver duplicate messages.

  Workers must use job_id, attempt_id, and lifecycle transition validation to prevent duplicate domain effects.

  Duplicate delivery of an already terminal job must be a no-op.

  Duplicate delivery of an already in-progress leased job must fail closed or be rejected by lease ownership.

  ### Worker Crash Recovery

  If a worker crashes:

  - the active lease expires;
  - the attempt is classified as incomplete;
  - the job becomes retry eligible if max attempts is not exhausted;
  - captured artifacts already persisted remain preserved;
  - downstream stages must not be repeated unless their idempotent registration contracts permit it.

  ### Ordering Guarantees

  The queue does not guarantee global FIFO ordering.

  Within the same deterministic priority and visibility time, implementations may choose any delivery order. Delivery order must not affect job identity or downstream domain output.

  ### Fairness

  Queue fairness is operational. The minimum requirement is starvation avoidance by platform and capture type. The exact scheduling algorithm is deferred.

  ## 7. Scheduler

  ### Scheduler Responsibility

  The scheduler creates or reuses jobs. It does not execute jobs.

  The scheduler owns:

  - translating manual/API/cron/refresh/batch requests into immutable job requests;
  - deduplicating by canonical job identity;
  - assigning deterministic priority class;
  - applying platform rate-limit admission rules;
  - enqueueing valid jobs.

  The scheduler does not own:

  - scraping;
  - parsing;
  - normalization;
  - artifact persistence;
  - retry classification;
  - downstream matching or cost evaluation.

  ### Job Sources

  Jobs may be created by:

  - manual API request;
  - cron schedule;
  - recurring refresh policy;
  - batch ingestion;
  - explicit replay request;
  - internal refresh trigger.

  All sources must produce the same canonical job request shape.

  ### Priority

  Priority is a scheduler input.

  Priority affects queue delivery only. It must not affect job identity unless the requested business capture itself differs.

  ### Deduplication

  Deduplication is based on canonical job identity.

  Two scheduler requests that produce the same identity payload must map to the same job_id.

  ### Rate Limiting

  Rate limiting is applied before enqueue or before dequeue depending on adapter capability.

  Rate-limit wait time is operational metadata and does not affect job identity.

  The scheduler must not silently alter request parameters to satisfy rate limits.

  ## 8. Cancellation

  ### Cancellation State

  Cancellation is requested by transitioning to CANCEL_REQUESTED.

  Cancellation is completed by a worker transitioning to CANCELLED.

  ### When Cancellation May Occur

  Cancellation may be requested while a job is:

  - CREATED;
  - QUEUED;
  - DEQUEUED;
  - ACQUIRING;
  - ARTIFACT_CAPTURED;
  - PARSING;
  - PARSED;
  - NORMALIZING;
  - NORMALIZED;
  - REGISTERING_OBSERVATION;
  - REGISTERED;
  - PUBLISHING_PIPELINE_EVENT;
  - RETRY_SCHEDULED.

  Cancellation has no effect after terminal states.

  ### Stage-Specific Semantics

   Current Stage                 Cancellation Behavior
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Before browser opens          Stop immediately; terminal CANCELLED; no artifact required.
  ────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Browser already opened        Close browser context at safe boundary; preserve diagnostics if captured.
  ────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Artifact captured             Preserve artifact; do not delete.
  ────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Parser started                Finish or stop at parser-safe boundary; preserve parser diagnostics if available.
  ────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Normalization started         Stop only before registration unless normalizer has a safe cancellation boundary.
  ────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Registration started          Do not interrupt partial registry writes; finish idempotent registration or fail closed.
  ────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Pipeline already triggered    Do not revoke downstream event; job may complete if event publication already succeeded.
  ────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────
   Completed                     Cancellation request is rejected as no-op terminal conflict.

  ### Artifact Preservation

  Cancellation must never delete raw artifacts, failure artifacts, parser diagnostics, or registered observations already produced.

  Cancellation stops future work. It does not rewrite history.

  ## 9. Replay

  ### Replay Definition

  Replay means re-executing a deterministic stage from preserved inputs to reproduce or inspect output.

  Replay is not retry.

  Retry responds to execution failure for the same live job.
  Replay is an explicit diagnostic or regeneration operation using preserved artifacts and policy versions.

  ### Replay Targets

  Replay may target:

  - raw artifact to parser output;
  - parser output to normalized observation;
  - normalized observation to registry dry-run;
  - registered observation to Product Intelligence;
  - checkout observation to Cost Intelligence;
  - complete job audit reconstruction.

  ### Job Replay

  Replaying a job does not mutate the original job lifecycle.

  A replay run must create a distinct replay execution record, but it references the original job_id.

  ### Identity Stability

  Stable across replay:

  - original job_id;
  - original immutable job request fields;
  - raw artifact identity;
  - parser version if replaying same parser contract;
  - normalization version if replaying same normalizer contract;
  - downstream deterministic outputs when inputs and versions match.

  Changes across replay:

  - replay execution id;
  - operational timestamps;
  - replay worker id;
  - trace id;
  - diagnostics from the replay environment.

  ### Retry Versus Replay

   Property                           Retry                           Replay
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Mutates job lifecycle              Yes                             No
  ─────────────────────────────────  ──────────────────────────────  ───────────────────────────────
   Creates new attempt                Yes                             No, creates replay execution
  ─────────────────────────────────  ──────────────────────────────  ───────────────────────────────
   Caused by failure                  Yes                             Not necessarily
  ─────────────────────────────────  ──────────────────────────────  ───────────────────────────────
   Uses live acquisition              Yes, if retrying acquisition    No if replaying from artifact
  ─────────────────────────────────  ──────────────────────────────  ───────────────────────────────
   Preserves original job identity    Yes                             Yes
  ─────────────────────────────────  ──────────────────────────────  ───────────────────────────────
   Can change terminal job state      Yes                             No

  ## 10. Observability

  ### Required Metadata

  Every job lifecycle record must carry:

  - job_id;
  - current state;
  - previous state;
  - transition reason;
  - attempt number where applicable;
  - platform;
  - capture type;
  - safe request summary;
  - lifecycle timestamp;
  - actor type;
  - worker id where applicable;
  - queue id where applicable;
  - correlation id;
  - trace id;
  - artifact references where applicable;
  - failure classification where applicable.

  ### Domain Identity Versus Operational Metadata

  Identity-bearing:

  - job_id;
  - immutable job request payload;
  - artifact identity;
  - parser/normalization policy versions.

  Operational only:

  - attempt timestamps;
  - worker id;
  - queue id;
  - trace id;
  - correlation id;
  - lease id;
  - queue position;
  - retry schedule timestamp;
  - API request id.

  Operational metadata is required for observability but must never affect deterministic domain identity.

  ## 11. API Impact

  ### User-Visible States

  The API should expose a stable public status vocabulary:

   Internal State                                                                                                                                      Public Status
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━
   CREATED, QUEUED, RETRY_SCHEDULED                                                                                                                    queued
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   DEQUEUED, ACQUIRING, ARTIFACT_CAPTURED, PARSING, PARSED, NORMALIZING, NORMALIZED, REGISTERING_OBSERVATION, REGISTERED, PUBLISHING_PIPELINE_EVENT    running
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   COMPLETED                                                                                                                                           completed
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   CANCEL_REQUESTED                                                                                                                                    cancelling
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   CANCELLED                                                                                                                                           cancelled
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   EXPIRED                                                                                                                                             expired
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   DEAD_LETTERED                                                                                                                                       dead_lettered
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   FAILED                                                                                                                                              failed
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   BLOCKED                                                                                                                                             blocked
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  ───────────────
   INVALID                                                                                                                                             invalid

  ### Internal States

  Stage-level states remain available in detailed job diagnostics but should not be required by normal API consumers.

  ### Blocked Jobs

  Blocked jobs expose:

  - public status blocked;
  - safe block reason;
  - whether operator action is required;
  - replay eligibility if artifact exists.

  ### Retrying Jobs

  Retrying jobs expose:

  - public status queued;
  - attempt count;
  - max attempts;
  - next retry delay or scheduled time;
  - last failure category.

  ### Cancelled Jobs

  Cancelled jobs expose:

  - public status cancelled;
  - cancellation boundary;
  - artifact references already preserved;
  - whether downstream event had already been published.

  ### Failed And Dead-Lettered Jobs

  Failed jobs expose safe diagnostics.

  Dead-lettered jobs expose:

  - final failure classification;
  - attempt count;
  - preserved evidence/artifacts;
  - operator action guidance;
  - replay eligibility.

  ## 12. Failure Matrix

   Failure Type                                   Retry               Terminal          Dead Letter              Cancel Allowed    Observable                       Replayable    Operator Action
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Network error                 Yes until max attempts     After max attempts                  Yes                         Yes           Yes               If artifact exists    Inspect network/platform
                                                                                                                                                                                  availability
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Request timeout               Yes until max attempts     After max attempts                  Yes                         Yes           Yes       If partial artifact exists    Inspect timeout policy
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Browser timeout               Yes until max attempts     After max attempts                  Yes                         Yes           Yes             If diagnostics exist    Inspect browser resources
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   HTTP 403                                          No                    Yes                   No           No after terminal           Yes      If response artifact exists    Platform/session review
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   CAPTCHA / anti-bot                                No                    Yes                   No           No after terminal           Yes     If challenge artifact exists    Platform access review
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   HTTP 404                               No by default                    Yes    Context-dependent           No after terminal           Yes      If response artifact exists    Validate request scope
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Parser runtime failure        Yes until max attempts     After max attempts                  Yes                         Yes           Yes       Yes if raw artifact exists    Parser diagnostics
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Parser layout change                              No                    Yes                  Yes           No after terminal           Yes                              Yes    Update parser
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Missing required fields                           No                    Yes      Yes if unusable           No after terminal           Yes                              Yes    Review parser/partial contract
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Malformed HTML/JSON                               No                    Yes                  Yes           No after terminal           Yes                              Yes    Inspect raw artifact
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Normalization runtime         Yes until max attempts     After max attempts                  Yes                         Yes           Yes       Yes if parsed batch exists    Inspect normalizer
   failure
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Normalization contract                            No                    Yes                  Yes           No after terminal           Yes                              Yes    Fix contract or parser output
   failure
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Storage failure               Yes until max attempts     After max attempts                  Yes                         Yes           Yes     No unless artifact persisted    Inspect storage
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Observation registration      Yes until max attempts     After max attempts                  Yes           Yes before commit           Yes         Yes if normalized output    Inspect registry
   failure                                                                                                             boundary                                         exists
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Pipeline publication          Yes until max attempts     After max attempts                  Yes      Yes before publication           Yes                              Yes    Inspect downstream queue
   failure
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Worker crash                    Yes via lease expiry     After max attempts                  Yes          Yes after recovery           Yes                  Stage-dependent    Inspect worker/runtime
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Queue lease expiry            Yes until max attempts     After max attempts                  Yes                         Yes           Yes                  Stage-dependent    Inspect queue/worker health
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Duplicate job                       No new execution                     No                   No    Existing job rules apply           Yes          Existing result applies    None
                                               required
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Duplicate delivery               No domain duplicate                     No                   No    Existing job rules apply           Yes          Existing result applies    Queue diagnostics if frequent
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Cancellation                                      No                    Yes                   No                         N/A           Yes              Preserved artifacts    None unless stuck
                                                                                                                                                                    replayable
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Malformed request                                 No                    Yes                   No                          No           Yes                               No    Fix caller request
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Unsupported platform                              No                    Yes                   No                          No           Yes                               No    Add platform support
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Unsupported capture type                          No                    Yes                   No                          No           Yes                               No    Add capture support
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Empty results with                                No    Successful terminal                   No         No after completion           Yes                              Yes    None
   completeness evidence
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Empty results without                             No                    Yes                  Yes           No after terminal           Yes           Yes if artifact exists    Inspect parser/scope
   completeness evidence
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Expired queued job                                No                    Yes                   No                          No           Yes                               No    Review scheduling capacity
  ────────────────────────────  ────────────────────────  ─────────────────────  ───────────────────  ──────────────────────────  ────────────  ───────────────────────────────  ────────────────────────────────
   Expired running lease         Yes until max attempts     After max attempts                  Yes          Yes after recovery           Yes                  Stage-dependent    Inspect worker crash/lease

  ## 13. Scalability

  ### One Worker

  The lifecycle works with one worker using local queue and filesystem artifact storage.

  Lease semantics may be implemented in memory for development, but lifecycle state transitions must remain the same.

  ### Ten Workers

  Multiple workers require shared queue leases and shared job-state storage.

  The contract does not change because duplicate delivery, leases, and idempotency are already lifecycle concepts.

  ### One Hundred Workers

  At larger scale:

  - queues may be partitioned by platform and capture type;
  - rate limits may be distributed;
  - browser capacity may be separated from parser capacity;
  - artifact storage may move to object storage.

  No state names, identity rules, or retry semantics change.

  ### Multiple Queues

  Jobs may move between requested, retry, and dead-letter queues.

  Queue topology must not change job lifecycle semantics.

  ### Multiple Countries

  Country, locale, currency expectation, and location scope belong inside capture_context.

  They participate in job identity only through canonical capture context identity.

  ### Millions Of Jobs

  Job lookup must be indexed by job_id.

  Append-only lifecycle records allow audit and replay without mutating historical state.

  Retention policy may archive old artifacts but must preserve auditable references.

  ## 14. Contract Freeze

  The following behavior-affecting decisions are frozen for implementation:

  - ScrapeJob represents one deterministic ingestion request, not an attempt or worker execution.
  - Job identity is derived only from immutable request-defining inputs.
  - Timestamps, worker IDs, attempt counts, UUIDs, queue position, and runtime ordering never participate in job identity.
  - Duplicate job submission resolves to the same job_id.
  - Attempts are immutable once finalized.
  - Attempt identity is job_id + ":" + attempt_number.
  - Maximum attempts default to 3 total attempts.
  - Backoff is deterministic: min(300, 30 * 2^(next_attempt_number - 2)).
  - Canonical state names are those listed in this RFC.
  - Invalid state transitions fail closed.
  - Terminal states are immutable.
  - BLOCKED, INVALID, CANCELLED, COMPLETED, EXPIRED, FAILED, and DEAD_LETTERED are terminal.
  - Cancellation is a lifecycle transition, not an exception.
  - Cancellation never deletes captured artifacts.
  - Retry mutates job lifecycle; replay does not.
  - Queue duplicate delivery must not create duplicate domain effects.
  - Worker crash recovery is governed by lease expiry and retry policy.
  - API public status is a projection of internal state, not a separate lifecycle.
  - Operational observability metadata never participates in domain identity.

  ### Intentionally Deferred

  The following are intentionally deferred until the first Blinkit implementation slice:

  - exact storage schema;
  - queue adapter implementation;
  - distributed lease mechanism;
  - platform-specific timeout values;
  - platform-specific rate limits;
  - exact API response schemas;
  - artifact retention durations;
  - operator dashboard behavior;
  - replay API shape;
  - cron schedule format;
  - batch scheduling format.

  These deferred items must not contradict the frozen lifecycle.

  ## Self-Critique

  ### Weaknesses

  The state machine is intentionally explicit. That improves auditability but increases implementation surface area.


  Another risk is partial stage completion. For example, registration may succeed but acknowledgement may fail. Registry idempotency must be strong before distributed workers are introduced.

  Cancellation during registration and pipeline publication needs careful boundary handling to avoid pretending work did not happen.

  ### Future Extension Points

  The contract leaves room for:

  - distributed queue adapters;
  - per-platform retry policies;
  - replay APIs;
  - richer public job diagnostics;
  ### Possible Over-Engineering

  For the first Blinkit-only implementation, states like PUBLISHING_PIPELINE_EVENT, EXPIRED, and DEAD_LETTERED may feel heavy.

  They should still remain in the contract because removing them would force redesign once background execution and operator recovery exist.

  ### Should Wait Until Blinkit Is Operational

  The following should wait:

  - multiple queue backends;
  - dynamic adapter loading;
  - distributed rate-limit coordination;
  - replay API;
  - operator dashboard;
  - automated artifact retention enforcement;
  - multi-country scheduling;
  - sophisticated fairness policy.

  The first implementation should focus on deterministic local lifecycle execution for Blinkit while preserving this contract.