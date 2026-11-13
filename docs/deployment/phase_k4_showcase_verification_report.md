# Phase K.4 — Showcase verification and consumer-journey correction

**Date:** 2026-11-10
**Branch:** `feat/cartel-production-foundation`
**HEAD:** `59560b9dcab78c82c8bd3b0c47f8d7d33508a821`
**Decision:** `READY_WITH_CONSTRAINTS` (see §18)

This report closes the three K.3 constraints that blocked showcase sign-off:
database-backed integration tests were skipped, the browser E2E journey was
skipped, and the local `/cart` → `/optimize` journey was inconsistent. All three
are now executed or corrected against disposable local infrastructure. No
deployment, cloud account, paid service, live retailer access, or Git mutation
occurred.

---

## 1. Scope, constraints, and non-goals

**In scope**

- Verify every K.3 finding against the current tree.
- Correct the `/cart` → `/optimize` journey inconsistency.
- Explain `ready` / `partial` / `unresolved` optimization results, including the
  synthetic-evidence and unknown-economics disclosures.
- Run PostgreSQL-backed integration tests and the real-browser E2E journey on
  disposable local infrastructure.
- Validate the Architecture A staging configuration with dummy values.
- Re-run the named regression suite and the reseed procedure.
- Produce this report and a readiness decision.

**Out of scope / forbidden (all honoured)**

- ₹0 recurring cost; no card, paid API, cloud provisioning, deployment, provider
  account, OAuth submission, domain purchase, or external load test.
- No external retailer access, scraping, or browser automation. Blinkit remains
  centrally blocked; Swiggy Instamart remains unauthorized.
- No modification of the central retailer policy to make a test pass.
- No fake checkout totals, fees, taxes, discounts, or serviceability. Unknown
  stays unknown.
- No bypass of auth, CSRF, same-origin, owner scoping, rate limits, idempotency,
  or provenance in tests or E2E.
- No weakened/removed assertions, no `skip`/`xfail` added, no tests excluded.
- No SQLite or mock substitute for PostgreSQL.
- No touching the user's application database, external database, containers, or
  volumes that this phase did not create.
- No operator-only `/api/v1/cart/optimize` exposure and no duplicate cart state
  or optimization logic introduced.
- No unrelated UI redesign.
- No staging/commit/push/pull/reset/stash/checkout/clean/discard.
- No real secrets; dummy values only.

---

## 2. Baseline

Captured before any K.4 edit in
`/private/var/folders/ms/1k66djnj0ld5d7w18dn6hk7r0000gp/T/opencode/k4/baseline.txt`.

| Item | Baseline |
| --- | --- |
| Branch | `feat/cartel-production-foundation` |
| HEAD | `59560b9dcab78c82c8bd3b0c47f8d7d33508a821` |
| Staged files | 0 |
| Modified tracked files | 63 |
| Untracked files | 129 (`-uall`) |
| `git diff --stat` | 63 files, +1989, −563 |

Baseline validation, run before K.4 edits:

| Command | Result |
| --- | --- |
| `cd backend && python3 -m pytest tests/unit -q` | **1006 passed**, 2 warnings, exit 0 |
| `cd frontend && npm run typecheck` | exit 0 |
| `cd frontend && npm run build` | exit 0, 19 static pages |

The working tree already contained the K.2/K.3 implementation, including 63
modified tracked files and 129 untracked files. K.4 preserved all of it.

---

## 3. Verification of the K.3 findings

`docs/deployment/phase_k3_demo_readiness_report.md` §13.3 and §14.4 listed three
constraints. Each is verified below.

| K.3 finding | K.4 verification | Result |
| --- | --- | --- |
| Integration tests were skipped; no PostgreSQL/Docker run | Disposable PostgreSQL 16.15 + Redis 7 started; 20 integration tests executed with `-rs`; 0 skipped | **RESOLVED** |
| Browser E2E was skipped; no Chromium/frontend stack | Native FastAPI + Next.js stack on `127.0.0.1`; Playwright Chromium installed; 1 E2E journey executed | **RESOLVED** |
| Local `/cart` page showed a local cart and routed to `/optimize`, which operates on persisted lists | `/cart` now renders the user's persisted shopping lists from `GET /api/v2/lists`, labels the data source, and links to `/optimize?list_id=…&revision=…`; local `useCartStore` usage removed from `/cart` | **RESOLVED** |

No other K.3 safety finding regressed (see §11 and §14).

---

## 4. Consumer UX correction

### 4.1 The problem

`/cart` was a client-only local cart (`useCartStore`) whose “Optimize” action
opened `/optimize`. `/optimize` operates on a **persisted shopping list and
revision**, not on the local store. A user could therefore review local cart
items and then optimize a different (or empty) persisted list. That is a
navigation/copy inconsistency, not a safety violation, but it breaks the
showcase journey.

### 4.2 Chosen approach — Preferred (persisted-list-backed basket)

**Preferred:** `/cart` becomes a read-only basket view over the user's persisted
shopping lists.

