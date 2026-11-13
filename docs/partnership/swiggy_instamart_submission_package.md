# Cartel Smart Cart Optimizer

## Swiggy Instamart Submission Package

**Status:** Draft for manual owner review. Not submitted.

**Submission readiness:** PARTIALLY READY

This package is copy-ready except for owner-specific fields marked `TBD`. No email, application, account, credential request, or API call has been made.

Cartel has not received Swiggy authorization, is not a Swiggy partner, has no Instamart adapter, and has no Instamart credentials or production access. Cross-retailer comparison remains unapproved. Production pricing and sustainable zero-cost availability remain `UNKNOWN`.

## 1. Final Inquiry Email

**To:** `TBD - use the official Swiggy Builders Club route`

**Subject:** Cartel request for written authorization and zero-cost production terms for cross-retailer Instamart comparison

Hello Swiggy Builders Club / Instamart Partnerships team,

Cartel is an early-stage consumer grocery comparison and basket-optimization product currently in development. Cartel helps consumers describe a shopping need, select exact products and pack configurations, compare supported retailer evidence, and allocate a basket across retailers based on available product, price, and serviceability information.

Cartel's product is explicitly cross-retailer. It may display Instamart information alongside information from other authorized retailers and may derive product-equivalence and basket-allocation recommendations. Cartel is therefore not presenting itself as merely an Instamart shopping assistant.

Subject to written authorization, we are evaluating Swiggy's Instamart MCP and Enterprise/Startup partnership routes for:

- product identity, title, brand, pack, and variant information;
- location-specific price and availability;
- address/coordinate serviceability context;
- capture/freshness metadata;
- consumer OAuth/delegated access;
- future cart preparation and checkout handoff, with payment authorization remaining under user control.

We understand that Swiggy's published production-access rules restrict competitive intelligence and benchmarking. We request an explicit determination of whether Cartel's cross-retailer comparison model is permitted and, if necessary, whether a written exception or negotiated enterprise agreement is available.

Please provide written answers to the following:

1. Is commercial cross-retailer grocery comparison permitted for an approved Instamart integration?
2. Is Cartel's use case considered competitive intelligence or benchmarking?
3. May Instamart prices, availability, and serviceability appear beside competing retailer information?
4. May Cartel aggregate Instamart catalog data with data from other authorized retailers?
5. May Cartel store and cache product identity, pack, price, availability, and serviceability data?
6. What retention, refresh, deletion, and redistribution restrictions apply?
7. May Cartel generate derived product-equivalence and basket-allocation recommendations?
8. Is consumer OAuth/delegated authorization supported for this product model?
9. How may Cartel process delivery addresses, coordinates, serviceability results, and retailer account data?
10. Is production access available to an early-stage startup?
11. Are mandatory fees, API charges, paid credits, subscriptions, or minimum commitments required?
12. Is sustainable zero-budget development and production access available?
13. Should Cartel use MCP, an enterprise API, or another supported interface?
14. What rate limits, SLA, versioning, support, revocation, and credential-lifecycle requirements apply?
15. Are cart preparation and checkout handoff permitted?
16. What attribution, branding, or “Powered by Swiggy/Instamart” requirements apply?

Cartel can provide an architecture diagram, data-flow description, security controls, privacy approach, expected traffic, and product demonstration for review. We will not request credentials or invoke production services until the commercial and technical permissions are documented.

Cartel currently has no budget for paid API credits, subscriptions, platform fees, minimum commitments, or commercial data services. We disclose this constraint so any proposed production arrangement can be evaluated honestly.

Regards,

`TBD - owner name and role`

Cartel team

## 2. Application-Form Materials

### Product description: concise

Cartel is a consumer grocery comparison and basket-optimization product. Users describe what they need, select exact governed products and pack configurations, compare permitted retailer evidence for their delivery context, and receive an explainable basket allocation. Cartel is explicitly cross-retailer and may display comparative product, price, availability, and serviceability information, subject to each retailer's written authorization and data-use terms.

