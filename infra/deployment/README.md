# Cartel — Free-Tier Deployment Kit (Architecture A)

Stage A preparation only. Nothing in this directory creates an account,
resource, database, OAuth app, or public deployment by itself. Every external
action needs explicit per-action approval.

## Files

| File | Purpose |
|---|---|
| `render.env.example` | Render Free backend environment template (placeholders only) |
| `vercel.env.example` | Vercel Hobby frontend environment template (one server-side variable) |
| `neon-migration.env.example` | Neon direct-endpoint template for the one-time Alembic gate |
| `migrate_neon.sh` | Masked, single-head-checked, direct-endpoint migration runner |
| `smoke_check.py` | Read-only hosted checks: health, `/ready` PostgreSQL+Redis, docs disabled, `/api` rewrite, no `api:8000` |

## Deployment order (state machine)

Each step is a separate approval. Do not proceed past a failed gate.

1. Neon Free project + database (observe cardless flow).
2. Upstash Free Redis database (observe cardless flow).
3. GitHub OAuth App (callback placeholder first; correct after Vercel URL exists).
4. Render Free Web Service environment + deploy (no migration in start command).
5. Verify backend `/health` and `/ready` (PostgreSQL and Redis must both be `ready`).
6. Approved migration: `infra/deployment/migrate_neon.sh` with the Neon **direct** endpoint.
7. Confirm the synthetic catalog is present in the deployed checkout (`DATA_DIR=../data/demo_catalog`); no remote seeding unless separately approved.
8. Vercel project configuration + deploy with `BACKEND_INTERNAL_URL`.
9. Verify the same-origin `/api` rewrite and run `smoke_check.py`.
10. GitHub login and full browser journey, including two-account isolation and reload persistence.
11. Optional cron-job.org keep-alive (not a suspension guarantee).

## Non-negotiable settings

- `APP_ENV=staging` (production forbids `DEMO_FIXTURES_ENABLED=true`).
- `AUTH_REQUIRED=true`, `AUTH_COOKIE_SECURE=true`, exact `PUBLIC_ORIGIN` / `CORS_ALLOWED_ORIGINS`.
- `DATABASE_REQUIRED=true`, `postgresql+psycopg://`, `sslmode=require`, pool `1/0/300`.
- `REDIS_URL=rediss://`, 1-second connect/operation timeouts.
- `DEMO_FIXTURES_ENABLED=true`, `DATA_DIR=../data/demo_catalog`.
- `RETAILER_DATA_PROVIDER_MODE=unavailable`, `CHECKOUT_OBSERVATION_PROVIDER_MODE=unavailable`, `CHECKOUT_CAPTURE_ADAPTER_MODE=unavailable`, `VAULT_KEY_PROVIDER=unavailable`.
- `EMAIL_DELIVERY_MODE=smtp` with empty SMTP values; email endpoints fail closed with 503.
- `DOCS_ENABLED=false`; `/docs`, `/redoc`, and the OpenAPI JSON are disabled.
- `BACKEND_INTERNAL_URL` is server-side only; `NEXT_PUBLIC_API_BASE_URL` stays unset.

## Git publication prerequisite

Render and Vercel build from the Git repository. The synthetic generator and
catalog are currently untracked. The user must commit and push:

- `backend/app/dev/seed_synthetic_demo_cart.py`
- `backend/app/demo_catalog.py`
- `data/demo_catalog/` (18 files; digest `33b042f20aaec34ca9400983763f64e6a920f0b0892b0e1e0b8f8b2edafe3068`)
- `backend/tests/fixtures/synthetic_demo/` (optional test mirror)

No Git mutation is performed by this kit.
