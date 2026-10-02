<div align="center">

<br/>

# 🛒 Cartel

### The real cost of groceries, deterministically computed.

**Product Intelligence · Cost Intelligence · Cart Optimization**

<br/>

[![Build](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-release%20validated-informational?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/tree/main/backend/tests)
[![Status](https://img.shields.io/badge/status-active%20development-yellow?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)

<!-- TODO: Add screenshot/GIF of demo pipeline -->
<!-- TODO: Add Codecov badge once coverage reporting is wired -->

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

Cartel is built around principles that mature engineering teams recognize immediately:

- **Deterministic by design** — given identical governed inputs, the system produces identical outputs every time
- **Replayable decisions** — every matching and pricing decision can be reproduced and inspected, not just trusted
- **Evidence-backed reasoning** — every match traces back to the raw source data that justified it
- **Fail-closed validation** — invalid inputs are rejected explicitly rather than silently degraded
- **Immutable audit trails** — decision records are append-only and designed for auditability
- **Explicit governance contracts** — matching rules are declared, versioned, and enforced, not implicit
- **Contract-first architecture** — every component defines its input/output contract before implementation
- **Deterministic identities** — products, carts, and decisions have stable, reproducible identifiers
- **Immutable value objects** — pipelines consume immutable inputs and produce immutable outputs
- **Replay references** — every operation can be replayed given the same inputs and context

---

## 🏗 Layered Architecture

Cartel is structured as four composable layers with explicit boundaries:

```
Layer 4: Cart Optimization
    Recommends cheapest full cart, cross-platform splits
         │
         ▼
Layer 3: Cost Intelligence
    Models fees, offers, memberships into effective cost
         │
         ▼
Layer 2: Product Intelligence
    Matches products deterministically across platforms
         │
         ▼
Layer 1: Real Data Ingestion
    Scrapes, validates, persists raw data with replay capability
```

Each layer follows an **architecture-first development process:** contracts and design are completed before implementation, enabling multiple implementation efforts to progress in parallel.

Solid lines = implemented, integrated, and tested components.
Dashed lines = implemented components or contracts whose end-to-end production integration is still being completed.
Dotted lines = designed or planned components not yet implemented.

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

## 📥 Real Data Ingestion

Raw data acquisition: scraped, validated, stored, and made deterministically replayable.

```
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

### 🚧 Data Acquisition — Active Integration

- RFC: Data Ingestion Architecture
- Lifecycle contracts: Job scheduling, context capture, artifact storage
- Deterministic serialization contracts and identity builders
- Filesystem-backed observation, artifact, catalog, association, and planning-record persistence is implemented for the current MVP boundaries.
- Deterministic replay and serialization are implemented across ingestion, catalog, planning, checkout fixtures, and optimization boundaries.
- Durable scrape-job lifecycle persistence
- Append-only lifecycle transition history
- Observation registration and downstream Product Intelligence handoff

**Implementation Status**
- Filesystem-backed lifecycle, storage, observation registration, catalog, planning, checkout-capture, and deterministic replay boundaries are implemented for the current MVP.
- Live Blinkit acquisition is operational; live checkout capture remains blocked by Blinkit access control/cart evidence.
- BigBasket and Zepto remain incomplete.

---

## 🔬 Product Intelligence Pipeline

Match products deterministically across platforms using evidence-backed reasoning.

```
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

> The frozen `v0.1.0-deploy.1` Compose topology was validated locally. This working tree adds PostgreSQL-backed consumer identity and changes the Compose services/volumes; that updated topology has not been runtime-validated here because the Docker daemon and PostgreSQL service are unavailable. Public-host DNS/TLS/proxy/firewall/secret delivery, backup integrity and restore testing, public-origin reachability, and live Blinkit checkout remain unverified or unavailable.

The system processes scraped retail observations through ingestion, normalization, observation registration, canonical catalog resolution, and Product Intelligence execution. The current executable pipeline continues from normalized observations into canonical Product/ProductVariant resolution and Product Intelligence execution. Canonical catalog persistence and lifecycle governance are filesystem-backed MVP infrastructure.

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

Product Intelligence resolves observations against an externally/curated canonical catalog. Matching and candidate generation do not create canonical Product or ProductVariant entities.

Canonical identity is governed separately from platform identity. Platform identifiers, observation IDs, timestamps, and runtime metadata do not define canonical Product or ProductVariant identity.

The MVP includes a filesystem-backed authoritative catalog path with deterministic canonical resolution, snapshot construction, catalog population tooling, and candidate discovery.

The canonical catalog and observation stores remain filesystem-backed. PostgreSQL now backs the consumer identity slice (users, identities, password credentials, sessions, verification challenges, and audit events); user-owned lists and catalog persistence have not yet migrated.

### 🚧 Execution Lifecycle — Production Hardening

- Deterministic ScrapeJob identity
- Durable ScrapeAttempt records
- Append-only lifecycle transition history
- Filesystem-backed lifecycle state projection
- Retry and attempt identity contracts

The implementation persists acquisition and parsing lifecycle transitions. Lifecycle terminal-state ownership remains a separate hardening area; this does not negate the locally validated single-instance Compose deployment.

Retry semantics are contractually defined, including a maximum of three attempts and retryable failure categories. Filesystem persistence is used by the runtime; operational backup integrity and restore testing on a deployment host remain unverified.

The scrape API is wired into the ingestion and Product Intelligence runtime path, with filesystem-backed runtime dependencies.

Product Intelligence execution is implemented and tested. Lifecycle terminal-state ownership remains an application hardening concern; public-host deployment and recovery are not verified by local Compose validation.

Data Acquisition through the implemented Product Intelligence components, with canonical catalog and lifecycle integration actively under development.

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

## ⚠️ Current Limitations

- Canonical Product and ProductVariant entities are manually curated.
- Canonical IDs are externally assigned stable identifiers.
- The canonical catalog currently uses filesystem-backed persistence.
- Candidate generation operates over the populated canonical catalog snapshot.
- Scrape lifecycle terminal-state ownership remains a hardening area; public-host backup/restore and recovery have not been verified.
- Automatic canonical entity creation from observations is not supported.
- Unresolved or conflicting identity remains unresolved and requires manual resolution.
- Additional live retailer integrations beyond Blinkit remain incomplete.

---

## Production Deployment Handoff

The commands in this section deploy only the frozen `v0.1.0-deploy.1` artifact. The PostgreSQL-backed consumer identity changes in the current working tree are not included in that tag and are not deployable by these commands. This Compose topology is for one Linux host and one application instance. It binds the frontend to `127.0.0.1:3000` by default; the API has no host-published port. Provide DNS, HTTPS, firewall policy, and secrets outside this repository.

### Host prerequisites

- A supported Linux host with Docker Engine and the Docker Compose plugin, enough disk for images and persistent application data, and permission to run Compose.
- A DNS `A` record (and `AAAA` only if IPv6 ingress is configured) for the public hostname pointing to the host. Configure the hostname in the TLS proxy/hosting platform; the app does not provision DNS or certificates.
- A TLS-terminating reverse proxy on the host or hosting platform, with a valid certificate and upstream `http://127.0.0.1:3000`. Preserve the original `Host` and forwarded-protocol headers. Restrict public ingress to HTTPS (and HTTP only when redirecting to HTTPS); do not publish ports 3000 or 8000 publicly. The backend is only reachable on the private Compose network.
- A secret manager or protected deployment environment to inject the operator auth token. Do not put production secrets in Git, image build arguments, command history, or deployment logs.
- A backup destination and procedure for the `cartel-data` volume. Backups must be access-controlled and encrypted. Test restoration before relying on the service.

### Configuration

Required runtime secret for the frozen release:

- `AUTH_TOKENS`: one or more `user_id=high-entropy-token` entries (comma-separated). The frozen release uses these operator-provisioned bearer credentials for the application session. Provision securely and rotate through the deployment environment.

Optional deployment variables:

- `FRONTEND_BIND_ADDRESS`: defaults to `127.0.0.1`, recommended for a reverse proxy on the same host. Only set this to a private interface address when a separate trusted load balancer must connect directly; firewall that interface so the frontend port is not public.
- `BACKEND_INTERNAL_URL`: defaults to `http://api:8000`, the Compose service-to-service route. Change only if the internal topology is intentionally changed.
- `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`: optional API rate limit overrides; defaults are 120 requests and 60 seconds.
- `CORS_ALLOWED_ORIGINS`: normally leave empty. The browser uses the same-origin frontend `/api/*` proxy, so public CORS is not needed.

Do not set `NEXT_PUBLIC_API_BASE_URL` in production. The frontend server proxies `/api/*` to `BACKEND_INTERNAL_URL`; the browser must use the public HTTPS origin. The frozen release runs with bearer authentication required, API docs disabled, and checkout observation/capture explicitly unavailable. Do not configure fixture evidence for production. The deployment does not provide live checkout evidence.

### Deploy

Run from the checked-out release directory. Have the deployment system inject `AUTH_TOKENS` into the environment before invoking Compose; avoid typing the secret into a shell command.

```bash
set -eu
set +x
git clone --branch v0.1.0-deploy.1 --depth 1 https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer.git /srv/Cartel-Smart-Cart-Optimizer
cd /srv/Cartel-Smart-Cart-Optimizer
git checkout --detach v0.1.0-deploy.1
test "$(git rev-parse HEAD)" = "518df303803eab4031d533edc3f47c0cd685e027"
: "${AUTH_TOKENS:?Inject AUTH_TOKENS from the deployment secret manager first}"
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

Configure the external TLS proxy upstream as `http://127.0.0.1:3000`, then point DNS to the host and verify the certificate. The frontend container starts only after API readiness succeeds. Both services use `restart: unless-stopped`.

### Smoke test

Set `PUBLIC_ORIGIN` to the HTTPS deployment URL. `SMOKE_TOKEN` must be a token provisioned in `AUTH_TOKENS`; avoid enabling shell tracing while it is set.

```bash
set -eu
set +x
: "${AUTH_TOKENS:?Load AUTH_TOKENS from the deployment secret manager}"
export PUBLIC_ORIGIN='https://cartel.example.com'
: "${SMOKE_TOKEN:?Set SMOKE_TOKEN from the same secret source without shell tracing}"
docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').status, urllib.request.urlopen('http://127.0.0.1:8000/ready').status)"
test "$(curl -sS -o /dev/null -w '%{http_code}' "$PUBLIC_ORIGIN/login")" = 200
test "$(curl -sS -o /dev/null -w '%{http_code}' "$PUBLIC_ORIGIN/api/v1/health")" = 200
test "$(curl -sS -o /dev/null -w '%{http_code}' "$PUBLIC_ORIGIN/api/v1/auth/session")" = 401
printf 'header = "Authorization: Bearer %s"\n' "$SMOKE_TOKEN" | \
  curl -fsS --config - "$PUBLIC_ORIGIN/api/v1/auth/session"
printf 'header = "Authorization: Bearer %s"\n' "$SMOKE_TOKEN" | \
  curl -fsS --config - \
  -H 'Content-Type: application/json' \
  --data '{"cart_id":"deployment-smoke","items":[{"item_id":"deployment-smoke-item","canonical_product_id":"deployment-smoke-product","canonical_variant_id":"deployment-smoke-variant","quantity":1}]}' \
  "$PUBLIC_ORIGIN/api/v1/cart/optimize"
```

Use an opaque URL-safe token value (for example, generated hex/base64url text) so it is valid in curl's config syntax. The commands disable shell xtrace and pass the bearer header through standard input rather than curl's process arguments.

The optimize smoke request uses deliberately unknown canonical IDs and must return the API's honest unresolved/unavailable result; it must not report checkout-backed success or a fabricated cost. The health route indicates application health, not retailer availability. `/ready` is an internal backend check at `http://api:8000/ready` and does not imply Blinkit checkout is available.

### Persistent data and operations

The frozen `v0.1.0-deploy.1` artifact creates the named `cartel-data` volume mounted at `/app/data`; Docker prefixes its physical name with the Compose project. These procedures inspect that actual mount, stop the stack for a consistent archive, encrypt with `age`, and checksum the encrypted backup. The host needs `age`, `sha256sum`, and Docker; the `alpine:3.20` helper image must be present or pullable. Set `AGE_RECIPIENT` to the public age recipient and `BACKUP_DIR` to an access-controlled destination. Keep the private age identity separately for restore. Backup integrity and restore have not been tested on a deployment host.

#### Backup

Run in the frozen release's Compose project directory while the stack is running. Tracing is disabled before backup configuration is read, and services are restarted on exit or failure.

```bash
set -euo pipefail
set +x
: "${AGE_RECIPIENT:?Load the public age recipient from approved configuration}"
: "${BACKUP_DIR:?Set an access-controlled backup destination directory}"
umask 077
mkdir -p "$BACKUP_DIR"
api_container="$(docker compose ps -q api)"
test -n "$api_container"
data_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Name}}{{end}}{{end}}' "$api_container")"
test -n "$data_volume"
backup_name="cartel-state-$(date -u +%Y%m%dT%H%M%SZ).tar.gz.age"
backup_path="$BACKUP_DIR/$backup_name"
restart_services() { docker compose start; }
trap restart_services EXIT
docker compose stop
docker run --rm \
  --mount "type=volume,src=$data_volume,dst=/backup/app-data,readonly" \
  alpine:3.20 tar -C /backup -czf - app-data | age -r "$AGE_RECIPIENT" -o "$backup_path"
(cd "$BACKUP_DIR" && sha256sum "$backup_name" > "$backup_name.sha256")
docker compose start
trap - EXIT
printf 'Encrypted backup and checksum created in %s\n' "$BACKUP_DIR"
```

#### Restore

Restore only into an empty `cartel-data` volume for the same Compose project name. The procedure verifies the checksum and archive before writing, refuses a non-empty volume, and starts the stack only after extraction. Set `BACKUP_FILE` to the `.tar.gz.age` file and `AGE_IDENTITY` to the separately protected private age identity file path. Do not put private key contents in commands or enable tracing. If the volume is non-empty, stop and make a separate recovery plan; this procedure will not overwrite or merge it.

```bash
set -euo pipefail
set +x
: "${AUTH_TOKENS:?Load AUTH_TOKENS from the deployment secret manager}"
: "${BACKUP_FILE:?Set BACKUP_FILE to the encrypted backup file}"
: "${AGE_IDENTITY:?Set AGE_IDENTITY to the protected private age identity file path}"
backup_dir="$(cd "$(dirname "$BACKUP_FILE")" && pwd)"
backup_name="$(basename "$BACKUP_FILE")"
(cd "$backup_dir" && sha256sum -c "$backup_name.sha256")
age -d -i "$AGE_IDENTITY" "$BACKUP_FILE" | tar -tzf - >/dev/null
docker compose stop
docker compose create api
api_container="$(docker compose ps -aq api)"
test -n "$api_container"
data_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Name}}{{end}}{{end}}' "$api_container")"
test -n "$data_volume"
empty="$(docker run --rm \
  --mount "type=volume,src=$data_volume,dst=/restore/app-data,readonly" \
  alpine:3.20 sh -ec 'test -z "$(find /restore/app-data -mindepth 1 -print -quit)" && printf empty')"
test "$empty" = empty
age -d -i "$AGE_IDENTITY" "$BACKUP_FILE" | docker run --rm -i \
  --mount "type=volume,src=$data_volume,dst=/restore/app-data" \
  alpine:3.20 tar -xzf - -C /restore
docker compose up -d
```

Ordinary `docker compose down` preserves `cartel-data`. **Never use `docker compose down -v` for routine operations**; that deletes the volume. Do not extract over a non-empty volume. A host loss without a valid backup loses filesystem-backed application state.

To inspect service health and recent logs:

```bash
set -eu
set +x
docker compose ps
docker compose logs --since=15m api frontend
```

Logs should contain operational status only; do not enable shell tracing or add commands that print bearer tokens, browser session state, or raw retailer payloads. To stop containers while retaining data, run `docker compose down`.

The repository cannot verify public DNS propagation, certificate issuance/renewal, cloud firewall rules, secret-manager delivery/rotation, backup integrity, host monitoring, or public-origin reachability until these are configured on the deployment host. The frozen artifact is a single-instance filesystem-backed Compose deployment, not a horizontally scalable topology. PostgreSQL-backed consumer identity is present only in the untagged working tree and is not part of this deployment procedure.

### Local Setup

Prerequisites: Python 3.12

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt
# Configure .env using docs/setup.md
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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

### Planned Demo Assets

The following demonstrations are the remaining MVP-facing verification targets:

- Live Blinkit acquisition ✅
- Product matching ✅
- Deterministic checkout/ECE path ✅
- Live checkout-derived effective-cost computation 🚧 Blinkit access/cart evidence blocked
- Cart optimization and automatic optimization flow ✅
- Consumer web interface ✅ repository-local production Compose validated; public-host DNS/TLS/proxy/reachability remain unverified

---

## 📡 API

Currently implemented endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Basic health check |
| `GET` | `/api/v1/health` | API health check |
| `GET` | `/api/v1/products/search` | Governed product search |
| `POST` | `/api/v1/cart/plan` | Explicit cart planning |
| `POST` | `/api/v1/cart/optimize` | Automatic cart planning and optimization |

Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs` only for a locally run backend when `DOCS_ENABLED=true`; it is disabled in the production Compose configuration, whose backend port is private.

The current MVP exposes health, governed product search, explicit planning, and automatic cart optimization. Checkout/ECE-backed live retailer results depend on successful retailer checkout capture.

---

## 📁 Repository Structure

```
Cartel-Smart-Cart-Optimizer/
│
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI routers
│   │   ├── core/                   # config, logging, security
│   │   ├── db/                     # database models and session management
│   │   ├── cart_optimization/      # optimization contracts, identity, orchestration and service
│   │   ├── cost_intelligence/      # effective-cost evaluation pipeline
│   │   │   ├── observation/
│   │   │   ├── context/
│   │   │   ├── evaluation/
│   │   │   ├── offer/
│   │   │   ├── fee/
│   │   │   ├── membership/
│   │   │   ├── effective_cost/
│   │   │   ├── pipeline/
│   │   │   └── shared/
│   │   ├── data_ingestion/         # immutable ingestion contracts, enums, identity builders and observation registry (Slice 1)
│   │   ├── product_intelligence/   # deterministic product matching pipeline
│   │   │   ├── evidence/
│   │   │   ├── candidate_generation/
│   │   │   ├── matching/
│   │   │   ├── assertions/
│   │   │   ├── review/
│   │   │   ├── catalog/            # canonical catalog, identity resolution, persistence, snapshots
│   │   │   └── orchestrator/
│   │   ├── normalization/          # pricing / products / units normalization
│   │   ├── schemas/                # shared pydantic models
│   │   ├── scrapers/               # scraper infrastructure
│   │   │   ├── blinkit/            # Blinkit scraper (live acquisition integrated; checkout capture wired, live retailer verification externally blocked)
│   │   │   ├── bigbasket/          # integration placeholder
│   │   │   ├── zepto/              # integration placeholder
│   │   │   ├── base/               # scraper base contracts
│   │   │   └── utils/
│   │   ├── workers/                 # ingestion and Product Intelligence runtime boundaries
│   │   ├── utils/
│   │   └── main.py
│   ├── tests/
│   └── requirements/, Dockerfile, .env.example
│
├── data/                           # scraped and derived data artifacts
│   ├── raw/blinkit/
│   ├── cleaned/
│   └── product_intelligence/
│
├── docs/                           # architecture & governance specs
├── scripts/                        # demo scripts
└── docker-compose.yml, LICENSE
```

---

## 📈 Project Metrics

- **40+** architecture and governance specifications
- **Deterministic** Product Intelligence architecture spanning evidence, canonical catalog, candidate generation, matching, review, and assertion
- **Cost Intelligence** checkout observation, effective-cost evaluation, and ECE-backed planning infrastructure implemented
- **Cart Optimization** contracts, identity builders, planning, checkout integration boundaries, deterministic ECE flow, and automatic planning implemented
- **Real Data Ingestion** live Blinkit acquisition, normalization, persistence, replay, and observation registration implemented for the MVP
- **Deterministic identity system** across products, carts and operational entities
- **Immutable value contracts** throughout implemented pipelines
- Backend test results are recorded by each release validation run; this README does not assert a current test count.

---

## 📚 Documentation

The `docs/` directory contains **40+ architecture and governance specifications**. Key starting points:

**Core Architecture & Design:**
- `docs/product_intelligence_design.md` — Product Intelligence system design
- `docs/product_intelligence_pipeline.md` — Pipeline architecture  
- `docs/canonical_product_schema.md` — Cross-platform product model
- `docs/product_matching_architecture.md` — Product matching system design
- `docs/variant_matching_architecture.md` — Variant matching in depth

**Implementation & System Details:**
- `docs/product_intelligence_evidence_registry.md` — Evidence system design
- `docs/product_intelligence_candidate_generation.md` — Candidate generation strategy
- `docs/research_analysis.md` — Cross-platform pricing analysis and research findings

**RFC & Contracts:**
- `docs/architecture/real_data_ingestion_rfc.md` — Real Data Ingestion RFC
- `docs/architecture/cart_optimization_contract.md` — Cart Optimization system contracts

**Additional documentation** is located throughout `docs/` covering governance, testing strategies, and implementation details.

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

**Live Blinkit Checkout Integration** — Live cart/checkout evidence remains blocked by Blinkit access control; the checkout capture, cart-verification, ECE, and automatic-planning integration are implemented and fail closed.

**Cost Intelligence** — Checkout observation → ECE is implemented and integrated with automatic planning; live retailer checkout evidence remains blocked by the Blinkit retailer boundary.

**Cart Optimization** — automatic planning, checkout-capture invocation, ECE integration, and deterministic result generation are implemented.

---

## 🗺 Roadmap

| Phase | Focus | Status |
|---|---|---|
| 1 | Real Data Ingestion Architecture & RFC | ✅ Complete |
| 2 | Product Intelligence Foundation | ✅ Complete |
| 3 | Product Intelligence Implementation | ✅ Complete |
| 4 | Cost Intelligence Foundation | ✅ Complete |
| 5 | Cost Intelligence Evaluation | ✅ Complete |
| 6 | Effective Cost & Cart Optimization | ✅ Complete for deterministic MVP path |
| — | Complete canonical catalog and lifecycle integration, including post-PARSED lifecycle transitions, restart/idempotency behavior, and durable catalog/runtime boundaries | 🚧 Active |
| 7 | Live Scraper Integration | 🚧 Active — Blinkit acquisition and checkout integration implemented; live cart/checkout evidence remains blocked by Blinkit access control |
| 8 | Consumer Experience (API, Web, Android) | 🚧 Active |

---

## 🤝 Contributing

Cartel is early — architecture decisions are being made, and contributing now shapes the foundation.

**Before contributing:**
- Read the relevant RFC in `docs/` — architecture comes first, implementation second
- Open an issue for large PRs to discuss design
- Tests are required — PRs that reduce coverage don't merge

**Best entry points:**

| Area | What's Needed |
|---|---|
| 🌐 **Live scrapers** | BigBasket, Zepto, JioMart, Instamart integrations |
| 💰 **Cost Intelligence** | Live checkout observation hardening and retailer-specific integrations |
| 🧪 **Tests** | End-to-end browser acceptance, live retailer regression, and production hardening |
| 📚 **Docs** | Production deployment, API, consumer application, and operational guides |

---

## 💡 Vision

> *"What is the cheapest way to buy my entire grocery cart right now?"*

Across platforms, locations, offers, memberships, rewards, and delivery constraints — not as an approximation, but as a number you can trust.

Most price-intelligence tools optimize the easy thing: the sticker price. Cartel is being built to model the hard thing: the real economics of a grocery purchase, end to end, with every decision auditable and every result reproducible.

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
