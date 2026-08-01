<div align="center">

<br/>

# 🛒 Cartel

### The real cost of groceries, deterministically computed.

**Product Intelligence · Cost Intelligence · Cart Optimization**

<br/>

[![Build](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.2.0-blue?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-164%20passing-brightgreen?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer/tree/main/backend/tests)
[![Status](https://img.shields.io/badge/status-active%20development-yellow?style=for-the-badge)](https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer)

<!-- TODO: Add screenshot/GIF of demo pipeline -->
<!-- TODO: Add Codecov badge once coverage reporting is wired -->

<br/>

**[🤔 Why This Exists](#-why-this-exists) · [✨ Architecture](#-layered-architecture) · [🏗 Real Data Ingestion](#-real-data-ingestion) · [🚀 Quick Start](#-quick-start) · [🗺 Roadmap](#-roadmap) · [🤝 Contributing](#-contributing)**

</div>

---

## 🤔 Why This Exists

Every grocery price-comparison tool compares the same thing: the price printed on the product. That number is mostly fiction.

What you *actually* pay depends on delivery fees, handling charges, platform fees, cashback, loyalty pricing, coupon stacking rules, minimum-order thresholds, membership pricing, and free-item promotions that activate or expire depending on what's already in your cart.

Research across **Blinkit, BB Now, Zepto, Instamart, and JioMart** confirmed the problem is structural, not incidental:

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
- **Immutable audit trails** — decision records are append-only and tamper-evident
- **Explicit governance contracts** — matching rules are declared, versioned, and enforced, not implicit
- **Contract-first architecture** — every component defines its input/output contract before implementation
- **Deterministic identities** — products, carts, and decisions have stable, reproducible identifiers
- **Immutable value objects** — pipelines consume immutable inputs and produce immutable outputs
- **Replay references** — every operation can be replayed given the same inputs and context

---

## 🏗 Layered Architecture

Cartel is built as four independent, composable layers:

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

---

## 🔬 Engineering Highlights

What makes Cartel fundamentally different from typical e-commerce projects:

- **Deterministic architecture** — same inputs always produce same outputs, no hidden state
- **Replayable operations** — every scrape, match, and cost computation can be replayed from stored artifacts
- **Immutable contracts** — every layer defines its input/output contract as immutable value objects
- **Audit-first design** — every operation is logged, checksummed, and reproducible
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

**Architecture & Contracts Complete ✅**
- RFC: Data Ingestion Architecture
- Lifecycle contracts: Job scheduling, context capture, artifact storage
- Deterministic serialization contracts and identity builders
- Storage architecture specified through RFCs; implementation in progress.
- Replay system specified through RFCs; implementation in progress.

**Implementation In Progress 🚧**
- Lifecycle implementation
- Storage implementation
- Live scraper integration with Blinkit, BigBasket, Zepto

---

## 🔬 Product Intelligence Pipeline

Match products deterministically across platforms using evidence-backed reasoning.

```
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
      ▼
Review Queue
      │
      ▼
Assertion Manager
      │
      ▼
Pipeline Orchestrator
      │
      ▼
Canonical Product Intelligence
```

**Status: ✅ Complete**

Every stage consumes immutable governed inputs and produces deterministic, replayable outputs with a complete audit trail.

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

**In Progress:**
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

**In Progress:**
- Optimization engine
- Multi-platform recommendation logic

---

## 🚀 Quick Start

### Docker (Recommended)

Prerequisites: Docker Desktop with Compose.

```bash
git clone https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer.git
cd Cartel-Smart-Cart-Optimizer
docker compose up --build
```

API: `http://localhost:8000`
Docs: `http://localhost:8000/docs`
Health: `http://localhost:8000/health`

Stop with:

```bash
docker compose down
```

### Local Setup

Prerequisites: Python 3.12+

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt
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

```bash
pytest backend/tests/ -v
```

---

## 📸 Demos & Screenshots

### Planned Demo Assets

The following demonstrations will be added as implementation progresses:

- Live data ingestion
- Product matching
- Effective-cost computation
- Cart optimization
- Consumer web interface

---

## 📡 API

Currently implemented endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Basic health check |
| `GET` | `/api/v1/health` | API health check |

Interactive API documentation (Swagger UI) will be available at `http://localhost:8000/docs` once the backend is running.

Additional endpoints will be introduced as implementation progresses across Cost Intelligence and Cart Optimization.

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
│   │   │   └── shared/
│   │   ├── data_ingestion/         # immutable ingestion contracts, enums and identity builders (Slice 1)
│   │   ├── product_intelligence/   # deterministic product matching pipeline
│   │   │   ├── evidence/
│   │   │   ├── candidate_generation/
│   │   │   ├── matching/
│   │   │   ├── assertions/
│   │   │   ├── review/
│   │   │   └── orchestrator/
│   │   ├── normalization/          # pricing / products / units normalization
│   │   ├── schemas/                # shared pydantic models
│   │   ├── scrapers/               # Blinkit scraper infrastructure
│   │   │   ├── blinkit/            # Blinkit scraper (not yet live-integrated)
│   │   │   └── base/               # scraper base contracts
│   │   ├── utils/
│   │   └── main.py
│   ├── tests/
│   └── requirements/, Dockerfile, .env.example
│
├── data/                           # real production data
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
- **Product Intelligence** implementation complete
- **Cost Intelligence** core implementation in progress
- **Cart Optimization** contracts, identity builders, request builder, orchestrator and service implemented; optimization engine in progress
- **Real Data Ingestion** immutable contract layer implemented (Slice 1)
- **Deterministic identity system** across products, carts and operational entities
- **Immutable value contracts** throughout implemented pipelines
- **164 automated tests**

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
- **Thresholds & Minimums** — Blinkit: free delivery >₹500. Zepto: >₹400. Same cart (₹450) has different effective cost on each platform.
- **Offer Stacking** — "₹100 off >₹1000 + 10% cashback" (excludes some categories, expires after 3 uses). Eligibility depends on cart composition, user history, and time.
- **Membership Pricing** — BigBasket Plus (₹299/mo) vs Zepto Silver (₹199). Some items 20% cheaper, some no discount. Must amortize membership cost.
- **Split Carts** — Buying ₹300 from Blinkit + ₹200 from Zepto can be cheaper than ₹500 from one platform due to different fee thresholds.
- **Location Pricing** — Same milk: ₹45 in Bangalore, ₹48 in Hyderabad. Zones affect pricing dynamically.

**Why Determinism Matters:**
With this many variables interacting, approximation is useless. You need reproducible results, auditable decisions, and testable logic. That's what Cartel delivers.

---

**End users** — anyone buying groceries across Blinkit, Zepto, Instamart, or BigBasket who wants the actual cheapest option before checkout.

**Developers** — engineers interested in deterministic matching systems, scrapers, immutable pipelines, or quick-commerce infrastructure.

**Researchers** — anyone studying quick-commerce pricing, platform economics, or behavioral pricing in Indian e-commerce.

**Teams building similar systems** — this architecture is designed to be forkable and extensible.

---

## 🎯 Current Focus

**Real Data Ingestion Implementation** — Building live scraper integration with Blinkit, BigBasket, and Zepto (architecture & RFC complete).

**Cost Intelligence Implementation** — Fee evaluation and membership evaluation (context & offer evaluation complete).

**Cart Optimization** — optimization engine implementation in progress.

---

## 🗺 Roadmap

| Phase | Focus | Status |
|---|---|---|
| 1 | Real Data Ingestion Architecture & RFC | ✅ Complete |
| 2 | Product Intelligence Foundation | ✅ Complete |
| 3 | Product Intelligence Implementation | ✅ Complete |
| 4 | Cost Intelligence Foundation | ✅ Complete |
| 5 | Cost Intelligence Evaluation | 🚧 Active |
| 6 | Effective Cost & Cart Optimization | 🚧 Planned |
| 7 | Live Scraper Integration | 🚧 Planned |
| 8 | Consumer Experience (API, Dashboard, Apps) | 📋 Planned |

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
| 💰 **Cost Intelligence** | Fee evaluation and membership evaluation |
| 🧪 **Tests** | Always welcome across all modules |
| 📚 **Docs** | Architecture specs, setup guides, examples |

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
