# Phase K.3 Demo Readiness Report — Deterministic `CARTEL_DEMO` Synthetic Catalog

**Decision: `READY_WITH_CONSTRAINTS`**

The synthetic demo lane is implemented, provenance-safe, and unit-verified. The
full authenticated consumer journey is implemented against persisted
`/api/v2` APIs, and the local-cart page no longer calls the operator-only
`/api/v1/cart/optimize`. Database-backed integration tests and the browser E2E
journey are written but could not be executed in this environment because no
disposable PostgreSQL or Docker daemon is available. They are reported as
**skipped**, never as passed.

---

## 1. Scope and non-actions

### 1.1 In scope

- A deterministic, retailer-independent synthetic catalog with the dedicated
  source identity `CARTEL_DEMO`.
- Explicit synthetic provenance on every generated record and through the
  search, list, optimization, persistence, reload, and UI surfaces.
- Consumer discovery → exact-variant selection → list persistence → persisted
  optimization → reload, using authenticated `/api/v2` APIs only.
- A deterministic E2E fixture dataset and a rewritten browser journey.
- Unit coverage for determinism, provenance, Blinkit exclusion, variant
  identity, availability states, discovery gating, and adapter/acquisition
  isolation.

### 1.2 Explicitly not done

- No live retailer acquisition, scraping, browser automation, or checkout.
- No Blinkit access, relabelling, or policy change. Blinkit remains centrally
  blocked by `app/retailer_policy.py`.
- No Swiggy Instamart authorization or access.
- No paid API, cloud service, or external account was used.
- No credential-vault access, account connection, cart preparation, or checkout
  capability was added for `CARTEL_DEMO`.
- No simulated fee, tax, discount, serviceability, checkout total, payment
  outcome, or payable recommendation was fabricated.
- No Git mutation: nothing was staged, committed, pushed, pulled, reset,
  stashed, checked out, cleaned, or discarded.
- No unrelated refactoring was performed.

### 1.3 Constraints carried forward

- Blinkit must remain blocked regardless of configuration or fixture state.
- Synthetic records must never be presented as live retailer evidence, and
  live retailer records must never be relabelled synthetic.
- Fixture/demo evidence must never produce a payable plan.
- Pre-existing uncommitted work must be preserved.
- Only required files may be modified.

---

## 2. Baseline workspace state

| Item | Value |
| --- | --- |
| Branch | `feat/cartel-production-foundation` |
| HEAD | `59560b9dcab78c82c8bd3b0c47f8d7d33508a821` |
| Staged files | 0 |
| Modified tracked files | 63 |
| Untracked files (expanded) | 128 |

The baseline already contained substantial uncommitted work from earlier
phases. Many files modified for K.3 were already dirty; only targeted
additions were made. No pre-existing change was reverted or overwritten.

---

## 3. Verification of K.2 findings

Both K.2 blockers were verified against the current tree before changing
anything.

### 3.1 Blinkit is excluded before the fixture gate

`ProductSearchService.search` performs:

```python
for association in self._association_registry.all():
    if is_blinkit(association.platform):
        continue
    ...
    fixture_supported = self._include_fixtures and is_explicit_fixture(observation)
```

The Blinkit check precedes every fixture check. Direct verification with
`include_fixtures=True` against both tracked Blinkit-labelled dataset roots
returned zero items:

```text
data amul items 0 milk items 0 platforms []
demo_journey amul items 0 milk items 0 platforms []
```

This proves the zero-result behaviour was not merely a disabled-fixture
artifact: Blinkit is blocked first, centrally, and unconditionally.

### 3.2 The local-cart `/optimize` page used the operator-only API

The previous default `/optimize` branch imported `optimizeCart` and posted to
`/api/v1/cart/optimize`. That call has been removed from the page. The page now
uses the persisted-list flow:

```text
GET  /api/v2/lists
POST /api/v2/optimizations
GET  /api/v2/optimizations/{request_id}
```

No consumer page imports `optimizeCart` any more. The helper still exists in
`services/automaticPlanning.ts` but has no caller in `app/` or `components/`.

---

## 4. Synthetic catalog design (`CARTEL_DEMO`)

### 4.1 Source identity

- `Platform.CARTEL_DEMO` is a dedicated, retailer-independent source identity.
- It is deliberately excluded from `SUPPORTED_RETAILER_IDS` and therefore from
  the default retailer-adapter registry and from retailer-connection creation.
