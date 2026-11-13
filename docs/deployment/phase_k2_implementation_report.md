# Phase K.2 Implementation Report — Free-Tier Deployment Readiness

**Date:** 2026-11-09
**Repository:** `Cartel-Smart-Cart-Optimizer`
**Branch:** `feat/cartel-production-foundation`
**HEAD:** `59560b9dcab78c82c8bd3b0c47f8d7d33508a821`
**Authoritative predecessor:** `docs/deployment/free_tier_deployment_readiness.md` (Phase K.1)

**Final decision: `READY_WITH_CONSTRAINTS`**

The Architecture A deployment (Vercel Hobby + Render Free native Python + Neon Free
PostgreSQL + Upstash Free Redis + GitHub OAuth + tracked fixtures) is
implementation-compatible and can proceed to K.3 provisioning. It is **not**
launch-ready for public consumer use until the demo-fixture lane is fixed,
because the tracked demo catalogue is Blinkit-labelled and the central Blinkit
policy excludes it from every consumer serving path. That is the single
launch-blocking product constraint (see §12 and §17).

No infrastructure was provisioned. No account was created. No paid service was
activated. No Git mutation (stage, commit, push, pull, reset, stash, checkout,
clean, discard) was performed.

---

## 1. Scope and non-actions

### 1.1 In scope

- Read the K.1 report in full and re-verify every assumption against the current
  implementation.
- Make only the minimum compatibility changes required for the free-tier
  architecture.
- Verify the frontend, backend, PostgreSQL, Redis, authentication, worker/email
  deferral, filesystem persistence, and demo behaviour.
- Produce this report with a complete environment-variable matrix and honest
  evidence of what was and was not executed.

### 1.2 Explicitly out of scope / not done

| Action | Status |
| --- | --- |
| Create Neon, Upstash, Render, Vercel, or GitHub OAuth accounts | Not done |
| Provision any database, Redis instance, service, or domain | Not done |
| Deploy anything | Not done |
| Contact a provider | Not done |
| Enter payment or card details | Not done |
| Activate any paid plan | Not done |
| Live retailer access (Blinkit, Swiggy Instamart, any retailer) | Not done |
| Weaken authentication, authorization, CSRF, cookies, owner scoping, migrations, idempotency, rate limiting, `CredentialVault`, or evidence provenance | Not done |
| Add non-Blinkit demo fixtures | Not done (deferred to K.3) |
| Rewrite migration history | Not done |
| Mutate Git state | Not done |

### 1.3 Hard constraints carried forward from K.1

- ₹0 mandatory recurring cost, no payment card.
- Blinkit remains centrally blocked pending written commercial-use authorization.
- Swiggy Instamart remains unauthorized.
- No fabricated live retailer data.
- Demo data must always be labelled as fixture evidence.

---

## 2. Baseline workspace state

Recorded **before** any K.2 edit:

| Item | Value |
| --- | --- |
| Branch | `feat/cartel-production-foundation` |
| HEAD | `59560b9dcab78c82c8bd3b0c47f8d7d33508a821` |
| Staged files | 0 |
| Modified tracked files | 61 |
| Untracked entries | 87 (includes `docs/deployment/`) |

Recorded **after** the K.2 edits:

| Item | Value |
| --- | --- |
| Branch | `feat/cartel-production-foundation` (unchanged) |
| HEAD | `59560b9dcab78c82c8bd3b0c47f8d7d33508a821` (unchanged) |
| Staged files | 0 |
| Modified tracked files | 63 |
| Untracked entries | 87 |

The delta of two tracked files is exactly the two frontend files changed in K.2.
`backend/app/core/config.py` was already in the pre-existing modified set; K.2
added one validator change inside it. No file was staged, committed, pushed,
pulled, reset, stashed, checked out, cleaned, or discarded.

`backend/app/core/config.py` also contains pre-existing user work unrelated to
K.2 (`DEMO_FIXTURES_ENABLED`, credential-vault settings, and other changes). K.2
did not revert or rewrite any of it.

---

## 3. K.1 assumption verification

Each K.1 assumption was checked against the current tree. “Verified” means it was
confirmed by reading code or by a local execution. “Corrected” means K.1 was
incomplete or wrong and this report supersedes it.

### 3.1 Verified assumptions

| # | K.1 assumption | Evidence |
| --- | --- | --- |
| V1 | Frontend is Next.js 16 with App Router and `output: "standalone"`. | `frontend/package.json` pins `next@16.3.8`, `react@19.2.8`; `frontend/next.config.ts` sets `output: "standalone"`. |
| V2 | Frontend calls same-origin `/api` and relies on a rewrite. | `frontend/lib/apiClient.ts` uses a relative base (`NEXT_PUBLIC_API_BASE_URL ?? ""`); `next.config.ts` rewrites `/api/:path*`. |
| V3 | Frontend sends credentials and a CSRF header on unsafe methods. | `apiClient.ts` sets `credentials: "same-origin"`, fetches a CSRF token, and adds `X-CSRF-Token`. |
| V4 | Frontend has a 15 s request timeout. | `REQUEST_TIMEOUT_MS = 15_000` in `apiClient.ts`. |
| V5 | No backend secret is exposed through `NEXT_PUBLIC_*`. | Only `NEXT_PUBLIC_API_BASE_URL` is read client-side, and it must be empty in this architecture. No backend secret is referenced in the frontend. |
| V6 | Backend runs natively on Python 3.12. | `backend/Dockerfile` uses `python:3.12-slim`; a Python 3.12 venv resolved `backend/requirements/base.txt` successfully. |
| V7 | Backend serves on `0.0.0.0:$PORT` under Render. | `uvicorn` is the ASGI server; `$PORT` injection is a start-command concern, documented in §6. |
| V8 | `alembic upgrade head` is the migration command and the head is `0009_credential_vault`. | `alembic history` shows `<base> -> 0001_consumer_identity -> … -> 0009_credential_vault (head)`. |
| V9 | Migrations use PostgreSQL UUID/JSONB, constraints, and indexes, with no required extensions. | Grep of `app/db/migrations/versions/*.py` shows `postgresql.UUID`, JSONB, FKs, unique/check constraints, and `create_index`; no `CREATE EXTENSION`, `gen_random_uuid`, trigger, or function. |
| V10 | Offline migration SQL generation succeeds. | `alembic upgrade head --sql` generated SQL through `0009_credential_vault`. |
| V11 | DB engine uses `pool_pre_ping` and configurable pool settings. | `app/db/session.py`; pool size/overflow/timeout/recycle are settings. |
| V12 | Redis rate limiting is distributed and fail-closed. | `app/core/rate_limit.py` uses a Redis `EVAL` script and raises `RateLimitBackendUnavailable` on any Redis error. |
| V13 | Blinkit is centrally blocked and not configurable. | `app/retailer_policy.py` hard-codes Blinkit identifiers; `blinkit_consumer_eligible()` returns `False`. |
| V14 | Consumer v2 routes require an owner-scoped session and CSRF on mutations. | `app/api/v2/lists.py`, `optimizations.py`, `connections.py`, `products.py` use `current_consumer` / `csrf_protected`; `require_owner` hides other users’ resources as 404. |
| V15 | GitHub OAuth requires a verified primary email. | `app/auth/providers.py` requests `read:user user:email` and rejects unverified/absent primary email. |
| V16 | Email-dependent endpoints return 503 when SMTP is unconfigured. | `app/api/v2/auth.py` gates signup, resend, and recovery on `email_delivery_configured`. |
| V17 | `/health` does not touch DB/Redis. | `app/api/routes/health.py` returns static service metadata only. |
| V18 | `/ready` checks the DB only when `DATABASE_REQUIRED=true`. | Readiness route and lifespan. |
| V19 | `/docs` is disabled when `DOCS_ENABLED=false`. | Local TestClient returned 404 for `/docs`. |
| V20 | Staging accepts the proposed environment matrix. | A `Settings` instance built with the proposed staging values validated successfully; `secure_auth_cookie=True`, `email_delivery_configured=False`, `github_oauth_configured=True`, `cors_origins=()`. |
| V21 | An unreachable database fails startup explicitly when required. | `DATABASE_REQUIRED=true` + unreachable PostgreSQL raised `OperationalError` during lifespan. |
| V22 | An unreachable Redis fails closed. | A limiter pointed at `redis://127.0.0.1:1/0` raised `RateLimitBackendUnavailable`. |
| V23 | Unit tests pass. | `993 passed, 2 warnings` under Python 3.14.7. |
| V24 | Frontend typecheck and production build pass. | `npm run typecheck` exit 0; `npm run build` produced 19 static routes. |
| V25 | The Vercel rewrite target is baked into the build. | Built `routes-manifest.json` contains `destination: https://cartel-api.onrender.com/api/:path*` when `BACKEND_INTERNAL_URL` is set. |
| V26 | `docker compose config` is valid. | Exit 0 with dummy required values. |
| V27 | The app imports without a Chromium browser binary. | `python3 -c "import app.main"` succeeds with the Python `playwright` package installed but no browser download. |

