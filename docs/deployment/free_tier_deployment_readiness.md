# Cartel — Free-Tier Deployment Readiness

**Report date:** 2026-11-09
**Repository:** `Cartel-Smart-Cart-Optimizer`
**Branch / HEAD at audit time:** `feat/cartel-production-foundation` / `59560b9dcab78c82c8bd3b0c47f8d7d33508a821`
**Scope:** Read-only readiness audit and deployment plan. No deployment, account creation, provisioning, paid activation, or Git mutation was performed.

---

## 1. Executive summary and decision

### Decision

> **`READY_WITH_CONSTRAINTS`**

A publicly reachable, ₹0-mandatory-cost, cardless Cartel showcase is **deployable** using the split free-tier architecture in §8 (Architecture A), but only with the constraints in §1.1. The decision is **not** `READY_FOR_DEPLOYMENT` because the showcase necessarily runs as a labelled **demo-fixture** experience, not a live-retailer-data product, and because several free-tier limits impose functional and availability constraints that must be accepted before launch.

If the showcase is intended for **commercial** use, the decision changes to **`BLOCKED`**, because Vercel Hobby is restricted to non-commercial personal use and no verified cardless free frontend host with equivalent capability was found (§7).

### 1.1 Mandatory constraints

| # | Constraint | Consequence |
|---|---|---|
| C1 | The app cannot run with `APP_ENV=production` while demo fixtures are enabled. `config.py` raises if `DEMO_FIXTURES_ENABLED=true` in production, and the demo seeder refuses production. | Run the API with `APP_ENV=staging` plus production-equivalent security settings, and set `DEMO_FIXTURES_ENABLED=true`. |
| C2 | Only demo fixture data is available for a functional showcase. No cardless free live retailer data source exists, and live Blinkit is policy-blocked by the app. | Every result must be visibly labelled **Demo fixture · not live retailer evidence**. The UI already does this (§6.3). |
| C3 | Email/password auth is unusable on Render Free. Signup, resend, and recovery return HTTP 503 when email delivery is unconfigured; Render Free blocks outbound SMTP ports 25/465/587. | Use **GitHub OAuth only**. Do not advertise email/password signup. |
| C4 | Redis is mandatory for authenticated public use. The rate limiter fails closed with HTTP 503 if Redis is unavailable. | Provision Upstash Free Redis; never disable rate limiting. |
| C5 | PostgreSQL is mandatory. `DATABASE_URL` accepts PostgreSQL only; models and migrations use PostgreSQL `UUID`/`JSONB`. | Provision Neon Free Postgres; run Alembic migrations at deploy. |
| C6 | Render Free spins down after 15 minutes of no inbound traffic and takes ~1 minute to wake. The frontend API client times out at 15 s. | Run a cardless external keep-alive pinger against `/health` (§7, cron-job.org). |
| C7 | Render grants 750 Free instance hours per workspace per month. An always-awake service consumes up to ~744 h in a 31-day month. | Margin is ~6 h/month. Either accept the tight margin or schedule spin-down windows and accept cold starts. |
| C8 | Render Free has an ephemeral filesystem and no persistent disks. | Never rely on runtime filesystem writes for durable state. All durable user state is in Postgres; demo catalog/evidence is committed to Git (§6). |
| C9 | Vercel Hobby is free and cardless but restricted to **non-commercial, personal use**. | Acceptable for a non-commercial showcase; commercial use is blocked. |
| C10 | Requests proxied through the Vercel rewrite share one client identity (`request.client.host` = Vercel proxy). | The auth rate-limit bucket (`AUTH_RATE_LIMIT_REQUESTS=8`/min) is shared across all users. Do not raise the limit to “fix” this; it would weaken rate limiting. |
| C11 | No background worker is deployed. | Async scrape ingestion and the email outbox are deferred. Consumer search/list/optimize flows work synchronously from tracked fixtures. |
| C12 | `CredentialVault` defaults to `unavailable`. | Retailer connection features fail closed and are not usable in the demo. |
| C13 | `/metrics` is public and unauthenticated, and the Render service URL is directly reachable. | Metrics counters are publicly readable. Accepted residual risk; no code change is made in this audit. |

### 1.2 What is not claimed

- No provider account was created. Card requirements are verified against **official provider documentation**, not by exercising a signup flow.
- No live retailer evidence exists or is fabricated. Demo data is explicitly marked as fixture provenance.
- Integration and end-to-end tests were **not run** (no test database, Docker daemon unavailable). They are reported as unavailable, not passed.
- No deployment, DNS, TLS, OAuth app, database, or Redis instance was provisioned.

---

## 2. Repository baseline and scope

### 2.1 Baseline commands and results (executed)

| Command | Result |
|---|---|
| `git rev-parse --abbrev-ref HEAD` | `feat/cartel-production-foundation` |
| `git rev-parse HEAD` | `59560b9dcab78c82c8bd3b0c47f8d7d33508a821` |
| `git diff --cached --stat` | empty (0 staged files) |
| `git diff --name-only \| wc -l` | `61` modified tracked files |
| `git ls-files --others --exclude-standard \| wc -l` | `86` untracked files |
| `git status --porcelain \| wc -l` | `90` (untracked directories collapse entries) |
| `test -e docs/deployment/free_tier_deployment_readiness.md` | `ABSENT` before this report; `docs/deployment/` did not exist |

The working tree was already dirty before this audit. This report is the only file created by the audit.

### 2.2 Files inspected

- `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`
- `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/db/session.py`
- `backend/app/db/migrations/versions/0001`–`0009`
- `backend/app/core/rate_limit.py`, `backend/app/api/routes/health.py`
- `backend/app/api/v2/auth.py`, `backend/app/api/v2/lists.py`, `backend/app/api/v2/optimizations.py`, `backend/app/api/v2/products.py`
- `backend/app/auth/service.py`, `backend/app/auth/providers.py`, `backend/app/auth/email_delivery.py`
- `backend/app/services/product_search.py`, `backend/app/dev/seed_demo_cart.py`
- `backend/app/worker_entrypoint.py`, `backend/app/workers/bootstrap.py`
- `frontend/next.config.ts`, `frontend/package.json`, `frontend/lib/apiClient.ts`, `frontend/app/(app)/search/page.tsx`, `frontend/app/(app)/optimize/page.tsx`, `frontend/app/(app)/lists/page.tsx`
- `backend/.env.example`, `.env.example`, `frontend/.env.example`, `.gitignore`
- `.github/workflows/ci.yml`
- Tracked demo dataset under `data/product_intelligence/`