- It has no retailer account, credential, adapter, acquisition, cart, or
  checkout capability.

### 4.2 Dataset layout

Two physically separate roots are generated from the same deterministic
generator:

| Purpose | Root | Selection |
| --- | --- | --- |
| Runtime demo | `data/demo_catalog/` | `DATA_DIR=data/demo_catalog` |
| E2E fixture | `backend/tests/fixtures/synthetic_demo/` | harness copies to `/app/data` |

The generator writes `<root>/product_intelligence/{catalog,observations}/...`.
The tracked Blinkit fixtures under `data/product_intelligence/` and
`backend/tests/fixtures/demo_journey/` are untouched and are never used by the
consumer demo lane.

### 4.3 Catalog contents

Four product families, each with two exact pack-size variants and two synthetic
listings per variant (16 observations total):

| Product | Variants | Availability coverage |
| --- | --- | --- |
| Cartel Demo Toned Milk | 500 ml, 1 l | available / unavailable |
| Cartel Demo Whole Wheat Atta | 1 kg, 5 kg | available / unknown (`None`) |
| Cartel Demo Basmati Rice | 1 kg, 5 kg | unavailable / available |
| Cartel Demo Sunflower Oil | 1 l, 2 l | available / unknown (`None`) |

Each variant has a complete `PackConfiguration` with normalized units and net
content. Prices are deterministic integer minor units. Product and variant IDs
are stable and human-auditable, e.g.:

```text
cartel-demo-product-milk
cartel-demo-variant-milk-500ml
cartel-demo-listing-milk-500ml-a
```

### 4.4 Determinism

Two independent generations produced identical data digests. The checked-in
runtime and E2E datasets also match:

```text
runtime data_digest 4013a7c5fc601d869a6fb6d7267adb4d8c7f0c928023c065f1fdf466c0151613 files 18
fixture data_digest 4013a7c5fc601d869a6fb6d7267adb4d8c7f0c928023c065f1fdf466c0151613 files 18
```

The fixed capture timestamp is `2026-01-01T00:00:00+00:00`, so results do not
drift with wall-clock time.

### 4.5 Unknowns are preserved, not invented

- Unknown availability is stored as `None` and is never converted to
  "available".
- `tax_status` is `UNKNOWN`.
- No fees, discounts, serviceability, checkout totals, or payment outcomes are
  generated.
- The optimization result discloses that these values are unknown.

---

## 5. Provenance guarantees

Every synthetic observation carries all of the following:

| Field | Value |
| --- | --- |
| `platform` | `CARTEL_DEMO` |
| `parser_version` | `synthetic-v1` |
| `normalization_version` | `synthetic-v1` |
| `completeness.basis` | `synthetic-demo-catalog-v1` |
| `raw_artifact_reference.source_reference` | `synthetic://cartel-demo/<listing>` |
| `evidence_references[0].source_type` | `synthetic_catalog` |
| `tax_status` | `UNKNOWN` |

Representative persisted record:

```text
platform = CARTEL_DEMO
parser_version = synthetic-v1
normalization_version = synthetic-v1
availability_signal = None
observed_selling_price = {'currency': 'INR', 'minor_units': 28000}
tax_status = UNKNOWN
platform_identifiers = [['synthetic_listing_id', 'cartel-demo-listing-oil-2l-b']]
basis = synthetic-demo-catalog-v1
source_reference = synthetic://cartel-demo/cartel-demo-listing-oil-2l-b
```

Provenance is preserved through every layer:

- **Search** returns `evidence_state="synthetic_demo"` and `synthetic=true`.
- **Lists** returns `evidence_class="synthetic_demo"`.
- **Optimization** returns `evidence_class`, `is_synthetic`,
  `observation_state="synthetic_demo_observation"`, `tax_status="UNKNOWN"`,
  `fees_status="unknown"`, and `checkout_total=null` on every synthetic offer.
- **Reload** returns the identical persisted snapshot.
- **UI** labels synthetic results, prices, and availability explicitly and never
  describes them as live retailer evidence.

The live-evidence gate rejects the source:

```python
has_supported_retailer_evidence("CARTEL_DEMO", observation) is False
has_supported_retailer_evidence("BLINKIT", observation) is False
```

---

## 6. Blinkit block and retailer isolation

### 6.1 Blinkit remains centrally blocked

- `app/retailer_policy.py` is unchanged: `is_blinkit()` and
  `blinkit_consumer_eligible()` remain the single policy boundary.