### 3.2 Corrected / contradicted assumptions

| # | K.1 statement | Finding | Impact |
| --- | --- | --- | --- |
| C-1 | “Demo fixtures come from the Git checkout, so no object storage and no runtime writes are needed.” | The tracked fixtures are all `Platform.BLINKIT` / association platform `"blinkit"`. `ProductSearchService` unconditionally skips `is_blinkit(association.platform)` before the fixture gate. The tracked catalogue is therefore **not servable**. | **Launch-blocking product constraint.** The demo showcase returns zero search results. See §12. |
| C-2 | The demo seeder produces a usable demo catalogue. | `app/dev/seed_demo_cart.py` writes `Platform.BLINKIT` records, and the same central Blinkit filter excludes them. The E2E fixture dataset (`backend/tests/fixtures/demo_journey`) is also `"platform":"BLINKIT"`. | The checked-in E2E journey expectations (`Demo Item A` → 2 results) cannot be met under the current policy. |
| C-3 | The default database URL is acceptable. | `database_url` built from `POSTGRES_*` already uses `postgresql+psycopg://`, but a plain `DATABASE_URL=postgresql://…` was silently accepted and would resolve to the uninstalled `psycopg2` driver. | Fixed in K.2: the validator now rejects plain `postgresql://`. |
| C-4 | A Vercel build without configuration fails safely. | The rewrite fell back to the Docker-only host `http://api:8000` on Vercel, producing a deploy that builds but cannot reach an API. | Fixed in K.2: Vercel builds now fail explicitly when `BACKEND_INTERNAL_URL` is unset. |
| C-5 | Client-side routing can start OAuth. | `LoginForm` used `router.push()` for `/api/v2/auth/github/start`, which returns a server `303` to GitHub. Client-side routing does not reliably follow that cross-origin redirect. | Fixed in K.2: full-page `window.location.assign()`. |
| C-6 | `apscheduler` is used by the application. | No `apscheduler` import exists anywhere in `backend/app`. The dependency is declared but unused. | Harmless, but it is dead weight; do not rely on it for scheduling. |
| C-7 | The frontend “Optimize” flow uses the persisted optimization API. | The local-cart `/optimize` page calls `POST /api/v1/cart/optimize`, which is operator-only. A consumer cookie receives `403 operator_authentication_required`. The usable consumer path is the persisted list flow via `POST /api/v2/optimizations`. | Functional constraint, not a security weakening. See §6.4. |

### 3.3 Assumptions that could not be verified locally

| # | Assumption | Why not verified |
| --- | --- | --- |
| U1 | Neon accepts the exact connection string and TLS parameters. | No Neon account or database may be created. |
| U2 | Upstash `rediss://` works end-to-end. | No Upstash account or database may be created. |
| U3 | Render’s native Python build/start succeeds. | No Render service may be created. |
| U4 | Vercel serves the rewrite and preserves cookies in production. | No Vercel project may be created. |
| U5 | GitHub OAuth round-trip works with a real OAuth App. | No OAuth App may be created. |
| U6 | Integration/E2E suites pass against PostgreSQL + Redis. | `CARTEL_TEST_DATABASE_URL` is unset and the Docker daemon is unavailable. |
| U7 | Cold-start latency stays under the frontend timeout with keep-alive. | Requires a real Render Free service. |

These are explicitly reported as **unexecuted**, not passed.

---

## 4. Compatibility changes made

Three files changed. Each change is minimal and security-preserving.

### 4.1 `frontend/next.config.ts` — explicit Vercel build failure

```diff
+const backendInternalUrl = process.env.BACKEND_INTERNAL_URL;
+
+// Vercel has no Docker network. Fail the build explicitly instead of silently
+// rewriting /api traffic to the local-compose hostname.
+if (process.env.VERCEL && !backendInternalUrl) {
+  throw new Error(
+    "BACKEND_INTERNAL_URL must be set to the public Render backend origin for Vercel builds.",
+  );
+}
+
 const nextConfig: NextConfig = {
   output: "standalone",
   turbopack: { root: process.cwd() },
   async rewrites() {
     return [{
       source: "/api/:path*",
-      destination: `${process.env.BACKEND_INTERNAL_URL ?? "http://api:8000"}/api/:path*`,
+      destination: `${backendInternalUrl ?? "http://api:8000"}/api/:path*`,
     }];
   },
 };
```

**Rationale:** The Docker path keeps its `http://api:8000` fallback. Vercel has no
Docker network, so an unset variable would silently produce a broken deployment.
Failing the build is the honest, fail-closed behaviour.

**Verified:** `VERCEL=1 npm run build` fails with the explicit message;
`BACKEND_INTERNAL_URL=https://cartel-api.onrender.com npm run build` succeeds and
the rewrite manifest contains the Render origin.

### 4.2 `frontend/components/auth/LoginForm.tsx` — full-page OAuth start

```diff
-onClick={() => { router.push(`/api/v2/auth/${provider}/start?next=${encodeURIComponent(safeNextPath())}`); }}
+onClick={() => { window.location.assign(`/api/v2/auth/${provider}/start?next=${encodeURIComponent(safeNextPath())}`); }}
```

**Rationale:** `/api/v2/auth/{provider}/start` is a backend `GET` that returns a
`303` to the provider’s authorization URL. A full-page navigation lets the
browser follow the cross-origin redirect. `safeNextPath()` and the backend’s
`_safe_next()` both continue to reject open-redirect targets.

**Verified:** `npm run typecheck` and `npm run build` pass.

### 4.3 `backend/app/core/config.py` — require the psycopg 3 driver

```diff
 if value is not None:
     parsed = urlsplit(value.get_secret_value())
-    if parsed.scheme not in {"postgresql", "postgresql+psycopg"} or not parsed.hostname:
-        raise ValueError("DATABASE_URL must identify a PostgreSQL database")
+    if parsed.scheme != "postgresql+psycopg" or not parsed.hostname:
+        raise ValueError(
+            "DATABASE_URL must use the postgresql+psycopg:// scheme "
+            "(the psycopg2 driver is not installed)"
+        )
 return value
```

**Rationale:** `backend/requirements/base.txt` installs `psycopg[binary]`
(psycopg 3), not `psycopg2`. A plain `postgresql://` URL makes SQLAlchemy select
`psycopg2` and fail at runtime. The built-from-parts URL already uses
`postgresql+psycopg://`; only the explicit `DATABASE_URL` path needed tightening.

**Verified:** `postgresql://u:p@h/db` is rejected; `postgresql+psycopg://u:p@h/db`
and the `?sslmode=require` form are accepted. All 993 unit tests still pass.

