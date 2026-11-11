# Phase K.5 — Cardless Free-Tier Deployment Preparation (Stage A)

**Date:** 2026-11-10
**Branch:** `feat/cartel-production-foundation`
**HEAD:** `59560b9dcab78c82c8bd3b0c47f8d7d33508a821`
**Scope:** Stage A preparation baseline. As of this date, no account, resource, OAuth app, hosted service, public deployment, remote migration, fixture seeding, or keep-alive had been created or executed. Later user-executed actions are recorded in the addendum below and in §10.
**Decision:** `READY_FOR_DEPLOYMENT` (see §19)

> This report is preparation evidence, not deployment evidence. Nothing here proves a public URL, a hosted journey, provider-side cardless prompts, or commercial approval. Those remain unverified until the user performs the corresponding approved external action.
>
> **Addendum 2026-11-11:** the user created the Neon Free project out-of-band. Read-only connection verification is recorded in [`phase_k5_neon_connection_verification.md`](./phase_k5_neon_connection_verification.md). The approved schema migration was then executed by the user against `neondb` over the direct endpoint and reported successful at `0009_credential_vault` with 18 tables (see §10 and [`phase_k5_neon_migration_plan.md`](./phase_k5_neon_migration_plan.md) §12). No seeding or demo-data load was performed, and no other provider was configured.

---

## 1. Scope, constraints, and non-goals

Architecture A remains:

| Layer | Provider | Plan |
| --- | --- | --- |
| Frontend | Vercel | Hobby (free, non-commercial) |
| Backend | Render | Free native Python web service |
| PostgreSQL | Neon | Free |
| Redis | Upstash | Free |
| Login | GitHub | OAuth App (free) |
| Keep-alive (optional) | cron-job.org | Free |

Hard constraints honoured in this stage:

- ₹0 and cardless. No card, paid plan, PAYG, paid credits, domain purchase, auto-upgrade, or temporary paid activation. No paid substitute was configured.
- No external account or resource was created. No signup form was opened or submitted.
- No connection string, password, OAuth secret, token, or API key was printed, logged, committed, or pasted. Only placeholders, masked targets, and dummy local values appear in this report.
- No demo-catalog identity change: `CARTEL_DEMO`, deterministic generator, fixed identities and provenance. No Blinkit relabel, no retailer observation, no acquisition invocation, no fixture persisted as live evidence.
- No in-memory Redis fallback. Distributed fail-closed rate limiting is preserved.
- No SMTP requirement, worker deployment, Chromium/Playwright runtime dependency, or persistent-filesystem assumption in the hosted design.
- No destructive database or user-data action. No database drop/recreate as "rollback".
- No build/redeploy beyond the local validations below. No weakened safeguard.
- No Git mutation: no stage, commit, push, pull, reset, stash, checkout, clean, or discard.

---

## 2. Baseline and workspace comparison

Baseline captured at `2026-11-10T13:18:26Z` in `…/k5/baseline.txt`.

| Item | Baseline | After Stage A | Delta |
| --- | --- | --- | --- |
| Branch | `feat/cartel-production-foundation` | same | none |
| HEAD | `59560b9d…` | same | none |
| Modified files | 65 | 66 | `+backend/app/api/routes/health.py` |
| Untracked files (`-uall`) | 133 | 139 | `+6` under `infra/deployment/` |
| Staged files | 0 | 0 | none |
| Tracked diffstat | 65 files, +2372/−613 | 65 files, +2372/−613 | none |
| Staged diffstat | empty | empty | none |

The only tracked source change made in K.5 is the real Redis readiness probe in `backend/app/api/routes/health.py` (9 added lines). All other K.5 artifacts are new untracked documentation/configuration files.

K.4 comparison (documented baseline commands):

| Gate | K.4 | K.5 | Result |
| --- | --- | --- | --- |
| Unit suite | 1009 passed | 1009 passed | unchanged |
| `tests/integration/api/test_consumer_auth.py` | 20 passed | 20 passed | unchanged |
| `tests/integration/api/test_staging_config_validation.py` | 6 passed | 6 passed | unchanged |
| Browser E2E `test_consumer_journey_browser.py` | 1 passed | 1 passed | unchanged |

A full `tests/integration` run is **not** a K.4 gate and is not clean: it reports 38–57 failures from pre-existing retailer-connection input validation and shared rate-limit keys. Re-running the K.4-documented command (`test_consumer_auth.py`, 20 passed) is clean. This is disclosed, not hidden.

---

## 3. Provider documentation verification

All pages fetched over HTTPS on **2026-11-10** (HTTP 200 unless noted). Labels: **[DOC]** = provider documentation/pricing page; **[UNVERIFIED]** = assumption not proven by a fetched source or not yet observed in a real signup flow.

### 3.1 Vercel Hobby

| Fact | Quoted clause | Source | Label |
| --- | --- | --- | --- |
| Non-commercial only | "As stated in the fair use guidelines, the Hobby plan restricts users to non-commercial, personal use only." | https://vercel.com/docs/accounts/plans/hobby | [DOC] |
| No billing cycle | "As the Hobby plan is a free tier there are no billing cycles." | same | [DOC] |
| 100 GB Fast Data Transfer/month included | "100 GB / month included" | https://vercel.com/pricing | [DOC] |
| 100 deployments/day | "Deployments per day … 100" | https://vercel.com/docs/accounts/plans/hobby | [DOC] |
| Function max duration 300 s | "Vercel Function maximum duration … 300s (5 minutes)" | same | [DOC] |
| 200 projects; 50 domains/project | "Projects … 200"; "Domains per project … 50" | same | [DOC] |
| 45-minute build; 2 vCPU / 8 GB | "The maximum duration of the Build Step is 45 minutes."; "Build vCPUs 2"; "Build memory (GB) 8" | https://vercel.com/docs/limits and hobby page | [DOC] |