### 2.3 Deployment infrastructure present

| Artifact | Present? | Note |
|---|---|---|
| `docker-compose.yml` | Yes | 5 services: Postgres 16, Redis 7, API, worker, frontend |
| `backend/Dockerfile` | Yes | Python 3.12-slim; installs Playwright + Chromium |
| `frontend/Dockerfile` | Yes | Multi-stage Node 22, Next.js standalone |
| `render.yaml` | No | Render must be configured manually in the dashboard |
| `vercel.json` | No | Vercel project settings must be configured manually |
| `fly.toml`, `Procfile`, `railway.json` | No | Not applicable |
| `.github/workflows/ci.yml` | Yes | Python 3.12 compile + full pytest suite |

No infrastructure-as-code exists for the recommended architecture; the deployment sequence in §11 is a manual dashboard procedure.

---

## 3. Runtime and dependency inventory

### 3.1 Backend runtime

| Item | Value | Source |
|---|---|---|
| Language | Python | `backend/requirements/base.txt` |
| Container base | `python:3.12-slim` | `backend/Dockerfile` |
| Local audit Python | `3.14.7` | `python3 --version` |
| ASGI server | `uvicorn[standard]` | `requirements/base.txt` |
| Framework | FastAPI, Pydantic, pydantic-settings | `requirements/base.txt` |
| ORM / migrations | SQLAlchemy, Alembic, `psycopg[binary]` | `requirements/base.txt` |
| Password hashing | `argon2-cffi` | `requirements/base.txt` |
| Redis client | `redis` | `requirements/base.txt` |
| HTTP / OAuth | `httpx`, `Authlib`, `requests` | `requirements/base.txt` |
| HTML parsing | `beautifulsoup4` | `requirements/base.txt` |
| Browser automation | `playwright` (+ Chromium in Docker) | `requirements/base.txt`, `backend/Dockerfile` |
| Scheduler | `apscheduler` | `requirements/base.txt` |
| Vault crypto | `cryptography>=42` | `requirements/base.txt` |

**Dependency risk:** `backend/requirements/base.txt` has **no version pins** except `cryptography>=42`. Builds are not reproducible. This is pre-existing and is not changed by this audit. Pin versions before treating a deployment as reproducible.

**Playwright note:** `app/main.py` imports `app.scrapers.blinkit.checkout_capture`, which imports Playwright modules at import time. The Python package must be installed, but **browsers are not required** unless a Blinkit scrape path is invoked. With `RETAILER_DATA_PROVIDER_MODE=unavailable` and `CHECKOUT_CAPTURE_ADAPTER_MODE=unavailable`, no browser launch occurs. Architecture A therefore installs the package but does **not** run `playwright install`.

### 3.2 Frontend runtime

| Item | Value |
|---|---|
| Framework | Next.js `16.3.8` (App Router) |
| React | `19.2.8` |
| Build output | `output: "standalone"` |
| API proxying | `/api/:path*` → `${BACKEND_INTERNAL_URL}/api/:path*` |
| Client API base | same-origin `/api` (unless `NEXT_PUBLIC_API_BASE_URL` is set) |
| Client timeout | 15 s |
| Node in Docker | 22-alpine |
| Package manager | `npm` with `package-lock.json` |

`BACKEND_INTERNAL_URL` is consumed by `next.config.ts` `rewrites()`. Treat it as a **build-time** value: changing it requires a rebuild/redeploy.

### 3.3 Process topology in the existing Compose architecture

| Service | Command | Required for showcase? |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Replaced by Neon Free |
| `redis` | `redis:7-alpine` | Replaced by Upstash Free |
| `api` | `alembic upgrade head && uvicorn app.main:app` | Yes |
| `worker` | `python -m app.worker_entrypoint` | Deferred (not deployed) |
| `frontend` | `node server.js` | Replaced by Vercel |

---

## 4. Database and migration compatibility

### 4.1 Mandatory PostgreSQL

- `backend/app/db/session.py` creates a SQLAlchemy engine from `DATABASE_URL` (or `POSTGRES_*`) with `pool_pre_ping=True`.
- `DATABASE_URL` must use the **`postgresql+psycopg://`** scheme. Plain `postgresql://` resolves to a driver that is not installed (`psycopg2`); only `psycopg[binary]` is present.
- Migrations use `postgresql.UUID(as_uuid=True)` (`0002`, `0008`, `0009`) and `postgresql.JSONB` (`0008`). SQLite is not a substitute.

### 4.2 Migration chain (executed)

Command:

```bash
cd backend && python3 -m alembic -c alembic.ini history
```

Result: exit 0, chain from `<base>` to head:

```
<base> -> 0001_consumer_identity
0001_consumer_identity -> 0002_shopping_lists
0002_shopping_lists -> 0003_optimization_records
0003_optimization_records -> 0004_oauth_challenges
0004_oauth_challenges -> 0005_idempotency_records
0005_idempotency_records -> 0006_background_jobs
0006_background_jobs -> 0007_email_outbox
0007_email_outbox -> 0008_retailer_connections
0008_retailer_connections -> 0009_credential_vault (head)
```

Migrations live in `backend/app/db/migrations/versions/`. `alembic.ini` uses `script_location = %(here)s/app/db/migrations`.

### 4.3 Neon Free compatibility

| Requirement | Neon Free | Verdict |
|---|---|---|
| PostgreSQL protocol | Yes (Postgres-compatible) | Compatible |
| `UUID`, `JSONB` | Yes | Compatible |
| TLS | Required; use `?sslmode=require` | Compatible |
| Connection pooling | PgBouncer transaction mode available | Compatible |
| `pool_pre_ping` | Handles suspend/reconnect | Compatible |
| Scale-to-zero | After 5 min inactivity; Free plan fixed | Compatible, but see CU-hour risk |
| Card required | **No** — “The Free plan is permanent (not a trial); no credit card required.” | Eligible |
| Cost | ₹0 within 100 CU-hours/project/month, 1 GB storage/project (20 GB/account), 5 GB egress/project | Eligible |

**CU-hour risk:** Free compute is ~0.25 CU. 100 CU-hours ≈ 400 compute-hours/month (~16.7 days) if compute never suspends. Scale-to-zero after 5 minutes of inactivity is the mitigation. `/health` does not touch the database, and the API only queries Postgres on authenticated user actions. Residual uncertainty: whether an idle pooled connection delays scale-to-zero. Monitor Neon CU-hours after launch. If quota is exhausted, compute suspends until the next month; data is not deleted and no charge is incurred.