- Search skips Blinkit associations before the fixture gate.
- Candidate discovery skips Blinkit associations.
- List selection rejects Blinkit source platforms with `409`.
- Ingestion and product-intelligence workers block Blinkit jobs.
- Tracked Blinkit fixtures still return zero consumer results even with
  `include_fixtures=True`.

### 6.2 `CARTEL_DEMO` has no retailer capability

- Not in `SUPPORTED_RETAILER_IDS`:

  ```text
  registry ids: ['BIGBASKET', 'BLINKIT', 'FLIPKART_MINUTES', 'INSTAMART', 'ZEPTO']
  CARTEL_DEMO connectable: False
  ```

- No placeholder adapter is registered for it.
- `LocalIngestionWorker` blocks a `CARTEL_DEMO` job before acquisition with
  `failed_stage="synthetic_no_acquisition"` and `FailureCategory.POLICY_BLOCKED`.
- `ProductIntelligenceRuntime` blocks it with
  `synthetic_catalog_has_no_acquisition_capability`.
- The generator never contacts a retailer, never opens a credential vault, and
  never creates cart or checkout evidence.

### 6.3 Swiggy Instamart

No Instamart authorization, connection, credential, or acquisition was added or
used. `CARTEL_DEMO` is not an Instamart alias and does not reuse Instamart
branding or identifiers.

---

## 7. Consumer discovery and search results

The consumer search endpoint is `GET /api/v2/products/search`, authenticated
and consumer-scoped.

With the synthetic runtime root selected and the demo gate enabled:

| Query | Items | Evidence state | Platforms |
| --- | --- | --- | --- |
| `milk` | 4 | `synthetic_demo` | `CARTEL_DEMO` |
| `atta` | 4 | `synthetic_demo` | `CARTEL_DEMO` |
| `rice` | 4 | `synthetic_demo` | `CARTEL_DEMO` |
| `oil` | 4 | `synthetic_demo` | `CARTEL_DEMO` |

With the demo gate disabled, the same query returns zero items. The synthetic
lane is therefore opt-in and never leaks into a default deployment.

Candidate discovery is also gated:

- `include_synthetic=False` → `not_ready_for_allocation` with reason
  `synthetic demo evidence is not enabled`.
- `include_synthetic=True` → available listings are
  `ready_for_allocation`; unavailable and unknown listings remain
  `not_ready_for_allocation`.

Exact variant identity is preserved. A milk query returns two distinct
variants (`500 ml`, `1 l`), not one merged product. Unknown and unavailable
states are preserved exactly.

---

## 8. Persisted optimization, reload, and unknown states

### 8.1 Flow

`/optimize` now:

1. loads the authenticated user's saved lists;
2. lets the user choose a list (or receives `list_id`/`revision` in the URL);
3. posts `{list_id, expected_revision}` to `/api/v2/optimizations`;
4. renders the persisted result and rewrites the URL with `request_id`;
5. reloads the same result via `GET /api/v2/optimizations/{request_id}`.

No optimization logic is duplicated in the frontend, and no operator-only
`/api/v1` endpoint is exposed.

### 8.2 Synthetic optimization outcome

Synthetic items are excluded from `optimizer_exact_items` and are never passed
to the automatic planner. They are discovered separately only to produce
observed synthetic offers.

A list containing available synthetic milk, unavailable synthetic rice, and a
free-text unresolved item produces:

| Field | Value |
| --- | --- |
| `status` | `unresolved` |
| `completeness` | `partial` |
| `optimizer_result` | `null` |
| `offers` | observed synthetic unit prices/subtotals only |
| `unresolved_items` | every synthetic item plus the free-text item |
| `explanation` | states synthetic data, unknown fees/taxes, and no payable recommendation |

Offers include only listings that explicitly establish current availability.
The unavailable rice listing does not become an offer. Every offer has
`tax_status="UNKNOWN"`, `fees_status="unknown"`, and `checkout_total=null`.

The optimization never produces a `ready` payable plan for synthetic evidence,
and no `optimization_plans` row is written.

### 8.3 Reload

`GET /api/v2/optimizations/{request_id}` returns the stored snapshot unchanged.
The browser reloads the URL and renders the same status, offers, unknown-state
disclosures, and explanation. Missing or stale results are handled with explicit
error copy; a result for a different list revision is rejected.

### 8.4 Why the result is `unresolved`, not `ready`