**Fit:** the showcase is a personal, non-commercial portfolio project. If it ever becomes commercial, Hobby is not permitted and the deployment must stop rather than upgrade.

### 3.2 Render Free (backend)

| Fact | Quoted clause | Source | Label |
| --- | --- | --- | --- |
| 750 instance hours/month | "Render grants 750 Free instance hours to each workspace per calendar month" | https://render.com/docs/free | [DOC] |
| Suspension on overage | "If you consume all of your Free instance hours during a given month, Render suspends all of your Free web services until the start of the next month." | same | [DOC] |
| Spin-down after 15 min idle | "Render spins down a Free web service that goes 15 minutes without receiving any inbound traffic." | same | [DOC] |
| ~1 minute cold start | "This process takes about one minute." | same | [DOC] |
| Bandwidth overage without a card | "If you haven't added a payment method, Render instead suspends all of your Free services for the remainder of the month." | same | [DOC] |
| 5 GB outbound bandwidth | "5 GB of bandwidth included" | https://render.com/pricing | [DOC] |
| 500 build pipeline minutes/month | "Hobby: 500" (included Starter pipeline minutes) | https://render.com/docs/build-pipeline | [DOC] |
| SMTP ports blocked | "Free web services can't send outbound network traffic on ports 25, 465, or 587, commonly used for SMTP." | https://render.com/docs/free | [DOC] |
| Ephemeral filesystem | "any changes to your web service's filesystem … are lost every time the service redeploys, restarts, or spins down." | same | [DOC] |
| No persistent disks / scaling | "Persistent disks" listed as unsupported; "Scaling beyond a single instance" unsupported | same | [DOC] |
| Restart at any time | "Render might restart a Free web service at any time." | same | [DOC] |
| Python 3.12 selectable | `PYTHON_VERSION` accepts fully qualified released versions from 3.7.3 onward; current default is newer than 3.12 | https://render.com/docs/python-version | [DOC] |

**Fit:** the app is stateless except PostgreSQL/Redis and the read-only Git-tracked catalog, so ephemeral disk is acceptable. SMTP is deliberately unavailable; email endpoints fail closed. Spin-down means the first request after idle is slow; this is disclosed to the user.

### 3.3 Neon Free (PostgreSQL)

| Fact | Quoted clause | Source | Label |
| --- | --- | --- | --- |
| $0 and cardless | "Build and learn free with no time limits and no credit card required." | https://neon.com/pricing | [DOC] |
| Permanent, not a trial | "The Free plan is permanent, not a trial, and doesn't require a credit card. Most limits are per project, and none of them delete your data" | same | [DOC] |
| 100 projects; 10 branches/project | "Projects 100"; "Branches 10/project" | https://neon.com/docs/introduction/plans | [DOC] |
| 100 CU-hours/project | "Compute 100 CU-hours/project" | same | [DOC] |
| Scale to zero after 5 min | "Scale to zero … After 5 min" | same | [DOC] |
| 1 GB/project, 20 GB account | "Storage 1 GB/project, 20 GB account total" | same | [DOC] |
| 5 GB public transfer/project | "Public network transfer … 5 GB" | same | [DOC] |
| Pooled endpoint | pooled host contains `-pooler`; PgBouncer transaction pooling | https://neon.com/docs/connect/connection-pooling | [DOC] |
| TLS required | `sslmode=require` in connection guidance | https://neon.com/docs/connect/connect-from-any-app | [DOC] |

**Fit:** runtime uses the pooled endpoint; Alembic uses the direct endpoint. Pool is `1/0` to stay inside Neon's pooled limits and avoid connection exhaustion.

### 3.4 Upstash Free (Redis)

| Fact | Quoted clause | Source | Label |
| --- | --- | --- | --- |
| 250 MB data | "Free tier includes 250MB data size" | https://upstash.com/pricing/redis | [DOC] |
| 500K commands/month | "… and 500K commands per month." | same | [DOC] |
| 10 GB monthly bandwidth | Free column "10 GB" | same | [DOC] |
| 1 free database | "A free account can have 1 database." | same | [DOC] |
| TLS | "TLS Encryption" listed as free/included; clients use `rediss://` | same | [DOC] |
| Card entry upgrades to PAYG | "Once you enter your credit card, your database will be upgraded to the pay-as-you-go plan and limits will be updated." | same | [DOC] |

**Fit:** rate limiting is one Redis script call per request. At showcase traffic this is far below 500K/month. Entering a card would silently change the plan, so the user must not add one.

### 3.5 GitHub OAuth

| Fact | Quoted clause / behaviour | Source | Label |
| --- | --- | --- | --- |
| OAuth App needs Homepage + callback URL | OAuth App creation requires "Homepage URL" and "Authorization callback URL" | https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app | [DOC] |
| Up to 10 callback URLs | callback URL list supports up to 10 entries | same | [DOC] |
| Client secret is server-side | client secret must not be exposed in client code | same | [DOC] |
| Scopes | `read:user`, `user:email` | https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps | [DOC] |