**Recommended DB settings for Architecture A:** `DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=0`, `DB_POOL_RECYCLE_SECONDS=300`, `DB_POOL_TIMEOUT_SECONDS=30`. This bounds connections and lets Neon drop/recreate them safely under `pool_pre_ping`.

### 4.4 Migration execution at deploy

Render’s start command must run migrations before Uvicorn:

```bash
cd backend && alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
```

If migrations fail, the service must not start serving. Do not “fix” a failed migration by disabling it.

---

## 5. Redis and worker analysis

### 5.1 Redis is mandatory

- `app/main.py` constructs `RedisRateLimiter` and applies it to `/api/v2/auth/*` and protected API paths.
- On Redis error, `RedisRateLimiter.allow()` raises `RateLimitBackendUnavailable`; the middleware returns **HTTP 503 `rate_limit_unavailable`** (fail closed). It does not bypass limiting.
- In `APP_ENV=production`, lifespan pings Redis at startup and aborts if unavailable. In `APP_ENV=staging`, startup does not ping, but the limiter still fails closed at request time.

**Conclusion:** Redis is a mandatory component for any authenticated public deployment. Removing it or disabling the limiter would weaken security and is not permitted.

### 5.2 Upstash Free compatibility

| Requirement | Upstash Free | Verdict |
|---|---|---|
| Redis protocol | Yes | Compatible |
| TLS | `rediss://` supported | Compatible |
| Lua `EVAL` | Supported | Compatible |
| Persistence | Yes (free tier data is persistent) | Compatible |
| Limits | 250 MB data, 500K commands/month, 10 GB bandwidth, 1 database | Sufficient for a demo |
| Card required | **No** for Free; entering a card upgrades to pay-as-you-go | Eligible |
| Cost | ₹0 within limits | Eligible |

**Command budget:** one Lua `EVAL` per rate-limited request. `/health` is exempt. 500K commands/month ≈ 16K/day, far above demo traffic.

**Important:** Do not enter a card in Upstash. Doing so upgrades the database to pay-as-you-go, which violates the ₹0 mandatory-cost rule.

### 5.3 Worker

`backend/app/worker_entrypoint.py` runs two loops:

1. `BackgroundWorker` for `scrape_ingestion` jobs.
2. `EmailOutboxWorker` for transactional email.

Consumer showcase flows (OAuth login, product search, shopping lists, optimization planning) execute synchronously and do **not** require the worker. The only producer of background scrape jobs is the operator scrape route (`/api/v1/scrape`), which is not part of the consumer showcase. Email delivery for auth is synchronous and is disabled because SMTP is unavailable.

**Decision:** Do **not** deploy a worker. Async scrape ingestion and the email outbox are explicitly deferred. This is a functional limitation, not a security weakening.

### 5.4 Email

- `email_delivery_configured` is false when SMTP is unconfigured.
- Signup (`POST /api/v2/auth/signup`), resend (`POST /api/v2/auth/verification/resend`), and password recovery return **HTTP 503 `email_delivery_unavailable`** when unconfigured.
- `EMAIL_DELIVERY_MODE=file` writes to local disk and is a development-only path; it is not a public delivery mechanism and does not survive Render’s ephemeral filesystem.
- Render Free blocks outbound ports 25, 465, and 587. Brevo Free and Resend Free are therefore not usable from Render Free via SMTP. Resend additionally requires a verified sending domain.

**Decision:** Do not deploy an email provider. Use GitHub OAuth only. This is honest and avoids a mandatory card/domain requirement.

---

## 6. Filesystem persistence inventory

### 6.1 Runtime filesystem writes

| Path (from `DATA_DIR`) | Written by | Required for demo? | Durable on Render Free? |
|---|---|---|---|
| `product_intelligence/catalog/` | Catalog store; demo seed | Read-only at runtime for demo | No (ephemeral), but **tracked in Git** |
| `product_intelligence/observations/` | Observation registry; demo seed | Read-only at runtime for demo | No, but **tracked in Git** |
| `product_intelligence/evidence/` | Evidence store | Not written in demo flow | No |
| `product_intelligence/demo_evidence/` | Fixture data | Read-only | No, but **tracked in Git** |
| `raw/` | Scraper artifact store | No (scraping disabled) | No |
| `cleaned/` | Scraper parser | No | No |
| `sessions/blinkit/` | Browser session state | No (browser disabled) | No |
| `cost_intelligence/checkout_captures/` | Checkout capture | No (adapter unavailable) | No |
| `data_ingestion/lifecycle/` | Lifecycle store | No (worker not deployed) | No |
| `/tmp/cartel-email/` | File email delivery | No (email deferred) | No |

### 6.2 Demo dataset is committed to Git

Command:

```bash
git ls-files data/product_intelligence | wc -l   # → 10
```

Tracked files:

- `data/product_intelligence/catalog/catalog.json`
- `data/product_intelligence/catalog/listing_associations.json`
- `data/product_intelligence/demo_evidence/blinkit/<digest>/bundle.json`
- `data/product_intelligence/demo_evidence/blinkit/<digest>/record.json`
- `data/product_intelligence/evidence/blinkit/<digest>/bundle.json`
- `data/product_intelligence/evidence/blinkit/<digest>/record.json`
- 4 files under `data/product_intelligence/observations/`

`data/product_intelligence/` is **not** ignored by `.gitignore` (unlike `data/raw`, `data/cleaned`, `data/normalized`, `data/exports`, `data/sessions`). Total `data/` size is ~2.3 MB, so cloning it into Render is cheap.

### 6.3 Provenance and demo labelling (verified)