The optimizer requires correlated checkout ECE (effective cost evidence) before
it can produce a payable plan. Fabricating fees, taxes, serviceability, or
checkout totals to force a `ready` result would violate the non-negotiable
honesty rules. The honest maximum is a persisted `unresolved`/`partial` result
with synthetic observed product prices and explicit unknown disclosures.

Allocation and cost comparison are therefore demonstrated at the observed-offer
level — exact variant, pack size, observed unit price, observed product
subtotal, and simulated availability — and not as a payable basket, fee-inclusive
comparison, or checkout total.

---

## 9. Owner isolation and authenticated consumer surface

- All consumer endpoints require an authenticated consumer principal.
- Mutations require CSRF and same-origin checks.
- List and optimization reads are scoped by `user_id`; a second user receives
  `404` for another user's list and optimization.
- The E2E journey and the integration test both assert cross-user `404`
  behaviour.
- The operator-only `/api/v1/cart/optimize` remains forbidden to consumer
  sessions.
- No synthetic endpoint bypasses auth, CSRF, or owner isolation.

The integration test additionally asserts that no `optimization_plans` row is
written for the synthetic result.

---

## 10. Frontend and UI labelling

The existing design language is preserved. Synthetic data is labelled at every
consumer surface:

- **Search**: “Synthetic demo · not live retailer evidence”,
  “Synthetic price INR …”, “Simulated availability: …”, and a page-level
  disclosure that synthetic prices/availability are not checkout quotes.
- **Lists**: “Synthetic demo selection · not live retailer evidence” and a
  “Synthetic demo” badge.
- **Optimize**: a result banner stating the comparison uses the Cartel Demo
  synthetic catalog, prices are synthetic, availability is simulated, and
  fees/taxes/serviceability/checkout totals are unknown.
- **Offers**: “Synthetic observed unit price”, “synthetic observed product
  subtotal”, “Simulated availability”, and “Fees and taxes: unknown”.
- **No** “A plan is ready to review”, “Selected retailer groups”, savings claim,
  or checkout total is shown for synthetic evidence.

Legacy `demo_fixture` results remain separately labelled as fixture evidence.
The two non-live classes are never conflated with each other or with live data.

---

## 11. Test fixtures and E2E journey changes

### 11.1 E2E fixture root

`scripts/e2e/run_consumer_journey.py` now copies
`backend/tests/fixtures/synthetic_demo` into the API container's `/app/data`.
The legacy Blinkit `demo_journey` dataset is not used by the E2E harness.

The fixture root contains a README documenting generation, provenance, and the
absence of checkout/fee/tax/serviceability evidence.

### 11.2 Browser journey

`backend/tests/e2e/test_consumer_journey_browser.py` now covers:

- signup → email verification → session restoration after reload;
- create a persisted list and add an unresolved free-text item;
- discover and select an exact synthetic milk variant;
- discover and select an exact synthetic rice variant with unavailable
  availability;
- PostgreSQL assertions for 3 items, exact product/variant/listing/observation
  IDs, and `CARTEL_DEMO` source platform;
- reload the list and verify synthetic labels and the unresolved item;
- optimize the persisted revision and assert `unresolved` / `partial`, no
  optimizer result, synthetic offers only, unknown fees/taxes, and no payable
  copy;
- reload the `request_id` URL and assert the same result;
- assert `optimization_plans` count is zero;
- a second user receives `404` for the list and result and cannot see the
  synthetic data.

### 11.3 Fixture isolation

- Runtime demo data (`data/demo_catalog/`) and test fixtures
  (`backend/tests/fixtures/synthetic_demo/`) are separate roots.
- The generator CLI entrypoint (`python3 -m app.dev.seed_synthetic_demo_cart`)
  refuses to run in `APP_ENV=production`.
- No production seeding occurs unless an operator explicitly points `DATA_DIR`
  at the synthetic root and enables `DEMO_FIXTURES_ENABLED=true`.
- Deterministic generation means setup/teardown cannot leak cross-test state;
  each test seeds its own temporary root.

### 11.4 Legacy fixtures

The tracked Blinkit-labelled `data/product_intelligence/` and
`backend/tests/fixtures/demo_journey/` datasets remain unchanged. They are used
only as negative-control evidence that Blinkit and fixture data are excluded.
They are not used by the consumer demo lane or the E2E journey.

---

## 12. Validation evidence

### 12.1 Executed and passed