### 4.4 What was deliberately not changed

- No rate limit was raised and no `X-Forwarded-For` trust was added.
- No authentication, CSRF, cookie, owner-scoping, migration, idempotency, or
  provenance logic was altered.
- No Redis fallback to process-local memory was added.
- No non-Blinkit demo fixture was added (K.3 prerequisite).
- No `/api/v1/cart/optimize` consumer exposure was added.
- No dependency pins were added (pre-existing risk; see §14).
- No `render.yaml` or `vercel.json` was added; configuration is documented in
  §13 and is applied through provider dashboards in K.3.

---

## 5. Frontend deployment compatibility

### 5.1 Next.js 16 / Vercel

| Check | Result |
| --- | --- |
| Next.js version | `16.3.8` (App Router, Turbopack build) |
| `output: "standalone"` | Present; Vercel ignores it and builds normally |
| Static route generation | 19 routes generated successfully |
| TypeScript | `tsc --noEmit` exit 0 |
| `BACKEND_INTERNAL_URL` required on Vercel | Enforced by the new build guard |
| Rewrite form | `beforeFiles`/`afterFiles` manifest entry for `/api/:path*` |
| Build-time env leakage | Only `NEXT_PUBLIC_API_BASE_URL` is client-visible; keep it empty |

`output: "standalone"` is harmless on Vercel. It remains required for the
Docker/local-compose path. Vercel’s build runs `npm run build` and uses its own
serverless/edge runtime, not `.next/standalone/server.js`.

### 5.2 Same-origin `/api` rewrites

The browser calls `https://<vercel-project>.vercel.app/api/...`. Vercel rewrites
to `https://<render-service>.onrender.com/api/...`. Consequences:

- Cookies are first-party to the Vercel origin.
- CORS is unnecessary; `CORS_ALLOWED_ORIGINS` stays empty.
- CSRF `Origin` checks compare against `PUBLIC_ORIGIN`, which must be the
  **Vercel** origin, not the Render origin.
- Vercel collapses the client IP to its proxy, so the backend sees a shared
  proxy identity for rate limiting. This is documented as a constraint; the
  limit is not raised and forwarding headers are not trusted.

### 5.3 Cookie, CSRF, and OAuth correctness

| Control | Behaviour |
| --- | --- |
| Session cookie | `cartel_session`, `httponly`, `samesite=lax`, `secure` from `secure_auth_cookie` |
| Staging default | `AUTH_COOKIE_SECURE` must be set to `true`; otherwise staging defaults to `False` |
| CSRF | `X-CSRF-Token` required on unsafe consumer methods; same-origin `Origin` required |
| OAuth start | Full-page navigation to the backend `303` (fixed) |
| OAuth state | One-use state/nonce/PKCE persisted in `oauth_challenges`, 10-minute expiry |
| Open redirect | `_safe_next()` rejects non-`/`, `//`, and backslash paths |
| Redirect URI | Taken from `GITHUB_REDIRECT_URI`, not from the request |

### 5.4 Cold-start handling

`apiClient.ts` aborts at 15 s and surfaces a safe error. Render Free spins down
after 15 minutes idle and can take roughly a minute to wake. The architecture
therefore depends on an external keep-alive (`GET /health` every 5 minutes via
cron-job.org or equivalent). This is an operational dependency, not a code
guarantee. A Vercel rewrite can also time out while Render wakes; the first
request after idle may fail even with keep-alive.

### 5.5 Frontend environment variables

| Name | Required | Secret | Example | Purpose |
| --- | --- | --- | --- | --- |
| `BACKEND_INTERNAL_URL` | Yes | No | `https://cartel-api.onrender.com` | Rewrite target for `/api/*` |
| `NEXT_PUBLIC_API_BASE_URL` | No — must be empty | No | *(empty)* | Optional absolute API base; leave empty for same-origin |

---

## 6. Backend deployment compatibility

### 6.1 Native Python 3.12 on Render Free

- Runtime: Python 3.12 (matches `python:3.12-slim` in the Dockerfile).
- Dependency file: `backend/requirements/base.txt`.
- A Python 3.12 venv `pip install --dry-run` resolved every requirement
  successfully, including `playwright`, `SQLAlchemy`, `FastAPI`, `psycopg`,
  `Authlib`, and `cryptography`.
- No Docker image is needed on Render.

### 6.2 Render build and start commands (to be entered in K.3)

```text
Root Directory: backend
Build Command:  pip install --upgrade pip && pip install -r requirements/base.txt
Start Command:  alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Notes:

- `alembic -c alembic.ini upgrade head` is safe on every deploy. It is
  idempotent and does not rewrite history.
- `$PORT` is injected by Render; do not hard-code `8000`.
- `backend/requirements.txt` is a thin `-r requirements/base.txt` include and may
  be used instead of the `base.txt` path.
- Do **not** run `playwright install chromium`. The Python package is imported
  transitively by `app.main`, but no browser binary is needed when live
  acquisition and Blinkit checkout capture are disabled.

### 6.3 Startup, shutdown, health

| Behaviour | Result |
| --- | --- |
| Startup DB check | Runs only when `DATABASE_REQUIRED=true`; a failure logs `database_startup_check_failed` and raises |
| Startup Redis check | Runs only when `APP_ENV=production`; a failure raises `RuntimeError` |
| Staging Redis outage | Does not fail startup; each rate-limited request returns `503 rate_limit_unavailable` |
| Shutdown | Closes the rate limiter and disposes engines |
| `/health` | 200 with service metadata; does not touch DB/Redis |
| `/ready` | 200 when runtime is wired; pings DB only when `DATABASE_REQUIRED=true` |
| `/docs` | 404 when `DOCS_ENABLED=false` |
| `/metrics` | Public Prometheus text; no secrets |

Because the deployment runs `APP_ENV=staging`, the Redis startup probe is
skipped. This is acceptable only because the per-request limiter is fail-closed.
If Redis is down, consumer and auth requests return 503 rather than bypassing the
limiter.

### 6.4 Playwright / Chromium runtime dependency

- `backend/requirements/base.txt` includes the `playwright` Python package.
- `backend/app/main.py` imports `app.scrapers.blinkit.checkout_capture`, which
  imports the Blinkit scraper and therefore Playwright modules.
- The Chromium browser binary is installed only in the Docker image
  (`playwright install --with-deps chromium`).
- With `RETAILER_DATA_PROVIDER_MODE=unavailable`,
  `CHECKOUT_CAPTURE_ADAPTER_MODE=unavailable`, and
  `CHECKOUT_OBSERVATION_PROVIDER_MODE=unavailable`, no browser is launched.
- `python3 -c "import app.main"` succeeds without a browser binary.

**Decision:** install the `playwright` Python package but not Chromium. If a
future change makes Playwright import lazy, the package could be removed; K.2
does not make that change.

### 6.5 Operator-only `/api/v1/cart/optimize`

`POST /api/v1/cart/optimize` is not in the consumer path allow-list in
`app/main.py`. A consumer cookie receives `403 operator_authentication_required`;
the integration test `test_consumer_auth.py` asserts this. The frontend
local-cart `/optimize` page calls this endpoint and therefore cannot complete for
a consumer. The supported consumer flow is:

1. Search via `GET /api/v2/products/search`.
2. Add items to a persisted list via `POST /api/v2/lists`.
3. Optimize the list revision via `POST /api/v2/optimizations`.

K.2 did not change this boundary. Making the local-cart page use the persisted
flow is a K.3 frontend task, not a compatibility fix.

---

## 7. PostgreSQL / Neon

### 7.1 Compatibility

| Check | Result |
| --- | --- |
| Driver | `psycopg[binary]` (psycopg 3); `DATABASE_URL` must use `postgresql+psycopg://` |
| Engine | SQLAlchemy 2.x PostgreSQL dialect |
| Pooling | `pool_pre_ping=True`; size/overflow/timeout/recycle configurable |
| TLS | Passed through in the URL (`?sslmode=require`) |
| UUID / JSONB | Native PostgreSQL types used; no extension required |
| Constraints / indexes | FKs, unique constraints, check constraints, and indexes present |
| Migration head | `0009_credential_vault` |
| Offline SQL | Generates successfully |