- `catalog.json` records use `catalog_revision: "demo-v1"` and names `Demo Item A` / `Demo Item B`.
- Observations use `parser_version: "demo-v1"`, `normalization_version: "demo-v1"`, `completeness.basis: "development-seed"`, `raw_artifact_reference.storage_reference: "development-seed"`.
- `app/services/product_search.py` defines `is_explicit_fixture()` and only includes fixtures when `include_fixtures=settings.demo_fixtures_enabled`.
- `ProductSearchService` is constructed with `include_fixtures=app_settings.demo_fixtures_enabled`.
- `app/api/v2/lists.py` only permits demo selection when `demo_fixtures_enabled` is true.
- `app/api/v2/optimizations.py` marks demo items as `evidence_class: "demo_fixture"` and returns a warning that fixture prices/availability cannot produce a payable recommendation.
- Frontend renders visible banners:
  - `frontend/app/(app)/search/page.tsx`: “Results marked **Demo fixture** are det…” (fixture legend).
  - `frontend/app/(app)/optimize/page.tsx`: “Demo fixture evidence. This comparison uses deterministic fixture data only; it cannot produce a payable recommendation, savings claim, or checkout total.”
  - `frontend/app/(app)/lists/page.tsx`: “Demo fixture selection · not live retailer evidence” and a “Demo fixture” badge.

**Demo Item C** is intentionally unresolved: it has canonical identity but no approved listing association or observation. It is useful for demonstrating unresolved-item handling, but it is not a complete third comparison item.

### 6.4 Persistence conclusion

The demo requires **no durable runtime filesystem writes**. All durable user state (users, sessions, OAuth challenges, shopping lists, optimization records, idempotency records, jobs, outbox, retailer connections, vault metadata) lives in PostgreSQL. Demo catalog/observations/evidence are read from the Git checkout. Render’s ephemeral disk is therefore acceptable.

---

## 7. Provider eligibility matrix

**Verification basis:** official provider documentation fetched during this audit. No account was created and no signup form was submitted. “Cardless” means the provider’s official documentation states or demonstrates that the free tier does not require a payment card.

| Provider / plan | Role | Free? | Card required? | Recurring cost? | Persistence / limits | Verdict |
|---|---|---|---|---|---|---|
| **Vercel Hobby** | Frontend (Next.js) | Yes | **No** for Hobby; card only for Pro | ₹0 | 100 GB fast data transfer, 1M function invocations, 4 CPU-hours, 360 GB-hours; 200 projects; **non-commercial personal use only** | **Eligible (non-commercial)** |
| **Render Free Web Service** | Backend API (native Python) | Yes | **No** documented; FAQ confirms services run with no payment method and overages suspend rather than bill | ₹0 | 750 instance hours/month, 0.1 CPU / 512 MB, 15-min idle spin-down (~1 min wake), ephemeral disk, SMTP ports 25/465/587 blocked, may restart anytime | **Eligible with constraints** |
| **Render Free Postgres** | Database | Yes | No | ₹0 | **Expires 30 days after creation**; 1 GB | **Ineligible (expiry)** |
| **Render Free Key Value** | Redis | Yes | No | ₹0 | **In-memory only; data lost on restart** | **Ineligible (no persistence)** |
| **Neon Free** | PostgreSQL | Yes | **No** — “permanent (not a trial); no credit card required” | ₹0 | 100 CU-hours/project/month, 1 GB storage/project (20 GB/account), 5 GB egress/project, 100 projects, scale-to-zero after 5 min, no inactivity pause, data retained on quota exhaustion | **Eligible** |
| **Upstash Free Redis** | Redis | Yes | **No** — free tier; entering a card upgrades to pay-as-you-go | ₹0 | 250 MB, 500K commands/month, 10 GB bandwidth, 1 DB, TLS, persistence | **Eligible** |
| **cron-job.org** | Keep-alive pinger | Yes | **No** documented — “entirely free of charge” | ₹0 | Up to 60 executions/hour (every minute); no documented job-count limit; fair-use policy | **Eligible** |
| **GitHub OAuth** | Identity provider | Yes | No | ₹0 | Requires a GitHub account and a primary **verified** email | **Eligible** |
| **Brevo Free** | Email | Yes | No (“free forever, no credit card required”) | ₹0 | 300 emails/day, transactional included | **Ineligible on Render Free** (SMTP ports blocked) |
| **Resend Free** | Email | Yes | No | ₹0 | 3,000/month, 100/day; requires verified domain | **Ineligible** (SMTP blocked + domain requirement) |
| **Cloudflare R2 Free** | Object storage | Free usage allowance | **Yes** — adding R2 requires completing an R2 subscription checkout | ₹0 within allowance | 10 GB storage, 1M Class A, 10M Class B, free egress | **Not selected** (checkout/subscription flow; object storage not needed) |
| **Supabase Free** | PostgreSQL / storage | Yes | Not explicitly cardless | ₹0 | 500 MB DB, 1 GB storage, 5 GB egress, 2 active projects, **pauses after 1 week inactivity** | **Not selected** (card not explicit; inactivity pause) |
| **Hugging Face Spaces** | Backend host | Static only | No | ₹0 | Docker/Gradio Spaces require a paid plan | **Ineligible** |
| **Koyeb** | Backend host | No free plan | — | Pro from $29/mo | — | **Ineligible** |
| **Oracle Cloud Always Free** | Single host / Docker | Yes | **Yes** (identity verification) | ₹0 | Always Free VM | **Ineligible** (card verification required) |
| **Fly.io / Railway** | Backend host | Trial/limited | Card typically required | Paid after trial | — | **Ineligible** |

### 7.1 Verified card statements (quoted from official docs)

- **Neon:** “The Free plan is permanent (not a trial); no credit card required.”
- **Upstash:** “Once you enter your credit card, your database will be upgraded to the pay-as-you-go plan…” and a free Redis database is available “with no signup, credit card, or API key” (claimable within 3 days).
- **Render:** “If you haven't added a payment method: Exceeding your included outbound bandwidth suspends your services for the remainder of the month.” This confirms free services can run without a payment method.
- **Vercel:** “The Hobby plan is **free** and aimed at developers with personal projects…” and “the Hobby plan restricts users to non-commercial, personal use only.”
- **cron-job.org:** “Our service is entirely free of charge.” Minimum interval “every minute.”
- **Cloudflare R2:** “You need a Cloudflare account with an R2 subscription… Complete the checkout flow to add an R2 subscription.”

### 7.2 Providers explicitly rejected

| Provider | Reason |
|---|---|
| Render Free Postgres | 30-day expiry violates persistence requirements |
| Render Free Key Value | In-memory; data lost on restart; violates persistence |
| Cloudflare R2 | Requires an R2 subscription checkout; object storage not needed |
| Supabase Free | Card requirement not explicit; project pause after inactivity |
| Brevo / Resend | SMTP blocked on Render Free; Resend also needs a verified domain |
| Hugging Face Spaces | Only Static Spaces are free; FastAPI not supported |
| Koyeb | No free plan |
| Oracle Cloud Always Free | Card verification required |
| Any paid API / DB / host / email / credits / subscription | Violates ₹0 mandatory-cost rule |