Repository code requests exactly `read:user user:email` (`backend/app/auth/providers.py:GitHubOAuthProvider`). The app requires a verified primary email before creating a session.

### 3.6 cron-job.org (optional)

| Fact | Quoted clause | Source | Label |
| --- | --- | --- | --- |
| Free | "entirely free of charge" | https://cron-job.org/en/faq/ | [DOC] |
| Up to 60 executions/hour | minimum interval one minute | same | [DOC] |
| 30 s timeout, 64 KB output | documented execution limits | same | [DOC] |

**Use:** optional, and only against `GET /health` (no database or Redis touch). A keep-alive is not a suspension guarantee and must never target `/ready`, because that would keep Neon compute active and consume CU-hours.

---

## 4. Cardless eligibility evidence

| Provider | Evidence that the Free path is cardless | Status |
| --- | --- | --- |
| Neon | "no credit card required"; "doesn't require a credit card" | [DOC] verified; **signup prompt unverified until the user performs signup** |
| Upstash | Free tier described with no card; card entry explicitly upgrades to PAYG | [DOC] verified; **signup prompt unverified until the user performs signup** |
| Vercel | Hobby is a free tier with no billing cycle | [DOC] verified; **signup prompt unverified until the user performs signup** |
| Render | Free instance hours and suspension-on-overage behaviour described; no card required for Free | [DOC] verified; **signup prompt unverified until the user performs signup** |
| GitHub | OAuth Apps are free for public use; no payment step described | [DOC] verified; **signup prompt unverified until the user performs signup** |
| cron-job.org | "entirely free of charge" | [DOC] verified; optional |

**Not claimed:** that any signup page actually omits a card field today. That can only be confirmed by the user at the real flow. If any provider asks for a card, paid activation, or plan change, the action stops and is reported — no paid substitute.

---

## 5. Account and resource status

| Resource | Created? | Notes |
| --- | --- | --- |
| Neon account/project/database | User-created (`my-first-project`, `neondb`) | Console-attested; no Cartel tables verified; see verification report |
| Upstash account/database | No | Awaiting approval |
| GitHub OAuth App | No | Awaiting approval |
| Render account/service | No | Awaiting approval |
| Vercel account/project | No | Awaiting approval |
| cron-job.org account/job | No | Optional; awaiting approval |
| Custom domain | No | Not purchased, not planned |

The assistant opened no provider dashboard and submitted no signup form. The user created the Neon project out-of-band on 2026-11-11. No external HTTP request from this workspace carried credentials.

Local disposable resources used only for validation (not deployment):

- `cartel-k5-pg` (PostgreSQL 16, `127.0.0.1:55433`, databases `cartel_k5`, `cartel_k5_e2e`) — ephemeral `--rm`, removed after use.
- `cartel-k5-redis` (Redis 7, `127.0.0.1:56380`) — ephemeral `--rm`, removed after use.
- The user's existing `cartel-smart-cart-optimizer-postgres-1` container/volume was never touched.

---

## 6. Configuration inventory

| File | Purpose |
| --- | --- |
| `infra/deployment/render.env.example` | Render Free backend environment template, 45 keys, placeholders only |
| `infra/deployment/vercel.env.example` | Vercel Hobby template; server-side `BACKEND_INTERNAL_URL` only; no `NEXT_PUBLIC_*` |
| `infra/deployment/neon-migration.env.example` | Direct-endpoint migration template |
| `infra/deployment/migrate_neon.sh` | Masked, single-head-checked, direct-endpoint migration runner |
| `infra/deployment/smoke_check.py` | Read-only hosted checks (health, readiness, docs, rewrite, no `api:8000`) |
| `infra/deployment/README.md` | Deployment order, non-negotiable settings, Git prerequisite |

No `.env` file with real values was created. No secret is stored in any tracked or untracked repository file.

---

## 7. Environment variable matrix

Legend: **S** = secret (never displayed), **R** = required for the hosted showcase, **O** = optional.

### 7.1 Render backend (45 keys)