### 7.2 Neon connection-string guidance

Use a **direct (non-pooler)** Neon connection string for the Render web service,
or verify PgBouncer compatibility before using the pooled endpoint. psycopg 3
uses server-side prepared statements by default; transaction-pooling PgBouncer
can break them. K.2 did not add `prepare_threshold=0`, because that changes
driver behaviour and was not verified against Neon.

Recommended shape:

```text
DATABASE_URL=postgresql+psycopg://<user>:<password>@<neon-host>/<db>?sslmode=require
```

If the Neon pooled host is used and prepared statements fail, the fix is to add
`?sslmode=require&prepare_threshold=0` or use the direct host. This must be
tested in K.3; it is not claimed as verified.

### 7.3 Render pool sizing

Because Render Free runs a single instance and Neon Free has a small connection
budget, set:

```text
DB_POOL_SIZE=1
DB_MAX_OVERFLOW=0
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=300
```

This is deliberately conservative. It does not weaken correctness; it avoids
exhausting Neon connections during a cold start or a burst.

### 7.4 Migration command and validation

```bash
# Render start command runs this before uvicorn:
alembic -c alembic.ini upgrade head

# Validation:
alembic -c alembic.ini current
alembic -c alembic.ini heads
```

Failure detection:

- A bad URL raises `OperationalError` during the start command and Render marks
  the deploy failed.
- A migration error aborts the start command before `uvicorn` binds the port.
- With `DATABASE_REQUIRED=true`, the app also runs `SELECT 1` at startup and
  raises on failure.

Never edit an applied migration. Add a new revision instead.

---

## 8. Redis / Upstash

### 8.1 Compatibility

| Check | Result |
| --- | --- |
| URL schemes | `redis://` and `rediss://` accepted; TLS via `rediss://` |
| Distributed limiter | Single Lua `EVAL` per request; atomic across instances |
| Fail-closed | Any Redis error raises `RateLimitBackendUnavailable` → HTTP 503 |
| Timeouts | Connect and operation timeouts are configurable |
| Connection cap | `REDIS_MAX_CONNECTIONS` configurable |
| Local fallback | None; process-local memory is not used |

### 8.2 Upstash settings

```text
REDIS_URL=rediss://default:<password>@<upstash-host>:6379
REDIS_CONNECT_TIMEOUT_SECONDS=1
REDIS_OPERATION_TIMEOUT_SECONDS=1
REDIS_MAX_CONNECTIONS=5
```

Upstash Free is remote, so keep timeouts short. A Redis outage degrades to 503,
not to unauthenticated or unlimited traffic.

### 8.3 Shared auth bucket

Vercel collapses client IPs to its proxy, so the backend’s `request.client.host`
is shared across users. `AUTH_RATE_LIMIT_REQUESTS=8` per 60 s is therefore a
shared bucket in this architecture. K.2 did **not** raise it and did **not**
trust `X-Forwarded-For`. This is a documented availability constraint: a burst
of logins can rate-limit unrelated users. The correct future fix is a trusted
proxy configuration, not a higher limit.

---

## 9. Worker-dependent feature classification

The worker is **not deployed** in K.2. Features are classified as follows.

| Feature | Classification | Behaviour without the worker | Security impact |
| --- | --- | --- | --- |
| Scrape ingestion (`scrape_ingestion` jobs) | Deferrable | Jobs can be persisted but never executed | None; live acquisition is disabled |
| Email outbox delivery | Deferrable | Outbox rows are not delivered | None; email endpoints return 503 |
| Async retailer scraping | Deferrable / unsafe to enable | Not available | Live acquisition is disabled by policy and configuration |
| Blinkit checkout capture | Unsafe / blocked | Unavailable | Blinkit policy block preserved |
| Credential vault operations | Deferrable | Vault provider is `unavailable` and fails closed | No weakening |
| Optimization runs | Synchronous | Executed inline by the API | Preserved |
| List mutations and idempotency | Synchronous | Executed inline in PostgreSQL transactions | Preserved |
| OAuth state / sessions | Synchronous | Executed inline in PostgreSQL | Preserved |
| Object storage / artifact retention | Deferrable | Not used | No weakening |

### 9.1 Preserved job semantics

The `DurableJobStore`, `BackgroundWorker`, `EmailOutboxWorker`,
`JobExecutionCoordinator`, retry/backoff settings, lease settings, and
idempotency records remain in the codebase unchanged. Deferring the worker does
not delete or weaken them; it only means queued work is not consumed. When a
worker is later deployed, the same tables and semantics apply.

### 9.2 What must not be done to “make it work”

- Do not replace Redis rate limiting with in-process memory.
- Do not execute scrape jobs inline in the API.
- Do not enable live acquisition to populate the demo.
- Do not mark outbox events as delivered without sending.

---

## 10. Authentication: GitHub OAuth-only, email deferral

### 10.1 GitHub OAuth-only operation

- `GET /api/v2/auth/providers` advertises only configured providers.
- With GitHub configured and Google/Apple unset, the login page shows only
  “Continue with GitHub” plus the email/password form.
- GitHub verification requires `read:user user:email` and a **primary, verified**
  email. Missing or unverified email is rejected.
- OAuth state, nonce, and PKCE are persisted one-use with a 10-minute expiry.
- The callback sets the same hardened session cookie as password login.

### 10.2 Email-dependent endpoints

When SMTP is unconfigured (`SMTP_HOST` or `SMTP_FROM` empty):

| Endpoint | Response |
| --- | --- |
| `POST /api/v2/auth/signup` | `503 email_delivery_unavailable` |
| `POST /api/v2/auth/verification/resend` | `503 email_delivery_unavailable` |
| `POST /api/v2/auth/password/recovery` | `503 email_delivery_unavailable` |
| `POST /api/v2/auth/password/reset` | Depends on a valid one-use challenge; no challenge can be issued |

This is intentional and honest. It is not a bypass: no unverified account is
created and no recovery is faked.

### 10.3 Consequences for users

- A first-time user must sign in with GitHub. Email/password signup cannot
  complete without SMTP.
- Password recovery is unavailable. A user who loses GitHub access cannot
  recover a password-only account. This is an accepted K.2 limitation.
- `EMAIL_DELIVERY_MODE=file` is development-only, writes to ephemeral disk, and
  must not be used as a public delivery mechanism.

### 10.4 SMTP on Render Free

Render Free blocks outbound ports 25, 465, and 587. Free SMTP providers such as
Brevo or Resend are therefore not usable from Render Free via SMTP. Resend also
requires a verified sending domain. K.2 does not deploy email.

---

## 11. Filesystem writes and persistence

### 11.1 Runtime write inventory

| Path (relative to `DATA_DIR`) | Written by | Needed for demo | Durable on Render Free |
| --- | --- | --- | --- |
| `product_intelligence/catalog/` | Catalog store; demo seed | Read-only at runtime | No (ephemeral), but tracked in Git |
| `product_intelligence/observations/` | Observation registry | Read-only at runtime | No, but tracked |
| `product_intelligence/evidence/` | Evidence registry | Read-only at runtime | No, but tracked |
| `product_intelligence/demo_evidence/` | Demo evidence registry | Read-only at runtime | No, but tracked |
| `cost_intelligence/checkout_captures/` | Checkout capture service | No | No |
| `sessions/blinkit/` | Blinkit session bootstrap | No (live disabled) | No |
| `raw/`, `cleaned/`, `normalized/`, `exports/` | Ingestion/export tooling | No | No |
| `LOCAL_EMAIL_DIR` (`/tmp/cartel-email`) | File email delivery | No (dev only) | No |
| Cart optimization persistence files | Legacy file persistence | No | No |

