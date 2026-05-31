# Cartel

Consumer-side grocery price intelligence and cart optimization platform.

## Vision

Cartel helps users discover the true cheapest way to purchase groceries across quick-commerce and e-commerce platforms.

Unlike traditional price comparison tools, Cartel aims to account for:

- product prices
- delivery fees
- handling charges
- platform fees
- cashback
- loyalty rewards
- coupons
- bundle offers
- cart-level discounts

The goal is to calculate the actual effective cost of a purchase, not just the displayed product price.

---

## Current Status

### Completed

- FastAPI backend foundation
- Structured logging
- Modular scraper architecture
- Blinkit browser automation
- Location-aware session handling
- Session persistence
- Product extraction pipeline
- Structured JSON output
- Initial architecture and research phase

### In Progress

- Product normalization
- Canonical product catalog design
- Offer modeling
- True-cost calculation engine

### Planned

- Zepto integration
- BB Now integration
- JioMart integration
- Product matching engine
- Cart optimization engine
- Multi-platform comparison API
- Frontend application

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

Successfully acquires and parses real Blinkit grocery data into structured product records.

---

## License

MIT