| Variable | Provider / service | S? | Source | R/O | Code reader |
| --- | --- | --- | --- | --- | --- |
| `APP_NAME` | Render | no | template | R | `backend/app/core/config.py:Settings.app_name` |
| `APP_ENV` | Render | no | template (`staging`) | R | `backend/app/core/config.py:Settings.app_env` |
| `APP_DEBUG` | Render | no | template (`false`) | R | `backend/app/core/config.py:Settings.app_debug` |
| `APP_VERSION` | Render | no | template | R | `backend/app/core/config.py:Settings.app_version` |
| `API_V1_PREFIX` | Render | no | template | R | `backend/app/core/config.py:Settings.api_v1_prefix` |
| `LOG_LEVEL` | Render | no | template | R | `backend/app/core/logging.py:configure_logging` |
| `LOG_JSON` | Render | no | template | R | `backend/app/core/logging.py:configure_logging` |
| `DOCS_ENABLED` | Render | no | template (`false`) | R | `backend/app/main.py:create_application` (`docs_url`, `redoc_url`) |
| `PUBLIC_ORIGIN` | Render | no | template (Vercel origin) | R | `backend/app/auth/service.py:ConsumerAuthService`; `backend/app/api/v2/dependencies.py` |
| `CORS_ALLOWED_ORIGINS` | Render | no | template (exact Vercel origin) | R | `backend/app/core/config.py:Settings.cors_origins`; `backend/app/main.py:create_application` |
| `AUTH_REQUIRED` | Render | no | template (`true`) | R | `backend/app/core/config.py:Settings`; `backend/app/main.py:create_application` |
| `AUTH_TOKENS` | Render | **S** | operator-generated | R | `backend/app/core/config.py:Settings.configured_auth_tokens`; `backend/app/core/security.py:authenticate_bearer` |
| `AUTH_COOKIE_SECURE` | Render | no | template (`true`) | R | `backend/app/core/config.py:Settings.secure_auth_cookie`; `backend/app/api/v2/auth.py` |
| `AUTH_SESSION_DAYS` | Render | no | template | O | `backend/app/auth/service.py:ConsumerAuthService` |
| `AUTH_IDLE_DAYS` | Render | no | template | O | `backend/app/auth/service.py:ConsumerAuthService` |
| `AUTH_CHALLENGE_MINUTES` | Render | no | template | O | `backend/app/auth/service.py:ConsumerAuthService` |
| `AUTH_RATE_LIMIT_REQUESTS` | Render | no | template | O | `backend/app/main.py:create_application` |
| `DATABASE_REQUIRED` | Render | no | template (`true`) | R | `backend/app/api/routes/health.py:readiness_check` |
| `DATABASE_URL` | Neon (pooled) | **S** | Neon dashboard | R | `backend/app/core/config.py:Settings.database_url`; `backend/app/db/session.py:get_session_factory` |
| `DB_POOL_SIZE` | Render | no | template (`1`) | R | `backend/app/db/session.py:get_session_factory` |
| `DB_MAX_OVERFLOW` | Render | no | template (`0`) | R | same |
| `DB_POOL_TIMEOUT_SECONDS` | Render | no | template (`30`) | R | same |
| `DB_POOL_RECYCLE_SECONDS` | Render | no | template (`300`) | R | same |
| `REDIS_URL` | Upstash | **S** | Upstash dashboard | R | `backend/app/core/config.py:Settings.redis_url`; `backend/app/core/rate_limit.py:RedisRateLimiter` |
| `REDIS_CONNECT_TIMEOUT_SECONDS` | Render | no | template (`1`) | R | `backend/app/core/rate_limit.py:RedisRateLimiter` |
| `REDIS_OPERATION_TIMEOUT_SECONDS` | Render | no | template (`1`) | R | same |
| `REDIS_MAX_CONNECTIONS` | Render | no | template (`5`) | R | same |
| `GITHUB_CLIENT_ID` | GitHub | no | OAuth App | R | `backend/app/auth/providers.py:GitHubOAuthProvider` |
| `GITHUB_CLIENT_SECRET` | GitHub | **S** | OAuth App | R | same |
| `GITHUB_REDIRECT_URI` | GitHub | no | template (Vercel callback) | R | `backend/app/api/v2/auth.py:provider_redirect_uri` |
| `DEMO_FIXTURES_ENABLED` | Render | no | template (`true`) | R | `backend/app/main.py:create_application` (`include_synthetic`, `include_fixtures`) |
| `DATA_DIR` | Render | no | template (`../data/demo_catalog`) | R | `backend/app/core/config.py:Settings.data_dir`; `backend/app/workers/bootstrap.py:build_product_intelligence_runtime` |
| `RETAILER_DATA_PROVIDER_MODE` | Render | no | template (`unavailable`) | R | `backend/app/core/config.py:Settings`; `backend/app/main.py:create_application` |
| `CHECKOUT_OBSERVATION_PROVIDER_MODE` | Render | no | template (`unavailable`) | R | same |
| `CHECKOUT_CAPTURE_ADAPTER_MODE` | Render | no | template (`unavailable`) | R | same |
| `VAULT_KEY_PROVIDER` | Render | no | template (`unavailable`) | R | `backend/app/core/config.py:Settings`; credential-vault factory |
| `EMAIL_DELIVERY_MODE` | Render | no | template (`smtp`) | R | `backend/app/main.py:create_application` |
| `SMTP_HOST` | Render | no | empty | O | `backend/app/auth/email_delivery.py:SmtpEmailDelivery` |
| `SMTP_PORT` | Render | no | template | O | same |
| `SMTP_USERNAME` | Render | no | empty | O | same |
| `SMTP_PASSWORD` | Render | **S** | empty (unused) | O | same |
| `SMTP_FROM` | Render | no | empty | O | same |
| `SMTP_STARTTLS` | Render | no | template | O | same |
| `RATE_LIMIT_REQUESTS` | Render | no | template | R | `backend/app/main.py:create_application` |
| `RATE_LIMIT_WINDOW_SECONDS` | Render | no | template | R | same |

Provider-only setting (not an app variable): `PYTHON_VERSION=3.12.11` on Render.

### 7.2 Vercel frontend

| Variable | Service | S? | Source | R/O | Code reader |
| --- | --- | --- | --- | --- | --- |
| `BACKEND_INTERNAL_URL` | Vercel (build + server) | no | Render service URL | R | `frontend/next.config.ts:nextConfig` (`/api/:path*` rewrite) |
| `NEXT_TELEMETRY_DISABLED` | Vercel | no | `1` | O | Next.js build |

`NEXT_PUBLIC_API_BASE_URL` is deliberately **unset**. It is a client-visible variable; setting it would bypass the same-origin rewrite.

### 7.3 Migration-only environment

| Variable | Service | S? | Source | R/O | Code reader |
| --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | Neon direct endpoint | **S** | Neon dashboard | R (migration only) | `backend/app/db/migrations/env.py:run_migrations_online` |