---

## 8. Two deployment architectures

### 8.1 Architecture A — Minimum viable showcase (recommended)

```
Browser (HTTPS)
   │
   ▼
Vercel Hobby  ──  Next.js 16 frontend (SSR + /api rewrite)
   │  same-origin /api/* → BACKEND_INTERNAL_URL
   ▼
Render Free Web Service  ──  FastAPI (native Python 3.12)
   │                                   │
   │                                   ├── Neon Free PostgreSQL (durable state)
   │                                   └── Upstash Free Redis (rate limiting)
   │
cron-job.org ── GET /health every 5 min ──┘
   │
GitHub OAuth ── identity (no email provider)
```

**Why this shape**

- Vercel terminates TLS and serves the frontend at a public HTTPS origin.
- The browser calls same-origin `/api/*`; Vercel rewrites to Render, so cookies are first-party, CORS is unnecessary, and CSRF origin checks pass against `PUBLIC_ORIGIN`.
- Render runs the API natively (no Docker build), avoiding the heavy Playwright/Chromium image.
- Neon and Upstash provide durable state and rate limiting without Render’s expiring/in-memory free add-ons.
- cron-job.org prevents Render’s 15-minute idle spin-down, keeping latency under the frontend’s 15 s timeout.
- GitHub OAuth removes the need for email delivery.
- Demo fixtures come from the Git checkout, so no object storage and no runtime writes are needed.

**Deployment steps (planned, not executed):**

1. Create a Neon Free project; copy the pooled or direct connection string; convert it to `postgresql+psycopg://…?sslmode=require`.
2. Create an Upstash Free Redis database in a region near Render; copy the `rediss://` URL.
3. Create a GitHub OAuth App:
   - Homepage URL: `https://<vercel-project>.vercel.app`
   - Authorization callback URL: `https://<vercel-project>.vercel.app/api/v2/auth/github/callback`
   - No card required.
4. Create a Render Free Web Service from the repository:
   - Runtime: Python 3.12 (set `PYTHON_VERSION=3.12.x` if required).
   - Build command: `pip install -r backend/requirements/base.txt`
   - Start command: `cd backend && alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port "$PORT"`
   - Health check path: `/health`
   - Instance type: Free
   - Do **not** add a disk.
5. Set Render environment variables from §9.
6. Deploy Render; confirm `/health` and `/ready` return 200.
7. Create a Vercel Hobby project from the same repository:
   - Root directory: `frontend`
   - Framework preset: Next.js
   - Build command: `npm run build`
   - Set `BACKEND_INTERNAL_URL=https://<render-service>.onrender.com`
   - Leave `NEXT_PUBLIC_API_BASE_URL` unset.
8. Deploy Vercel; open `https://<vercel-project>.vercel.app`.
9. Create a cron-job.org job: `GET https://<render-service>.onrender.com/health` every 5 minutes.
10. Complete an OAuth login with a GitHub account that has a verified primary email.
11. Verify demo labelling on search, lists, and optimize pages.

**Cost:** ₹0 within free-tier limits. No card entered at any step. No paid add-on.

**Constraints:** C1–C13 in §1.1.

### 8.2 Architecture B — Existing Compose topology on a single host

```
Internet ── TLS reverse proxy (Caddy/Traefik) ── docker compose
                                                    ├── frontend (Next.js standalone)
                                                    ├── api (FastAPI)
                                                    ├── worker (background jobs + email outbox)
                                                    ├── postgres:16 (volume)
                                                    └── redis:7 (volume)
```

**What it preserves**

- Full worker and email-outbox capability.
- Durable local volumes for Postgres, Redis, and `cartel-data`.
- The exact Compose topology in `docker-compose.yml`.
- No split-origin rewrite; the frontend can proxy to `api:8000` on the private network.

**Why it is blocked under the stated constraints**

- It requires an always-on Linux host with a persistent disk, public IP, and TLS.
- No verified cardless free host with those properties was found:
  - Oracle Cloud Always Free requires card verification.
  - Fly.io/Railway require a card or paid plan.
  - Render Free is ephemeral and cannot run persistent disks or the worker reliably.
  - Hugging Face Spaces and Koyeb are ineligible.
- Therefore Architecture B has **no eligible ₹0 cardless provider** and is **`BLOCKED`** under the mandatory rules.

**If a cardless host becomes available,** Architecture B remains the more faithful deployment: it preserves the worker, outbox, and local artifact volumes. It also avoids the Vercel non-commercial restriction and the shared-IP rate-limit issue.

### 8.3 Architecture comparison

| Dimension | Architecture A | Architecture B |
|---|---|---|
| Mandatory cost | ₹0 | ₹0 only if a cardless host exists (none found) |
| Card required | No | Card required for all found hosts |
| Frontend | Vercel Hobby (non-commercial) | Self-hosted Next.js |
| Backend | Render Free native Python | Docker Compose |
| Database | Neon Free | Postgres 16 volume |
| Redis | Upstash Free | Redis 7 volume |
| Worker | Not deployed | Deployed |
| Email | Deferred | SMTP-capable |
| Object storage | Not needed | Local volume |
| Cold start | ~1 min if keep-alive fails | None |
| Persistence | Postgres + Git fixtures | Volumes |
| Security posture | Production-equivalent settings in `staging` | `production` |
| Demo fixtures | Required (`APP_ENV=staging`) | Not permitted in production |
| Verdict | **READY_WITH_CONSTRAINTS** | **BLOCKED** |

---

## 9. Environment and secret inventory

### 9.1 Render backend (Architecture A)