- Calls `shoppingListsService.list()` → `GET /api/v2/lists`.
- Filters out archived and empty lists.
- Shows list name, revision, item count, item display name, quantity, unit, and
  resolution status.
- Labels the data source in the UI: “Data source: your persisted shopping lists
  (GET /api/v2/lists). This page does not keep a separate local cart.”
- Links each list to `/optimize?list_id=<id>&revision=<revision>` and to
  `/lists?list_id=<id>`.
- Shows a synthetic-evidence notice when any item is `synthetic_demo`.
- Shows **no** subtotal, savings, best-price, or payable total.

**Alternative rejected:** keep the local cart and make `/optimize` read it. This
would create a second cart state, duplicate optimization inputs, and diverge from
the persisted-list API that owns revisions and idempotency. It would also require
new optimization logic on the client. Rejected on the “no duplicate cart state or
optimization logic” requirement.

**Evidence**

- `frontend/app/(app)/cart/page.tsx` contains no `useCartStore`; it imports and
  calls `shoppingListsService`.
- `frontend/app/(app)/home/page.tsx` copy changed from “View your cart” to
  “Review your basket” and “recent baskets”.
- `backend/tests/unit/test_frontend_navigation_contract.py` asserts the source
  and forbidden strings statically.
- The browser E2E asserts the rendered data source, item count, synthetic notice,
  optimize link shape, and absence of “Subtotal”.

### 4.3 `/cart` reference sweep

Every `/cart` reference in the frontend was enumerated.

| File | Reference | Status |
| --- | --- | --- |
| `frontend/components/layout/AppSidebar.tsx` | `{ label: "Cart", href: "/cart" }` | Label matches destination; contract test + E2E |
| `frontend/components/layout/AppNavbar.tsx` | `aria-label="Open cart"` → `/cart` | Matches destination |
| `frontend/app/(app)/home/page.tsx` | Quick action → `/cart` | Copy changed to “Review your basket” |
| `frontend/app/(app)/results/page.tsx` | “Review cart” / “Back to cart” → `/cart` | Labels match the `/cart` destination |
| `frontend/app/(app)/cart/page.tsx` | The page itself | Rewritten as persisted-list basket |

Residual note: `/results` still reads the legacy local `useCartStore` for its
own comparison rendering. It is outside the corrected `/cart` → `/optimize`
journey, was not introduced by K.4, and was left unchanged to avoid an unrelated
redesign. The `/cart` page itself has no local cart state. This is recorded as a
non-blocking residual in §17.

### 4.4 Navigation label-vs-destination contract

| Label | Destination | Test |
| --- | --- | --- |
| Home | `/home` | `test_every_navigation_label_matches_its_destination` + E2E |
| Search | `/search` | same |
| Lists | `/lists` | same |
| Cart | `/cart` | same |
| Optimize | `/optimize` | same |
| Results | `/results` | same |
| Wrapped | `/wrapped` | same |
| Profile | `/profile` | same |
| Settings | `/settings` | same |

The contract test parses `appNavigation` from `AppSidebar.tsx` and asserts the
exact mapping. The E2E asserts each link’s `href` on the rendered page.

---

## 5. Partial-optimization explanation

### 5.1 Why a result is `ready`, `partial`, or `unresolved`

- **Ready** — every requested item has exact product evidence, so Cartel can
  describe a complete comparison.
- **Partial** — some items are covered and at least one is unresolved or lacks
  checkout evidence. **A partial result is not a failed calculation**: it reports
  exactly what is known and what is missing.
- **Unresolved** — Cartel could not match enough items to supported exact
  products, so it does not assert a comparison.

In the synthetic demo lane the result is intentionally `unresolved` with
`completeness: "partial"`: synthetic listings are simulated, real checkout
totals are unavailable, and fees, taxes, discounts, and serviceability are
unknown. Cartel must not invent them.

### 5.2 Required disclosures (exact rendered text)

`frontend/components/consumer/OptimizationStatusGuide.tsx` renders all three
meanings plus these disclosures:

- “Synthetic demo listings are simulated. They are not live retailer evidence.”
- “Real checkout totals are unavailable.”
- “Fees, taxes, discounts, and serviceability are unknown.”
- “A partial result is not a failed calculation.”
- “Cartel does not show a payable total, savings figure, or best-price claim from
  synthetic listings.”

The component also exposes the active status via
`data-testid="optimization-status-current"` and per-status cards
`status-guide-ready`, `status-guide-partial`, `status-guide-unresolved`.

### 5.3 Component and test coverage

- `frontend/app/(app)/optimize/page.tsx` renders
  `<OptimizationStatusGuide result={consumerResult} />` whenever a result exists.
- `backend/tests/unit/test_frontend_navigation_contract.py` asserts the guide is
  wired in and that all five disclosures and all three status keys are present.
- `backend/tests/e2e/test_consumer_journey_browser.py` asserts the rendered guide:
  current status `unresolved`, all three status cards, all five disclosures, and
  zero `payable-total` / `savings-figure` / `best-price` elements. It also asserts
  the result does not contain “You save” or “Best price”.