### 11.2 Persistence rule

**All durable user state is in PostgreSQL**: users, identities, password
credentials, sessions, verification challenges, OAuth challenges, audit events,
idempotency records, shopping lists and items, optimization requests/plans/
allocations, background jobs, email outbox events, retailer connections, and
credential secrets.

No K.2 claim depends on Render’s filesystem being durable. The demo catalogue is
read from the Git checkout at startup; runtime writes are treated as ephemeral.
This must be stated in any operator runbook.

---

## 12. Demo mode behaviour and limitations

### 12.1 How demo mode is enabled

- `APP_ENV=staging` (production rejects `DEMO_FIXTURES_ENABLED=true`).
- `DEMO_FIXTURES_ENABLED=true`.
- The demo seeder refuses production.

### 12.2 What works

- `ProductSearchService(include_fixtures=True)` classifies explicit fixture
  observations as `evidence_state="demo_fixture"`.
- The frontend labels fixture results and selections as
  “Demo fixture · not live retailer evidence”.
- The optimization warning states that fixture prices cannot produce a payable
  recommendation, savings claim, or checkout total.
- Live acquisition is disabled; Blinkit checkout capture is unavailable.
- Historical Blinkit observations are excluded from consumer serving.
- All retailer controls (Blinkit block, Instamart unauthorized) are preserved.

### 12.3 The blocking contradiction

The tracked fixtures are Blinkit-labelled:

```text
data/product_intelligence/observations/*.json      → "platform":"BLINKIT"
data/product_intelligence/catalog/listing_associations.json → "platform":"blinkit"
backend/tests/fixtures/demo_journey/...            → "platform":"BLINKIT"
```

`app/services/product_search.py` skips Blinkit **before** evaluating the fixture
gate:

```python
if is_blinkit(association.platform):
    continue
...
fixture_supported = self._include_fixtures and is_explicit_fixture(observation)
```

Empirical result with the tracked data:

```text
Demo Item   -> 0 items
Demo Item A -> 0 items
demo        -> 0 items
associations: [('blinkit', 'demo-a-1'), ('blinkit', 'demo-a-2'),
               ('blinkit', 'demo-b-1'), ('blinkit', 'demo-b-2')]
```

Proof that the fixture lane itself works: a **temporary copy** of the data with
only the platform label rewritten to `ZEPTO` returns:

```text
Demo Item   -> 4 items, all evidence_state="demo_fixture", platform="zepto"
Demo Item A -> 2 items, all evidence_state="demo_fixture", platform="zepto"
```

The temporary copy was deleted. No repository fixture was changed.

### 12.4 Consequence

A consumer who signs in and searches for the demo items sees **no results**. The
search → add → optimize showcase cannot be demonstrated with the tracked
fixtures. The checked-in E2E journey expectations are also unsatisfiable under
the current policy.

### 12.5 Why K.2 did not fix it

Fixing it requires one of:

1. A non-Blinkit demo fixture lane (recommended; a K.3 prerequisite), or
2. A narrowly scoped, explicitly labelled demo exception to the Blinkit consumer
   filter (rejected: it weakens the central policy).

K.2 was constrained to minimum compatibility changes and no new demo fixtures.
Option 1 is the correct K.3 task.

---

## 13. Environment-variable matrix

Legend:

- **Required**: needed for the K.2 Architecture A deployment.
- **Secret**: must be stored only in the provider’s secret manager and never
  committed.
- **Environment**: `Render` (backend), `Vercel` (frontend), or `Local`.
- Examples are placeholders, not real credentials.

### 13.1 Render backend — required

| Name | Component | Required | Secret | Example | Purpose | Provider | Environment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `APP_ENV` | Backend | Yes | No | `staging` | Enables the demo lane; production rejects demo fixtures | Render | Render |
| `APP_DEBUG` | Backend | Yes | No | `false` | Disable debug tracebacks | Render | Render |
| `DOCS_ENABLED` | Backend | Yes | No | `false` | Hide `/docs` and `/redoc` | Render | Render |
| `AUTH_REQUIRED` | Backend | Yes | No | `true` | Enforce operator/consumer authentication | Render | Render |
| `AUTH_TOKENS` | Backend | Yes | Yes | `operator=<random-32-byte-token>` | Operator bearer tokens; never used by the frontend | Render | Render |
| `PUBLIC_ORIGIN` | Backend | Yes | No | `https://cartel.vercel.app` | Cookie/CSRF origin; must be the Vercel origin | Render | Render |
| `AUTH_COOKIE_SECURE` | Backend | Yes | No | `true` | Secure session cookie in staging | Render | Render |
| `DATABASE_REQUIRED` | Backend | Yes | No | `true` | Fail startup and `/ready` when PostgreSQL is unreachable | Neon | Render |
| `DATABASE_URL` | Backend | Yes | Yes | `postgresql+psycopg://user:pass@host/db?sslmode=require` | PostgreSQL connection; must use `postgresql+psycopg://` | Neon | Render |
| `DB_POOL_SIZE` | Backend | Yes | No | `1` | Conservative pool for Neon Free | Neon | Render |
| `DB_MAX_OVERFLOW` | Backend | Yes | No | `0` | Prevent connection bursts | Neon | Render |
| `DB_POOL_TIMEOUT_SECONDS` | Backend | Yes | No | `30` | Bounded pool wait | Neon | Render |
| `DB_POOL_RECYCLE_SECONDS` | Backend | Yes | No | `300` | Recycle before Neon idle timeouts | Neon | Render |
| `REDIS_URL` | Backend | Yes | Yes | `rediss://default:pass@host:6379` | Distributed rate limiting | Upstash | Render |
| `REDIS_CONNECT_TIMEOUT_SECONDS` | Backend | Yes | No | `1` | Fast fail-closed connect | Upstash | Render |
| `REDIS_OPERATION_TIMEOUT_SECONDS` | Backend | Yes | No | `1` | Fast fail-closed operation | Upstash | Render |
| `REDIS_MAX_CONNECTIONS` | Backend | Yes | No | `5` | Stay within Upstash Free | Upstash | Render |
| `GITHUB_CLIENT_ID` | Backend | Yes | No | `Iv1.xxxxxxxx` | GitHub OAuth client | GitHub | Render |
| `GITHUB_CLIENT_SECRET` | Backend | Yes | Yes | `<random-secret>` | GitHub OAuth secret | GitHub | Render |
| `GITHUB_REDIRECT_URI` | Backend | Yes | No | `https://cartel.vercel.app/api/v2/auth/github/callback` | Must match the GitHub App callback | GitHub | Render |
| `DEMO_FIXTURES_ENABLED` | Backend | Yes | No | `true` | Enable the labelled fixture lane | Render | Render |
| `DATA_DIR` | Backend | Yes | No | `../data` | Tracked fixture directory relative to `backend/` | Repo | Render |
| `RETAILER_DATA_PROVIDER_MODE` | Backend | Yes | No | `unavailable` | Disable live acquisition | Render | Render |
| `CHECKOUT_CAPTURE_ADAPTER_MODE` | Backend | Yes | No | `unavailable` | Disable Blinkit checkout capture | Render | Render |
| `CHECKOUT_OBSERVATION_PROVIDER_MODE` | Backend | Yes | No | `unavailable` | Disable live checkout observations | Render | Render |

### 13.2 Render backend — recommended hardening