Cartel does not claim to be a Swiggy partner or to have Instamart access. Any Instamart integration would require written permission for comparative display, catalog aggregation, storage/caching, derived recommendations, delegated authorization, and any future cart or checkout handoff.

### Product description: detailed

Cartel's consumer workflow is:

1. Capture user shopping intent.
2. Resolve the exact governed Product/Variant and pack configuration.
3. Request permitted retailer evidence for the user's delivery context.
4. Preserve retailer-native identity separately from Cartel canonical identity.
5. Compare attributable observed prices and availability across authorized retailers.
6. Produce an explainable allocation recommendation where evidence is sufficient.
7. Keep unresolved, unavailable, stale, or conflicting evidence out of usable offers.
8. Require user approval before any retailer cart preparation or checkout handoff.

Observed listing prices are not represented as checkout totals. Cartel does not fabricate savings, fees, delivery costs, taxes, availability, or payable totals.

### Actual architecture summary

- Consumer frontend: Next.js application with a same-origin/server proxy path.
- Backend: FastAPI modular application.
- Persistence: PostgreSQL-backed user, retailer-connection, list, job, outbox, and governed metadata models in the current development/runtime work.
- Background work: PostgreSQL-backed worker and outbox foundation; production deployment maturity remains to be verified.
- Rate limiting: Redis-backed distributed rate limiting; Redis is not application source of truth.
- Retailer integrations: provider-neutral capability adapters with lifecycle authorization, credential resolution, and a Credential Vault.
- Identity: Cartel Product/Variant identity is separate from retailer-native product/listing identity.
- Evidence: provenance-aware observations and immutable artifact references; unresolved evidence is excluded from consumer eligibility.
- Security: server-managed sessions, CSRF, Argon2id password hashing, owner-scoped retailer connections, and AES-256-GCM vault cryptography.

No Instamart adapter, credentials, endpoint configuration, or live integration exists.

### Data-flow description

```text
Consumer browser
    -> Next.js frontend/proxy
    -> FastAPI API
       -> PostgreSQL: users, lists, connections, jobs, evidence metadata
       -> Credential Vault: encrypted retailer secret material, when configured
       -> governed Product/Variant resolution and consumer eligibility
       -> candidate discovery and optimizer
    -> worker/outbox for durable asynchronous work
       -> capability-authorized retailer adapter
       -> future Swiggy Instamart interface, only after written authorization
```

The final Swiggy edge is future-only and is not implemented.

## 3. Security and Privacy Summary

### Implemented in the repository

- Passwords are hashed with Argon2id; plaintext passwords are not stored.
- Cartel sessions are server-managed and token material is stored as hashes.
- CSRF protection applies to state-changing authenticated requests.
- Implemented Google/GitHub OAuth handling is server-side; provider tokens are not sent to the browser as reusable tokens. Apple is not enabled.
- Retailer connections are owner-scoped and lifecycle-controlled.
- Credential Vault cryptography uses AES-256-GCM with associated-data binding to owner, connection, retailer, secret type, version, and reference.
- Vault access fails closed when a key provider is unavailable.
- Audit and structured logging paths exclude passwords, OTPs, cookies, and token material from ordinary payloads.
- Evidence preserves source/artifact/provenance metadata and fails closed on missing or conflicting authority.

### Incomplete or planned

- Production KMS/HSM or external secret-manager key custody.
- Instamart-specific OAuth client, token, refresh, and revocation lifecycle.
- Formal data-processing agreement and retention/deletion schedule.
- Privacy impact assessment for addresses, coordinates, serviceability, and delegated retailer access.
- External security audit or certification. No SOC 2, ISO, penetration-test, or regulatory approval is claimed.
- Production deployment-specific key rotation, backup, disaster recovery, and incident-response evidence.

### Intended Instamart privacy model, pending approval

Cartel would request only the minimum data required for the user's selected delivery context. Retailer credentials or refresh material would remain server-side, scoped to the owning Cartel user and retailer connection. Cartel would not store retailer passwords, OTPs, payment credentials, or UPI PINs.