| Variable | Value | Secret? | Notes |
|---|---|---|---|
| `APP_NAME` | `Cartel` | No | |
| `APP_ENV` | `staging` | No | Required for demo fixtures; production forbids them |
| `APP_DEBUG` | `false` | No | Production-equivalent |
| `APP_VERSION` | `0.1.0` | No | |
| `API_V1_PREFIX` | `/api/v1` | No | |
| `LOG_LEVEL` | `INFO` | No | |
| `LOG_JSON` | `true` | No | |
| `DOCS_ENABLED` | `false` | No | Hides OpenAPI |
| `CORS_ALLOWED_ORIGINS` | empty | No | Same-origin via Vercel rewrite |
| `AUTH_REQUIRED` | `true` | No | |
| `AUTH_TOKENS` | `operator=<high-entropy-random>` | **Yes** | Required by validator when `AUTH_REQUIRED=true`; not used by the frontend |
| `AUTH_COOKIE_SECURE` | `true` | No | HTTPS-only cookie |
| `AUTH_SESSION_DAYS` | `14` | No | |
| `AUTH_IDLE_DAYS` | `7` | No | |
| `AUTH_CHALLENGE_MINUTES` | `30` | No | |
| `AUTH_RATE_LIMIT_REQUESTS` | `8` | No | Do not raise; shared proxy IP bucket |
| `DATABASE_REQUIRED` | `true` | No | |
| `DATABASE_URL` | `postgresql+psycopg://…neon.tech/…?sslmode=require` | **Yes** | Must use `+psycopg` |
| `DB_POOL_SIZE` | `1` | No | Bounds Neon connections |
| `DB_MAX_OVERFLOW` | `0` | No | |
| `DB_POOL_RECYCLE_SECONDS` | `300` | No | |
| `DB_POOL_TIMEOUT_SECONDS` | `30` | No | |
| `REDIS_URL` | `rediss://…upstash.io:6379` | **Yes** | TLS |
| `REDIS_MAX_CONNECTIONS` | `5` | No | |
| `REDIS_CONNECT_TIMEOUT_SECONDS` | `1` | No | |
| `REDIS_OPERATION_TIMEOUT_SECONDS` | `1` | No | |
| `PUBLIC_ORIGIN` | `https://<vercel-project>.vercel.app` | No | Must be the browser-visible origin |
| `GITHUB_CLIENT_ID` | GitHub OAuth App client ID | **Yes** (semi) | |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App secret | **Yes** | |
| `GITHUB_REDIRECT_URI` | `https://<vercel-project>.vercel.app/api/v2/auth/github/callback` | No | Must be the frontend origin, not Render |
| `DEMO_FIXTURES_ENABLED` | `true` | No | Required for showcase |
| `DATA_DIR` | `../data` | No | Resolves to repo `data/` |
| `RETAILER_DATA_PROVIDER_MODE` | `unavailable` | No | No live scraping |
| `CHECKOUT_OBSERVATION_PROVIDER_MODE` | `unavailable` | No | |
| `CHECKOUT_CAPTURE_ADAPTER_MODE` | `unavailable` | No | |
| `VAULT_KEY_PROVIDER` | `unavailable` | No | Retailer connections fail closed |
| `EMAIL_DELIVERY_MODE` | `smtp` | No | With empty SMTP, signup/resend/recovery return 503 |
| `SMTP_HOST` | empty | No | Email intentionally deferred |
| `SMTP_PORT` | `587` | No | |
| `SMTP_USERNAME` | empty | No | |
| `SMTP_PASSWORD` | empty | **Yes** (if set) | Leave empty |
| `SMTP_FROM` | empty | No | |
| `SMTP_STARTTLS` | `true` | No | |
| `RATE_LIMIT_REQUESTS` | `120` | No | |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | No | |
| `SCRAPER_TIMEOUT_SECONDS` | `15` | No | Unused when scraping disabled |
| `SCRAPER_MAX_RETRIES` | `3` | No | |
| `SCRAPER_RETRY_BACKOFF_SECONDS` | `1` | No | |
| `PLANNING_MAX_CART_ITEMS` | `20` | No | |
| `PLANNING_MAX_CANDIDATES_PER_ITEM` | `20` | No | |
| `PLANNING_MAX_COMBINATIONS` | `10000` | No | |
| `PLANNING_MAX_SUPPLIED_PLANS` | `100` | No | |
| `OPTIMIZATION_POLICY_VERSION` | `policy-v1` | No | |
| `BLINKIT_DELIVERY_LOCATION_NAME` | `Gurugram` | No | Not used without scraping |
| `BLINKIT_DELIVERY_LATITUDE` | `28.413333` | No | |
| `BLINKIT_DELIVERY_LONGITUDE` | `77.072833` | No | |
| `PYTHON_VERSION` | `3.12.x` (or Render default 3.12) | No | Avoids 3.14-only behavior |

Do **not** set `GOOGLE_*` or `APPLE_*` unless those providers are configured. Do **not** set `NEXT_PUBLIC_API_BASE_URL` on Vercel.

### 9.2 Vercel frontend

| Variable | Value | Secret? | Notes |
|---|---|---|---|
| `BACKEND_INTERNAL_URL` | `https://<render-service>.onrender.com` | No | Build-time rewrite target |
| `NEXT_TELEMETRY_DISABLED` | `1` | No | Optional |

`NEXT_PUBLIC_API_BASE_URL` must remain unset so the browser uses same-origin `/api`.

### 9.3 Secret handling rules

- Never commit `.env` files; `.gitignore` ignores `.env` and `.env.*` except `.env.example`.
- Enter secrets only in Render/Vercel dashboards. Do not put them in build commands, logs, or Git.
- Rotate `AUTH_TOKENS` and OAuth secrets through the provider dashboard.
- The operator `AUTH_TOKENS` value is not needed by the frontend; keep it random and unused.

---

## 10. Security and operational risks