| Name | Component | Required | Secret | Example | Purpose | Provider | Environment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `APP_NAME` | Backend | No | No | `Cartel` | Service name in logs | Render | Render |
| `APP_VERSION` | Backend | No | No | `0.1.0` | Reported by `/health` | Render | Render |
| `LOG_LEVEL` | Backend | No | No | `INFO` | Log verbosity | Render | Render |
| `LOG_JSON` | Backend | No | No | `true` | Structured logs | Render | Render |
| `CORS_ALLOWED_ORIGINS` | Backend | No | No | *(empty)* | Not needed for same-origin rewrite | Render | Render |
| `RATE_LIMIT_REQUESTS` | Backend | No | No | `120` | Per-path API limit | Upstash | Render |
| `RATE_LIMIT_WINDOW_SECONDS` | Backend | No | No | `60` | Limiter window | Upstash | Render |
| `AUTH_SESSION_DAYS` | Backend | No | No | `14` | Session lifetime | Render | Render |
| `AUTH_IDLE_DAYS` | Backend | No | No | `7` | Idle expiry | Render | Render |
| `AUTH_CHALLENGE_MINUTES` | Backend | No | No | `30` | Verification challenge lifetime | Render | Render |
| `AUTH_RATE_LIMIT_REQUESTS` | Backend | No | No | `8` | Shared auth bucket; do not raise for Vercel | Upstash | Render |
| `IDEMPOTENCY_TTL_SECONDS` | Backend | No | No | `86400` | Mutation idempotency retention | Render | Render |
| `API_V1_PREFIX` | Backend | No | No | `/api/v1` | Operator API prefix | Render | Render |
| `OPTIMIZATION_POLICY_VERSION` | Backend | No | No | `policy-v1` | Recorded policy version | Render | Render |
| `PLANNING_MAX_CART_ITEMS` | Backend | No | No | `20` | Planning bound | Render | Render |
| `PLANNING_MAX_CANDIDATES_PER_ITEM` | Backend | No | No | `20` | Planning bound | Render | Render |
| `PLANNING_MAX_COMBINATIONS` | Backend | No | No | `10000` | Planning bound | Render | Render |
| `PLANNING_MAX_SUPPLIED_PLANS` | Backend | No | No | `100` | Planning bound | Render | Render |

### 13.3 Render backend — deferred / unused in K.2

These must remain at safe defaults or be left unset. Setting them can enable
live acquisition, email, a worker, or a vault path that K.2 does not deploy.

| Name | Component | Required | Secret | Example | Purpose | Provider | Environment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POSTGRES_HOST` | Backend | No | No | `localhost` | Only used when `DATABASE_URL` is unset | — | Render |
| `POSTGRES_PORT` | Backend | No | No | `5432` | Only used when `DATABASE_URL` is unset | — | Render |
| `POSTGRES_DB` | Backend | No | No | `cartel` | Only used when `DATABASE_URL` is unset | — | Render |
| `POSTGRES_USER` | Backend | No | No | `cartel` | Only used when `DATABASE_URL` is unset | — | Render |
| `POSTGRES_PASSWORD` | Backend | No | Yes | `<secret>` | Only used when `DATABASE_URL` is unset | — | Render |
| `QUICKCOMMERCE_API_BASE_URL` | Backend | No | No | *(empty)* | QuickCommerce provider; leave empty | — | Render |
| `QUICKCOMMERCE_API_KEY` | Backend | No | Yes | *(empty)* | QuickCommerce key; leave empty | — | Render |
| `QUICKCOMMERCE_TIMEOUT_SECONDS` | Backend | No | No | `10` | Provider timeout | — | Render |
| `PLANNING_RETAILER_IDENTITY_MAP` | Backend | No | No | *(empty)* | Operator planning authority | — | Render |
| `PLANNING_CHECKOUT_GROUP_MAP` | Backend | No | No | *(empty)* | Operator planning authority | — | Render |
| `PLANNING_INCONVENIENCE_PENALTY_UNITS` | Backend | No | No | *(empty)* | Operator planning authority | — | Render |
| `PLANNING_RETAILER_PREFERENCE_PRIORITY` | Backend | No | No | *(empty)* | Operator planning authority | — | Render |
| `PLANNING_FEASIBILITY` | Backend | No | No | *(empty)* | Operator planning authority | — | Render |
| `PLANNING_FEASIBILITY_EVIDENCE` | Backend | No | No | *(empty)* | Operator planning evidence | — | Render |
| `SCRAPER_TIMEOUT_SECONDS` | Backend | No | No | `15` | Scraper timeout (unused while disabled) | — | Render |
| `SCRAPER_MAX_RETRIES` | Backend | No | No | `3` | Scraper retry (unused while disabled) | — | Render |
| `SCRAPER_RETRY_BACKOFF_SECONDS` | Backend | No | No | `1` | Scraper backoff (unused while disabled) | — | Render |
| `SCRAPER_USER_AGENT` | Backend | No | No | `<browser UA>` | Scraper UA (unused while disabled) | — | Render |
| `BLINKIT_DELIVERY_LOCATION_NAME` | Backend | No | No | `Gurugram` | Blinkit location (live disabled) | — | Render |
| `BLINKIT_DELIVERY_LATITUDE` | Backend | No | No | `28.413333` | Blinkit location (live disabled) | — | Render |
| `BLINKIT_DELIVERY_LONGITUDE` | Backend | No | No | `77.072833` | Blinkit location (live disabled) | — | Render |
| `BLINKIT_GEOLOCATION_ACCURACY` | Backend | No | No | `50` | Blinkit location (live disabled) | — | Render |
| `BLINKIT_SESSION_STATE_PATH` | Backend | No | No | `../data/sessions/blinkit/browser_state.json` | Blinkit session (live disabled) | — | Render |
| `BLINKIT_BROWSER_EXECUTABLE_PATH` | Backend | No | No | *(empty)* | Blinkit browser (live disabled) | — | Render |
| `SMTP_HOST` | Backend | No | No | *(empty)* | Leave empty to disable email | — | Render |
| `SMTP_PORT` | Backend | No | No | `587` | SMTP port (blocked on Render Free) | — | Render |
| `SMTP_USERNAME` | Backend | No | No | *(empty)* | SMTP auth | — | Render |
| `SMTP_PASSWORD` | Backend | No | Yes | *(empty)* | SMTP auth | — | Render |
| `SMTP_FROM` | Backend | No | No | *(empty)* | Leave empty to disable email | — | Render |
| `SMTP_STARTTLS` | Backend | No | No | `true` | SMTP TLS | — | Render |
| `EMAIL_DELIVERY_MODE` | Backend | No | No | `smtp` | Keep `smtp`; `file` is dev-only | — | Render |
| `LOCAL_EMAIL_DIR` | Backend | No | No | `/tmp/cartel-email` | Dev-only file delivery | — | Render |
| `GOOGLE_CLIENT_ID` | Backend | No | No | *(empty)* | Google OAuth disabled | — | Render |
| `GOOGLE_CLIENT_SECRET` | Backend | No | Yes | *(empty)* | Google OAuth disabled | — | Render |
| `GOOGLE_REDIRECT_URI` | Backend | No | No | *(empty)* | Google OAuth disabled | — | Render |
| `APPLE_CLIENT_ID` | Backend | No | No | *(empty)* | Apple readiness only; adapter not implemented | — | Render |
| `APPLE_TEAM_ID` | Backend | No | No | *(empty)* | Apple readiness only | — | Render |
| `APPLE_KEY_ID` | Backend | No | No | *(empty)* | Apple readiness only | — | Render |
| `APPLE_PRIVATE_KEY` | Backend | No | Yes | *(empty)* | Apple readiness only | — | Render |
| `APPLE_REDIRECT_URI` | Backend | No | No | *(empty)* | Apple readiness only | — | Render |
| `WORKER_CONCURRENCY` | Worker | No | No | `1` | Worker not deployed | — | — |
| `JOB_POLL_INTERVAL_SECONDS` | Worker | No | No | `1` | Worker not deployed | — | — |
| `JOB_MAX_ATTEMPTS` | Worker | No | No | `3` | Preserved semantics | — | — |
| `JOB_RETRY_BASE_SECONDS` | Worker | No | No | `5` | Preserved semantics | — | — |
| `JOB_RETRY_MAX_SECONDS` | Worker | No | No | `300` | Preserved semantics | — | — |
| `JOB_LEASE_SECONDS` | Worker | No | No | `300` | Preserved semantics | — | — |
| `OUTBOX_MAX_ATTEMPTS` | Worker | No | No | `5` | Preserved semantics | — | — |
| `OUTBOX_RETRY_BASE_SECONDS` | Worker | No | No | `5` | Preserved semantics | — | — |
| `OUTBOX_RETRY_MAX_SECONDS` | Worker | No | No | `300` | Preserved semantics | — | — |
| `OUTBOX_LEASE_SECONDS` | Worker | No | No | `300` | Preserved semantics | — | — |
| `OUTBOX_POLL_INTERVAL_SECONDS` | Worker | No | No | `1` | Worker not deployed | — | — |
| `VAULT_KEY_PROVIDER` | Backend | No | No | `unavailable` | Fail-closed vault; keep unavailable | — | Render |
| `VAULT_DEV_KEYS` | Backend | No | Yes | *(empty)* | Dev-only vault keys; never set publicly | — | Render |
| `VAULT_ACTIVE_KEY_VERSION` | Backend | No | No | *(empty)* | Vault version; unused while unavailable | — | Render |

### 13.4 Vercel frontend

| Name | Component | Required | Secret | Example | Purpose | Provider | Environment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `BACKEND_INTERNAL_URL` | Frontend | Yes | No | `https://cartel-api.onrender.com` | `/api/*` rewrite target; Vercel build fails if unset | Render | Vercel |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | No — empty | No | *(empty)* | Optional absolute API base; empty means same-origin | — | Vercel |
| `VERCEL` | Frontend | Auto | No | `1` | Injected by Vercel; triggers the build guard | Vercel | Vercel |

