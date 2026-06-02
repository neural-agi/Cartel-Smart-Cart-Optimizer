# Cartel

Consumer side grocery price intelligence and cart optimization platform.

## Vision

Cartel helps users discover the true cheapest way to purchase groceries across quick commerce and ecommerce platforms.

Unlike traditional price comparison tools, Cartel aims to account for:

* product prices
* delivery fees
* handling charges
* platform fees
* cashback
* loyalty rewards
* coupons
* bundle offers
* cart level discounts
* minimum order requirements
* membership exclusive pricing
* free item promotions
* quantity based offers
* location dependent pricing
* platform specific offer stacking rules

The goal is to calculate the actual effective cost of a purchase, not just the displayed product price.

---

## Key Research Findings

Research across Blinkit, BB Now, Zepto, Instamart, JioMart, and other grocery platforms revealed several important insights:

* The cart, not the individual product, is the true unit of optimization.
* Displayed product prices rarely represent the final amount paid.
* Delivery fees, handling charges, platform fees, and loyalty rewards significantly affect effective cost.
* Offers often have activation conditions, expiry windows, and stacking restrictions.
* Identical products are frequently represented differently across platforms.
* Grocery platforms use behavioral economics techniques such as anchoring, urgency, scarcity, and free delivery thresholds to influence purchasing decisions.
* Effective grocery optimization requires product normalization, offer modeling, fee modeling, and cart level reasoning.

These findings transformed Cartel from a simple price comparison project into a true cost grocery intelligence platform.

---

## Current Status

### Completed

* FastAPI backend foundation
* Structured logging
* Modular scraper architecture
* Blinkit browser automation
* Location aware session handling
* Session persistence
* Product extraction pipeline
* Structured JSON output
* Initial architecture and research phase

### In Progress

* Canonical product catalog design
* Cross platform product normalization
* Offer and promotion rule modeling
* Fee and surcharge modeling
* True cost calculation engine
* Platform offer intelligence framework

### Planned

* Zepto integration
* BB Now integration
* JioMart integration
* Product matching engine
* Cart optimization engine
* Multi platform comparison API
* Frontend application

---

## Roadmap

### Phase 1: Data Acquisition ✅

* Blinkit integration
* Session persistence
* Product extraction
* Structured JSON output

### Phase 2: Product Intelligence 🚧

* Canonical product catalog
* Product normalization
* Cross platform product matching

### Phase 3: Cost Intelligence

* Offer engine
* Fee engine
* Cashback modeling
* Loyalty reward modeling
* True cost calculation engine

### Phase 4: Cart Optimization

* Multi platform comparison
* Cart splitting optimization
* Cheapest cart recommendation engine

### Phase 5: Platform Expansion

* Zepto integration
* BB Now integration
* JioMart integration
* Instamart integration

### Phase 6: User Experience

* REST APIs
* Dashboard
* Frontend application

---

## Example Workflow

```text
Raw HTML
    ↓
Parser
    ↓
Structured Product Data
    ↓
Normalization
    ↓
Product Matching
    ↓
Offer Engine
    ↓
True Cost Engine
    ↓
Cart Optimizer
```

---

## Current Milestone

v0.1.0

Successfully acquires, parses, and structures real world Blinkit grocery data while maintaining location aware sessions and persistent browser state.

Research and architecture work for multi platform true cost grocery optimization has been completed.

---

## License

MIT
