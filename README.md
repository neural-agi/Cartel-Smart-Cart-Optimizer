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

## Current Status

### Completed

* FastAPI backend foundation
* Structured logging
* Modular scraper architecture
* Blinkit browser automation
* Location aware session handling
* Session persistence
* Raw extraction pipeline
* Structured raw product output
* Evidence corpus across multiple grocery categories
* Canonical product schema design
* Product intelligence domain models
* Product intelligence pipeline
* Product intelligence component architecture
* Product matching architecture
* Product intelligence package skeleton
* Initial architecture and research phase

### In Progress

* Product intelligence implementation
* Evidence registry implementation
* Candidate generation implementation
* Product matching implementation
* Variant matching implementation
* Review workflow implementation
* Canonical assertion updates
* Cross platform product normalization
* Offer and promotion rule modeling
* Fee and surcharge modeling
* True cost calculation engine
* Platform offer intelligence framework

### Planned

* Zepto integration
* BB Now integration
* JioMart integration
* Instamart integration
* Cart optimization engine
* Multi platform comparison API
* Frontend application

## Roadmap

### Phase 1: Data Acquisition ✅

* Blinkit integration
* Session persistence
* Raw extraction
* Structured raw output

### Phase 2: Product Intelligence 🚧

* Canonical product catalog
* Product intelligence domain models
* Product intelligence pipeline
* Product matching architecture
* Product intelligence component skeleton

### Phase 3: Product Intelligence Implementation

* Evidence registry
* Candidate generation
* Product matching
* Variant matching
* Review queue
* Canonical assertion updates

### Phase 4: Cost Intelligence

* Offer engine
* Fee engine
* Cashback modeling
* Loyalty reward modeling
* True cost calculation engine

### Phase 5: Cart Optimization

* Multi platform comparison
* Cart splitting optimization
* Cheapest cart recommendation engine

### Phase 6: Platform Expansion

* Zepto integration
* BB Now integration
* JioMart integration
* Instamart integration

### Phase 7: User Experience

* REST APIs
* Dashboard
* Frontend application

## Example Workflow

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
Offer Engine
    ↓
True Cost Engine
    ↓
Cart Optimizer

```

---

## Current Milestone

v0.2.0

Successfully acquires, parses, and structures real world Blinkit grocery data while maintaining location aware sessions and persistent browser state.

The project now includes research backed product intelligence architecture, domain models, pipeline design, component boundaries, matching architecture, and implementation skeletons.

---

## License

MIT