### 13.5 Local / development only

| Name | Component | Required | Secret | Example | Purpose | Provider | Environment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POSTGRES_PASSWORD` | Compose | Local only | Yes | `<secret>` | Local compose PostgreSQL | — | Local |
| `AUTH_TOKENS` | Local | Local only | Yes | `operator=<token>` | Local operator auth | — | Local |
| `SMTP_HOST` / `SMTP_FROM` | Local | Local only | No | `mail.invalid` / `no-reply@example.com` | Local compose startup validation | — | Local |

---

## 14. Security and operational risks

### 14.1 Accepted constraints

| # | Risk | Mitigation / statement |
| --- | --- | --- |
| R1 | Demo catalogue is not servable (Blinkit filter) | K.3 must add a non-Blinkit fixture lane. Do not launch consumer demo before this. |
| R2 | Vercel Hobby is for non-commercial personal use | Accept only if the showcase is non-commercial. Otherwise a paid plan or different host is required. |
| R3 | Render Free cold start can exceed the 15 s frontend timeout | External keep-alive every 5 minutes; first request after idle may still fail. |
| R4 | Render Free filesystem is ephemeral | All durable state is in PostgreSQL; no durability claim is made. |
| R5 | Shared auth rate-limit bucket behind Vercel | Documented; limit not raised and `X-Forwarded-For` not trusted. |
| R6 | No email delivery / no password recovery | GitHub OAuth only; email endpoints return 503. |
| R7 | No worker | Scrape ingestion, outbox delivery, and async work are deferred; semantics preserved. |
| R8 | Dependencies are unpinned | Builds are not reproducible. Pin versions before treating a deploy as reproducible. Pre-existing, not changed in K.2. |
| R9 | `apscheduler` is declared but unused | No scheduling depends on it. |
| R10 | Staging is not production | Production validators are not exercised. The deployment must set the production-equivalent security values manually (listed in §13.1). |
| R11 | Local Python is 3.14.7, deploy is 3.12 | Unit tests ran on 3.14.7; Python 3.12 dependency resolution passed, but the full suite was not re-run on 3.12. |
| R12 | Neon pooled endpoint may break prepared statements | Use the direct endpoint or verify `prepare_threshold=0` in K.3. |

### 14.2 Security controls confirmed intact

- Authentication required for protected routes when `AUTH_REQUIRED=true`.
- Consumer sessions are owner-scoped; cross-owner access returns 404.
- CSRF and same-origin checks remain on unsafe consumer methods.
- Cookies remain `httponly`, `samesite=lax`, and `secure` when configured.
- OAuth state is one-use, expiring, and PKCE-protected.
- GitHub requires a verified primary email.
- Redis rate limiting remains distributed and fail-closed.
- Migrations are unchanged and forward-only.
- Idempotency records and TTLs are unchanged.
- Blinkit remains centrally blocked; Instamart remains unauthorized.
- `CredentialVault` remains fail-closed (`unavailable`).
- Evidence provenance and demo labelling are preserved.

---

## 15. Verification evidence

### 15.1 Executed and passed

| Check | Command | Result |
| --- | --- | --- |
| Unit tests | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit -q -p no:cacheprovider` | `993 passed, 2 warnings` (Python 3.14.7) |
| Frontend typecheck | `npm run typecheck` | Exit 0 |
| Frontend build | `npm run build` | Success; 19 static routes |
| Vercel guard | `VERCEL=1 npm run build` | Expected explicit failure: `BACKEND_INTERNAL_URL must be set…` |
| Vercel build with backend | `BACKEND_INTERNAL_URL=https://cartel-api.onrender.com npm run build` | Success |
| Rewrite manifest | Inspect `.next/routes-manifest.json` | `destination: https://cartel-api.onrender.com/api/:path*` |
| Migration history | `python3 -m alembic -c alembic.ini history` | Head `0009_credential_vault` |
| Offline migration SQL | `DATABASE_URL=postgresql+psycopg://… alembic upgrade head --sql` | Success through `0009_credential_vault` |
| Python 3.12 dependency resolution | Temp venv `pip install --dry-run -r requirements/base.txt` | Success |
| Staging config validation | Construct `Settings` with the §13 matrix | Accepted; `secure_auth_cookie=True`, `email_delivery_configured=False`, `github_oauth_configured=True`, `cors_origins=()` |
| DB URL validator | `Settings(database_url_override=…)` | Plain `postgresql://` rejected; `postgresql+psycopg://` accepted |
| DB startup failure | `DATABASE_REQUIRED=true` + unreachable host | `OperationalError` during lifespan |
| Redis fail-closed | Limiter at `redis://127.0.0.1:1/0` | `RateLimitBackendUnavailable` |
| Health/ready/docs/metrics | TestClient | `/health` 200, `/ready` 200, `/docs` 404, `/metrics` 200 |
| App import without Chromium | `python3 -c "import app.main"` | Success |
| Compose config | `docker compose config` with dummy values | Exit 0 |

### 15.2 Executed and failed as expected

| Check | Result | Interpretation |
| --- | --- | --- |
| `VERCEL=1 npm run build` without `BACKEND_INTERNAL_URL` | Explicit build failure | Correct fail-closed behaviour |
| Plain `postgresql://` database URL | Validation error | Correct driver guard |

### 15.3 Not executed

| Check | Reason |
| --- | --- |
| Integration tests | `CARTEL_TEST_DATABASE_URL` unset |
| E2E browser journey | Requires Docker + a running frontend/backend + PostgreSQL; Docker daemon unavailable |
| Real Neon connection | No account/provisioning permitted |
| Real Upstash connection | No account/provisioning permitted |
| Real Render deployment | No account/provisioning permitted |
| Real Vercel deployment | No account/provisioning permitted |
| Real GitHub OAuth round-trip | No OAuth App permitted |
| Cold-start timing | Requires a real Render Free service |

No unexecuted check is reported as passed.

### 15.4 Demo-fixture evidence

