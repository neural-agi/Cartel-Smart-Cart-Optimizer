# Phase J.1.1: Legacy Blinkit Path Lockdown

## Decision

Blinkit is **LOCKED** pending written authorization that explicitly permits Cartel's commercial product-discovery and price-comparison use case. This is an engineering policy decision, not legal advice. The restriction is deny-by-default in code and cannot be re-enabled through ordinary environment configuration, feature flags, connection state, or an admin setting.

Phase J.1 investigated whether Cartel could obtain Blinkit data for its commercial product-discovery and price-comparison product. It concluded `BLOCKED` because:

- Blinkit does not publish an official, public developer or partner data API for this use case.
- Blinkit's consumer terms prohibit commercial collection, data mining, and automated access, and do not authorize B2B redistribution or commercial comparison.
- Blinkit's `robots.txt` disallows the `/s/*` search path used by the legacy scraper.
- A user's ownership of, or consent to use, an account does not authorize automated commercial extraction.
- The `AUTHORIZED_BROWSER` acquisition label was only an internal Cartel classification; it never constituted retailer authorization.

Phase J.1.1 therefore enforces that decision at every production boundary where Blinkit data could be acquired, ingested, exposed, or used.

## Central policy boundary

`app/retailer_policy.py` is the single explicit Blinkit policy boundary. It exports:

- `RetailerPolicyBlocked` — typed denial carrying `reason_code = "blinkit_commercial_authorization_required"`.
- `ensure_retailer_allowed(retailer_id, operation)` — the deny-by-default check.
- `is_blinkit(retailer_id)` — identifier/host/URL recognition for `BLINKIT`, `blinkit`, `blinkit.com`, `www.blinkit.com`, `blinkit.in`, `blinkit-*`/`blinkit_*` provider IDs, and Blinkit URLs.
- `blinkit_consumer_eligible()` — always `False`; there is no configuration or environment override.

Every enforcement point calls this boundary. There is no generalized multi-retailer policy framework; the abstraction is deliberately Blinkit-specific and minimal.

## Acquisition boundaries

Blinkit acquisition is denied **before** any external side effect:

- `BlinkitScraper` denies before HTTP, browser fallback, or product-detail navigation.
- `BlinkitBrowserSession.new_context` denies before persisted storage-state loading or browser context creation.
- `BlinkitBrowserSession.persist_state` denies before session-state persistence.
- `BlinkitAcquisitionAdapter` denies before invoking the scraper.
- `BlinkitCheckoutCaptureAdapter.capture` and `.acapture` deny before probing or browser work.
- `ProviderAcquisitionAdapter.acquire_for_job` denies before request construction.
- `QuickCommerceRetailerDataProvider` configured for Blinkit returns typed `policy_blocked` / `request_not_attempted` before API-key resolution or HTTP.
- Native `BlinkitRetailerDataProvider` returns the same typed outcome before invoking its adapter.
- The shared retailer adapter executor denies Blinkit connections with `AdapterOutcome.POLICY_BLOCKED` before credential-vault resolution and adapter execution.

Policy denial is distinct from network, rate-limit, or authentication failure. Callers receive a typed policy outcome rather than a transient failure that might be retried.

## Ingestion boundaries

Blinkit ingestion is denied at every production ingestion boundary:

- `LocalOperatorEvidenceAdapter` and `import_validated_evidence` reject Blinkit at the governed operator-evidence import boundary.
- `load_operator_evidence` and the offline parser remain usable for validation and fixture tests; they do not persist evidence.
- `BlinkitParserBridge.build_batch` denies before validation or transformation.
- `BlinkitIdentityAdapter.adapt` denies before identity adaptation; the deterministic resolver therefore denies Blinkit before resolution.
- `LocalIngestionWorker.execute` returns a typed `AttemptOutcome.BLOCKED` / `FailureCategory.POLICY_BLOCKED` result before acquisition, storage, or parsing.
- `ProductIntelligenceRuntime.execute_worker_result` returns `policy_blocked` before normalization or observation registration.
- `JobExecutionCoordinator` maps `POLICY_BLOCKED` to `JobState.BLOCKED` and returns `status = "policy_blocked"`; it never schedules a retry.
- The lifecycle transition table explicitly permits `DEQUEUED`, `ARTIFACT_CAPTURED`, and `PARSING` to transition to `BLOCKED`.

## Consumer-serving boundaries

Historical Blinkit records are retained but never served as usable commercial offers:

- `ProductSearchService` excludes Blinkit associations and rejects Blinkit evidence through the common admissibility helper.
- `CartCandidateDiscoveryService` skips Blinkit associations entirely, so they cannot enter optimization candidates.
- `RetailObservationQueryService.list_observations` and `.get_observation` hide Blinkit observations.
- `RetailPriceComparisonQueryService.compare` excludes Blinkit observations.
- `api/v2/lists.py` filters Blinkit list items from responses and rejects selecting Blinkit evidence as a resolved item.
- `api/v2/optimizations.py` labels Blinkit items `policy_blocked`, excludes them from exact optimization inputs, and never uses them to produce a payable plan.
- `api/routes/scrape.py` (`/scrape` and `/scrape/async`), `api/routes/cost_intelligence.py` (`/cost-intelligence/evaluate`), and `api/routes/cart_checkout_capture.py` (`/cart/checkout-capture`) reject Blinkit with HTTP 403 and `blinkit_commercial_authorization_required`.

## Historical evidence

No observations, artifacts, associations, catalog records, or database rows are deleted or rewritten. Existing historical Blinkit state remains available for audit, reconciliation, and future review, but cannot be returned as a usable commercial offer, price comparison, or optimization candidate while the policy is blocked.

Deletion is explicitly out of scope. The lockdown is an access-control decision, not a data-retention decision.

## Offline testing

Regression coverage uses mocks and fixtures only and never makes live retailer requests:

- Policy, acquisition, ingestion, lifecycle, serving, and API denial tests live in `tests/unit/test_blinkit_policy_lockdown.py` and the retailer-specific suites.
- Generic pipeline and serving tests use `Platform.ZEPTO` with the test-local `ZeptoFixtureParser` / `ZeptoFixtureParserBridge` in `tests/support/fixture_pipeline.py`.
- Offline Blinkit parser/fixture replay remains available, but the parser bridge denies before ingestion.
- No OTP, cookie, token, session identifier, credential, paid provider credit, or browser automation was used during reconnaissance or testing.

## What is intentionally not implemented

The lockdown does not add scrapers, adapters, OTP login, cookie/token/session reuse, undocumented endpoints, Playwright automation, Cloudflare/CAPTCHA/anti-bot bypass, or paid QuickCommerceAPI usage. It does not weaken access-denial handling, disable unrelated retailers, or delete historical evidence.

## Reconsideration requirements

Reconsideration requires all of the following:

1. Written authorization from Blinkit that explicitly permits Cartel's commercial product-discovery and price-comparison use case.
2. A reviewed technical authorization record identifying the permitted scope, data, and retention terms.
3. Updated lifecycle, capability, and provenance documentation.
4. A new security and compliance review covering acquisition, ingestion, serving, and retention.
5. Removal of the central policy denial only after the above are recorded.

A browser session, cookie file, provider classification, account ownership, connection state, environment variable, or feature flag is not authorization.