User addresses, coordinates, serviceability results, product data, prices, availability, and derived recommendations would be retained, cached, displayed, or deleted only according to written Swiggy terms. Payment authorization would remain user-controlled at the retailer boundary.

## 4. Expected Usage and Traffic

The following are planning estimates only, not observed production traffic:

| Metric | Value | Status |
|---|---|---|
| Current production users | `TBD` | No production user base is claimed |
| Expected launch users | `TBD` | Owner must supply |
| Expected orders/day | `TBD` | Owner must supply |
| Expected Instamart tool calls/day | `TBD` | Owner must supply |
| Expected peak QPS | `TBD` | Owner must supply after workflow/load planning |
| Expected launch geography | India, subject to Swiggy coverage and approval | Product intent; final scope TBD |
| Burst/traffic events | `TBD` | Owner must supply |

Cartel will not submit fabricated traffic numbers. Swiggy's official application asks for expected volume and, for enterprise applicants, expected peak QPS and end-user geography. [Swiggy access requirements](https://mcp.swiggy.com/builders/access/)

## 5. Data Collection, Storage, Caching, Retention, and Display Declaration

Subject to written Swiggy authorization, Cartel proposes to collect only:

- stable retailer-native product identity;
- title, brand, pack, quantity, and variant attributes;
- location/address or coordinate context needed for serviceability;
- observed price and currency;
- explicit availability/inventory state;
- capture timestamp or freshness metadata;
- permitted retailer URL/reference;
- structured unavailable/error results.

Cartel proposes to:

- preserve source and capture provenance;
- match observations to exact governed Product/Variant records;
- display attributable observed Instamart facts beside other authorized retailer facts;
- cache or retain observations only for the period and purpose Swiggy authorizes;
- delete or refresh data according to Swiggy's written policy;
- derive basket recommendations without presenting listing observations as checkout totals;
- exclude unresolved, stale, unavailable, or conflicting facts from usable offers.

No Swiggy authorization currently covers these activities for Cartel.

## 6. Explicit Commercial Authorization Questions

Cartel requires written answers on:

1. Commercial cross-retailer grocery comparison.
2. Comparative display of Instamart prices, availability, and serviceability.
3. Competitive-intelligence or benchmarking classification.
4. Product catalog aggregation and exact Product/Variant matching.
5. Collection, storage, caching, retention, refresh, deletion, and redistribution.
6. Derived product-equivalence and basket-allocation recommendations.
7. Consumer OAuth/delegated authorization.
8. Address, coordinate, serviceability, and personal-data handling.
9. Cart preparation and checkout handoff.
10. Attribution, branding, liability, support, revocation, and termination.

Swiggy's published production-access rules currently restrict competitive intelligence and benchmarking, so generic developer approval is insufficient. [Swiggy production access rules](https://mcp.swiggy.com/builders/access/)

## 7. Zero-Budget Production Requirements

Cartel has no budget for paid API credits, subscriptions, platform fees, minimum commitments, or commercial data services.

Cartel requests confirmation that the proposed arrangement provides:

- free local development;
- free staging access;
- free production credentials;
- free production API usage;
- no mandatory API credits;
- no subscription or platform fee;
- no minimum commitment;
- no mandatory paid support or commercial data charge.

These are requests, not assumptions. Swiggy's public materials document free local development but do not establish sustainable zero-cost production access. Staging and production access are conditional on review/allowlisting, and enterprise commercial terms are negotiated per partner. [Swiggy onboarding](https://mcp.swiggy.com/builders/docs/operate/access/)

If either written commercial authorization or sustainable zero-cost production access is unavailable, the Instamart integration is commercially infeasible under Cartel's current constraints.

## 8. Technical Documentation Available on Request

Cartel can provide, subject to owner review:

- architecture and data-flow diagram;
- security/privacy questionnaire responses;
- data minimization and retention proposal;
- OAuth/delegated-access flow proposal;
- exact Product/Variant and evidence-provenance model;
- fail-closed unavailable/unresolved behavior;
- expected-traffic worksheet once owner values are supplied;
- local validation evidence for authentication, governed ingestion, adapter authorization, and Blinkit lockdown.