No synthetic price is presented as a payable total, savings figure, or best-price
claim anywhere in the corrected surface.

---

## 6. Disposable infrastructure

### 6.1 Docker probe

Docker Desktop was started locally (free, no account). The Server block was
probed for real:

```
Server: Docker Desktop 4.97.0 (244584)
 Engine:
  Version:          29.9.2
  API version:      1.56 (minimum version 1.40)
  Go version:       go1.26.10
  Git commit:       0367cbe
  Built:            Tue Oct 20 18:44:14 2026
  OS/Arch:          linux/arm64
  Experimental:     false
```

### 6.2 Created resources

| Resource | Value |
| --- | --- |
| Project/suffix | `1794313192` (unique) |
| PostgreSQL container | `cartel-k4-pg-1794313192` (`postgres:16-alpine`) |
| PostgreSQL volume | `cartel-k4-pgdata-1794313192` (own volume) |
| PostgreSQL host port | `127.0.0.1:55432` → `5432/tcp` (non-default) |
| Redis container | `cartel-k4-redis-1794313192` (`redis:7-alpine`) |
| Redis host port | `127.0.0.1:56379` → `6379/tcp` (non-default) |
| Label | `cartel.k4=true` on both containers |
| DB user / password / DB | `cartel` / `dummy` / `cartel_k4` |

Port freedom: both containers bound non-default host ports successfully; Docker
fails to start a container when a requested host port is already in use, and both
started healthy. No pre-creation `lsof` snapshot was retained, so freedom is
inferred from the successful bind rather than directly captured.

### 6.3 Database target confirmation

The application was pointed at the disposable database with an explicit
`DATABASE_URL` override, not the user's `cartel` database:

```
DATABASE_URL=postgresql+psycopg://cartel:dummy@127.0.0.1:55432/<db>
```

Masked: `postgresql+psycopg://cartel:***@127.0.0.1:55432/<db>`.

Databases created inside the disposable server:

| Database | Purpose |
| --- | --- |
| `cartel_k4` | default container database |
| `cartel_k4_it` | integration tests |
| `cartel_k4_e2e` | browser E2E |
| `cartel_k4_staging` | staging-config validation |
| `cartel_k4_migrate` | clean-migration proof |

The test run asserts the live database identity and server:

```sql
SELECT current_database(), current_setting('server_version');
-- cartel_k4_it | 16.15
```

The integration test also asserts inside the run:

- `current_database()` equals the database named in `CARTEL_TEST_DATABASE_URL`;
- `server_version` matches `^\d+\.\d+(\.\d+)?$`;
- `version()` contains `PostgreSQL`;
- `alembic_version` contains exactly `0009_credential_vault`.

No SQLite was used anywhere.

### 6.4 `docker ps` before/after

Before K.4 (captured in `docker_ps_before.txt`): four containers existed,
including the user's healthy `cartel-smart-cart-optimizer-postgres-1`, which was
never touched.

After K.4 (before teardown): the same four containers plus exactly the two
`cartel-k4-*` containers. The user's container remained `Up (healthy)`.

Before/after volume comparison: the pre-existing 21 volumes were all still
present; exactly one volume, `cartel-k4-pgdata-1794313192`, was added. Teardown is
in §15.

---

## 7. Migrations from clean

Run on a freshly created `cartel_k4_migrate` database with
`DATABASE_URL=postgresql+psycopg://cartel:dummy@127.0.0.1:55432/cartel_k4_migrate`.

| Command | Output | Exit |
| --- | --- | --- |
| `python3 -m alembic -c alembic.ini heads` | `0009_credential_vault (head)` | 0 |
| `python3 -m alembic -c alembic.ini upgrade head` | ran `0007 → 0008 → 0009` | 0 |
| `python3 -m alembic -c alembic.ini current` | `0009_credential_vault (head)` | 0 |
| `python3 -m alembic -c alembic.ini check` | `No new upgrade operations detected.` | 0 |
| DB assertion | `cartel_k4_migrate \| 16.15 \| 1 \| 0009_credential_vault` | 0 |

Single head, clean upgrade, no drift, one `alembic_version` row.

The integration fixture also drops and recreates the schema and runs
`downgrade base → upgrade head` in `test_00_migration_can_downgrade_and_upgrade`.

---

## 8. PostgreSQL integration results

### 8.1 Command and result

`cartel_k4_it` was dropped and recreated empty before the final run.

```bash
CARTEL_TEST_DATABASE_URL=postgresql+psycopg://cartel:dummy@127.0.0.1:55432/cartel_k4_it \
DATABASE_URL="$CARTEL_TEST_DATABASE_URL" \
REDIS_URL=redis://127.0.0.1:56379/0 \
AUTH_RATE_LIMIT_REQUESTS=1000 \
RATE_LIMIT_REQUESTS=100000 \
python3 -m pytest tests/integration/api/test_consumer_auth.py -q -rs
```

```
20 passed, 3 warnings in 3.32s
exit 0
```