---

## 8. Configuration validation evidence

All validation used dummy/local values only.

### 8.1 Template validation (Python 3.12, Render's runtime)

Script: `…/k5/validate_templates.py`. Result: `ALL_TEMPLATE_ASSERTIONS_PASSED`.

```
render_template_keys=45
vercel_template_keys=['BACKEND_INTERNAL_URL', 'NEXT_TELEMETRY_DISABLED']
neon_template_keys=['DATABASE_URL']
data_dir=/Users/…/data/demo_catalog
public_origin=https://cartel-k5.vercel.app
cors_origins=('https://cartel-k5.vercel.app',)
database_scheme=postgresql+psycopg
database_target_masked=postgresql+psycopg://cartel:***@ep-k5-pooler…neon.tech:5432/cartel_k5?sslmode=require
redis_scheme=rediss
pool=1/0/300
redis_timeouts=1.0/1.0/5
email_configured=False
github_configured=True
demo_fixtures_enabled=True
```

Proven fail-closed behaviours:

- `APP_ENV=production` + `DEMO_FIXTURES_ENABLED=true` raises `ValueError`.
- `AUTH_REQUIRED=true` + empty `AUTH_TOKENS` raises `ValueError`.
- Every Render template key maps to a real `Settings` field (or the documented provider-only `PYTHON_VERSION`).
- `DATA_DIR` resolves to the repo's committed `data/demo_catalog`, not the legacy `data/product_intelligence`.

### 8.2 K.4 executable staging validation

```
CARTEL_TEST_DATABASE_URL=…/cartel_k5 REDIS_URL=redis://127.0.0.1:56380/0 \
python -m pytest tests/integration/api/test_staging_config_validation.py -q -rs
```

Result: `6 passed`. Covers staging env, exact CORS, secure/HttpOnly/SameSite cookie, and auth gating with dummy values.

### 8.3 Readiness with real PostgreSQL and Redis

`/ready` now performs a real Redis ping and returns `not_ready` if Redis is unavailable (K.5 change in `health.py`). With disposable PostgreSQL and Redis:

```json
{"status":"ready","checks":{
  "product_intelligence_runtime":"ready","cart_planning":"ready",
  "product_search":"ready","data_directory":"ready",
  "checkout_capture":"unavailable","authentication":"ready",
  "database":"ready","rate_limiter":"ready","redis":"ready"}}
```

`/health` 200; `/docs` 404; `/redoc` 404; `/api/v1/openapi.json` 401 without credentials.

### 8.4 Render start command, locally

Exact start command validated under Python 3.12:

```
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Bound successfully; `/health` 200 and `/ready` 200 with database and Redis ready. Local PostgreSQL has no TLS, so this local check used `sslmode=disable`; the Neon template keeps `sslmode=require`.

### 8.5 Frontend production build

- `VERCEL=1` with no `BACKEND_INTERNAL_URL` fails closed:
  `Error: BACKEND_INTERNAL_URL must be set to the public Render backend origin for Vercel builds.`
- `VERCEL=1 BACKEND_INTERNAL_URL=https://cartel-k5.onrender.com npm run build` exits 0.
- Rewrite manifest: `/api/:path*` → `https://cartel-k5.onrender.com/api/:path*`.
- After removing the build cache: `api:8000` occurrences in `.next` = **0**; client static `api:8000` = **0**; `onrender` in client static = **0**.
- Backend-secret names in client static: `DATABASE_URL` 0, `REDIS_URL` 0, `AUTH_TOKENS` 0, `GITHUB_CLIENT_SECRET` 0, `SMTP_PASSWORD` 0, `POSTGRES_PASSWORD` 0, `VAULT_DEV_KEYS` 0, `BACKEND_INTERNAL_URL` 0.
- `NEXT_PUBLIC_API_BASE_URL` appears only as an unset literal (`?? ""`) in client code, not as a value.

**Conclusion:** a Vercel build cannot silently fall back to the Docker-only `http://api:8000`, and no backend secret reaches the browser bundle.

---

## 9. OAuth status

- GitHub OAuth App: **not created**.
- Required scopes in code: exactly `read:user user:email` (`backend/app/auth/providers.py`).
- Callback route in code: `/api/v2/auth/{provider}/callback`; for GitHub this is `/api/v2/auth/github/callback`.
- The callback must be on the **Vercel** origin, because the browser completes the flow there and Vercel rewrites `/api` to Render:

  `https://<vercel-project>.vercel.app/api/v2/auth/github/callback`

- Because the Vercel URL does not exist until the frontend project is created, the sequence is:
  1. Create the OAuth App with a placeholder callback (or defer creation until after Vercel).
  2. After the Vercel production URL is known, correct the callback URL in GitHub and `GITHUB_REDIRECT_URI` on Render.
  3. Re-verify login. Until then, login is expected to fail with a redirect-URI error.
- The client secret is server-side only. It is never placed in Vercel or any client bundle.
- Email/password signup, resend, and recovery return `503 email_delivery_unavailable` because SMTP is intentionally unconfigured (Render Free blocks SMTP ports and no email provider is in scope). **GitHub OAuth is the only login path.**

---

## 10. Migration status