| # | Risk | Severity | Mitigation / status |
|---|---|---|---|
| S1 | Vercel rewrite collapses client IP; auth rate-limit bucket shared across users | Medium (availability) | Accept; keep `AUTH_RATE_LIMIT_REQUESTS=8`. Do not raise it. Document that concurrent logins may be limited. |
| S2 | `/metrics` is public and unauthenticated; Render URL is directly reachable | Low–Medium (info disclosure) | Accepted residual risk. No code change. If required later, add an authenticated metrics route or an edge rule. |
| S3 | `/health` is unauthenticated (needed for keep-alive) | Low | Returns only name/env/version; no secrets. Accept. |
| S4 | Render Free is not intended for production and may restart anytime | Medium (availability) | Demo only. Keep-alive reduces spin-down. Postgres/Redis are external, so restarts do not lose state. |
| S5 | Render 750 instance hours/month is tight for always-on | Medium (availability) | Monitor hours; optionally schedule spin-down windows and accept cold starts. |
| S6 | Neon 100 CU-hours/month may be exhausted if compute stays awake | Medium (availability) | `DB_POOL_SIZE=1`, `pool_pre_ping`, `pool_recycle=300`; monitor CU-hours; no card so no bill. |
| S7 | Demo fixtures could be mistaken for live evidence | High (integrity) | Enforced `demo_fixture` evidence class, `demo_fixtures_enabled` gating, visible UI banners, and optimization warnings. Never enable fixtures in `production`. |
| S8 | Email/password UI may be shown but returns 503 | Medium (UX) | Hide or disable email/password signup in the demo; document GitHub OAuth as the only path. |
| S9 | GitHub users without a verified primary email cannot log in | Low | Document requirement; ask demo users to verify their GitHub email. |
| S10 | Vercel Hobby non-commercial restriction | High (policy) | Non-commercial showcase only. Commercial use is `BLOCKED`. |
| S11 | Unpinned Python dependencies | Medium (reproducibility/supply chain) | Pre-existing. Pin versions before a reproducible release. |
| S12 | `APP_ENV=staging` does not auto-enforce production validations | Medium (misconfiguration) | Manually set `AUTH_REQUIRED=true`, `APP_DEBUG=false`, `DOCS_ENABLED=false`, `AUTH_COOKIE_SECURE=true`, HTTPS `PUBLIC_ORIGIN`. Verify `/ready`. |
| S13 | CredentialVault unavailable | Low for demo | Retailer connection features fail closed. Do not claim they work. |
| S14 | Public operator bearer token if leaked | High | Generate high entropy; do not reuse; rotate. It is not exposed to the browser. |
| S15 | No automated backup/restore of Neon data | Medium (data loss) | Neon Free retains data; export manually if needed. No backup guarantee claimed. |
| S16 | Cold start exceeds 15 s if keep-alive fails | Medium (UX) | cron-job.org every 5 min; monitor job failures. |
| S17 | SMTP ports blocked; no email delivery | Medium (functional) | OAuth-only; signup/resend/recovery intentionally 503. |
| S18 | No worker; async scrape jobs never run | Low for demo | Deferred. Do not expose operator scrape flows publicly. |

**Security invariants preserved (not weakened):**

- `AUTH_REQUIRED=true`, `APP_DEBUG=false`, `DOCS_ENABLED=false`.
- `AUTH_COOKIE_SECURE=true`; cookies remain `HttpOnly` and `SameSite=Lax`.
- CSRF validation and same-origin enforcement remain active (`PUBLIC_ORIGIN` = Vercel origin).
- Rate limiting remains Redis-backed and fail-closed.
- Owner scoping, idempotency, migrations, and CredentialVault fail-closed behavior are unchanged.
- Evidence provenance remains explicit; no fixture is promoted to live evidence.

---

## 11. Deployment sequence (planned, not executed)

> These steps were **not** run during this audit. They are the recommended order for a future operator.

### Phase 1 — Data services

1. Create a Neon Free project (no card).
2. Copy the connection string; ensure scheme is `postgresql+psycopg://` and `sslmode=require`.
3. Create an Upstash Free Redis database (no card); copy the `rediss://` URL.
4. Do **not** enter a card in either provider.

### Phase 2 — Identity

5. Create a GitHub OAuth App (no card).
6. Set callback URL to `https://<vercel-project>.vercel.app/api/v2/auth/github/callback`.
7. Record client ID and secret.

### Phase 3 — Backend

8. Create a Render Free Web Service from the repo.
9. Build: `pip install -r backend/requirements/base.txt`
10. Start: `cd backend && alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port "$PORT"`
11. Health check: `/health`.
12. Set env vars from §9.1.
13. Deploy and wait for build.
14. Verify:
    - `curl -fsS https://<render>/health` → 200
    - `curl -fsS https://<render>/ready` → 200 with `database: ready`, `data_directory: ready`, `authentication: ready`
    - `curl -fsS https://<render>/api/v2/auth/providers` → `{"providers":{"google":false,"github":true,"apple":false}}`

### Phase 4 — Frontend

15. Create a Vercel Hobby project with root directory `frontend`.
16. Set `BACKEND_INTERNAL_URL=https://<render>`.
17. Leave `NEXT_PUBLIC_API_BASE_URL` unset.
18. Deploy and verify the public URL loads.

### Phase 5 — Keep-alive

19. Create a cron-job.org job: `GET https://<render>/health` every 5 minutes.
20. Enable failure notifications.
21. Confirm Render does not spin down for 20+ minutes.

### Phase 6 — Smoke test

22. Open `https://<vercel-project>.vercel.app`.
23. Sign in with GitHub (verified primary email).
24. Search for `Demo Item A` and confirm the **Demo fixture** label.
25. Add a demo item to a list.
26. Run an optimization and confirm the “cannot produce a payable recommendation” warning.
27. Confirm email/password signup is not presented as usable.
28. Confirm `https://<vercel>/api/v2/auth/session` returns the expected session state.

### Rollback

- Vercel: promote the previous deployment.
- Render: redeploy the previous commit; migrations are forward-only — do not downgrade a production database casually.
- Neon: use point-in-time restore if available on the plan; otherwise restore from a logical export.
- Upstash: no durable app state beyond rate-limit counters; a reset is harmless.

---

## 12. Cost analysis

### 12.1 Mandatory recurring cost

| Component | Plan | Monthly cost | Card |
|---|---|---|---|
| Frontend | Vercel Hobby | ₹0 | No |
| Backend | Render Free Web Service | ₹0 (750 h) | No |
| Database | Neon Free | ₹0 (100 CU-h) | No |
| Redis | Upstash Free | ₹0 (500K commands) | No |
| Keep-alive | cron-job.org | ₹0 | No |
| Identity | GitHub OAuth | ₹0 | No |
| Email | None | ₹0 | No |
| Object storage | None (Git fixtures) | ₹0 | No |
| **Total** | | **₹0 mandatory** | **No card** |

### 12.2 What happens at limit exhaustion (no card)

| Provider | Behavior |
|---|---|
| Render | Free instance hours exhausted → Free web services suspended until next month; no bill without a payment method |
| Render | Bandwidth/pipeline exhausted → services suspended or builds paused; no bill without a payment method |
| Vercel | Hobby usage exceeded → feature unavailable until the 30-day window resets |
| Neon | CU-hours exhausted → compute suspends until next month; data retained; no bill |
| Upstash | Command/data limits → requests may fail; entering a card would upgrade to paid, so do not |
| cron-job.org | Fair-use limits → job may be disabled; no bill |

### 12.3 Cost uncertainties