| Command | Result |
| --- | --- |
| `cd backend && python3 -m pytest tests/unit -q` | **1006 passed**, 2 warnings |
| `cd backend && python3 -m pytest tests/unit/services/test_synthetic_demo_catalog.py -q` | **13 passed** |
| `cd backend && python3 -m pytest tests/unit/services/test_synthetic_demo_catalog.py tests/unit/services/test_product_search.py tests/unit/services/test_cart_candidate_discovery.py tests/unit/test_blinkit_policy_lockdown.py tests/unit/retailer_adapters/test_registry.py tests/unit/retailer_connections/test_lifecycle.py -q` | **252 passed**, 1 warning (targeted regression run; includes the 13 synthetic tests) |
| `cd frontend && npm run typecheck` | **passed** (no output) |
| `cd frontend && npm run build` | **passed** (19 static pages generated) |
| `git diff --check` | **exit 0** |

The synthetic unit suite proves:

- byte-for-byte deterministic generation;
- every record carries explicit synthetic provenance;
- the live-evidence gate rejects `CARTEL_DEMO`;
- the source is not a connectable retailer and has no adapter;
- search is gated by `include_fixtures` and returns only `CARTEL_DEMO` rows;
- Blinkit never appears;
- exact pack-size variants remain distinct;
- unknown/unavailable availability is preserved;
- discovery is gated and keeps unknown availability not-ready;
- ingestion and product-intelligence workers block synthetic acquisition;
- the declared catalog contains exactly the expected products, variants,
  listings, and fixed timestamp.

### 12.2 Executed and skipped (not passed)

| Command | Result | Reason |
| --- | --- | --- |
| `cd backend && python3 -m pytest tests/integration/api/test_consumer_auth.py -q` | **18 skipped** | `CARTEL_TEST_DATABASE_URL` is unset; no disposable PostgreSQL |
| `cd backend && python3 -m pytest tests/e2e/test_consumer_journey_browser.py -q` | **1 skipped** | `E2E_BASE_URL`/`E2E_DATABASE_URL` unset; no browser stack |

The integration test file includes the new
`test_synthetic_demo_catalog_journey_persists_unknown_states_and_is_owner_scoped`,
which is collected but skipped locally. It must be run in a provisioned
PostgreSQL environment before K.4 sign-off.

### 12.3 Not executed

- Full `backend/tests/integration` suite (requires PostgreSQL).
- Full browser E2E stack (requires Docker, PostgreSQL, Redis, Chromium).
- Neon/Render/Vercel deployment smoke tests (no cloud accounts used).

### 12.4 Environment limitations

```text
CARTEL_TEST_DATABASE_URL=<unset>
docker: unavailable
pg: unavailable
```

No live retailer, paid API, cloud account, or browser automation service was
used.

---

## 13. Infrastructure limitations, blockers, and residual risks

### 13.1 Validation constraints (non-code)

| ID | Constraint | Impact |
| --- | --- | --- |
| V1 | No disposable PostgreSQL locally | DB-backed integration tests skipped |
| V2 | No Docker daemon locally | Browser E2E harness cannot start |
| V3 | No Redis locally | Rate-limit/worker E2E paths not exercised |
| V4 | No Chromium/E2E frontend stack | Browser journey skipped |

These are environment constraints, not implementation failures. The tests are
present and collected; they must be executed in CI or a provisioned host.

### 13.2 By-design product constraints

| ID | Constraint | Rationale |
| --- | --- | --- |
| P1 | Synthetic optimization is always `unresolved`/`partial` | No fabricated checkout ECE |
| P2 | No fees, taxes, serviceability, or checkout total | Unknown values must stay unknown |
| P3 | No payable plan from synthetic evidence | Honesty and safety boundary |
| P4 | `CARTEL_DEMO` is not a connectable retailer | No adapter/account/credential capability |

### 13.3 Residual UX risk

The local `/cart` page still presents a local cart and a button that routes to
`/optimize`. `/optimize` now operates on persisted shopping lists, so local cart
items are not automatically optimized. This is a navigation/copy inconsistency,
not a safety or API violation. It should be cleaned up in K.4 (for example, by
routing local-cart users to `/lists` or relabelling the button). No
operator-only API is exposed, and no optimization logic is duplicated.

### 13.4 Legacy fixture risk