| Item | Status |
| --- | --- |
| Repository heads | `alembic heads` → single head `0009_credential_vault` |
| Expected head | `0009_credential_vault` — matches |
| Remote migration | **Executed 2026-11-11 by the user** (direct endpoint) |
| Remote revision | **`0009_credential_vault`** (reported) |
| Remote table count | **18**, no missing expected tables (reported) |
| Local dry run | Passed on disposable PostgreSQL |
| Second run | Idempotent; no duplicate tables/errors |
| Target masking | `migrate_neon.sh` prints `user:***@host:port/db?query` only |
| Implicit `DATABASE_URL` | Refused: script exits if `DATABASE_URL` is unset |
| Pooled endpoint | Refused: script exits if the URL contains `-pooler` |
| Single-head gate | Refused unless exactly one `(head)` line |
| Table verification | `alembic_version=0009_credential_vault`, 18 tables, no missing expected tables |

Local run evidence (disposable PostgreSQL, masked):

```
migration target: postgresql+psycopg://cartel:***@127.0.0.1:55433/cartel_k5?sslmode=require
repository head: 0009_credential_vault (head)
… upgrade chain 0001 → 0009 …
alembic_version=0009_credential_vault
table_count=18
missing_expected_tables=none
migration verification passed
```

Remote run — fields reported by the user (Neon `neondb`, direct endpoint, 2026-11-11). This is a summary of the reported results, not a verbatim console capture:

| Reported field | Value |
| --- | --- |
| Target | Neon Free `neondb`, direct (non-pooled) endpoint |
| `alembic_version` | `0009_credential_vault` |
| Table count | `18` (17 application tables + `alembic_version`) |
| Missing expected tables | `none` |
| Script verification | passed |

The full masked console output was not provided, so intermediate Alembic log lines are not reproduced here.

**Confirmed:** the remote schema is at `0009_credential_vault` with 18 tables and no missing expected tables. **Not yet confirmed:** zero application rows, the specific 0009 constraints/indexes, the 18 `credential_secrets` columns, and post-migration TLS/encoding — these SELECT-only checks were not included in the reported output. Do not treat them as passing until run (see the migration plan §12.2). No seeding or DML was performed, so the schema is expected to be row-free, but that is an expectation, not a verified result.

---

## 11. Demo-catalog init status

| Item | Status |
| --- | --- |
| Runtime catalog | `data/demo_catalog` (18 files) |
| Digest | `33b042f20aaec34ca9400983763f64e6a920f0b0892b0e1e0b8f8b2edafe3068` |
| Generator | `backend/app/dev/seed_synthetic_demo_cart.py` |
| Generator output matches committed tree | yes (`runtime_matches_generator=true`) |
| Fixture mirror | `backend/tests/fixtures/synthetic_demo` (19 files incl. README) |
| Products | `cartel-demo-product-{milk,atta,rice,oil}` |
| Runtime listings | 16 (4 products × 2 variants × 2 listings) |
| Platform label | `CARTEL_DEMO` only |
| Provenance | `synthetic-demo-catalog-v1`, source scheme `synthetic://cartel-demo/…` |
| Second generation | idempotent, no duplicates |
| External calls during generation | none |
| Init command required at runtime | **No** — the service reads the Git-tracked directory |
| Remote seeding | **Not performed and not planned** |

Runtime assertion result:

```
item_count=16
product_ids=['cartel-demo-product-atta','cartel-demo-product-milk','cartel-demo-product-oil','cartel-demo-product-rice']
platforms=['CARTEL_DEMO']
all_synthetic=True
provenance=['synthetic-demo-catalog-v1']
source_schemes=['synthetic']
DEMO_CATALOG_RUNTIME_ASSERTIONS_PASSED
```

**Prerequisite:** `data/demo_catalog/` and `backend/app/dev/seed_synthetic_demo_cart.py` are currently untracked. A Git-based Render deploy will not include them until the user commits and pushes. No remote seeding is needed once they are committed.

---

## 12. Frontend and backend deployment status

| Item | Status |
| --- | --- |
| Render backend | **Not deployed** |
| Vercel frontend | **Not deployed** |
| Public backend URL | none |
| Public frontend URL | none |
| DNS / custom domain | none |
| Hosted environment variables | none set |
| Repo linked to Render/Vercel | no |

Local production-shaped validation only: backend start command, frontend production build, same-origin rewrite, readiness, and full browser journey.

### 12.1 Local browser journey (K.4 regression)

Stack: backend `127.0.0.1:18000` (staging, disposable `cartel_k5_e2e`, Redis `56380`, file email capture, demo gate on), frontend production build served at `127.0.0.1:13000`.

```
E2E_BASE_URL=http://127.0.0.1:13000 E2E_BACKEND_URL=http://127.0.0.1:18000 \
E2E_DATABASE_URL=postgresql+psycopg://…@127.0.0.1:55433/cartel_k5_e2e \
E2E_REQUEST_LOG=…/e2e_requests.log \
python -m pytest tests/e2e/test_consumer_journey_browser.py -q -rs
```

Result: `1 passed in 3.96s`.

Network-log evidence: 432 browser requests, all to `127.0.0.1:13000`; retailer-host hits 0; operator-only path hits 0. The journey proves signup/verify/session restore, persisted list, exact synthetic variant identity in PostgreSQL, unresolved item honesty, optimization reload persistence, status guide, navigation contract, `/cart` data source, and no payable total. It does **not** prove a hosted deployment or GitHub OAuth.

Cleanup: both local servers stopped; `cartel-k5-pg` and `cartel-k5-redis` removed; only the user's pre-existing container remained.

---

## 13. Hosted smoke plan and acceptance criteria (not executed)