- **Render 750 h margin:** always-on consumes up to ~744 h in a 31-day month; ~6 h margin. Any extra service or long build could consume hours. Only one Free web service is planned.
- **Neon CU-hours:** 100 CU-h at 0.25 CU ≈ 400 active hours/month. Demo traffic should stay far below this, but idle-connection behavior is not fully verified. Monitor.
- **Upstash commands:** 500K/month is ample for a demo; a traffic spike or bot scan could consume it.
- **Vercel:** Hobby is free but non-commercial. No cost, but a policy limit.
- **No paid fallback is authorized.** If limits are exceeded, the showcase degrades rather than incurs cost.

---

## 13. Unresolved questions and blockers

### 13.1 Blockers (must be resolved before launch)

| # | Blocker | Status |
|---|---|---|
| B1 | **Commercial-use eligibility.** Vercel Hobby is non-commercial only. If the showcase is commercial, Architecture A is `BLOCKED`. | Unresolved; requires a product decision. |
| B2 | **No cardless free host for Architecture B.** The full Compose topology cannot run on a verified cardless free host. | Blocked; Architecture B not recommended. |
| B3 | **No cardless free email provider usable from Render Free.** SMTP ports are blocked. | Accepted; email deferred, OAuth-only. |
| B4 | **No cardless free object storage.** R2 requires an R2 subscription checkout. | Avoided; fixtures are in Git. |

### 13.2 Unresolved questions

| # | Question | Impact |
|---|---|---|
| Q1 | Does Render’s actual signup flow request a card for this account/region? Docs say no payment method is required to run Free services, but the signup UI was not exercised. | Confirm at signup before committing. If a card is demanded, stop. |
| Q2 | Does an idle pooled Postgres connection prevent Neon scale-to-zero? | Monitor CU-hours; if exhausted, reduce pool lifetime or close connections. |
| Q3 | Will the demo’s shared auth rate-limit bucket frustrate concurrent users? | Monitor 429/503 responses; keep the limit, do not weaken it. |
| Q4 | Should email/password UI be hidden entirely, or left visible with a 503? | UX decision; hiding is clearer and avoids confusion. |
| Q5 | Is a custom domain required? | Not required for Vercel/Render default domains; custom domains are free on Vercel but add DNS work. |
| Q6 | Should `/metrics` be blocked at the edge? | Security hardening; no code change in this audit. |
| Q7 | Are dependency versions to be pinned before launch? | Recommended for reproducibility. |

### 13.3 Explicitly unavailable validation

| Check | Status | Reason |
|---|---|---|
| Unit tests | **Executed: 993 passed, 2 warnings in 1.35s** | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit -q -p no:cacheprovider` |
| Frontend typecheck | **Executed: exit 0** | `npx tsc --noEmit --incremental false` |
| Alembic history | **Executed: exit 0, head `0009_credential_vault`** | `python3 -m alembic -c alembic.ini history` |
| `docker compose config` | **Executed: exit 0** (with dummy required env) | Compose v5.5.1; host `arm64` |
| Integration tests | **Skipped / unavailable** | `CARTEL_TEST_DATABASE_URL` unset; no local PostgreSQL |
| End-to-end browser tests | **Skipped / unavailable** | Docker daemon unavailable; no browser harness |
| Docker runtime validation | **Failed / unavailable** | `docker ps` → “Cannot connect to the Docker daemon” |
| Live retailer data | **Unavailable** | No cardless free live source; Blinkit policy-blocked |
| Deployment smoke test | **Not executed** | No accounts/provisioning permitted |

---

## 14. Final status

### Final decision: `READY_WITH_CONSTRAINTS`

**Recommended architecture:** Architecture A

| Layer | Provider / plan |
|---|---|
| Frontend | Vercel Hobby |
| Backend API | Render Free Web Service (native Python 3.12) |
| Database | Neon Free PostgreSQL |
| Redis | Upstash Free Redis |
| Identity | GitHub OAuth (verified primary email) |
| Keep-alive | cron-job.org → `GET /health` every 5 min |
| Demo data | Tracked Git fixtures under `data/product_intelligence/` |
| Email | Not deployed |
| Worker | Not deployed |
| Object storage | Not used |

**Components replaced, removed, or deferred**

- **Replaced:** Render Free Postgres → Neon Free; Render Free Key Value → Upstash Free; Docker frontend → Vercel; Docker API → Render native Python.
- **Removed:** Playwright/Chromium build step from the deploy path; persistent disk; SMTP; object storage.
- **Deferred:** background worker, email outbox, async scrape ingestion, live retailer connections, CredentialVault-backed features.

**Conditions for this decision to remain valid**

1. The showcase is non-commercial.
2. No card is entered in any provider.
3. `APP_ENV=staging` with production-equivalent security settings.
4. Demo fixtures remain visibly labelled.
5. Redis and Postgres remain mandatory; rate limiting and migrations are not weakened.
6. Free-tier limits are monitored; degradation is accepted over paid overages.

**If any condition fails — especially commercial use or a mandatory card — the correct decision is `BLOCKED`.**

---

## Appendix A — Provider documentation references

- Vercel Hobby plan: <https://vercel.com/docs/plans/hobby>
- Render free tier limits: <https://render.com/docs/free>
- Render FAQ (payment method behavior): <https://render.com/docs/faq>
- Neon pricing (free plan, no card): <https://neon.com/pricing>
- Neon scale-to-zero: <https://neon.com/docs/introduction/scale-to-zero>
- Upstash Redis pricing: <https://upstash.com/docs/redis/overall/pricing>
- cron-job.org FAQ: <https://cron-job.org/en/faq/>
- Cloudflare R2 get started (subscription checkout): <https://developers.cloudflare.com/r2/get-started/>
- Cloudflare R2 pricing: <https://developers.cloudflare.com/r2/pricing/>
- Supabase billing: <https://supabase.com/docs/guides/platform/billing-on-supabase>
- Brevo free plan: <https://help.brevo.com/hc/en-us/articles/208589409-What-is-the-free-plan>
- Resend pricing: <https://resend.com/pricing>

## Appendix B — Audit safety statement

- No deployment was performed.
- No provider account was created.
- No signup form, checkout, or paid activation was submitted.
- No infrastructure was provisioned.
- No DNS, TLS, OAuth app, database, or Redis instance was created.
- No application code, config, dependency, Dockerfile, schema, or migration was modified.
- No Git state was mutated: no stage, commit, push, pull, reset, stash, checkout, clean, or discard.
- The only file created is this report: `docs/deployment/free_tier_deployment_readiness.md`.