`-rs` reported **zero skips**. The Redis limiter remained active; the limits were
raised only so the functional tests would not be throttled. No test was skipped,
excluded, or `xfail`ed.

### 8.2 Integration coverage map (14 required areas)

| # | Coverage area | Test(s) | Result |
| --- | --- | --- | --- |
| 1 | Clean migration downgrade/upgrade + live DB identity | `test_00_migration_can_downgrade_and_upgrade`, `test_auth_migration_upgrade_downgrade_upgrade_and_lifecycle` | PASS |
| 2 | Signup challenge + outbox persistence | `test_signup_persists_verification_challenge_and_outbox_with_autoflush_disabled` | PASS |
| 3 | Auth/session lifecycle and user scoping | `test_password_recovery_revokes_sessions_and_authentication_is_user_scoped` | PASS |
| 4 | Verified email + same-origin login | `test_login_requires_verified_email_and_origin_is_checked` | PASS |
| 5 | Consumer API scope + CSRF on v1 mutations | `test_consumer_session_is_limited_to_consumer_api_and_v1_mutations_require_csrf` | PASS |
| 6 | Idle/absolute expiry and reset revocation | `test_idle_expiry_revokes_consumer_session`, `test_absolute_expiry_revokes_consumer_session`, `test_password_reset_revokes_previously_issued_cookie` | PASS |
| 7 | List create/manage + CSRF/origin/owner negatives + both-direction isolation | `test_user_owned_shopping_list_create_manage_and_cross_user_isolation`, `test_cross_user_isolation_is_enforced_in_both_directions` | PASS |
| 8 | Item add persistence + idempotent replay | `test_shopping_list_item_add_persists_and_idempotent_replay_is_stable` | PASS |
| 9 | List-create idempotency replay/conflict | `test_shopping_list_create_idempotency_replay_and_conflict` | PASS |
| 10 | Optimization-create idempotency replay/conflict | `test_optimization_create_idempotency_replay_and_conflict` | PASS |
| 11 | Archival + selected product requires current governed evidence | `test_shopping_list_archival_and_selected_product_require_current_governed_evidence` | PASS |
| 12 | Search excludes non-live fixture evidence (incl. Blinkit) | `test_consumer_search_excludes_non_live_fixture_evidence` | PASS |
| 13 | Demo fixture labelled and never payable | `test_demo_fixture_selection_is_labelled_and_never_used_for_a_payable_plan` | PASS |
| 14 | Persisted optimization revision + owner scoping + synthetic unknowns + restart persistence | `test_consumer_optimization_persists_revision_and_replay_is_owner_scoped`, `test_synthetic_demo_catalog_journey_persists_unknown_states_and_is_owner_scoped`, `test_persisted_optimization_survives_new_client_and_app_restart` | PASS |

All 20 test functions passed; the table groups them into the 14 required
coverage areas. **0 FAILED, 0 SKIPPED.**

### 8.3 Persistence across sessions is real

`test_persisted_optimization_survives_new_client_and_app_restart`:

1. Creates a list and a persisted optimization in the original application.
2. Disposes all pooled engines and discards the original `TestClient`.
3. Builds a **new application instance** against the same PostgreSQL database.
4. Re-reads the optimization by `request_id` and asserts
   `reloaded.json() == result` field-for-field.
5. Re-reads the list and asserts the same revision and exact
   `canonical_variant_id`.
6. Asserts the restarted application still returns `401` without a session.

Because the original client and engines are gone, equality proves the result was
stored in PostgreSQL, not re-derived in memory.

### 8.4 Auth and cross-user isolation

`test_cross_user_isolation_is_enforced_in_both_directions` creates two verified
users with separate sessions and CSRF tokens. Each user is denied the other's
list, item mutation, and optimization with `404` (not-found convention avoids
leaking existence), in **both directions**, with valid ids and valid CSRF. It also
asserts neither owner's stored revision changed after the denied mutations.

The E2E repeats this at browser level: the second user sees the empty-list state,
gets `404` for both the list and the optimization, and the `/optimize` page shows
the not-available alert with no first-user content.

---

## 9. Browser E2E results

### 9.1 Stack

Because the repository's Docker E2E harness targets the user's `cartel_test`
database/container, a native stack was used instead:

- Backend: `python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18000`
  with `APP_ENV=staging`, `DATABASE_URL=…/cartel_k4_e2e`,
  `REDIS_URL=redis://127.0.0.1:56379/0`, `AUTH_REQUIRED=true`,
  `AUTH_COOKIE_SECURE=false` (local HTTP override), `DEMO_FIXTURES_ENABLED=true`,
  `DATA_DIR` copied from `backend/tests/fixtures/synthetic_demo`, and all retailer
  modes `unavailable`.
- Frontend: production build with
  `BACKEND_INTERNAL_URL=http://127.0.0.1:18000`, served by `next start -p 13000`.
- Browser: Playwright Chromium (free, local, no account).

Rewrite proof: `GET http://127.0.0.1:13000/api/v2/auth/csrf` returned `401` from
uvicorn (not a Next.js page), and `/health` on the frontend returned `404` (not
rewritten).