Because nothing is deployed, hosted smoke results are **not available**. The read-only script is prepared:

```
python3 infra/deployment/smoke_check.py \
  --frontend https://<vercel-project>.vercel.app \
  --backend https://<render-service>.onrender.com
```

Acceptance criteria:

| Check | Pass condition |
| --- | --- |
| Backend health | `GET /health` 200 |
| Backend readiness | `GET /ready` 200; `checks.database == ready` **and** `checks.redis == ready` |
| Docs restricted | `/docs` 404; `/redoc` 404; `/api/v1/openapi.json` 401 or 404 |
| Same-origin rewrite | `GET <frontend>/api/v2/auth/providers` 200 from FastAPI, not a Next.js page |
| No Docker-only host | `api:8000` absent from served HTML/JS |
| Real session cookie | `Set-Cookie` includes `HttpOnly`, `Secure`, `SameSite=Lax` |
| Browser egress | no retailer-bound request; no operator-only path |
| Cross-user isolation | two real accounts; list and optimization access denied across users |
| Logout | session invalidated; protected routes reject |
| Password recovery | clearly unavailable (`503 email_delivery_unavailable`), not broken silently |
| Blinkit | excluded from consumer search/planning |
| Partial/unresolved | explanation visible and honest |
| Persistence | reload preserves optimization; backend restart (if safe/approved) preserves data |

If a hosted check fails, the gate stops, diagnostics are preserved, and the report is updated.

---

## 14. Free-tier usage and cost risks

No hosted usage exists yet, so no dashboard value is claimed. The following are documented ceilings, not observed usage.

| Provider | Ceiling | Showcase risk | Mitigation |
| --- | --- | --- | --- |
| Vercel Hobby | 100 GB transfer/month; 100 deployments/day; 300 s function; 45 min build | Low for a portfolio showcase | Do not deploy per-commit unnecessarily; no paid upgrade |
| Render Free | 750 instance hours; 5 GB bandwidth; 500 pipeline minutes; 15 min spin-down | 24/7 is ~744 h, close to 750 h; cold starts ~1 min | Accept spin-down; do not add a card; watch bandwidth after demos |
| Neon Free | 100 CU-hours/project; 1 GB storage; 5 GB transfer; scale-to-zero 5 min | Always-on compute could exceed 100 CU-hours; a `/ready` keep-alive would keep compute active | Keep-alive (if any) hits `/health` only; let compute scale to zero |
| Upstash Free | 250 MB; 500K commands/month; 10 GB bandwidth; 1 DB | Low for showcase traffic | Never enter a card (auto-upgrades to PAYG) |
| GitHub OAuth | Free | None | — |
| cron-job.org | 60 executions/hour; 30 s timeout | Optional | `/health` only, not `/ready` |

Cost exposure if a limit is exceeded without a card: Render suspends Free services for the remainder of the month; Neon fails storage-increasing operations without deleting data; Upstash would require a card to upgrade (must not be entered); Vercel Hobby pauses features rather than billing. **No paid fallback will be used.**

---

## 15. Rollback plan (written before any deployment)

| Scenario | Rollback | Limits / irreversibility |
| --- | --- | --- |
| Bad frontend deploy | Vercel: promote the previous production deployment (instant rollback) | No data loss; old deployment remains until removed |
| Bad backend deploy | Render: roll back to a previous deploy (docs: two most recent previous deploys) | Env changes are not rolled back with code; ephemeral disk is lost on restart |
| Wrong backend env var | Correct in Render dashboard and restart | A bad `DATABASE_URL` can prevent startup; no data change |
| Migration partially applied | Alembic `downgrade` one revision at a time, only if data is compatible | **Not guaranteed**; this showcase has no down-migration rehearsal against real user data |
| Bad migration / data damage | Neon instant restore within the documented history window (6 h, up to 1 GB changes) | After the window or beyond the change volume, **data is not recoverable**; deleting/recreating the project is destructive and is **not** rollback |
| Wrong OAuth callback | Edit the callback URL in GitHub and `GITHUB_REDIRECT_URI` on Render | Old callback stops working immediately; existing sessions are unaffected |
| Demo catalog wrong/missing | Fix locally, commit, redeploy | Catalog is read-only at runtime; no DB fixture rows to clean |
| Compromised secret | Rotate in provider dashboard and Render env; redeploy | Old secret invalid immediately; audit logs may not be available on Free |
| Provider suspension | Wait for the monthly reset, or stop using the service | No card means no automatic overage billing; suspension is not data deletion |
| Project deletion | None | **Irreversible**; requires explicit approval and is not part of normal rollback |

Plain statement: remote user data written to Neon is the only truly persistent state. Once the restore window or change budget is exceeded, it cannot be recovered. Migrations are effectively one-way for this showcase.

---

## 16. Stop conditions

Stop immediately, preserve diagnostics, and report if any of these occur:

- A provider asks for a card, paid plan, PAYG activation, paid credits, or auto-upgrade.
- A plan changes or a "temporary paid activation" is offered.
- `alembic heads` is not exactly `0009_credential_vault`.
- `/health` or `/ready` fails, or `/ready` does not show both PostgreSQL and Redis ready.
- A secret appears in a response, log, client bundle, or report.
- A migration target is ambiguous, pooled, or not the new empty Neon database.
- A destructive database action would be required.
- A retailer request is observed in the browser network log.
- A hosted check cannot distinguish FastAPI from a Next.js fallback.
- Any Git mutation would be required of the assistant.

