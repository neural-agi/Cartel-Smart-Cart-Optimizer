<div align="center">

<br/>

# 🛒 Cartel

### The real cost of groceries, deterministically computed.

**Product Intelligence · Cost Intelligence · Cart Optimization · Consumer Application · Production Runtime**

<br/>

[![Build](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-700%2B%20validated-brightgreen?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/tree/main/backend/tests)
[![Status](https://img.shields.io/badge/status-active%20development-yellow?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)

<!-- Add current consumer UI screenshots and authenticated E2E captures once the populated retailer/catalog journey is available. -->
<!-- Add coverage badge when repository-wide coverage reporting is established. -->

<br/>

**[🤔 Why This Exists](#-why-this-exists) · [✨ Architecture](#-layered-architecture) · [🔬 Pipelines](#-product-intelligence-pipeline) · [🚀 Quick Start](#-quick-start) · [📡 API](#-api) · [📚 Documentation](#-documentation) · [🗺 Roadmap](#-roadmap)**

</div>

---

## 🤔 Why This Exists

Every grocery price-comparison tool compares the same thing: the price printed on the product. That number is mostly fiction.

What you *actually* pay depends on delivery fees, handling charges, platform fees, cashback, loyalty pricing, coupon stacking rules, minimum-order thresholds, membership pricing, and free-item promotions that activate or expire depending on what's already in your cart.

Research (see [`docs/research_analysis.md`](docs/research_analysis.md)) across **Blinkit, BB Now, Zepto, Instamart, and JioMart** confirmed the problem is structural, not incidental:

- **The cart is the unit of optimization, not the product.** Comparing item prices in isolation misses fees and thresholds that only resolve at checkout.
- **Identical products are represented differently across platforms** — naive price-scraping silently compares the wrong things.
- **Offer eligibility is conditional** — activation rules, expiry windows, and stacking limits change what a price actually means.
- **Pricing is engineered to be hard to compare.** Anchoring, urgency, and free-delivery thresholds are deliberate, not accidental.

Cartel exists to answer one question honestly:

> *"What does this cart actually cost, right now, on each platform?"*

---

## ✨ What Makes It Different

|  | Typical Price Comparison Tools | Cartel |
|---|---|---|
| **Optimization unit** | Single product | Entire cart |
| **Price model** | Displayed sticker price | Effective cost (price + fees − rewards) |
| **Delivery & platform fees** | Ignored | Explicitly modeled |
| **Offers, coupons, cashback** | Ignored | Explicitly modeled |
| **Offer stacking rules** | Ignored | Deterministically enforced |
| **Location-aware pricing** | Rare | Built in from the start |
| **Product matching** | Manual or fuzzy | Deterministic, evidence-backed, auditable |
| **Matching audit trail** | None | Full traceability for every match |
| **Deterministic execution** | ❌ | ✅ Same inputs always produce identical outputs |
| **Replayability** | ❌ | ✅ Every decision can be reproduced from stored artifacts |
| **Full audit trail** | ❌ | ✅ Immutable records for all operations |

---

## 🏛 Core Principles

Cartel is built around deterministic product intelligence, evidence governance, consumer data integrity, secure identity, and production-safe operation:

- **Deterministic by design** — governed inputs produce reproducible outputs
- **Evidence-backed reasoning** — canonical identity is never established from retailer observations alone
- **Fail closed** — unknown identity, unavailable evidence, and unsupported capabilities remain explicit
- **Immutable auditability** — important decisions and transitions remain replayable and inspectable
- **Strong ownership boundaries** — PostgreSQL owns mutable consumer/application state while filesystem artifacts remain isolated to governed evidence/catalog paths
- **Safe mutation** — database constraints, idempotency, transactions, and at-least-once job semantics protect business invariants
- **Production-shaped runtime** — health/readiness, structured logging, metrics, rate limiting, durable jobs, retries, recovery, and secure configuration are first-class concerns

---

## 🏗 Layered Architecture

Cartel is structured as composable product, data, orchestration, and runtime boundaries, with a consumer application layer sitting above Product/Cost/Cart Intelligence and shared PostgreSQL, Redis, workers, and observability infrastructure underneath.

```
Consumer Application
    (identity, lists, optimization, results)
         │
         ▼
Product Intelligence · Cost Intelligence · Cart Optimization
    (matching · effective-cost · ranking)
         │
         ▼
PostgreSQL + Redis + Workers + Observability
    (state · rate-limiting · jobs · metrics)
```

Each component follows an **architecture-first development process:** contracts and design are completed before implementation, enabling multiple efforts to progress in parallel.

---

## 🔬 Engineering Highlights

What makes Cartel fundamentally different from typical e-commerce projects:

- **Deterministic architecture** — same inputs always produce same outputs, no hidden state
- **Replayable operations** — every scrape, match, and cost computation can be replayed from stored artifacts
- **Immutable contracts** — every layer defines its input/output contract as immutable value objects
- **Audit-first design** — operations are designed to be logged, checksummed, and reproducible
- **Contract-first development** — architecture RFCs define contracts before implementation
- **Evidence-backed decisions** — every product match links back to source data that justified it

---

## 🧭 Engineering Process

Every major subsystem follows the same development lifecycle:

Research → RFC → Contract Freeze → Implementation → Validation

Architecture decisions are documented and reviewed before production code is written, allowing implementation to proceed against stable, deterministic contracts.

---

## 🧱 Current Runtime Architecture

```
Browser → Frontend (Next.js)
    ↓
API Replicas (FastAPI)
    ↓
PostgreSQL (state, identity, lists, jobs, outbox)
Redis (ephemeral rate-limit state)
    ↓
Worker Service(s)
    → PostgreSQL jobs/outbox
    → Email/Acquisition
```

PostgreSQL is authoritative application state. Redis is intentionally ephemeral rate-limit state, lost across complete restarts. Filesystem-backed evidence and canonical catalog artifacts remain isolated from consumer runtime state.

---

## 📥 Real Data Ingestion

Raw data acquisition: scraped, validated, stored, and made deterministically replayable.

### 🚧 Data Acquisition — Active Integration

- Provider-neutral retailer acquisition boundary implemented
- QuickCommerce-backed Blinkit search integration implemented
- Durable asynchronous scrape-job execution implemented
- PostgreSQL-backed job state with lease/retry/recovery semantics implemented
- Existing filesystem-backed evidence/artifact lifecycle preserved
- Canonical catalog admission remains independent from retailer observations

**Implementation Status**
- Filesystem-backed lifecycle, storage, observation registration, catalog, planning, checkout-capture, and deterministic replay boundaries are implemented for the current MVP.
- QuickCommerce-backed Blinkit acquisition is integrated through the retailer-data provider boundary; direct Blinkit access remains constrained by retailer access control, and live checkout/cart evidence remains unavailable.
- BigBasket and Zepto remain incomplete.

---

## 🔬 Product Intelligence Pipeline

Match products deterministically across platforms using evidence-backed reasoning.

```
Retailer Observation
      │
      ▼
Normalized Ingestion
      │
      ▼
Evidence Registry
      │
      ▼
Canonical Catalog
      │
      ▼
Candidate Generation
      │
      ▼
Product Matching
      │
      ▼
Variant Matching
      │
      ├── unresolved / ambiguous ──► Review Queue
      │
      ▼
Assertion Manager
      │
      ▼
Product Intelligence Execution
      │
      ▼
Cost Intelligence
```

> The current Compose topology has been runtime-validated locally with PostgreSQL, Redis, API, frontend, and worker services, including database migrations, authenticated browser E2E, two API replicas, distributed rate limiting, background-job execution, and email outbox behavior. Public-host DNS/TLS/firewall/secret-manager configuration and production-host backup/restore remain unverified.

The system processes retailer observations through acquisition, normalization, evidence registration, governed canonical resolution, and Product Intelligence execution. Consumer-facing product eligibility remains strictly gated by canonical identity and admissible evidence.

### 🚧 Product Intelligence Foundation — Active Development

- Canonical product schema + domain models
- Matching architecture + governance contracts
- Deterministic matching framework
- Canonical catalog boundary and governance contracts
- Filesystem-backed catalog persistence and deterministic snapshot construction

### ✅ Product Intelligence — MVP Implemented

- Evidence Registry
- Deterministic Candidate Generation
- Deterministic Product Matching
- Deterministic Variant Matching
- Deterministic Review Queue
- Deterministic Assertion Manager
- Product Intelligence execution trigger
- Canonical catalog persistence and deterministic snapshot construction
- End-to-end Product Intelligence execution path — implemented and tested
- Audit trails & deterministic replay
- Canonical assertion pipeline

Every stage consumes immutable governed inputs and produces deterministic, replayable outputs with a complete audit trail.

### ✅ Canonical Catalog — MVP Implemented

- Governed canonical Product and ProductVariant identity
- Manually curated canonical catalog
- Stable externally assigned canonical IDs
- Filesystem-backed catalog persistence
- Product/Variant listing association
- Deterministic CandidateCatalogSnapshot construction
- Fail-closed duplicate and conflict handling
- Approved, active, parent-consistent entities only

Product Intelligence resolves observations against an externally-curated canonical catalog. Matching and candidate generation do not create canonical Product or ProductVariant entities.

Canonical identity is governed separately from platform identity. Platform identifiers, observation IDs, timestamps, and runtime metadata do not define canonical Product or ProductVariant identity.

The MVP includes a governed filesystem-backed canonical catalog and observation path with deterministic resolution, snapshot construction, catalog population tooling, and candidate discovery, while consumer identity, shopping lists, optimization records, idempotency, background jobs, and email outbox state are PostgreSQL-backed.

PostgreSQL now backs consumer identity, sessions, verification challenges, audit events, user-owned shopping lists, optimization records, idempotency records, background jobs, and email outbox events; canonical catalog and observation persistence remain filesystem-backed.

### ✅ Execution Lifecycle — Runtime Foundation

- Durable asynchronous job records
- Transactionally exclusive worker claiming
- Lease and stale-job recovery
- Bounded exponential retry with jitter
- PostgreSQL-backed idempotency
- Structured request/job/outbox telemetry
- Dedicated worker Compose service

Remaining lifecycle hardening is now primarily deployment/operations work rather than absence of a job execution mechanism.

The scrape API is wired into the ingestion and Product Intelligence runtime path, with durable PostgreSQL-backed asynchronous scrape jobs and filesystem-backed ingestion/catalog artifacts.

Product Intelligence execution is implemented and tested. Lifecycle terminal-state ownership remains an application hardening concern; public-host deployment and recovery are not verified by local Compose validation.

---

## 💰 Cost Intelligence Pipeline

Evaluate what a cart will actually cost: price, fees, offers, memberships, rewards.

```
Checkout Observation
        │
        ▼
Cost Context
        │
        ▼
Offer Evaluation
        │
        ▼
Fee Evaluation
        │
        ▼
Membership Evaluation
        │
        ▼
Effective Cost Computation
        │
        ▼
Cart Optimization Input
```

**Completed:**
- Checkout Observation, Cost Context, Offer Evaluation
- Offer Evaluation Orchestrator
- Deterministic result models

**Implemented:**
- Fee Evaluation
- Membership Evaluation
- Effective Cost Computation

---

## 🛍️ Cart Optimization Pipeline

Recommend the cheapest full cart, including cross-platform splits.

```
Input: Grocery list + platform state
         │
         ▼
Enumerate Options
(single platform vs multi-platform splits)
         │
         ▼
Rank by Effective Cost
         │
         ▼
Apply Constraints
(membership, loyalty, minimums)
         │
         ▼
Generate Recommendation
         │
         ▼
Audit Trail & Replay Reference
```

**Completed:**
- RFC and architecture design
- Immutable request and result contracts
- Identity builders
- Request builder
- Service layer
- Orchestrator

**Implemented:**
- Optimization engine for the currently supported deterministic planning path
- Multi-platform recommendation logic remains limited by retailer availability and checkout evidence

---

## 👤 Consumer Application

The authenticated consumer web application provides:

- **Signup & Verification** — email verification with secure links and rate limiting
- **Login & Sessions** — password-based Argon2id hashing with server-managed sessions
- **OAuth Provider Discovery** — Google and GitHub sign-in with secure state/nonce/PKCE
- **Shopping Lists** — persistent user-owned lists with exact-product selection
- **Optimization** — submit cart to get platform-specific recommendations
- **Results Display** — show effective costs and cross-platform splits
- **Profile & Settings** — account management and provider linking
- **Logout** — secure session termination

Authenticated E2E validation covers signup → verification → login → protected-route flows.

---

## ⚙️ Production Foundations

Implemented runtime infrastructure:

- **PostgreSQL Connection Pooling** — efficient database resource management
- **Request IDs & Correlation** — distributed tracing across services
- **Structured Logging** — JSON logs with context at INFO/DEBUG levels
- **Distributed Rate Limiting** — Redis-backed limits validated across multiple API replicas
- **Idempotency** — PostgreSQL-backed request deduplication
- **Durable Background Jobs** — leased, retried, recovered, at-least-once semantics
- **Email Outbox** — transactional delivery with retry and recovery
- **Health & Readiness** — liveness probes and startup readiness checks
- **Prometheus Metrics** — protected endpoint for operational observability
- **Local Authenticated E2E** — disposable Compose validation with real browser automation

---

## 🔐 Security Model

- **Password Storage** — Argon2id hashing with industry-standard parameters
- **Sessions** — server-managed, opaque tokens in secure httpOnly cookies
- **CSRF Protection** — same-origin POST/PUT/PATCH enforcement
- **OAuth Flow** — state/nonce/PKCE with provider discovery
- **Token Handling** — no provider tokens persisted in browser; server-to-server only
- **Secrets Management** — environment-injected, never in Git or logs
- **Rate Limiting** — fail-closed, distributed across replicas
- **Authenticated Metrics** — protected Prometheus endpoint, not public

---

## 🧪 Validation

**Repository Validation**
- Backend suite: 700+ passing tests
- Frontend lint, typecheck, and build
- Docker Compose health checks

**Runtime Validation**
- Authenticated browser E2E (signup, verify, login, protected routes)
- Two-API-replica rate-limit validation
- Background-job lease/recovery validation
- Email-outbox delivery/retry validation
- Consumer list and optimization E2E

---

## 🚧 Current Blockers

**Canonical Evidence** — durable independent manufacturer/barcode evidence is required before canonical Products/Variants can be populated without promoting retailer observations into canonical identity.

**Retailer Checkout Evidence** — legitimate checkout/cart evidence remains constrained by retailer access boundaries and is essential for live checkout-backed recommendations.

---

## ⚠️ Current Limitations

- Independent canonical manufacturer/barcode evidence for the next governed SKU has not yet been imported.
- Canonical Product/Variant creation remains governed and fail-closed; retailer observations cannot establish canonical identity by themselves.
- Canonical catalog and observation persistence remain filesystem-backed while consumer/application state is PostgreSQL-backed.
- QuickCommerce-backed acquisition is available, but retailer checkout/cart evidence remains constrained by retailer access boundaries.
- Populated Search → List → Optimize → Results cannot be demonstrated honestly without admissible governed retailer records.
- Metrics are currently process-local and require external scraping/aggregation for multi-instance production observability.
- Rate-limit state is ephemeral in Redis and is intentionally lost across a complete Redis restart.
- Background jobs and email delivery use at-least-once semantics; exactly-once external side effects are not claimed.
- Public DNS/TLS/firewall, production secret-manager integration, production dashboards/alerting, host-level backup/restore drills, and regional disaster recovery remain deployment-stage work.

---

## Production Deployment Handoff

The commands in this section describe the historical frozen `v0.1.0-deploy.1` single-instance deployment only. They do not deploy the current PostgreSQL/Redis/worker/OAuth/consumer-runtime working tree. Current development and validation use the updated Compose topology documented separately below.

### Frozen Release Deployment Prerequisites

This section applies only to `v0.1.0-deploy.1`. Current production deployment must use the updated PostgreSQL/Redis/worker/OAuth/consumer architecture and therefore needs a new deployment runbook before the current branch is presented as production-deployable.

### Local Development and Validation

The supported full-stack path is Docker Compose. Host-side Next.js development is intentionally separate because `api:8000` is a Compose-only hostname.

```bash
docker compose up --build
```

For disposable authenticated browser validation, use the dedicated local-test Compose override documented in `docs/local_authenticated_e2e.md`.

Do not use `docker compose down -v` for routine operations because it deletes persistent volumes.

### Demo Scripts

Run the product intelligence pipeline against real Blinkit data (no API keys needed):

```bash
python scripts/demo_evidence_registry.py
python scripts/demo_candidate_generation.py
python scripts/demo_product_matching.py
```

### Tests

Run from the repository root (if you're still inside `backend/` from local setup, `cd ..` first):

```bash
pytest backend/tests/ -v
```

---

## 📸 Demos & Screenshots

### Consumer Application

Add authenticated screenshots of Home, Search, Lists, Cart, Optimize, Results, Profile, and Settings once governed retailer records allow the populated journey to be demonstrated without synthetic data.

### Runtime Validation

Document representative Compose validation, authenticated browser E2E, two-API-replica rate-limit validation, background-job recovery, and email-outbox delivery/retry validation.

### Current Verification Targets

- Live/provider-backed retailer acquisition ✅
- Deterministic product matching ✅
- Canonical catalog governance ✅
- Authenticated consumer web interface ✅
- Signup → verification → login → protected-route E2E ✅
- Distributed rate-limit validation across two API replicas ✅
- Durable background-job validation ✅
- Email outbox retry/recovery validation ✅
- Live checkout-derived effective-cost computation 🚧 retailer/cart evidence blocked
- Populated consumer Search → List → Optimize → Results 🚧 requires governed retailer records

---

## 📡 API

The API is now split between legacy/operator-oriented v1 surfaces and authenticated consumer v2 surfaces.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Lightweight liveness |
| `GET` | `/ready` | Runtime readiness |
| `GET` | `/api/v1/health` | API health |
| `GET` | `/api/v1/metrics` | Protected Prometheus-compatible metrics |
| `POST` | `/api/v1/scrape/async` | Durable asynchronous scrape-job submission |
| `GET` | `/api/v2/auth/providers` | Available social-auth providers |
| `POST` | `/api/v2/auth/*` | Consumer authentication flows |
| `GET` | `/api/v2/me` | Authenticated consumer identity/session state |
| `GET` | `/api/v2/products/search` | Governed consumer product search |
| `...` | `/api/v2/lists/*` | User-owned shopping lists and requested items |
| `...` | `/api/v2/optimizations/*` | Persisted consumer optimization requests/results |

Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs` only for a locally run backend when `DOCS_ENABLED=true`; it is disabled in the production Compose configuration, whose backend port is private.

The current consumer application exposes authenticated identity, governed product search, persistent shopping lists, persisted optimization requests/results, asynchronous scrape operations, distributed rate limiting, durable jobs, transactional email delivery, and protected operational metrics. Live retailer checkout-backed consumer results remain constrained by retailer evidence availability.

---

## 📁 Repository Structure

```
Cartel-Smart-Cart-Optimizer/
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI routes: health, scrape, consumer v2 APIs
│   │   ├── auth/                # Password, email verification, OAuth, delivery
│   │   ├── core/                # Config, logging, rate limiting, metrics, security
│   │   ├── db/                  # PostgreSQL models, sessions, migrations
│   │   ├── data_ingestion/      # Acquisition/evidence contracts and observation registry
│   │   ├── product_intelligence/# Canonical catalog, evidence, matching, review
│   │   ├── cart_optimization/   # Optimization contracts and orchestration
│   │   ├── retailer_data/       # Provider-neutral retailer acquisition boundary
│   │   ├── scrapers/            # Retailer acquisition implementations
│   │   ├── services/            # Consumer/search/idempotency/domain services
│   │   └── workers/             # Background jobs, ingestion, email outbox
│   ├── tests/
│   └── requirements/
├── frontend/
│   ├── app/                     # Consumer routes and auth surfaces
│   ├── components/              # Brand, consumer, auth, layout primitives
│   ├── services/                # Consumer API services
│   └── lib/                     # API client and consumer copy/error translation
├── data/                        # Filesystem-backed evidence/catalog artifacts
├── docs/                        # Architecture, governance, runtime, E2E documentation
├── scripts/                     # Operator/evidence/catalog tooling
└── docker-compose*.yml          # Local/validation Compose topologies
```

---

## 📈 Project Metrics

- **40+** architecture and governance specifications
- **Authenticated consumer web application** with persistent identity, lists, optimization records, and protected routes
- **OAuth/OIDC foundation** for Google and GitHub with secure account-linking boundaries; Apple remains intentionally disabled pending verifier implementation
- **PostgreSQL-backed runtime state** for consumer identity, lists, optimization, idempotency, jobs, and email outbox
- **Redis-backed distributed rate limiting** validated across multiple API replicas
- **Durable background jobs** with leases, retries, recovery, and at-least-once semantics
- **Transactional email outbox** with retry and recovery semantics
- **Prometheus-compatible operational metrics** plus structured request/job/outbox logging
- **Deterministic Product Intelligence** across evidence, canonical catalog, candidate generation, matching, review, and assertion
- **Current major product blocker:** durable independent canonical evidence and live retailer checkout evidence
- Backend suite: 700+ passing tests
- Local authenticated E2E validation included

---

## 📚 Documentation

**Architecture & Product:**
- `CARTEL_CONSUMER_PRODUCT_ARCHITECTURE_v1.0.md` — current consumer product source of truth
- `CARTEL_SHIPPING_STRATEGY_v1.0.md` — shipping/deployment strategy
- `docs/product_intelligence_design.md` — Product Intelligence design
- `docs/cart_optimization_contract.md` — Cart Optimization architecture and contracts

**Canonical Data & Evidence:**
- `docs/canonical_product_identity_matching.md` — governed canonical identity and exact-match rules
- `docs/canonical_source_provider_contract.md` — future independent canonical-source provider boundary
- `docs/consumer_product_evidence_ingestion.md` — operator evidence ingestion
- `docs/retailer_data_provider_architecture.md` — provider-neutral retailer acquisition boundary

**Consumer & Identity:**
- `docs/consumer_list_optimization.md` — consumer list/optimization behavior
- `docs/consumer_oauth_identity.md` — OAuth identity architecture and account linking
- `docs/local_authenticated_e2e.md` — disposable authenticated Compose/browser validation

**Runtime & Operations:**
- `docs/runtime_rate_limiting.md` — distributed Redis rate limiting
- `docs/background_jobs.md` — durable PostgreSQL background jobs
- `docs/observability.md` — logs, metrics, request correlation, and runtime telemetry

The `docs/` directory contains **40+ architecture and governance specifications** covering Product Intelligence, Cost Intelligence, and Cart Optimization systems.

---

## 🤯 Why This Problem Is Harder Than It Looks

Comparing grocery prices seems simple: `price1 < price2`. It's not.

**The Variables:**
- **Thresholds & Minimums** — Platforms apply different free-delivery thresholds, so the same cart subtotal can produce different effective costs depending on which platform's threshold it crosses.
- **Offer Stacking** — "₹100 off cart >₹1000 + 10% cashback" (excludes some categories, expires after 3 uses). Eligibility depends on cart composition, user history, and time.
- **Membership Pricing** — Paid membership tiers reduce prices on some items and not others, so effective cost must account for membership fees amortized across purchases.
- **Split Carts** — Splitting a purchase across two platforms can be cheaper than buying everything from one, because different platforms cross fee thresholds at different subtotals.
- **Location Pricing** — The same product can be priced differently across delivery zones, so location affects effective cost even for identical carts.

**Why Determinism Matters:**
With this many variables interacting, approximation is useless. You need reproducible results, auditable decisions, and testable logic. That's what Cartel delivers.

---

## 👥 Who Cartel Is For

**End users** — anyone buying groceries across Blinkit, Zepto, Instamart, or BigBasket who wants the actual cheapest option before checkout.

**Developers** — engineers interested in deterministic matching systems, scrapers, immutable pipelines, or quick-commerce infrastructure.

**Researchers** — anyone studying quick-commerce pricing, platform economics, or behavioral pricing in Indian e-commerce.

**Teams building similar systems** — this architecture is designed to be forkable and extensible.

---

## 🎯 Current Focus

**Canonical Evidence** — establish durable independent manufacturer/barcode evidence so governed canonical Products/Variants can be populated without promoting retailer observations into canonical identity.

**Consumer Product Journey** — complete the real Search → exact selection → List → Optimize → Results path once admissible governed retailer records are available.

**Retailer Integration** — continue provider-backed retailer acquisition and pursue legitimate checkout/cart evidence where retailer access permits it.

**Production Runtime** — continue deployment-safe rollout, backup/restore verification, HA/DR, external metrics/log aggregation, and operational alerting as the product moves toward production.

---

## 🗺 Roadmap

| Phase | Focus | Status |
|---|---|---|
| 1 | Real Data Ingestion Architecture & RFC | ✅ Complete |
| 2 | Product Intelligence Foundation | ✅ Complete |
| 3 | Product Intelligence Implementation | ✅ Complete |
| 4 | Cost Intelligence Foundation | ✅ Complete |
| 5 | Cost Intelligence Evaluation | ✅ Complete |
| 6 | Effective Cost & Cart Optimization | ✅ Complete for supported deterministic paths |
| 7 | Canonical Evidence + Catalog Population | 🚧 Current blocker/active |
| 8 | Consumer Identity + Web Application | ✅ Implemented |
| 9 | Distributed Runtime Foundations | ✅ Implemented: PostgreSQL pooling, Redis rate limiting, idempotency, durable jobs, email outbox, observability |
| 10 | Real Retailer Checkout / Order Orchestration | 🚧 Active, retailer-dependent |
| 11 | Production Deployment / HA / DR | 🚧 Next infrastructure phase |
| 12 | Scale-driven architecture evolution | ⏳ Adopt only when measured workload requires it |

---

## 🤝 Contributing

Cartel is in active development with a growing consumer application and production-runtime foundation. Contributions should preserve the existing governance, evidence, determinism, security, and operational contracts.

**Before contributing:**
- Read the relevant RFC in `docs/` — architecture comes first, implementation second
- Open an issue for large PRs to discuss design
- Tests are required — PRs that reduce coverage don't merge

**Best entry points:**

| Area | What's Needed |
|---|---|
| 🧾 **Canonical data** | Independent manufacturer/barcode evidence and governed catalog population |
| 🛍️ **Retailer integrations** | Legitimate provider-backed acquisition and checkout/cart evidence |
| 🌐 **Consumer web** | Browser acceptance coverage and populated journey validation |
| ⚙️ **Runtime** | Deployment, backup/restore, HA, DR, and operational tooling |
| 🧪 **Tests** | Browser acceptance, failure injection, retailer regression, migration/recovery tests |
| 📚 **Docs** | Current consumer, runtime, provider, and operational guides |

---

## 💡 Vision

> *"What is the cheapest verifiable way to buy my entire grocery cart right now?"*

Across platforms, locations, offers, memberships, delivery constraints, and checkout state — with exact product identity, explicit evidence provenance, deterministic optimization, and honest handling of anything that cannot currently be verified.

Cartel is being built as both a consumer product and a serious data/decision system: the user experience should feel simple, while the machinery underneath remains auditable, reproducible, secure, and resilient.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

Created and maintained by [@neural-agi](https://github.com/neural-agi)

[![GitHub stars](https://img.shields.io/github/stars/neural-agi/Cartel-Smart-Cart-Optimizer?style=social)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)
[![GitHub forks](https://img.shields.io/github/forks/neural-agi/Cartel-Smart-Cart-Optimizer?style=social)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/fork)
[![GitHub watchers](https://img.shields.io/github/watchers/neural-agi/Cartel-Smart-Cart-Optimizer?style=social)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)

</div>
