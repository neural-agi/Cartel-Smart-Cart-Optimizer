# Final Swiggy Instamart Partnership Inquiry (Manual Send)

**Status:** Ready for manual sending after owner input is completed. **Not sent.**

**To:** `builders@swiggy.in` — published on the official Swiggy Builders Club access page and enterprise page (accessed 2026-11-09).

**Subject:** Cartel request for written authorization and zero-cost production terms for cross-retailer Instamart comparison

**Word count (email body only):** 392 words including the two owner-input markers (verified with `wc -w`; see element checklist below).

> Send manually. Do not send until every `OWNER_INPUT_REQUIRED` field is completed and the owner has reviewed the cross-retailer disclosure, the competitive-intelligence acknowledgement, and the zero-budget statement.

## Email body

Hello Swiggy Builders Club team,

I am writing on behalf of Cartel, an early-stage consumer grocery comparison and basket-optimization product in development. Cartel helps a user describe a shopping need, resolve exact products and pack sizes, compare attributable retailer observations for the user's delivery context, and receive an explainable basket allocation. Cartel is explicitly cross-retailer: Instamart information would appear beside information from other authorized retailers, and Cartel would derive product-equivalence and basket-allocation recommendations. We are not presenting Cartel as an Instamart-only shopping assistant.

We are evaluating the Instamart MCP and the Enterprise/Startup route. Before any integration work, we request written authorization or a negotiated exception covering:

- commercial cross-retailer grocery comparison and comparative display;
- catalog aggregation and exact product/variant matching;
- collection, storage, caching, refresh, retention, and deletion of permitted Instamart observations;
- derived product-equivalence and basket-allocation recommendations;
- consumer OAuth/delegated authorization;
- future cart preparation and checkout handoff, with payment authorization remaining with the user.

We have read Swiggy's production-access rules. Under "Not Allowed", they list "Using the APIs for competitive intelligence or benchmarking" (https://mcp.swiggy.com/builders/access/, accessed 9 November 2026). We are not asking you to waive that rule by implication. We ask for an explicit written determination of whether Cartel's comparative model falls within the restriction and, if it does, whether a written exception or negotiated enterprise agreement is available. We also note the related restriction on "Building aggregation layers that hide Swiggy's brand or confuse users"; we will follow Swiggy's attribution and branding requirements.

Please also confirm in writing:

1. whether Instamart prices, availability, and serviceability may be displayed beside competing retailer information;
2. what retention, refresh, deletion, and redistribution rights would apply to Instamart-originated data;
3. whether a sustainable zero-cost production arrangement is available.

On cost: Cartel cannot accept mandatory API credits, platform fees, subscriptions, minimum commitments, paid data licences, or mandatory usage charges. Free local development is not the constraint; Cartel needs a sustainable zero-cost production arrangement. If Swiggy cannot offer a qualifying zero-cost production arrangement, we will record the integration as commercially infeasible under our current constraint rather than proceed.

No Instamart adapter, credentials, API call, or integration will be built or requested before written approval. We can provide an architecture overview, data-flow description, security summary, data-handling declaration, and product demonstration on request.

Regards,

`OWNER_INPUT_REQUIRED (OI-04)` — name and role
`OWNER_INPUT_REQUIRED (OI-05)` — business email

Cartel

## Required-element checklist

| Required element | Present? | Quote or line reference |
|---|---|---|
| Introduces Cartel | Yes | "I am writing on behalf of Cartel, an early-stage consumer grocery comparison and basket-optimization product in development." |
| Explains the actual cross-retailer comparison model | Yes | "Cartel is explicitly cross-retailer: Instamart information would appear beside information from other authorized retailers, and Cartel would derive product-equivalence and basket-allocation recommendations." |
| Acknowledges the competitive-intelligence restriction | Yes | Quotes Swiggy's "Using the APIs for competitive intelligence or benchmarking" with the access-page URL and access date. |
| Requests written authorization or a negotiated exception | Yes | "We request written authorization or a negotiated exception covering..." and "whether a written exception or negotiated enterprise agreement is available." |
| Requests confirmation of comparative-display rights | Yes | Item 1: "whether Instamart prices, availability, and serviceability may be displayed beside competing retailer information." |
| Requests confirmation of data-retention rights | Yes | Item 2: "what retention, refresh, deletion, and redistribution rights would apply to Instamart-originated data." |
| Requests zero-cost production terms | Yes | "whether a sustainable zero-cost production arrangement is available" plus the explicit exclusions and consequence. |
| States no integration before approval | Yes | "No Instamart adapter, credentials, API call, or integration will be built or requested before written approval." |
| No marketing claims, traction, or user counts | Yes | No users, revenue, funding, or growth claims appear. |
| No invented Swiggy authorization or partnership | Yes | The email requests authorization and never implies it exists. |

## Source of the competitive-intelligence quotation

- Page: `https://mcp.swiggy.com/builders/access/`
- Final URL after redirects: `https://mcp.swiggy.com/builders/access/`
- Access date: 2026-11-09
- Section: "02 / Operating Boundaries — The Ground Rules — Not Allowed / Restricted"
- Exact clause relied on: "Using the APIs for competitive intelligence or benchmarking"
- Related clause relied on: "Building aggregation layers that hide Swiggy's brand or confuse users"