Backend readiness at E2E time:

```json
{"status":"ready","checks":{"product_intelligence_runtime":"ready",
"cart_planning":"ready","product_search":"ready","data_directory":"ready",
"checkout_capture":"unavailable","authentication":"ready","database":"ready",
"rate_limiter":"ready"}}
```

### 9.2 Command and result

```bash
E2E_BASE_URL=http://127.0.0.1:13000 \
E2E_BACKEND_URL=http://127.0.0.1:18000 \
E2E_DATABASE_URL=postgresql+psycopg://cartel:dummy@127.0.0.1:55432/cartel_k4_e2e \
E2E_REQUEST_LOG=…/request-log-final.txt \
python3 -m pytest tests/e2e/test_consumer_journey_browser.py -q -rs
```

```
1 passed in 2.64s
exit 0
```

The test is gated by `pytest.mark.skipif` when `E2E_BASE_URL` /
`E2E_DATABASE_URL` are unset. With the stack running it **executed**, it did not
skip. No assertion was relaxed for the run. Because the journey passed, no
failure traces or screenshots were produced; the request log in §9.4 is the
network evidence.

### 9.3 15-step journey map

| Step | Journey action | Assertion |
| --- | --- | --- |
| 1 | Signup, verify email, reload | Session restored to `/home` |
| 2 | Create persistent list | List heading visible |
| 3 | Add free-text unresolved item | “product match still unresolved” |
| 4 | Search synthetic variants | “Synthetic demo · not live retailer evidence” |
| 5 | Add exact milk variant | Saved status; exact identity later checked |
| 6 | Add unavailable rice variant | Simulated availability: unavailable |
| 7 | Verify persistence in PostgreSQL | 3 items; exact product/variant/listing/observation ids |
| 8 | Reload `/lists` | 3 persisted items with synthetic labels |
| 9 | Optimize persisted revision | `Some items need review`; synthetic/unknown copy; no plan |
| 10 | Reload persisted request URL | Same honest result; request id preserved |
| 11 | Status guide | `ready`/`partial`/`unresolved`, 5 disclosures, no payable/savings/best-price |
| 12 | Navigation labels | All 9 label→href pairs match |
| 13 | `/cart` | Data source `GET /api/v2/lists`; 1 list, 3 items, synthetic notice, optimize link, no “Subtotal” |
| 14 | Second user isolation | Empty list state; `404` for list and optimization; not-available alert |
| 15 | Egress/provenance guard | 0 retailer-bound, 0 operator-only, 0 non-local requests; readiness; `retailer_connections = 0`; DB snapshot |

### 9.4 Step-15 egress evidence

Final request log: **457 requests**, all to `127.0.0.1:13000`.

| Check | Count |
| --- | --- |
| Requests to `127.0.0.1:13000` | 457 |
| Requests to any other host | **0** |
| Retailer-bound markers (`blinkit`, `swiggy`, `instamart`, `zepto`, `bigbasket`, `jiomart`, `dunzo`, `amazon.`, `flipkart`) | **0** |
| Operator-only paths (`/api/v1/cart/optimize`, `/api/v1/retailer`, `/api/v1/scrape`) | **0** |
| `retailer_connections` rows | **0** |
| Optimization rows | 2, both `unresolved` |
| `optimization_plans` rows for the journey | 0 |

API calls were limited to `/api/v2/auth/*`, `/api/v2/me`, `/api/v2/lists*`,
`/api/v2/products/search`, and `/api/v2/optimizations*`. No retailer host or
operator endpoint was contacted.

The persisted snapshot also asserts every offer is `is_synthetic: true`,
`evidence_class: synthetic_demo`, `observation_state:
synthetic_demo_observation`, `tax_status: UNKNOWN`, `fees_status: unknown`, and
`checkout_total: null`.

---

## 10. Staging-configuration validation

File: `backend/tests/integration/api/test_staging_config_validation.py`.
All values are dummy. No provider is contacted.

```bash
CARTEL_TEST_DATABASE_URL=postgresql+psycopg://cartel:dummy@127.0.0.1:55432/cartel_k4_staging \
DATABASE_URL="$CARTEL_TEST_DATABASE_URL" \
REDIS_URL=redis://127.0.0.1:56379/0 \
python3 -m pytest tests/integration/api/test_staging_config_validation.py -q -rs
```

```
6 passed, 2 warnings in 0.36s
exit 0
```

