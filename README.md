# Cartel

Consumer-side grocery price intelligence and cart optimization platform.

## Vision

Cartel helps consumers discover the true lowest-cost way to purchase groceries across quick-commerce and ecommerce platforms.

Traditional price comparison systems compare displayed product prices.

Cartel models the complete economics of a grocery purchase, including:

* Product prices
* Delivery fees
* Handling charges
* Platform fees
* Cashback rewards
* Loyalty benefits
* Coupons and promo codes
* Bundle offers
* Cart-level discounts
* Minimum order thresholds
* Membership-exclusive pricing
* Free-item promotions
* Quantity-based offers
* Location-dependent pricing
* Platform-specific offer stacking rules

The objective is to calculate the actual effective cost paid by a consumer rather than the advertised product price.

---

## Why Cartel Exists

Research across Blinkit, BB Now, Zepto, Instamart, JioMart, and other grocery platforms revealed several key realities:

* The cart, not the individual product, is the true optimization unit.
* Displayed prices rarely represent the final amount paid.
* Fees, rewards, and promotions materially affect effective cost.
* Offer eligibility depends on activation conditions, thresholds, expiry windows, and stacking constraints.
* Identical products are represented differently across platforms.
* Platform-specific pricing and offer logic make direct comparisons unreliable.
* Consumer decisions are heavily influenced by behavioral pricing mechanisms such as anchoring, urgency, scarcity, and free-delivery thresholds.

These findings transformed Cartel from a simple price-comparison project into a grocery intelligence platform capable of reasoning about products, offers, fees, and complete shopping carts.

---

## Core Principles

Cartel is built around several architectural principles:

* Deterministic matching and decision-making
* Replayable audit trails
* Evidence-backed product intelligence
* Explicit governance rules
* Platform-independent canonical product modeling
* Reproducible matching outcomes
* Location-aware pricing intelligence
* Cart-level optimization rather than product-level comparison

---

## Architecture Overview

```text
Raw HTML
    ↓
Parser
    ↓
Structured Raw Product Data
    ↓
Evidence Bundle
    ↓
Platform Listing
    ↓
Listing Observation
    ↓
Candidate Generation
    ↓
Product Matching
    ↓
Variant Matching
    ↓
Canonical Assertion Update
    ↓
Offer Intelligence
    ↓
Cost Intelligence
    ↓
Cart Optimization
```

---

## Current Status

### Completed

#### Data Acquisition

* FastAPI backend foundation
* Structured logging
* Modular scraper architecture
* Blinkit browser automation
* Location-aware session handling
* Persistent browser state
* Raw extraction pipeline
* Structured raw product output

#### Product Intelligence Foundation

* Evidence corpus across multiple grocery categories
* Canonical product schema
* Product intelligence domain models
* Product intelligence pipeline architecture
* Product matching architecture
* Variant matching architecture
* Governance contracts
* Deterministic matching framework
* Product intelligence package structure

#### Research

* Cross-platform grocery analysis
* Offer system research
* Fee structure research
* Cart optimization research
* Consumer pricing behavior research

### In Progress

#### Product Intelligence

* Evidence registry
* Candidate generation
* Product matching implementation
* Variant matching implementation
* Review workflow
* Canonical assertion updates

#### Cost Intelligence

* Offer modeling
* Promotion-rule modeling
* Fee modeling
* Platform-pricing intelligence

### Planned

#### Platform Expansion

* Zepto integration
* BB Now integration
* JioMart integration
* Instamart integration

#### Optimization

* True-cost calculation engine
* Cart optimization engine
* Cart-splitting optimization
* Multi-platform recommendation engine

#### User Experience

* Comparison APIs
* Consumer dashboard
* Frontend application

---

## Roadmap

### Phase 1: Data Acquisition ✅

* Blinkit integration
* Session persistence
* Raw extraction
* Structured output generation

### Phase 2: Product Intelligence Foundation ✅

* Canonical product modeling
* Product intelligence architecture
* Product matching architecture
* Variant matching architecture
* Governance contracts
* Domain models

### Phase 3: Product Intelligence Implementation 🚧

* Evidence registry
* Candidate generation
* Product matching
* Variant matching
* Review workflow
* Canonical assertion updates

### Phase 4: Cost Intelligence

* Offer engine
* Promotion engine
* Fee engine
* Cashback modeling
* Loyalty reward modeling
* Effective-cost calculation

### Phase 5: Cart Optimization

* Multi-platform comparison
* Cart splitting
* Cheapest-cart recommendation engine

### Phase 6: Platform Expansion

* Zepto
* BB Now
* JioMart
* Instamart

### Phase 7: Consumer Experience

* Public APIs
* Dashboard
* Frontend application

---

## Current Milestone

### v0.2.0

Cartel can successfully acquire, parse, and structure real-world Blinkit grocery data while maintaining location-aware sessions and persistent browser state.

The project now includes:

* Product intelligence architecture
* Canonical product models
* Evidence-driven matching design
* Deterministic matching governance
* Product matching framework
* Variant matching framework
* Audit and replay foundations
* Cost-intelligence research foundation

Cartel is currently transitioning from architecture and governance design into implementation of the product-intelligence layer.

---

## Long-Term Goal

Enable consumers to answer a simple question:

> "What is the cheapest way to buy my entire grocery cart right now?"

Across platforms, locations, offers, memberships, rewards, and delivery constraints.

---

## License

MIT