Cartel cannot provide the following as completed evidence:

- Instamart integration tests;
- Instamart credentials or production traffic;
- Swiggy authorization;
- production security certification;
- production user/customer metrics;
- production SLA or load results.

## 9. Verified Application Route and Requirements

Use the official [Swiggy Builders Club production-access page](https://mcp.swiggy.com/builders/access/). It links to Developer and Enterprise/Startup application tracks and publishes `builders@swiggy.in` as the support/contact route.

Published application inputs include:

- company details or individual developer profile;
- brief use case;
- architecture overview;
- exact authentication redirect URI(s);
- static IP ranges or gateway IPs;
- security contact;
- data-handling/privacy declaration;
- environment and infrastructure details;
- acknowledgement of Swiggy MCP terms;
- optional security audit summary;
- optional SOC 2/ISO information if available;
- optional expected traffic/scaling plan.

The onboarding documentation additionally identifies exact-match HTTPS redirects, expected volume, primary technical contact, and enterprise security attestations/peak QPS where available. `http://localhost` is allowed for local development; production redirect handling requires allowlisting. [Swiggy access and onboarding](https://mcp.swiggy.com/builders/docs/operate/access/)

### Currently unmet or owner-supplied fields

- Legal entity/company details: `TBD`.
- Registration details: `TBD`.
- Owner name and role: `TBD`.
- Primary technical contact: `TBD`.
- Security contact: `TBD`.
- Production HTTPS redirect URI: `TBD`; no Instamart callback exists.
- Static IP/gateway range: `TBD`; no production deployment value exists in the repository.
- Expected users, orders/day, tool calls/day, peak QPS: `TBD`.
- Security audit/certification: not available and must not be claimed.
- Commercial authorization: not obtained.
- Zero-cost production commitment: not obtained.

## 10. Manual Submission Checklist

- [ ] Owner supplies legal/entity identity.
- [ ] Owner supplies sender name, role, and primary technical contact.
- [ ] Owner supplies security contact.
- [ ] Owner supplies production HTTPS redirect URI, if applying for production access.
- [ ] Owner supplies static IP or gateway range after deployment architecture is finalized.
- [ ] Owner supplies traffic estimates without fabricating current users or orders.
- [ ] Owner reviews the cross-retailer disclosure.
- [ ] Owner reviews the competitive-intelligence/benchmarking question.
- [ ] Owner reviews the data collection/storage/caching/retention declaration.
- [ ] Owner reviews the zero-budget request.
- [ ] Owner attaches the architecture/security materials only after confirming no sensitive secrets or internal infrastructure details are included.
- [ ] Owner submits manually through the official access page or its linked application track.
- [ ] Owner records Swiggy's written response and commercial terms before any integration work.

## 11. Source Register

- [Swiggy Builders Club production access](https://mcp.swiggy.com/builders/access/) - official application inputs, review stages, operating restrictions, developer and enterprise tracks, and published support contact.
- [Swiggy access and onboarding](https://mcp.swiggy.com/builders/docs/operate/access/) - invite/review model, redirect requirements, required application information, staging/production sequence, revocation, and typical enterprise timeline.
- [Swiggy Instamart technical reference](https://mcp.swiggy.com/builders/docs/reference/instamart/) - documented Instamart tools including product search, variants, address context, cart, checkout, and tracking.
- [Swiggy MCP authentication](https://mcp.swiggy.com/builders/docs/start/authenticate/) - documented OAuth 2.1/PKCE, scopes, redirect handling, and token lifecycle.

## 12. Final Boundaries

- No application has been submitted.
- No email has been sent.
- No Swiggy account or credentials have been created.
- No OTP or OAuth flow has been initiated.
- No API call has been made.
- No paid credits or services have been consumed.
- No Instamart adapter has been implemented, registered, or invoked.
- Blinkit remains locked.
- No repository application code, configuration, schema, production data, or retailer behavior has been changed.