| Check | Evidence | Result |
| --- | --- | --- |
| `APP_ENV=staging`, `AUTH_REQUIRED=true` | settings assertions | PASS |
| GitHub OAuth structurally valid | dummy id/secret + HTTPS callback URL | PASS |
| Database required | startup with unreachable DB raises `SQLAlchemyError` | PASS |
| Redis required / fail-closed | unreachable Redis → `503 rate_limit_unavailable` | PASS |
| Secure cookie flags from a real `Set-Cookie` | `HttpOnly; Secure; SameSite=lax; Path=/` under HTTPS base URL | PASS |
| CORS exact, no wildcard, no credentials | exact origin allowed; `https://evil.invalid` rejected; no `Allow-Credentials` | PASS |
| Frontend rewrite target | `BACKEND_INTERNAL_URL` used in `next.config.ts` | PASS |
| Demo gate off by default | `Settings().demo_fixtures_enabled is False`; explicit gate enables | PASS |
| Live acquisition unavailable | all retailer/checkout/vault provider modes default `unavailable` | PASS |
| Worker/SMTP not required | file email delivery with empty `smtp_host` | PASS |

This is **structural and runtime-local** validation. It is **not** provider
connectivity and makes no deployment claim.

---

## 11. Named regression suite

Each area was run separately. The synthetic exclusion in
`optimizer_exact_items` was not changed.

| # | Regression area | Command target | Result |
| --- | --- | --- | --- |
| 1 | Blinkit policy | `tests/unit/test_blinkit_policy_lockdown.py` | **24 passed** |
| 2 | Adapter capability boundaries | `tests/unit/retailer_adapters/test_capabilities.py` | **8 passed** |
| 3 | CredentialVault isolation | `tests/unit/credential_vault` | **32 passed** |
| 4 | Synthetic exclusion from retailer capabilities | `tests/unit/services/test_synthetic_demo_catalog.py` | **13 passed** |
| 5 | Synthetic rejection by live-evidence gates | `tests/unit/services/test_product_search.py` | **21 passed** |
| 6 | Auth/session ownership | 6 named tests in `test_consumer_auth.py` | **6 passed** |
| 7 | CSRF/same-origin | 3 named tests in `test_consumer_auth.py` | **3 passed** |
| 8 | Rate limiting | `tests/unit/test_rate_limit.py` | **2 passed** |
| 9 | Idempotency | 3 `-k "idempotency or idempotent"` tests | **3 passed** |
| 10 | Persisted-optimization ownership | 4 named tests in `test_consumer_auth.py` | **4 passed** |
| 11 | Unknown economic fields (integration) | 2 named tests in `test_consumer_auth.py` | **2 passed** |
| 12 | Unknown economic fields (unit) | `tests/unit/cart_optimization/test_service.py -k unknown` | **5 passed** |

All exit codes were 0. No test was skipped or excluded.

---

## 12. Operational limits

Every numeric limit below is labelled by evidence source. No limit is quoted from
memory.

| Limit | Value | Label | Source / access date |
| --- | --- | --- | --- |
| Local PostgreSQL version | 16.15 | **VERIFIED LOCALLY** | `current_setting('server_version')`, 2026-11-10 |
| Local Redis | 7 (`redis:7-alpine`), `PING` → `PONG` | **VERIFIED LOCALLY** | `redis-cli ping`, 2026-11-10 |
| Local Alembic head | `0009_credential_vault`, single head, no drift | **VERIFIED LOCALLY** | `alembic heads/current/check`, 2026-11-10 |
| Render Free web service hours | 750 instance hours/month | **PROVIDER DOCUMENTATION** | <https://render.com/docs/free>, 2026-11-10 |
| Render Free idle behaviour | spins down after 15 minutes idle; ~1 minute spin-up | **PROVIDER DOCUMENTATION** | <https://render.com/docs/free>, 2026-11-10 |
| Render Free filesystem | ephemeral | **PROVIDER DOCUMENTATION** | <https://render.com/docs/free>, 2026-11-10 |
| Render Free Postgres | 1 GB, expires after 30 days | **PROVIDER DOCUMENTATION** | <https://render.com/docs/free>, 2026-11-10 |
| Render Free pooling | no managed pooling | **PROVIDER DOCUMENTATION** | <https://render.com/docs/free>, 2026-11-10 |
| Neon scale-to-zero | suspends after 5 minutes inactive; reactivates within a few hundred milliseconds | **PROVIDER DOCUMENTATION** | <https://neon.com/docs/introduction/scale-to-zero>, 2026-11-10 |
| Neon pooling | PgBouncer transaction mode; up to 10,000 client connections; pool ≈ 90% of `max_connections`; pooled host uses `-pooler`; direct connection for migrations | **PROVIDER DOCUMENTATION** | <https://neon.com/docs/connect/connection-pooling>, 2026-11-10 |
| Upstash Redis Free storage | 250 MB | **PROVIDER DOCUMENTATION** | <https://upstash.com/docs/redis/overall/pricing>, 2026-11-10 |
| Upstash Redis Free bandwidth | 10 GB | **PROVIDER DOCUMENTATION** | <https://upstash.com/docs/redis/overall/pricing>, 2026-11-10 |
| Upstash Redis Free commands | 500,000 commands/month | **PROVIDER DOCUMENTATION** | <https://upstash.com/docs/redis/overall/pricing>, 2026-11-10 |
| Upstash Redis max throughput | 10,000 commands/sec | **PROVIDER DOCUMENTATION** | <https://upstash.com/docs/redis/overall/pricing>, 2026-11-10 |
| Upstash free databases | one free database | **PROVIDER DOCUMENTATION** | <https://upstash.com/docs/redis/overall/pricing>, 2026-11-10 |
| Vercel Hobby function duration | 300 s max | **PROVIDER DOCUMENTATION** | <https://vercel.com/docs/functions/limitations>, 2026-11-10 |
| Vercel Hobby function resources | 2 GB memory / 1 vCPU | **PROVIDER DOCUMENTATION** | <https://vercel.com/docs/functions/limitations>, 2026-11-10 |
| Vercel request body | 4.5 MB | **PROVIDER DOCUMENTATION** | <https://vercel.com/docs/functions/limitations>, 2026-11-10 |
| Vercel file descriptors | 1,024 | **PROVIDER DOCUMENTATION** | <https://vercel.com/docs/functions/limitations>, 2026-11-10 |
| Vercel deployments | 100/day | **PROVIDER DOCUMENTATION** | <https://vercel.com/docs/limits>, 2026-11-10 |
| “Vercel shared auth rate-limit bucket” | no direct provider document found | **UNVERIFIED ASSUMPTION** | searched provider docs, 2026-11-10 |
| Provider connectivity / real free-tier behaviour | not exercised | **UNVERIFIED ASSUMPTION** | K.4 forbids deployment; to be validated in K5 |