---

## 17. Remaining blockers and prerequisites

1. **Git publication prerequisite (user action).** HEAD is still `59560b9`; all K.2–K.5 work is uncommitted (66 modified, 139 untracked). Render and Vercel build from Git. The user must commit and push at minimum:
   - the modified backend/frontend source and tests;
   - `backend/app/demo_catalog.py`, `backend/app/dev/seed_synthetic_demo_cart.py`;
   - `data/demo_catalog/` (18 files, digest `33b042f2…`);
   - optionally `backend/tests/fixtures/synthetic_demo/`.
   Without this, a Git-linked deploy builds the old commit and has no showcase. The assistant cannot commit.
2. **Cardless signup flow unverified.** Provider docs say Free is cardless; the real signup pages have not been observed. This is confirmed or stopped at the first approved signup.
3. **Hosted cross-user isolation unverified.** Requires two real accounts. The user must authorize a second account (or accept `UNVERIFIED`).
4. **OAuth callback sequencing.** Placeholder then correction after the Vercel URL exists; login is broken until corrected.
5. **Full integration suite is not clean.** Pre-existing retailer-connection and shared rate-limit failures remain; the K.4-documented gate passes 20/20. Not a K.5 regression, but not a clean full-suite claim.
6. **Render cold start / Neon CU-hour budget.** Operational constraints, not blockers; documented above.

---

## 18. Exact files created or modified in Stage A

Created:

- `docs/deployment/phase_k5_deployment_report.md` (this file)
- `infra/deployment/README.md`
- `infra/deployment/render.env.example`
- `infra/deployment/vercel.env.example`
- `infra/deployment/neon-migration.env.example`
- `infra/deployment/migrate_neon.sh`
- `infra/deployment/smoke_check.py`

Modified:

- `backend/app/api/routes/health.py` — real Redis ping in `/ready`; `status=not_ready` when Redis is unavailable (9 added lines)

No other tracked file was modified in K.5. Temporary validation scripts, logs, virtualenv, and browser cache live outside the repository under `…/T/opencode/k5/` and are not part of the deliverable.

---

## 19. Decision

**`READY_FOR_DEPLOYMENT`**

Rule applied: all Stage A preparation is complete and validated locally (configuration templates, fail-closed builds, staging validation, readiness with real PostgreSQL and Redis, migration runner, demo catalog, browser journey), and every external action still awaits explicit approval. The Neon schema migration has since been executed by the user (2026-11-11) and is confirmed at `0009_credential_vault` with 18 tables. No application is deployed, so the decision is **not** `DEPLOYED_AND_VERIFIED` or `DEPLOYED_WITH_CONSTRAINTS`. No gate failed, so it is **not** `BLOCKED`.

Conditions attached to this decision:

- The user must publish the working tree to Git before any Git-linked deploy.
- Cardless signup prompts remain unverified until the user performs each signup.
- Hosted cross-user isolation remains unverified until two real accounts exist.
- GitHub OAuth is the only login path; email recovery is unavailable by design.
- The database schema exists but post-migration row-emptiness, constraint/index/column, and TLS/encoding checks were not reported; TLS is unresolved (`pg_stat_ssl.ssl=false` vs `sslmode=require`). Run the plan §7 queries before treating the schema as fully verified.
- No seeding has been performed, so the demo catalog is not yet loaded into Neon.

---

## 20. First approval request — Neon Free project and database (completed by the user)

**Status 2026-11-11:** the user created the Neon Free project out-of-band. The approval request below is retained for the audit trail. Read-only verification is in [`phase_k5_neon_connection_verification.md`](./phase_k5_neon_connection_verification.md). The approved schema migration was subsequently executed by the user and reported successful at `0009_credential_vault` with 18 tables; no seeding or demo-data load was performed.

| Disclosure | Detail |
| --- | --- |
| **What** | Create one Neon account (if needed), one Free project, and one PostgreSQL database for the Cartel showcase; then read the pooled and direct connection strings into the Render/migration environment **without pasting them into chat**. |
| **Provider** | Neon (https://neon.com) |
| **Free?** | Yes — Free plan, `$0/month`, permanent, "no credit card required" per fetched pricing page. |
| **Card?** | No card should be requested. If Neon asks for a card or paid activation, **stop** and report. |
| **Public?** | The database is reachable over the public internet at a Neon hostname; the connection URL reportedly contains `sslmode=require`. TLS is unresolved: `pg_stat_ssl.ssl=false` was observed while `sslmode=require` is configured. It is not a public web page, but it is not private-network-only. |
| **Persistent?** | Yes — this is the persistent store for users, sessions, lists, and optimizations. Free limits: 100 CU-hours/project, 1 GB storage, 5 GB transfer, 6-hour restore window. |
| **Reversible?** | Project creation is reversible by deleting the project, but **deletion is irreversible and destructive**. No user data exists yet. Migration and data writes are separate approvals. |

Planned safe sequence after approval: create project/database → confirm the database is empty → record masked host/database (no credentials in chat) → stop before any migration. The migration is a later, separate approval.

**Completed:** the project/database were created, the emptiness check passed, and the separate migration approval was granted and executed on 2026-11-11 (`0009_credential_vault`, 18 tables). **Next gate:** optional post-migration SELECT-only verification, then the Render, Redis, OAuth, and deploy approvals. No seeding, provider configuration, deploy, snapshot, or Git action has been performed.