The legacy Blinkit `demo_journey` fixture remains in the tree as a
negative-control test fixture. It is not used by the consumer demo lane or the
E2E harness. If a future change points `DATA_DIR` at it, Blinkit remains
excluded by policy, so it still cannot serve consumer results.

---

## 14. Files changed, preservation, and final decision

### 14.1 Created

| File | Purpose |
| --- | --- |
| `backend/app/demo_catalog.py` | Synthetic identity/provenance constants and helpers |
| `backend/app/dev/seed_synthetic_demo_cart.py` | Deterministic synthetic catalog generator |
| `backend/tests/unit/services/test_synthetic_demo_catalog.py` | Provenance, determinism, gating, adapter/acquisition isolation |
| `backend/tests/fixtures/synthetic_demo/**` | Generated E2E dataset (16 observations, catalog, associations, README) |
| `data/demo_catalog/**` | Generated runtime demo dataset |
| `docs/deployment/phase_k3_demo_readiness_report.md` | This report |

### 14.2 Modified (K.3-targeted additions only)

| File | Change |
| --- | --- |
| `backend/app/data_ingestion/enums.py` | Added `Platform.CARTEL_DEMO` |
| `backend/app/services/product_search.py` | Synthetic detection, `synthetic` field, `synthetic_demo` evidence state |
| `backend/app/services/cart_candidate_discovery.py` | `include_synthetic` gate, synthetic-aware readiness, `evidence_class` |
| `backend/app/api/v2/lists.py` | Synthetic evidence class and selection gate |
| `backend/app/api/v2/optimizations.py` | Synthetic classification, separate optimizer/synthetic items, synthetic offers, unknown disclosures, no optimizer call for synthetic |
| `backend/app/schemas/shopping_lists.py` | `synthetic_demo` evidence class |
| `backend/app/main.py` | Wire `include_synthetic` into discovery |
| `backend/app/workers/local_ingestion.py` | Block synthetic acquisition |
| `backend/app/workers/product_intelligence_runtime.py` | Block synthetic jobs |
| `backend/app/retailer_connections/lifecycle.py` | Exclude `CARTEL_DEMO` from connectable retailers |
| `frontend/types/product.ts` | Synthetic evidence type |
| `frontend/types/shoppingLists.ts` | Synthetic evidence class |
| `frontend/types/consumerOptimization.ts` | Synthetic offer/evidence/unknown fields |
| `frontend/services/productSearch.ts` | Parse synthetic evidence |
| `frontend/app/(app)/search/page.tsx` | Synthetic labels and selectability |
| `frontend/app/(app)/lists/page.tsx` | Synthetic labels |
| `frontend/app/(app)/optimize/page.tsx` | Persisted-list picker + synthetic result UI |
| `scripts/e2e/run_consumer_journey.py` | Point E2E at synthetic fixture root |
| `backend/tests/e2e/test_consumer_journey_browser.py` | Rewritten synthetic journey |
| `backend/tests/integration/api/test_consumer_auth.py` | Added synthetic fixture and integration journey test |

Many of these files already had pre-existing uncommitted modifications. Only
the targeted K.3 additions were made; no unrelated work was reverted.

### 14.3 Preserved

- All pre-existing modified and untracked files remain.
- No file was staged, committed, pushed, pulled, reset, stashed, checked out,
  cleaned, or discarded.
- Branch and HEAD are unchanged:
  `feat/cartel-production-foundation` /
  `59560b9dcab78c82c8bd3b0c47f8d7d33508a821`.

### 14.4 Final decision

**`READY_WITH_CONSTRAINTS`**

The demo lane is implemented and unit-verified: `CARTEL_DEMO` is discoverable
only through the demo gate, Blinkit remains centrally blocked, synthetic
provenance survives search/lists/optimization/persistence/reload/UI, exact
variants remain distinct, unknown states remain unknown, and synthetic evidence
cannot reach retailer adapters, acquisition, checkout, or a payable plan.

The constraints are:

1. Database-backed integration tests and the browser E2E journey must be run in
   a provisioned PostgreSQL/Docker environment before K.4 sign-off. They are
   currently **skipped**, not passed.
2. Synthetic optimization is intentionally `unresolved`/`partial` because fees,
   taxes, serviceability, and checkout totals are unknown and must not be
   fabricated.
3. The local `/cart` → `/optimize` navigation/copy inconsistency should be
   cleaned up in K.4.

No live retailer access, account connection, scraping, browser automation,
checkout, paid service, or Git mutation occurred.