---

## 13. Reseed procedure

The synthetic demo catalog generator
(`backend/app/dev/seed_synthetic_demo_cart.py`) was run **twice** into a fresh
temporary directory with outbound `socket.connect` hard-blocked.

```
root: /var/folders/.../cartel-reseed-6g151te_
first_file_count: 18
second_file_count: 18
identical_manifests: true
first_product_ids:  cartel-demo-product-{milk,atta,rice,oil}
second_product_ids: cartel-demo-product-{milk,atta,rice,oil}
product_ids_identical: true
duplicate_paths: []
exit 0
```

- Idempotent: the second run produced a byte-identical 18-file tree (SHA-256
  manifest equality).
- No duplicates: same file set, same product ids.
- No external calls: the socket guard would have raised on any outbound connect;
  none occurred.
- The generator deletes only its own `product_intelligence/` subtree under the
  supplied root; it never touches the application database or another volume.

---

## 14. Test integrity

### 14.1 Collected counts before/after

| Suite | Baseline | After K.4 | Delta |
| --- | --- | --- | --- |
| Unit suite | 1006 passed | **1009 passed** | +3 (new navigation contract file) |
| `test_consumer_auth.py` | 18 passed (K.3 final) | **20 passed** | +2 (both-direction isolation, restart persistence) |
| `test_consumer_journey_browser.py` | 1 collected / skipped | **1 passed** | executed |
| `test_staging_config_validation.py` | not present | **6 passed** | new |
| `test_frontend_navigation_contract.py` | not present | **3 passed** | new |

### 14.2 `git diff` on pre-existing test files

`git diff -- backend/tests/integration/api/test_consumer_auth.py` shows 727
insertions and 9 deletions. The 9 deletions are mechanical, not weakened
assertions:

- `RecordingEmailDelivery.__init__` signature gained an optional engine;
- `_verification_token` gained a `recipient` argument and a `refresh()` call;
- two global `count(*)` assertions were scoped to the owning `user_id`.

The K.3 index-0 assumption was fixed by selecting intended items
deterministically; no assertion was removed. `test_consumer_journey_browser.py`
was already an untracked file at baseline (`?? backend/tests/e2e/`); K.4 edits to
it are additive (request recorder, nav/cart/status-guide assertions, egress
guard).

`grep` for `skip`/`xfail` in the touched files finds only the pre-existing
environment gates:

- E2E `pytest.mark.skipif` when `E2E_BASE_URL`/`E2E_DATABASE_URL` are unset;
- the standard integration guard that skips when no disposable PostgreSQL URL is
  configured.

Neither gate fired in the K.4 runs. No `skip`/`xfail` was added for the new
coverage.

`git diff --check` → exit 0.

---

## 15. Teardown and cleanup

Only the resources created by K.4 were removed:

```
docker rm -f cartel-k4-pg-1794313192 cartel-k4-redis-1794313192
docker volume rm cartel-k4-pgdata-1794313192
```

Verification after teardown:

- `docker ps -a` contains no `cartel-k4-*` container.
- `docker volume ls` contains no `cartel-k4-pgdata-*` volume.
- The user's `cartel-smart-cart-optimizer-postgres-1` container and
  `cartel-smart-cart-optimizer_cartel-postgres` volume remain intact.
- The other pre-existing containers/volumes (`aegis-modelops-*`,
  `flowforge-*`) remain untouched.

The native uvicorn/Next.js processes were stopped by PID after the final E2E run;
no user process was targeted.

---

## 16. Scope proof and files changed

Final `git status` differs from baseline only by K.4 files:

