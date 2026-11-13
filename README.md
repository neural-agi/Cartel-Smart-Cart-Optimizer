<div align="center">

# 🛒 Cartel

### Evidence-backed grocery product intelligence and cart optimization

**Product Identity · Retailer Evidence · Cost Intelligence · Shopping Lists**

[![Build](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/status-active%20development-yellow?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)

Cartel is being built to answer a practical question: **what is the cheapest trustworthy way to fulfil a grocery list right now?** It combines governed product identity, retailer observations, persistent shopping lists, and deterministic planning. It deliberately distinguishes an observed listing price from a verified checkout total.

[Why Cartel](#-why-cartel) · [Current capabilities](#-current-capabilities) · [Architecture](#️-architecture) · [Quick start](#-quick-start) · [API](#-consumer-api) · [Roadmap](#️-roadmap)

</div>

---

## 🧭 Why Cartel

Comparing the price printed beside one product is not the same as comparing the cost of a complete grocery basket. The final amount may depend on availability, delivery and handling fees, minimum-order thresholds, promotions, membership eligibility, and checkout-specific rules. Products that look similar may also differ in brand, pack size, or other identity-critical attributes.

Cartel is designed around three rules:

- **Compare the same product.** Product identity must be established from governed evidence, not a fuzzy title match alone.
- **Optimize the whole list.** Item prices are inputs to planning, not proof of the final amount payable.
- **Make uncertainty visible.** Missing, stale, ambiguous, or unsupported evidence stays unresolved instead of being silently converted into a confident-looking answer.

The long-term goal is cross-retailer basket optimization. The current implementation is an active-development consumer application and data platform, not yet a fully automated grocery checkout service.

## ✨ Current capabilities

| Area | Current state |
|---|---|
| Consumer accounts | Email/password authentication, email verification and recovery flows, server-managed sessions, CSRF protection, session revocation, and configured Google/GitHub sign-in flows |
| Shopping lists | Persistent, owner-scoped lists and items, quantity changes, item removal, and list lifecycle operations |
| Product search | Searches the governed catalog and returns products/variants with supporting retailer evidence where the active consumer policy permits selection |
| Product identity | Explicit `EXACT_MATCH`, `MISMATCH`, and `UNRESOLVED` outcomes; ambiguous or incomplete evidence does not become an exact association |
| Retailer acquisition | Provider boundary and acquisition-to-observation ingestion path. Provider use requires explicit configuration and permitted access; Blinkit consumer search remains disabled by commercial policy |
| Optimization | Persisted optimization requests, plans, and allocations using the deterministic planner; unsupported checkout totals remain unresolved/unavailable |
| Mutation safety | PostgreSQL-backed idempotency for supported consumer mutations, with replay and payload-conflict handling |
| Runtime | FastAPI, PostgreSQL-backed application state, Redis-backed production rate limiting, durable background jobs, and email outbox processing |
| Auditability | Evidence provenance, durable records for consumer operations, and deterministic ingestion/review boundaries |

These capabilities are not all equivalent to end-to-end production readiness. The current app does not yet have a verified live retailer checkout and confirmed-order flow, and the canonical catalog still requires governed admission and review.

### Retailer commercial policy

Blinkit consumer search is disabled by commercial policy: the consumer eligibility check for Blinkit returns `False`. Operator acquisition, review, and import tooling remains available for governed evidence capture, but it does not make Blinkit listings consumer-searchable. No Blinkit access, browser readiness, TLS termination, or hosted deployment readiness is claimed by this repository.

## ⚖️ What Cartel does not claim yet

Cartel does **not** currently guarantee a live, final payable total for every retailer or grocery list.

- A listing price is not a checkout quote. Fees, discounts, membership rules, and other checkout-dependent amounts must be backed by appropriate evidence before they can be treated as verified.
- A provider response does not automatically create a canonical product or an exact product match. Evidence must pass normalization, identity resolution, and governance rules.
- Retailer cart creation, checkout preparation, payment handoff, confirmed ordering, and tracking are not yet available as a complete multi-retailer consumer flow.
- Blinkit checkout access/evidence remains a blocker for verified live checkout-derived effective cost. Other retailer integrations are also incomplete.
- Apple and phone/OTP sign-in are not currently supported as complete consumer authentication flows. Apple provider configuration is not the same as an implemented Apple sign-in integration.
- Canonical catalog and retailer-evidence artifact boundaries still use filesystem-backed persistence in the current MVP. PostgreSQL is the source of truth for mutable consumer application records; this does not mean every product-intelligence artifact has moved to PostgreSQL.
- The Compose topology and public deployment path have not been validated on a production host. DNS, TLS certificates, reverse-proxy policy, firewall rules, secret delivery, backup integrity, and restore procedures remain deployment-owner responsibilities.

When evidence is missing, Cartel should return an unresolved or unavailable result rather than inventing savings, fees, stock, or a total.

---

## 🏛️ Core engineering principles

- **Deterministic decisions:** identical governed inputs and policy context should produce reproducible results.
- **Evidence-backed identity:** every retailer association must be supported by attributable evidence and the canonical identity rules.
- **Fail-closed validation:** malformed, conflicting, stale, or ambiguous evidence is not silently accepted.
- **Explicit cost semantics:** listing subtotals, provisional estimates, and checkout-backed payable costs are different concepts.
- **Idempotent mutations:** retries of supported operations must not create duplicate consumer records or repeat mutations.
- **Transactional state:** related consumer state changes and email-outbox events are persisted within database transactions where designed.
- **Durable background work:** asynchronous jobs use persistent records, leases, bounded retries, and at-least-once processing semantics.
- **Governed catalog admission:** retailer IDs and observations do not define canonical Product or ProductVariant identity.
- **User-controlled payment:** Cartel does not store card numbers, CVVs, UPI PINs, payment OTPs, or reusable payment credentials.

## 🏗️ Architecture

```text
Consumer Web App
      │
      ▼
Next.js frontend / same-origin API proxy
      │
      ▼
FastAPI application
      ├── Consumer authentication and sessions
      ├── Shopping lists and product search
      ├── Optimization requests and planning
      ├── Retailer/provider boundaries
      └── Health, readiness, and operator APIs
      │
      ├──────────────► PostgreSQL
      │                 Users, sessions, lists, optimization records,
      │                 idempotency, durable jobs, and email outbox
      │
      ├──────────────► Redis
      │                 Shared production rate limiting
      │
      ├──────────────► Worker process
      │                 Background jobs and email delivery
      │
      └──────────────► Governed evidence/artifact boundaries
                        Raw retailer artifacts, observations,
                        canonical catalog and review workflows
```

### Main layers

1. **Retailer data acquisition** captures provider responses and records acquisition context and provenance.
2. **Normalization and observation registration** converts provider data into typed observations while preserving source evidence.
3. **Canonical product intelligence** compares observations with governed Product and ProductVariant identities. Unresolved cases remain unresolved for review.
4. **Consumer shopping** persists lists and selections, validating that selected mappings remain admissible.
5. **Cost intelligence and planning** evaluates supported evidence and creates deterministic plans. It does not treat listing prices as checkout totals.
6. **Runtime foundations** provide sessions, database transactions, idempotency, distributed rate limiting, durable jobs, email delivery, health checks, and structured logs.

### Persistence boundaries

| Store | Responsibility |
|---|---|
| PostgreSQL | Authoritative mutable consumer and runtime records, including identity/session data, shopping lists, optimization records, idempotency, background jobs, and email-outbox events |
| Redis | Shared rate-limit state; not the source of truth for user or business records |
| Filesystem/artifact storage | Current MVP persistence for governed catalog/evidence and related immutable or replayable artifacts |

The architecture intentionally avoids treating one persistence mechanism as authoritative for every data domain before those boundaries have been migrated and validated.

## 🔎 Product identity and evidence flow

```text
Provider Acquisition
        │
        ▼
Immutable Raw Artifact + Provenance
        │
        ▼
Parse and Normalize
        │
        ▼
Retailer Observation Registry
        │
        ▼
Canonical Product / Variant Resolution
        │
        ├── EXACT_MATCH ──► governed listing association
        ├── MISMATCH ─────► reject association
        └── UNRESOLVED ───► review / more evidence required
                                  │
                                  ▼
                       Consumer-selectable catalog
                       only when current rules permit
```

Identity resolution considers the governed, identity-critical attributes and complete pack identity. Price, availability, capture age, and a retailer product ID do not prove that two records describe the same product. Canonical IDs are stable identifiers assigned through the governed catalog process; they are not derived from retailer IDs.

The acquisition pipeline preserves provenance and supports deterministic replay. A successful provider response alone does not mean that the item has been admitted to the canonical catalog or is selectable by a consumer. Retailer eligibility is evaluated separately, and Blinkit consumer search is currently disabled by commercial policy.

## 🧭 Engineering process

Every major subsystem follows the same development lifecycle:

Research → RFC → Contract Freeze → Implementation → Validation

Architecture decisions are documented and reviewed before production code is written, allowing implementation to proceed against stable, deterministic contracts.

## 📥 Real data ingestion

Raw data acquisition: captured, validated, stored, and made deterministically replayable.

```text
Scrape Jobs
    │
    ▼
Capture Context
    │
    ▼
Raw Artifacts
    │
    ▼
Validation & Normalization
    │
    ▼
Deterministic Storage
    │
    ▼
Replay & Audit Trail
```

### 🚧 Data acquisition — active integration

- RFC: Data Ingestion Architecture
- Lifecycle contracts: job scheduling, context capture, artifact storage
- Deterministic serialization contracts and identity builders
- Filesystem-backed observation, artifact, catalog, association, and planning-record persistence is implemented for the current MVP boundaries.
- Deterministic replay and serialization are implemented across ingestion, catalog, planning, checkout fixtures, and optimization boundaries.
- Durable scrape-job lifecycle persistence
- Append-only lifecycle transition history
- Observation registration and downstream Product Intelligence handoff

**Implementation status**

- Filesystem-backed lifecycle, storage, observation registration, catalog, planning, checkout-capture, and deterministic replay boundaries are implemented for the current MVP.
- Retailer acquisition requires explicit provider configuration and permitted access. Blinkit consumer search remains disabled by commercial policy, and live checkout capture remains unavailable.
- BigBasket and Zepto remain incomplete.

## 🔬 Product Intelligence Pipeline

Match products deterministically across platforms using evidence-backed reasoning.

```text
Scrape / Ingestion
      │
      ▼
Normalized Observation
      │
      ▼
Evidence Publication
      │
      ▼
Canonical Catalog
      │
      ▼
Candidate Catalog Snapshot
      │
      ▼
Evidence Registry
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

> The frozen `v0.1.0-deploy.1` Compose topology was validated locally. This working tree adds PostgreSQL-backed consumer identity, shopping lists, optimization records, and credential-vault migrations, and changes the Compose services/volumes; that updated topology has not been runtime-validated on a production host. Public-host DNS/TLS/proxy/firewall/secret delivery, backup integrity and restore testing, public-origin reachability, and live Blinkit checkout remain unverified or unavailable.

The system processes retail observations through ingestion, normalization, observation registration, canonical catalog resolution, and Product Intelligence execution. The current executable pipeline continues from normalized observations into canonical Product/ProductVariant resolution and Product Intelligence execution. Canonical catalog persistence and lifecycle governance are filesystem-backed MVP infrastructure.

### 🚧 Product Intelligence Foundation — active development

- Canonical product schema + domain models
- Matching architecture + governance contracts
- Deterministic matching framework
- Canonical catalog boundary and governance contracts
- Filesystem-backed catalog persistence and deterministic snapshot construction

### ✅ Product Intelligence — MVP implemented

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

### ✅ Canonical Catalog — MVP implemented

- Governed canonical Product and ProductVariant identity
- Manually curated canonical catalog
- Stable externally assigned canonical IDs
- Filesystem-backed catalog persistence
- Product/Variant listing association
- Deterministic CandidateCatalogSnapshot construction
- Fail-closed duplicate and conflict handling
- Approved, active, parent-consistent entities only

Product Intelligence resolves observations against an externally/curated canonical catalog. Matching and candidate generation do not create canonical Product or ProductVariant entities.

Canonical identity is governed separately from platform identity. Platform identifiers, observation IDs, timestamps, and runtime metadata do not define canonical Product or ProductVariant identity.

The MVP includes a filesystem-backed authoritative catalog path with deterministic canonical resolution, snapshot construction, catalog population tooling, and candidate discovery.

The canonical catalog and observation stores remain filesystem-backed. PostgreSQL backs the consumer identity, shopping-list, optimization, idempotency, background-job, and email-outbox slices; catalog persistence has not yet migrated.

### 🚧 Execution lifecycle — production hardening

- Deterministic ScrapeJob identity
- Durable ScrapeAttempt records
- Append-only lifecycle transition history
- Filesystem-backed lifecycle state projection
- Retry and attempt identity contracts

The implementation persists acquisition and parsing lifecycle transitions. Lifecycle terminal-state ownership remains a separate hardening area; this does not negate the locally validated single-instance Compose deployment.

Retry semantics are contractually defined, including a maximum of three attempts and retryable failure categories. Filesystem persistence is used by the runtime; operational backup integrity and restore testing on a deployment host remain unverified.

The scrape API is wired into the ingestion and Product Intelligence runtime path, with filesystem-backed runtime dependencies.

Product Intelligence execution is implemented and tested. Lifecycle terminal-state ownership remains an application hardening concern; public-host deployment and recovery are not verified by local Compose validation.

## 💰 Cost intelligence and optimization

Evaluate what a cart will actually cost: price, fees, offers, memberships, rewards.

```text
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

**Completed**

- Checkout Observation, Cost Context, Offer Evaluation
- Offer Evaluation Orchestrator
- Deterministic result models

**Implemented**

- Fee Evaluation
- Membership Evaluation
- Effective Cost Computation

The planning system evaluates the entire list, including candidate retailer allocations and supported cost constraints. It distinguishes the following evidence levels:

- **Observed listing data:** a captured listing price or availability signal. It may be useful for discovery but is not a checkout quote.
- **Provisional planning result:** a result computed from incomplete or non-checkout-backed evidence. It must be labelled accordingly.
- **Verified immediate payable cost:** a checkout-backed figure based on item subtotal plus mandatory immediate fees/taxes minus immediate discounts, using supported evidence.

Deferred cashback, points, and similar rewards are kept separate from immediate payable cost. Missing fees or checkout evidence are unknown, not zero. The current live checkout evidence boundary prevents Cartel from claiming verified checkout totals for unsupported retailer flows.

## 🛍️ Cart optimization pipeline

Recommend the cheapest full cart, including cross-platform splits.

```text
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

**Completed**

- RFC and architecture design
- Immutable request and result contracts
- Identity builders
- Request builder
- Service layer
- Orchestrator

**Implemented**

- Optimization engine for the currently supported deterministic planning path
- Multi-platform recommendation logic remains limited by retailer availability and checkout evidence

## 🔐 Security and reliability

- Consumer sessions are server-managed and carried in HTTP-only cookies; browser storage is not used as a persistent session-token store.
- Write routes enforce CSRF/same-origin protections where required.
- Passwords are hashed with Argon2id. OAuth flows use state/PKCE and server-side provider validation where configured.
- Operator bearer authentication is separate from consumer-cookie authentication.
- Supported consumer mutations require idempotency keys and replay compatible results; conflicting reuse is rejected.
- PostgreSQL is authoritative for mutable application records. Redis is used for shared production rate limiting.
- Durable jobs use leases and bounded retry/recovery behavior. Email delivery is at-least-once, so exactly-once delivery is not promised.
- Production deployments must supply unique secrets and explicit configuration. Never commit `.env` files, API keys, session secrets, or other credentials.
- Retailer integrations must respect the provider's terms and access controls. Cartel does not rely on CAPTCHA bypass, stealth evasion, or unauthorized checkout access.

---

## 🚀 Quick start

### Recommended: Docker Compose

**Prerequisites:** Docker Desktop with Docker Compose.

```bash
git clone https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer.git
cd Cartel-Smart-Cart-Optimizer

# macOS/Linux
cp .env.example .env

# Windows Command Prompt: use this instead
# copy .env.example .env
```

Edit `.env` before starting. Set a unique `POSTGRES_PASSWORD`, non-empty `AUTH_TOKENS` entries in the documented `user_id=token` format, and a `PUBLIC_ORIGIN` matching the browser-visible origin. For local file-based email, keep `EMAIL_DELIVERY_MODE=file`; for SMTP delivery, also set `SMTP_HOST` and `SMTP_FROM`. Use unique high-entropy secrets; do not copy example values into a deployment. Configure external provider credentials only when you intend to run that provider.

Validate the Compose configuration and start the stack:

```bash
docker compose config
docker compose up --build
```

Apply database migrations explicitly. Migrations are a separate deployment operation and are not run automatically by the API container:

```bash
docker compose run --rm api alembic upgrade head
```

When the stack is running:

| Service | Access |
|---|---|
| Consumer web app | `http://localhost:3000` (bound to `127.0.0.1` by default) |
| API | Internal Compose network only at `http://api:8000`; not host-published |
| Basic health | `docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').status)"` |
| Readiness | `docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/ready').status)"` |

Interactive API documentation is available only when `DOCS_ENABLED=true`; it is disabled by the production Compose configuration. The browser uses the same-origin frontend `/api/*` proxy, so public CORS is normally unnecessary.

Stop the stack with:

```bash
docker compose down
```

The Compose configuration uses PostgreSQL and Redis alongside the API and background worker. PostgreSQL and Redis are not published on host ports by default. Review the current Compose file and [`docs/setup.md`](docs/setup.md) for deployment-specific settings. Persisted volumes may outlive containers; `docker compose down` does not automatically remove persisted data.

### Local backend development

**Prerequisites:** Python 3.12 and reachable PostgreSQL/Redis services configured for the application.

```bash
cd backend
python -m venv .venv

# Windows Command Prompt
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

python -m pip install -r requirements/dev.txt
```

Configure the environment according to [`docs/setup.md`](docs/setup.md), then apply database migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run worker processing through the configured worker service or its documented entry point. A standalone API process does not replace the durable worker for background jobs and email-outbox delivery.

### Run tests

From the repository root:

```bash
python -m compileall -q backend/app backend/tests
pytest backend/tests/ -v
```

Integration tests depend on their configured test services and environment. The project is in active development; do not rely on a README badge or a stale historical test count as a substitute for running the current branch's suite.

---

## 📡 Consumer API

The consumer API is mounted under `/api/v1`. The routes below describe the principal current interfaces; operator and internal planning routes may expose additional endpoints.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Basic process health |
| `GET` | `/ready` | Readiness, including required dependency checks |
| `GET` | `/api/v1/health` | API health check |
| `GET` | `/api/v1/products/search` | Search the governed product catalog |
| `GET` | `/api/v1/lists` | List the current consumer's shopping lists |
| `POST` | `/api/v1/lists` | Create a shopping list |
| `GET` | `/api/v1/lists/{list_id}` | Read an owned list and its items |
| `PATCH` | `/api/v1/lists/{list_id}` | Update list metadata |
| `POST` | `/api/v1/lists/{list_id}/items` | Add an admissible product/variant to a list |
| `PATCH` | `/api/v1/lists/{list_id}/items/{item_id}` | Update item quantity/details |
| `DELETE` | `/api/v1/lists/{list_id}/items/{item_id}` | Remove a list item |
| `POST` | `/api/v1/optimizations` | Create and persist an optimization request/result |
| `GET` | `/api/v1/optimizations/{request_id}` | Read an optimization request owned by the current consumer |

Consumer mutation routes use the server-managed session and applicable CSRF/same-origin protections. Supported mutations require an `Idempotency-Key` header. A repeated key with the same operation and payload replays the stored result; incompatible key reuse is rejected.

The optimization API persists requests, plans, allocations, list revision/context, and evidence snapshots. It does not fabricate checkout totals when the required checkout evidence is absent. For current implementation details, inspect the route schemas and the architecture documents in the repository.

---

## 🗂️ Repository layout

```text
Cartel-Smart-Cart-Optimizer/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI routes, dependencies, and API composition
│   │   ├── auth/                   # Consumer auth, sessions, OAuth, and email delivery
│   │   ├── core/                   # Configuration, security, logging, rate limiting
│   │   ├── db/                     # SQLAlchemy models, sessions, and migrations
│   │   ├── data_ingestion/         # Acquisition and observation contracts
│   │   ├── product_intelligence/   # Catalog, identity, evidence, review, matching
│   │   ├── retailer_data/          # Retailer data-provider contracts and adapters
│   │   ├── cost_intelligence/      # Effective-cost evaluation boundaries
│   │   ├── cart_optimization/      # Planning contracts and optimization services
│   │   └── workers/                # Durable jobs and background processing
│   ├── alembic/                    # Database migrations
│   ├── tests/                      # Unit, integration, and API tests
│   └── requirements/               # Runtime and development dependencies
├── frontend/                       # Consumer web app and API clients
├── docs/                           # Architecture, setup, governance, and research
├── scripts/                        # Evidence ingestion and catalog review utilities
├── data/                           # Local/runtime artifacts where configured
├── docker-compose.yml
├── .env.example
└── LICENSE
```

---

## 📚 Documentation

Use the current consumer product architecture and shipping strategy documents as the primary guides to the application roadmap. The `docs/` directory contains additional implementation, governance, and research material, including:

- [`docs/product_intelligence_design.md`](docs/product_intelligence_design.md) — Product Intelligence design
- [`docs/product_intelligence_pipeline.md`](docs/product_intelligence_pipeline.md) — Pipeline architecture
- [`docs/canonical_product_schema.md`](docs/canonical_product_schema.md) — Canonical product model
- [`docs/product_matching_architecture.md`](docs/product_matching_architecture.md) — Product matching design
- [`docs/variant_matching_architecture.md`](docs/variant_matching_architecture.md) — Variant matching design
- [`docs/product_intelligence_evidence_registry.md`](docs/product_intelligence_evidence_registry.md) — Evidence registry
- [`docs/product_intelligence_candidate_generation.md`](docs/product_intelligence_candidate_generation.md) — Candidate generation
- [`docs/research_analysis.md`](docs/research_analysis.md) — Cross-platform pricing research
- [`docs/architecture/real_data_ingestion_rfc.md`](docs/architecture/real_data_ingestion_rfc.md) — Real data ingestion RFC
- [`docs/architecture/cart_optimization_contract.md`](docs/architecture/cart_optimization_contract.md) — Cart optimization contracts
- [`docs/canonical_source_provider_contract.md`](docs/canonical_source_provider_contract.md) — Canonical source provider contract
- [`docs/consumer_product_evidence_ingestion.md`](docs/consumer_product_evidence_ingestion.md) — Consumer evidence ingestion
- [`docs/background_jobs.md`](docs/background_jobs.md) — Durable jobs and email outbox
- [`docs/setup.md`](docs/setup.md) — Local setup guidance

Documentation paths may evolve as architecture documents are consolidated; the code and current architecture source of truth should be checked when they disagree with older notes.

---

## 🗺️ Roadmap

| Workstream | Current status |
|---|---|
| Consumer account and session foundations | Implemented; ongoing validation and hardening |
| Persistent shopping lists and item mutations | Implemented; integration/regression testing continues |
| Governed product search and exact identity resolution | Implemented; canonical catalog admission remains governed/manual |
| Retailer provider boundary and observation ingestion | Implemented for the current provider path; broader provider coverage remains incomplete |
| Persistent optimization requests/plans/allocations | Implemented; checkout-backed recommendations remain evidence-limited |
| Durable jobs and email outbox | Implemented with at-least-once delivery semantics; operational hardening continues |
| Verified live checkout price and fee capture | Blocked for current retailer flow by missing permitted checkout evidence/access |
| Retailer cart creation/modification and confirmed ordering | Not yet a complete supported consumer flow |
| Order status/tracking across retailers | Not yet complete |
| Additional retailer integrations | Incomplete; each adapter needs permitted acquisition and capability-specific validation |
| Production deployment, monitoring, recovery, and end-to-end validation | Ongoing |

## 🤝 Contributing

Cartel is under active development. Contributions should preserve the product's evidence and safety boundaries.

Before proposing a substantial change:

1. Read the relevant architecture or governance document.
2. Describe the behavior, evidence requirements, failure modes, and migration impact.
3. Add or update tests for success paths, invalid evidence, retries, ownership, and idempotency where applicable.
4. Never weaken exact-match requirements to increase apparent catalog coverage.
5. Never fabricate prices, stock, fees, savings, or checkout evidence.
6. Do not bypass retailer access controls or commit credentials.

Useful areas include additional permitted retailer data adapters, catalog evidence/review tooling, production-grade integration tests, recovery and deployment hardening, and consumer accessibility/usability.

## 🎯 Vision

> **Find the cheapest trustworthy way to fulfil an entire grocery list, without pretending uncertain data is certain.**

Cartel aims to make grocery decisions comparable across products, retailers, locations, fees, offers, and delivery constraints. The path there is governed product identity, accurate checkout evidence, deterministic optimization, and a consumer experience that keeps users in control of final payment authorization.

## 📄 License

MIT — see [`LICENSE`](LICENSE).

<div align="center">

Created and maintained by [@neural-agi](https://github.com/neural-agi)

[![GitHub stars](https://img.shields.io/github/stars/neural-agi/Cartel-Smart-Cart-Optimizer?style=social)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)
[![GitHub forks](https://img.shields.io/github/forks/neural-agi/Cartel-Smart-Cart-Optimizer?style=social)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/fork)
[![GitHub watchers](https://img.shields.io/github/watchers/neural-agi/Cartel-Smart-Cart-Optimizer?style=social)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)

</div>