| Check | Result |
| --- | --- |
| Tracked fixture platforms | All `BLINKIT` / `"blinkit"` |
| Search “Demo Item” with tracked fixtures | 0 items |
| Search “Demo Item A” with tracked fixtures | 0 items |
| Search “demo” with tracked fixtures | 0 items |
| Temporary ZEPTO relabel, “Demo Item” | 4 items, all `demo_fixture` |
| Temporary ZEPTO relabel, “Demo Item A” | 2 items, all `demo_fixture` |
| Temporary copy cleanup | Deleted; no repository change |

---

## 16. Files created / modified

### 16.1 Created

| File | Purpose |
| --- | --- |
| `docs/deployment/phase_k2_implementation_report.md` | This report |

### 16.2 Modified (K.2 changes only)

| File | Change |
| --- | --- |
| `frontend/next.config.ts` | Explicit Vercel build failure when `BACKEND_INTERNAL_URL` is unset; Docker fallback retained |
| `frontend/components/auth/LoginForm.tsx` | OAuth start uses full-page `window.location.assign()` |
| `backend/app/core/config.py` | `DATABASE_URL` validator requires `postgresql+psycopg://` |

### 16.3 Not modified

- No migration file.
- No dependency file.
- No Docker/Compose file.
- No fixture or data file.
- No authentication, CSRF, cookie, rate-limit, or provenance logic.
- No test file.

### 16.4 Pre-existing modifications

`backend/app/core/config.py` and 60 other tracked files were already modified
before K.2. They are not part of this report’s change set and were not reverted.

---

## 17. Limitations, blockers, and K.3 prerequisites

### 17.1 Launch-blocking

| # | Blocker | Required action |
| --- | --- | --- |
| B1 | Tracked demo fixtures are Blinkit-labelled and excluded from consumer serving, so search returns zero results. | K.3: add a deterministic non-Blinkit demo fixture lane (e.g. a dedicated demo platform) and point the demo `DATA_DIR` at it. Do not weaken the Blinkit policy. |
| B2 | The checked-in E2E journey expectations assume servable demo fixtures. | K.3: regenerate the E2E fixture dataset on the non-Blinkit demo lane and re-run the journey. |

### 17.2 Non-blocking constraints

| # | Constraint | Action |
| --- | --- | --- |
| C1 | Local-cart `/optimize` uses the operator-only `/api/v1/cart/optimize`. | K.3: route the UI through the persisted list/optimization flow, or clearly mark the local-cart page as unsupported. |
| C2 | No email / no password recovery. | Accept; document GitHub-only sign-in. |
| C3 | No worker. | Accept; document deferred ingestion/outbox. |
| C4 | Cold start may exceed the 15 s client timeout. | Configure keep-alive; document first-request failure. |
| C5 | Vercel Hobby non-commercial restriction. | Confirm the showcase is non-commercial. |
| C6 | Dependencies unpinned. | Pin before treating builds as reproducible. |
| C7 | Staging does not enforce production validators. | Set the §13.1 values explicitly. |
| C8 | Neon pooled vs direct connection. | Verify in K.3; prefer direct. |
| C9 | Shared auth bucket behind Vercel. | Accept; do not raise the limit or trust forwarding headers. |

### 17.3 K.3 entry checklist

1. Fix B1/B2 with a non-Blinkit demo fixture lane.
2. Create Neon Free, Upstash Free, Render Free, Vercel Hobby, and a GitHub OAuth
   App (cardless).
3. Apply the §13.1 matrix in the provider dashboards.
4. Run `alembic upgrade head` against Neon and verify `alembic current`.
5. Deploy Render and confirm `/health`, `/ready`, and `/metrics`.
6. Deploy Vercel with `BACKEND_INTERNAL_URL` set.
7. Configure the keep-alive job.
8. Complete a real GitHub OAuth round-trip.
9. Re-run the consumer journey against the demo lane.
10. Confirm every fixture result is labelled and no live claim is made.

---

## 18. Rollback

All K.2 changes are reversible without data migration:

| Change | Rollback |
| --- | --- |
| `next.config.ts` guard | Remove the guard and restore the inline `${process.env.BACKEND_INTERNAL_URL ?? "http://api:8000"}` destination |
| `LoginForm.tsx` navigation | Restore `router.push(...)` |
| `config.py` validator | Restore acceptance of `postgresql` and `postgresql+psycopg` |

No database schema, data, secret, or provider resource was changed, so no
database rollback is required. If a K.3 deployment fails, deleting the Render,
Vercel, Neon, Upstash, and GitHub OAuth resources returns the system to the
pre-deployment state.

---

## 19. Final decision

**`READY_WITH_CONSTRAINTS`**

Justification:

- The Architecture A deployment is implementation-compatible: the frontend
  builds and rewrites correctly, the backend runs natively on Python 3.12, the
  migrations are PostgreSQL/Neon-compatible, Redis rate limiting is distributed
  and fail-closed, GitHub OAuth works without SMTP, and every security control
  remains intact.
- Three minimal compatibility changes were required and made: the Vercel build
  guard, the full-page OAuth navigation, and the psycopg 3 URL validator.
- The deployment is **not** launch-ready for a consumer showcase because the
  tracked demo catalogue is Blinkit-labelled and excluded by the central policy.
  This is a content/fixture gap, not an architecture or security gap, and it is
  fixable in K.3 without weakening the Blinkit block.
- Integration/E2E tests, real provider connections, and cold-start timing were
  not executed and are reported as such.

Proceed to K.3 only after adding the non-Blinkit demo fixture lane and re-running
the consumer journey.

---

## Appendix A — Verification commands (reference)

```bash
# Backend
cd backend
python3 -m pytest tests/unit -q -p no:cacheprovider
python3 -m alembic -c alembic.ini history
python3 -m alembic -c alembic.ini heads
DATABASE_URL='postgresql+psycopg://cartel:cartel@localhost/cartel' \
  python3 -m alembic -c alembic.ini upgrade head --sql

# Frontend
cd frontend
npm run typecheck
npm run build
VERCEL=1 npm run build   # expected to fail without BACKEND_INTERNAL_URL
BACKEND_INTERNAL_URL=https://cartel-api.onrender.com npm run build

# Compose syntax only
POSTGRES_PASSWORD=dummy AUTH_TOKENS=operator=dummy \
PUBLIC_ORIGIN=http://localhost:3000 \
SMTP_HOST=mail.invalid SMTP_FROM=no-reply@example.com \
docker compose -f docker-compose.yml config
```

## Appendix B — Proposed Render environment (non-secret values only)

```text
APP_ENV=staging
APP_DEBUG=false
DOCS_ENABLED=false
AUTH_REQUIRED=true
AUTH_COOKIE_SECURE=true
DATABASE_REQUIRED=true
DB_POOL_SIZE=1
DB_MAX_OVERFLOW=0
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=300
REDIS_CONNECT_TIMEOUT_SECONDS=1
REDIS_OPERATION_TIMEOUT_SECONDS=1
REDIS_MAX_CONNECTIONS=5
DEMO_FIXTURES_ENABLED=true
DATA_DIR=../data
RETAILER_DATA_PROVIDER_MODE=unavailable
CHECKOUT_CAPTURE_ADAPTER_MODE=unavailable
CHECKOUT_OBSERVATION_PROVIDER_MODE=unavailable
CORS_ALLOWED_ORIGINS=
AUTH_RATE_LIMIT_REQUESTS=8
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
VAULT_KEY_PROVIDER=unavailable
EMAIL_DELIVERY_MODE=smtp
```

Secrets (`AUTH_TOKENS`, `DATABASE_URL`, `REDIS_URL`, `GITHUB_CLIENT_SECRET`,
`GITHUB_CLIENT_ID` if treated as sensitive) must be entered only in the Render
secret manager and never committed to this repository.