| File | Change | Why |
| --- | --- | --- |
| `frontend/app/(app)/cart/page.tsx` | modified | `/cart` persisted-list basket |
| `frontend/app/(app)/home/page.tsx` | modified | basket copy |
| `frontend/components/consumer/OptimizationStatusGuide.tsx` | new | partial/unknown explanation |
| `frontend/app/(app)/optimize/page.tsx` | modified (already modified at baseline) | renders the guide |
| `backend/tests/integration/api/test_consumer_auth.py` | modified (already modified at baseline) | K.3 fix + isolation/restart tests + DB identity assertion |
| `backend/tests/e2e/test_consumer_journey_browser.py` | modified (already untracked) | nav/cart/status-guide/egress coverage |
| `backend/tests/integration/api/test_staging_config_validation.py` | new | executable staging validation |
| `backend/tests/unit/test_frontend_navigation_contract.py` | new | static nav/UX contract |
| `docs/deployment/phase_k4_showcase_verification_report.md` | new | this report |

Counts: baseline 63 modified / 129 untracked → final **65 modified / 133
untracked**. The deltas are exactly the two newly modified frontend files and the
four newly untracked files (status guide, navigation contract, staging validation,
and this report); the E2E file was already inside an untracked directory.

Every file maps to `/cart` UX, the partial explanation, tests, config validation,
or this report. No unrelated file was changed.

Git state: branch and HEAD unchanged; 0 staged files; no
staging/commit/push/pull/reset/stash/checkout/clean/discard.

---

## 17. Skips, blockers, and residual risks

| Item | Status | Notes |
| --- | --- | --- |
| Integration skips | **0** | `-rs` showed none |
| E2E skips | **0** | executed against real stack |
| Unit skips | **0** | 1009 passed |
| Provider connectivity | **UNVERIFIED** | K.4 forbids deployment/accounts; validate in K5 |
| “Vercel shared auth rate-limit bucket” | **UNVERIFIED ASSUMPTION** | no direct provider doc found |
| Free-tier behaviour (spin-down, scale-to-zero, quotas) | **PROVIDER DOCUMENTATION** | documented, not exercised |
| `/results` legacy local-store rendering | **RESIDUAL, NON-BLOCKING** | outside the corrected `/cart` journey; unchanged to avoid redesign |
| Synthetic results are `unresolved`/`partial` | **INTENTIONAL** | fees/taxes/serviceability/checkout unknown; explained in UI |
| Blinkit | **BLOCKED BY POLICY** | regression green; no fixture exclusion changed |
| Swiggy Instamart | **UNAUTHORIZED** | no adapter/account/credential path used |

No blocker prevents K5. The residual `/results` item and the provider
assumptions are constraints, not safety failures.

---

## 18. Decision and decision rule

**Decision rule applied**

- `READY_FOR_K5` requires PostgreSQL integration + E2E executed with zero
  unexplained skips/failures, clean migrations, green regression, passing staging
  validation, and no blocker.
- `READY_WITH_CONSTRAINTS` applies when the core passed and only provider-specific
  unverified assumptions/limits remain.
- `BLOCKED` applies if PostgreSQL integration/E2E could not run, a safeguard
  failed, or policy/provenance/isolation is unproven.

**Application**

All core K.4 gates passed:

- PostgreSQL integration: **20 passed, 0 skipped, 0 failed**;
- Browser E2E: **1 passed, 0 skipped**, with zero retailer-bound or operator-only
  requests;
- Migrations: single head `0009_credential_vault`, clean upgrade, no drift;
- Regression: all 12 named areas green;
- Staging validation: **6 passed**;
- No policy, provenance, auth, CSRF, isolation, or idempotency failure.

The only remaining items are provider-specific assumptions that cannot be
verified without deployment (which K.4 forbids), plus one undocumented Vercel
rate-limit assumption. Under the stated rule, that is exactly the
`READY_WITH_CONSTRAINTS` case.

**Decision: `READY_WITH_CONSTRAINTS`**

Proceed to K.5 with the documented provider assumptions; validate real
provider connectivity, free-tier behaviour, and the Vercel rate-limit assumption
during deployment.

---

## 19. Compliance statement

- **No external accounts, cloud provisioning, paid services, or deployments.**
  Docker and Playwright Chromium were already free/local; provider docs were read
  over HTTP only.
- **No live retailer access, scraping, or browser automation.** The browser drove
  only the local Cartel frontend. Blinkit remained centrally blocked; Swiggy
  Instamart remained unauthorized.
- **No central retailer policy change** was made to pass a test.
- **No fake economics.** Synthetic prices are labelled simulated; checkout
  totals, fees, taxes, discounts, and serviceability remain null/unknown.
- **No safeguard bypass.** Auth, CSRF, same-origin, owner scoping, rate limits,
  idempotency, and provenance were exercised as real controls.
- **No SQLite or mock substitute** for PostgreSQL.
- **No user database/container/volume touched.** Only K.4-created resources were
  used and removed.
- **No Git mutation.** Branch, HEAD, index, and worktree history are unchanged;
  no staging/commit/push/pull/reset/stash/checkout/clean/discard occurred.
- **No real secrets.** All credentials were dummy values.
