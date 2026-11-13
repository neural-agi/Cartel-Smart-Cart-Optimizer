# Cartel Product Architecture v2.0

**Status:** Target architecture; proposed product direction, not a statement of shipped capability  
**Baseline inspected:** repository at the frozen `v0.1.0-deploy.1` release candidate; filesystem-backed prototype/deployment candidate  
**Purpose:** architectural source of truth for product evolution beyond the current prototype

This document defines what Cartel must become for a consumer to build a list, compare supported retailers, authorize a plan, and let Cartel orchestrate the work through retailer payment and order confirmation. It supersedes older product-roadmap descriptions for future work. It does not silently amend immutable identity, provenance, optimizer, or safety contracts: changes to those contracts require explicit decisions and migration tests.

## 1. Product North Star

Cartel is a shopping optimization and order-orchestration product. A user states what they need once. Cartel resolves exact purchasable variants, discovers current retailer offers and constraints, computes a governed allocation across retailers, explains the result, and—after explicit approval—prepares the required retailer carts and checkout sessions. The user retains the final retailer authorization/payment action. Cartel records retailer-confirmed orders and tracks them.

The product value is not a cheaper-looking comparison page. It is taking responsibility for coordinating equivalent items, quantities, retailers, baskets, fees, availability, checkout handoffs, and subsequent order status so the user does not have to recreate and reconcile the same shopping list in several retailer apps.

### Product goals

- One durable, user-owned shopping list with exact quantities and reusable preferences.
- Exact product/variant resolution, including brand, pack size, units, and other identity-critical attributes.
- Comparison based on fresh, attributable retailer evidence and checkout-relevant cost—not listing price alone.
- Multi-retailer allocation that honors coverage, delivery, basket, membership, and user constraints.
- Explainable recommendation, explicit user approval, reliable cart preparation, and clear payment handoff.
- Order history and status grounded in retailer-confirmed evidence.
- Honest unresolved/unavailable states and safe recovery from partial retailer failures.

### Non-goals and trust boundaries

- Cartel is not a payment processor, wallet, card vault, or UPI credential store.
- Cartel does not place an order or authorize payment without a deliberate user action at the supported retailer boundary.
- No bypass of retailer authentication, anti-bot controls, rate limits, access restrictions, or terms of service. A technically possible browser interaction is not automatically an allowed integration.
- No silent product substitution, pack equivalence, or brand substitution. The user may opt into an explicit substitution policy.
- No guaranteed stock, price, delivery time, savings, order acceptance, or retailer service level.
- No synthetic, fixture, listing-only, stale, or inferred data represented as live checkout or order evidence.
- No multi-region or horizontal-scale infrastructure before a real product requirement justifies it.

## 2. Current Repository Baseline

The repository is a technically substantial single-instance prototype/deployment candidate, not the consumer product described here.

| Capability | Current implementation and boundary |
|---|---|
| Product intelligence | Deterministic ingestion, evidence publication, canonical catalog resolution, product/variant matching, review queue, assertions, and filesystem-backed catalog/association/observation stores exist under `backend/app/product_intelligence`, `data_ingestion`, `normalization`, and `workers`. Canonical entities are governed; matching does not mint canonical IDs. |
| Retailer acquisition | Blinkit acquisition/parser/session code exists under `backend/app/scrapers/blinkit`. Live acquisition has been observed in permitted environments, but access varies. `bigbasket` and `zepto` packages do not constitute completed integrations. |
| Search | `GET /api/v1/products/search` queries the persisted governed catalog and listing associations; it is not a general live multi-retailer search. Search results expose canonical IDs, a Cartel listing association ID, observation provenance, observed price, and availability signal. |
| Cart UX | Frontend has a browser-local Zustand cart and search, cart, optimize, and results screens. The browser cart is not a durable server-owned shopping list and there is no cross-device user ownership model. |
| Planning and optimizer | Candidate discovery, enrichment, allocation/plan construction, deterministic plan identity, plan ranking/selection, and `POST /api/v1/cart/optimize` exist under `backend/app/cart_optimization` and `services`. Frozen feasibility, ranking, identity, and provenance semantics remain constraints. |
| Effective cost | Cost-intelligence components and checkout observation/ECE integration exist. The deterministic fixture path tests downstream contracts; fixture evidence is not production evidence. |
| Cart and checkout | Typed cart identity/line/snapshot/ownership contracts, strict Blinkit response parsing, capture artifacts, observation registration, and a Blinkit checkout adapter boundary exist. The live adapter is fail-closed; the production Compose configuration selects checkout unavailable. No live verified cart-to-order path is established. |
| Authentication | Current production deployment uses required configured bearer tokens. `/api/v1/auth/session` validates a configured token. The signup page explicitly says public signup is not supported. There are no consumer users, provider identities, password flows, or user-owned data authorization tables. |
| Persistence/database | Product, observation, lifecycle, checkout correlation, and planning records use filesystem-backed stores under `/app/data`. SQLAlchemy/Alembic/Redis dependencies and `backend/app/db` scaffolds exist, but there are no application domain tables or migration history establishing a PostgreSQL product store. |
| Deployment | Docker Compose is a single-host topology with frontend proxy, private backend network, and named `cartel-data` volume. It is not a multi-user database-backed or horizontally scaled target architecture. |
| Tests | Unit, API integration, product-intelligence, optimizer, checkout/ECE, and deterministic vertical-slice tests exist. The current test suite demonstrates contracts and deterministic paths; it does not prove consumer signup or live retailer order execution. |

The Compose fixture provider is not enabled. Current checkout being unavailable is an honest release state, not a feature to bypass. Earlier live Blinkit work established product identity/availability evidence for particular products but did not establish reusable cart ownership, checkout, payment handoff, order confirmation, or tracking.

## 3. End-to-End Target Journey

1. **Sign up and secure the account.** User verifies an email, Google/Apple identity, or phone number; completes account recovery setup; and accepts required privacy and retailer-session disclosures.
2. **Set shopping context.** User selects delivery address/zone, currency/locale, household preferences, and optional retailer memberships. Sensitive location data is private and purpose-limited.
3. **Create a shopping list.** User searches, enters free text, scans/imports where supported, or reuses a saved list. Every line retains the original request and quantity.
4. **Resolve exact products.** Cartel returns a confirmed canonical Product + ProductVariant or asks a focused clarification. User confirms ambiguous brand, size, count, flavor, or substitution choice.
5. **Discover current offers.** Cartel queries only supported retailer capabilities for the selected delivery zone and records listing, stock, price, promotions, fulfillment, source, timestamp, and freshness.
6. **Optimize.** Cartel evaluates feasible allocations, groups lines into retailer checkouts, computes checkout-derived effective cost where available, and compares only equivalent coverage. It exposes unknowns and delivery/checkout assumptions.
7. **Review and approve.** User sees exact products, quantities, retailers, line prices, checkout subtotals, fees, discounts, final totals, freshness, split-order count, delivery windows, and any unresolved evidence. Approval is bound to a versioned plan and quote snapshot.
8. **Prepare retailer carts.** Cartel revalidates freshness, availability, location, quantities, retailer identity, cart ownership, and totals. It prepares each supported retailer cart exactly once per idempotency key and reconciles ambiguous outcomes before retrying.
9. **Reach payment/authorization.** Cartel presents the legitimate retailer checkout/payment boundary. User completes any required retailer login, address confirmation, terms, OTP, and payment inside the retailer-controlled flow. Cartel does not receive/store card or UPI secrets.
10. **Record orders.** A retailer-confirmed order reference and status are required before Cartel labels a suborder placed. Prepared, awaiting-payment, submitted-but-unconfirmed, and confirmed are distinct.
11. **Track and recover.** Cartel shows each retailer order independently, status timestamps, delivery updates, and partial failures. User can retry only safe operations, resume a handoff, or cancel through supported retailer capabilities.

The critical UX promise is “one list and one orchestration flow,” not “one payment can always authorize several independent retailers.” Retailer payment authorization may still happen separately for each retailer.

## 4. Target System Shape

```text
Web / mobile clients
        |
Same-origin BFF / API edge -- authentication, authorization, request limits
        |
Application API
  |-- Accounts and user-owned lists
  |-- Product search / resolution / review
  |-- Retailer discovery and quote snapshots
  |-- Planning, cost intelligence, optimizer
  |-- Approval and order orchestration
  |-- Order history and tracking
        |                       \
PostgreSQL + object store       Transactional outbox / job workers
                                      |
                               Retailer capability adapters
                                | official APIs
                                | permitted isolated browser flows
                                | user-assisted checkout handoff
                                      |
                                Retailer systems
```

### Service boundaries

- **Web/BFF:** same-origin browser API, session-cookie management, CSRF controls, static assets, and response shaping. Do not expose internal service names to browsers. The current Next.js proxy is a useful starting point; current browser-held bearer token is transitional.
- **Application API:** modular monolith initially. Modules own transactions and authorization boundaries; avoid prematurely splitting services. FastAPI remains a viable implementation baseline.
- **PostgreSQL:** authoritative store for users, identities, lists, catalog governance, quote snapshots, optimization runs, approvals, order state, idempotency, and outbox jobs.
- **Artifact/object store:** immutable raw/sanitized retailer artifacts, large evidence payloads, and parser inputs, encrypted and access-controlled. PostgreSQL stores metadata, digest, retention, and access policy.
- **Workers:** asynchronous acquisition, retailer polling, reconciliation, notifications, and order state transitions. Start with a durable database outbox and worker leases; add Redis/broker only when measured throughput or latency warrants it.
- **Retailer adapters:** capability-based boundary with standardized evidence and operation results; each adapter is independently enabled only after policy, security, and correctness validation.
- **Redis:** optional derived cache, short-lived coordination, and rate-limit acceleration. Never the sole authority for orders, idempotency, approval, or durable jobs.

## 5. Identity, Authentication, and Tenant Authorization

### Consumer identity model (proposed)

- `User` is the stable internal principal; public email/phone/provider IDs are not primary foreign keys.
- `AuthIdentity` records an issuer/provider plus provider subject, verified contact state, and timestamps. Enforce uniqueness on `(issuer, subject)`; treat email normalization/change and duplicate-link cases explicitly.
- Support email + password, Google OIDC, Apple OIDC, and phone OTP as separate identity methods attached to one user only through verified, recently reauthenticated account linking.
- Passwords use a memory-hard password hash (Argon2id with reviewed parameters), never reversible encryption. OTP values are short-lived, single-use, stored hashed, attempt-limited, and delivered through a selected provider. OTP is not a durable password.
- OIDC uses state, nonce, PKCE where applicable, exact redirect URIs, issuer/audience/signature validation, and replay protection. Apple private relay addresses require normal verified-address handling.
- Signup, email/phone verification, password reset, account recovery, provider unlinking, and account deletion are explicit state machines with abuse limits and audit events. Recovery must not silently lower account assurance.
- Sessions are random, opaque, server-revocable, stored hashed, rotated on authentication/privilege change, and bound to expiry/last use/device metadata. Browser sessions use `HttpOnly`, `Secure`, appropriate `SameSite`, narrow-path cookies plus CSRF protection. Do not put long-lived auth tokens in local/session storage for the consumer product.
- Provide logout-current, revoke-all, session/device management, and credential-change revocation. Auth events are security audited without OTPs, tokens, or provider secrets.

### Authorization

Every user-owned request resolves a principal from the authenticated session and applies ownership in the service/database query. Never trust `user_id`, `cart_id`, list ID, plan ID, or retailer session ID supplied by the client as authorization proof. Use database constraints and application authorization; consider PostgreSQL row-level security as defense in depth after transaction-local principal propagation is proven.

Platform catalog and shared observations are global governed data. Shopping lists, addresses, preferences, memberships, retailer connections, optimization runs, approvals, carts, orders, and private artifacts are tenant-owned. Cross-tenant access tests are release-blocking.

### Migration from bearer-token prototype

Keep current `AUTH_REQUIRED=true` for the frozen deployment. The fixed `AUTH_TOKENS` map identifies deployment principals, not consumer accounts. Do not convert token labels into verified email identities. The consumer-auth phase adds a separate identity/session service and explicit operator/admin bootstrap; migrate users only through verified invitations or signup. Retire configured API tokens from browser use after the new session boundary is deployed. Machine/service credentials remain separate, scoped, rotated, and never accepted as consumer login.

## 6. Data Ownership and PostgreSQL Model

Use PostgreSQL migrations (Alembic is already a dependency/scaffold) and transactions for application records. UUID/ULID identifiers are opaque, stable, and non-semantic. Store money as integer minor units plus ISO currency; quantities as validated decimal/unit values where item-level units require them. Persist UTC instants, source timezone where relevant, schema versions, and immutable provenance references.

| Entity | Core purpose / relationships |
|---|---|
| `users` | Principal, account state, locale, created/deleted timestamps; no credentials embedded in unrelated rows. |
| `auth_identities` | User FK, provider/issuer, provider subject or normalized verified contact, verification and lifecycle state; uniqueness and unlink constraints. |
| `password_credentials`, `verification_challenges`, `sessions` | Separate sensitive auth records; hashed secrets only, expiry/attempt/revocation data, aggressive retention limits. |
| `user_addresses`, `user_preferences`, `retailer_connections` | Tenant-owned location and optional retailer account connection. Credentials/session material envelope-encrypted with external KMS-managed keys; access scoped to one user + retailer adapter. |
| `shopping_lists`, `shopping_list_items`, `list_revisions` | Owner, name, revision, archival state. Items retain raw intent, requested quantity/unit, canonical resolution state, confirmation, and sort position. Revision supports optimistic concurrency and immutable optimization input. |
| `canonical_products`, `canonical_variants`, `brands`, `categories`, `identity_assertions` | Shared governed catalog; stable canonical IDs, revision/status, pack/identity attributes, evidence, effective dates, reviewer decision. Do not auto-create approved identities from a name match. |
| `retailer_products`, `retailer_product_references`, `listing_associations` | Retailer-native product/listing identity and URL/reference kept distinct from Cartel `platform_listing_id` and canonical IDs. Mapping state, merchant/variant, locality, and governance decision are explicit. |
| `retailer_observations`, `quote_snapshots`, `availability_observations`, `price_observations` | Append-only evidence with source artifact/digest, parser version, observed-at, valid-until, location/merchant scope, currency, availability certainty, and capture result. |
| `optimization_runs`, `candidate_plans`, `plan_allocations`, `checkout_groups`, `ece_evaluations` | Owner, list revision, request identity, deterministic plan identity, policy/catalog revisions, candidate coverage, allocations, ECE links, outcome, provenance, and expiration. Preserve request ID distinct from deterministic plan ID. |
| `plan_approvals` | User, exact plan/revision/quote digest, disclosed totals and expiry, approval timestamp, terms/policy versions, revoke/expire state. Approval is not payment authorization. |
| `retailer_carts`, `retailer_cart_lines`, `checkout_sessions` | User + operation + retailer connection, opaque external references only when retailer exposes them, expected/observed lines, quantity, verification status, correlation key, source evidence, expiry. Browser session ID is not cart identity. |
| `orders`, `order_items`, `order_attempts`, `order_status_events` | Cartel order group and per-retailer suborders; explicit state, external retailer order ID only when confirmed, immutable attempts/events, failure and reconciliation evidence. |
| `idempotency_records`, `outbox_jobs`, `audit_events` | Scope by user/operation/key; request digest, result reference, lease/attempt state; append-only actor/action/object/time/outcome audit. Never store bearer/OTP/payment secrets in payloads. |

Foreign keys, uniqueness constraints, tenant predicates, and serializable/locked transitions protect critical state. Large raw artifacts may live in encrypted object storage; every database reference includes content digest, classification, retention, and owner/access policy. Catalog migration preserves existing canonical IDs and provenance rather than re-keying them.

## 7. Shopping Lists and Persistent User State

The list is the user's durable intent, not a retailer cart. Persist `list_revision` and each line's `item_id`, raw query, optional confirmed product/variant, quantity and unit, substitution policy, notes/preferences, and resolution state. The frontend may cache for responsiveness but PostgreSQL owns saved state, cross-device synchronization, and conflict detection.

Editing a list creates a new revision or increments a guarded version. An optimization run references an immutable revision; changes invalidate the displayed result/approval. Guest/local-only lists may be offered only as explicit pre-signup behavior with a clear migration/merge flow and no server-side retailer action until authenticated.

## 8. Product Search, Canonicalization, and Exact Variant Resolution

### Evidence and identity pipeline

```text
user words / scan / import
  -> normalized intent (raw input retained)
  -> canonical product-family candidates
  -> exact canonical variant candidates
  -> retailer-specific listing candidates
  -> verified local offer/availability snapshot
  -> user-confirmed list line or explicit unresolved outcome
```

- Distinguish canonical `Product` (family), canonical `ProductVariant` (purchasable size/pack/identity), retailer-native product/variant, retailer listing/reference, observation, and Cartel listing association. Never collapse these identifiers.
- Identity-critical evidence includes brand, product type, flavor/form, net content, count, package/pack kind, and regulated or dietary attributes when present. Unit conversion is allowed only under governed compatible dimensions/basis. Multipacks, combos, assortment packs, and “each” versus weight-based quantities require explicit semantics.
- Keep the original query and evidence. Normalize spelling/units but do not discard qualifiers. Search aliases and synonyms are retrieval aids, not proof of identity.
- Use deterministic candidate generation and existing matching/review contracts as a base. Add calibrated confidence only after a labeled evaluation set exists; report score, factors, model/rule version, and calibration range. A raw heuristic score must not be called a probability.
- Outcomes: `EXACT_CONFIRMED`, `NEEDS_USER_CONFIRMATION`, `AMBIGUOUS`, `NO_MATCH`, `CATALOG_REVIEW_REQUIRED`, and `SOURCE_UNAVAILABLE`. Product/variant identity mismatch is not “close enough.”
- Default automation may select only governed exact variants meeting an approved threshold with no critical attribute conflict. Below threshold, show a compact comparison and ask. Substitution is a separate user policy applied after exact product availability is known.
- Retailer mappings are evidence-backed and versioned. A retailer product ID or URL must originate from retailer evidence; `source_index`, display name, result order, and `platform_listing_id` are not identity substitutes.

Current modules to build on: `product_intelligence/{evidence,ingestion,candidate_generation,matching,review,assertions,catalog}`, `data_ingestion`, `normalization`, and governed catalog tooling. The manually curated catalog and deterministic matchers remain useful launch controls; do not replace them with an unreviewed probabilistic model.

## 9. Retailer Discovery and Adapter Architecture

### Capability contract

Each retailer is a versioned adapter plus an explicit capability declaration, not a boolean “supported” flag. Capabilities are independently enabled and tested:

| Capability | Contract output / safety gate |
|---|---|
| Search and listing discovery | Query, delivery zone, filters; paginated retailer-native references, result coverage/completeness, captured time, rate limit state. |
| Product detail and identity | Requested retailer product/variant ID must equal retailer-observed ID; typed pack, merchant, URL, and evidence. |
| Price, stock, fulfillment | Currency/minor units, availability enum, merchant/zone, delivery promise, source and expiry. Unknown is not available; stale is not current. |
| Cart read/mutate | Isolated retailer connection, exact product ID/quantity, normal authorized action, explicit result/line/cart references if exposed, before/after snapshot, idempotency or reconciliation semantics. |
| Checkout prepare/capture | Cart ownership verified, non-payment totals and terms captured, field completeness/provenance/freshness, no order/payment submission. |
| Payment handoff / order placement | Supported retailer-native user authorization boundary. Submit only after explicit approval and authorization; record attempt and result. |
| Order lookup/tracking/cancel | External order ID, authoritative status event and time; cancellation/refund only where the retailer supports it and the user requests it. |

Use separate typed methods/results per operation and capability states `SUPPORTED`, `UNAVAILABLE`, `NOT_IMPLEMENTED`, `ACCESS_DENIED`, `RATE_LIMITED`, `INVALID_EVIDENCE`, and `REQUIRES_USER_ACTION`. An unsupported method must not succeed with fabricated fixture values. A capability registry is scoped by retailer, market/zone, account mode, adapter version, and evidence freshness.

### Integration tiers

1. **Official partner/API:** preferred. Document permission, OAuth scopes, quotas, data retention, webhook signatures, sandbox/live distinction, and merchant/zone semantics. Use retailer-issued idempotency where supported.
2. **Permitted browser automation:** only when retailer terms and access policy explicitly allow the flow. Use normal UI/network behavior, per-user isolated browser contexts, bounded waits, and no stealth, anti-bot evasion, guessed endpoints, or shared user cookies. Treat access denial/Cloudflare as a stop, not a challenge to bypass.
3. **User-assisted handoff:** Cartel may present a retailer deep link or handoff only when retailer reference is authoritative and user-facing behavior is legitimate. Cartel marks cart/checkout/order states unavailable unless independently verified.
4. **Unsupported:** show retailer as unavailable/not supported and optimize only among remaining eligible retailers when the user permits; otherwise return no feasible plan.

An adapter result carries retailer, capability/version, `(user_id, operation_id, request_id, plan_id)`, retailer-native references, location/merchant scope, timestamps/expiry, content digest/evidence references, sanitized diagnostics, and a typed outcome. Secrets and full browser/network bodies are never ordinary logs or API fields.

Current reality: Blinkit product acquisition and parsing exist; live cart/checkout is not verified and production mode is unavailable. A strict parser can consume explicit cart IDs/line IDs but that contract does not prove Blinkit exposes them in a successful live operation. BigBasket/Zepto folders are not supported integrations. Do not list a retailer as order-capable until a capability-specific acceptance suite passes.

## 10. Quote, Effective Cost, and Optimization

### Quote integrity

A quote is a time- and zone-scoped snapshot, not a timeless catalog price. It includes exact retailer product/variant mapping, quantity basis, stock state, line price, tax inclusion/status, promotions, applicable delivery/handling/service fees, minimum basket constraints, membership assumptions, delivery window, captured time, expiry, and evidence. Revalidate before cart mutation and again at checkout when the retailer changes the quote.

### Effective-cost model

Keep the existing `Money`/minor-unit and `EffectiveCostEvaluationResult` semantics as a base. Define the comparable immediate payable amount from verified checkout components:

```text
verified immediate cost = verified item subtotal
                         + applicable mandatory immediate fees/taxes
                         - applicable immediate discounts
```

Deferred cashback/points, uncertain membership value, and conditional future benefits are separate values; never silently subtract them from payable cost. Unknown/missing components remain explicit and can make a plan unrankable. A retailer final payable total is preserved as observed and reconciled to components within a defined tolerance; discrepancies become unresolved evidence, not a corrected invented number. Currency conversion requires a timestamped approved FX source and remains distinguishable from native-currency payable totals.

Savings require a named, reproducible baseline (for example, feasible single-retailer purchase of the same exact quantities, with equivalent delivery/membership assumptions). Show baseline, optimized cost, included benefits, currency, quote times, retailer split, and formula. Suppress savings when comparison is incomplete, stale, or non-equivalent.

### Allocation and ranking

Enumerate/solve allocations subject to:

- exact requested canonical variants and quantities, with explicit governed unit semantics;
- verified retailer listing match and current availability in the user's delivery zone;
- complete coverage unless the user explicitly requests partial fulfillment;
- one checkout group per actual retailer order/session/merchant boundary as declared by adapter evidence;
- basket minimums, fees, delivery windows, membership consent, user retailer preferences, maximum split count, and any item-specific constraints;
- checkout evidence required for checkout-cost ranking. Listing-price-only candidates may be shown as provisional observations but cannot become a verified cheaper checkout plan.

Return a set of feasible, unresolved, and rejected plans with component costs, ECE IDs, evidence/freshness, and constraints. Preserve existing invariants: deterministic CandidatePlan IDs and tie-breaks, plan ID independent of `request_id`, declared feasibility is not mutated, ranking is not recommendation, and only a valid selected plan is labeled ready. Add policy versioning with explicit migrations, not hidden optimizer semantic changes.

## 11. Approval, Cart Preparation, Payment Boundary, and Orders

### Approval snapshot

Approval is attached to the exact immutable optimization run/plan, list revision, retailer allocation, quote digests, totals/currency, disclosure, and expiration. Any change in product, quantity, retailer, fees, total beyond user-approved tolerance, or freshness invalidates approval and requires review. “Approve plan” authorizes preparation only; it is not payment consent unless the retailer flow explicitly obtains it.

### Order orchestration state machine

Model an order group and one suborder per retailer checkout. Example states:

```text
DRAFT -> OPTIMIZED -> AWAITING_USER_APPROVAL -> APPROVED
  -> PREPARING_CART -> CART_VERIFIED -> CHECKOUT_READY
  -> AWAITING_RETAILER_AUTHORIZATION -> SUBMISSION_PENDING
  -> SUBMITTED_UNCONFIRMED -> CONFIRMED -> FULFILLING
  -> DELIVERED
```

Side exits include `STALE_REQUIRES_REVIEW`, `UNAVAILABLE`, `ACCESS_DENIED`, `CART_MISMATCH`, `PAYMENT_DECLINED`, `SUBMISSION_UNKNOWN`, `REJECTED`, `CANCEL_REQUESTED`, `CANCELLED`, and `PARTIALLY_COMPLETED`. State transitions are append-only events with actor, source evidence, adapter version, idempotency key, timestamps, and allowed predecessor checks. A prepared cart or a click that timed out is never labeled an order.

### Idempotency, concurrency, and partial failure

- Every external mutation has a stable key scoped to user, retailer connection, order attempt, and operation. Repeating an identical request returns its recorded state; a conflicting payload with the same key is rejected.
- Persist intent/outbox event transactionally before dispatch. Workers claim leased jobs with bounded attempts, fencing/lease expiry, and heartbeats. External I/O occurs outside long database transactions; result/event is committed with compare-and-set state/version.
- Retry reads and operations explicitly documented idempotent. After timeout on a non-idempotent add/submit, first reconcile retailer state using authoritative references; never blindly repeat.
- Per-user/list revision and per-retailer connection locks prevent concurrent cart preparation. Expired locks are fenced; late workers cannot overwrite newer state.
- Multi-retailer execution is a saga, not an atomic transaction. Each suborder succeeds/fails independently. Never claim all-or-nothing. Do not automatically remove user cart contents or compensate with a destructive action absent an explicit adapter contract and user consent.
- If one retailer fails before payment, present successful prepared groups and actionable failures. User chooses continue, retry after safe reconciliation, or abandon. If some orders are confirmed and others fail, preserve the confirmed orders and show a partial outcome; do not restart completed orders.

### Payment and retailer authorization

Cartel never collects/stores PAN, CVV, UPI PIN, OTP for payment, or payment tokens. The payment page, app handoff, or retailer authorization surface is retailer-controlled. Cartel may store only non-secret handoff correlation and safe state. Any retailer login/session credential storage is separate from payment credentials, opt-in, encrypted using envelope encryption and KMS, tightly scoped, revocable, and only implemented if retailer policy permits. If a retailer requires unsupported CAPTCHA/anti-bot/payment handling, stop and request user assistance or mark that operation unavailable.

Place/submit an order only after a clear user action at the legitimate retailer authorization boundary. Record the retailer's accepted order ID/status response or signed webhook. Timeout after submit is `SUBMISSION_UNKNOWN` until reconciled; never assume failure and resubmit, or assume success without confirmation.

### Order history and tracking

Persist order group, retailer suborders, exact order line identity/quantity, user-visible amount/currency, retailer confirmation reference, timestamps, delivery estimate, and append-only status events. Use verified retailer webhooks first, authenticated polling within quotas second, and user-provided updates only labeled as such. Status freshness is visible. Cancellation/refund states require retailer confirmation. Retain orders per published policy; support export and account deletion constraints.

## 12. Frontend Information Architecture

1. **Public landing and trust page:** supported areas/retailers, price/stock freshness caveats, payment boundary, privacy, clear capability matrix. No fabricated testimonials or savings.
2. **Signup / sign-in / recovery:** email, Google, Apple, phone OTP; verification and security/session recovery.
3. **Onboarding:** delivery zone/address, preferred retailers, memberships, substitution and split-order policy, consent.
4. **Shopping lists:** saved lists, revisions, add/search/import, quantities and units, completion/archive.
5. **Product resolution:** exact product/variant candidates with size/brand/pack evidence; compare listing candidates; explicit confirmation for ambiguity.
6. **Offer comparison:** current availability, retailer, listing price, stale/unavailable markers, merchant/zone, fulfillment and source time.
7. **Optimization review:** allocation, exact lines, checkout components, ECE status, quote expiry, split count, delivery, savings baseline, rejected alternatives, unresolved reasons.
8. **Approval and execution progress:** version-bound approve/cancel, per-retailer cart preparation and checkout handoffs, payment boundary, retry/reconcile actions.
9. **Orders:** order group/suborders, confirmation state, delivery tracking, partial failures, history and detail.
10. **Account/settings:** identities, active sessions, addresses, retailer connections, memberships, privacy/export/delete, notification preferences.

Every server result has an explicit UI state: loading, empty, exact-ready, needs-confirmation, unresolved, unavailable, stale/reconfirm, retailer access denied, rate limited, partial execution, submission unknown, and error. A result page cannot infer success from a non-null payload or listing price. Show source/freshness and keep payment/order confirmation language precise.

Current frontend `app/(app)`, `services`, `types`, `store`, `apiClient`, auth pages, and Next proxy are a visual/interaction starting point. The current token-in-sessionStorage login and browser-local cart are replaced by server sessions and persisted list state; preserve useful screen components only after accessibility, state, and API-contract review.

## 13. Backend/API Architecture

Keep a modular monolith until team/scale boundaries justify a split. Suggested bounded modules:

- `identity`: auth flows, sessions, account linking, authorization policy.
- `catalog`: canonical product/variant governance and retailer mapping.
- `shopping`: lists, revisions, intent, item resolution.
- `retailers`: capability registry, adapters, credential/session broker, quote and evidence capture.
- `optimization`: candidate enumeration, policies, ECE, deterministic optimizer.
- `orders`: approvals, order groups, orchestration state machine, idempotency, outbox, reconciliation.
- `tracking`: retailer status intake and user-visible history.
- `platform`: config, observability, rate limits, health, artifact storage.

API contracts should be versioned by consumer workflow, not expose internal ORM entities. Candidate endpoints (future; not current routes):

```text
POST   /api/v2/auth/signup | /auth/login | /auth/refresh | /auth/logout
POST   /api/v2/auth/verify-email | /auth/verify-phone | /auth/password-reset/*
GET    /api/v2/me | /api/v2/me/sessions
GET/POST/PATCH /api/v2/lists[/{list_id}] and /items
GET    /api/v2/products/search?q=...&zone_id=...
POST   /api/v2/product-resolutions (confirm/reject exact variant)
POST   /api/v2/retailer-quotes (async job/run reference)
GET    /api/v2/retailer-quotes/{run_id}
POST   /api/v2/optimization-runs
GET    /api/v2/optimization-runs/{run_id}
POST   /api/v2/optimization-runs/{run_id}/approvals
POST   /api/v2/order-groups/{id}/prepare | /resume | /cancel-request
GET    /api/v2/order-groups | /api/v2/orders/{id}
POST   /api/v2/retailer-webhooks/{retailer} (signature-verified ingress)
```

Long retailer work returns a job/run ID and explicit state; clients poll or subscribe using an authenticated, tenant-scoped channel. Mutations require idempotency keys, request IDs, optimistic list/run version, and explicit consent. Expose stable problem codes, safe user messages, retryability, and correlation IDs; never serialize retailer secrets or unredacted raw payloads.

Current `/api/v1` routes remain migration inputs: product search, cart resolve/candidates, explicit/automatic planning, checkout capture, cost evaluation, observations, scrape, and health. Keep V1 for the frozen deployment; do not pretend it already supports V2 signup, user lists, or orders.

## 14. Background Work and Freshness

Begin with PostgreSQL transactional outbox plus independently supervised worker processes. Persist job intent, dedupe key, lease, attempt count, next retry, deadline, cancellation, and sanitized failure. Use bounded concurrency per retailer/zone/account and per user. Jobs include search fanout, detail/availability refresh, quote assembly, optimization, cart preparation, checkout refresh, order reconciliation, and tracking.

Only add Redis or a message broker after measured need for fanout/throughput, and retain durable DB state as authority. Use provider-specific circuit breakers, shared rate budgets, jittered backoff only for safe/retryable operations, deadlines, and queue-age/lag monitoring. Stop on access denied and honor `Retry-After`; do not evade protection. Freshness thresholds are operation-specific: an old catalog mapping can still identify a product, but cannot prove current stock or payable total.

## 15. Security, Privacy, and Trust

- **Isolation:** every object lookup/mutation is user-scoped; every retailer browser profile/context and connection is isolated by user + retailer account + environment. Never share cookies/local storage between tenants. Do not use browser/session ID as retailer cart ownership.
- **Credentials:** use KMS-backed envelope encryption with key rotation, access auditing, purpose scoping, and deletion/revocation. No credentials in source, images, request logs, traces, analytics, crash reports, artifacts, or support exports. Secrets are not API response fields.
- **Browser automation:** approved host allowlists, normal UI path, least privileges, ephemeral or encrypted per-user profiles, bounded recording, no stealth/evasion, no arbitrary URL navigation from user input, and explicit cleanup/retention. Sanitized diagnostics redact headers, cookies, tokens, device identifiers, and payment information before persistence.
- **Payment:** redirect/retailer-native user authorization. Never capture card/UPI secrets or automate payment confirmation. Scope PCI review if product design changes this boundary; default architecture forbids it.
- **Authorization:** secure/HttpOnly/SameSite cookies, CSRF defense, CSP, TLS, OAuth PKCE, password/OTP abuse protection, login/session revocation, account enumeration resistance, secure recovery, and audit trails.
- **Data:** minimize addresses and purchase history; encrypt backups; retention/deletion/export policies; tenant-scoped artifact authorization; avoid storing raw HTML unless necessary, with short retention and access controls.
- **Abuse/availability:** per-IP, per-user, per-retailer/connection rate limits; bot/credential-stuffing controls on auth; quotas for expensive searches; safe circuit breaker behavior.
- **Audit:** append actor, tenant, operation, object IDs, consent version, idempotency key, transition, result, source, and time. Never log auth tokens, OTPs, cookies, payment fields, full browser storage, or full retailer response bodies.
- **Supply chain/operations:** dependency pinning, migration backup/rollback plan, least-privilege DB roles, encrypted secret delivery, restore exercises, security patching, and reviewed adapter permissions.

## 16. Failure Semantics

Failures are first-class domain outcomes, not empty arrays or guessed values. Preserve existing `ready`, `unresolved`, `unavailable`, retailer-access-denied, out-of-stock, and no-plan distinctions while extending with stable typed states.

| Condition | Product behavior |
|---|---|
| Exact product/variant unavailable | `NO_MATCH` or `NEEDS_USER_CONFIRMATION`; no silent substitution. |
| Retailer has no matching listing | That retailer is excluded with reason; if coverage incomplete, plan unresolved or no plan per explicit partial-fill policy. |
| Retailer access denied / rate limited | Stop the affected operation, honor cooldown, preserve sanitized reason, mark retailer capability unavailable; no retry bypass. Other supported retailers may continue only if user policy allows. |
| Stock unknown/out of stock | Unknown is not in stock. Out-of-stock lines cannot enter executable allocations. Refresh before mutation. |
| Price/checkout evidence stale | Require refresh and possibly reapproval. No old payable total presented as current. |
| Checkout total missing/malformed/inconsistent | No checkout-backed ECE or success; expose unresolved cost components. Never convert missing fee to zero. |
| Cart ownership/line mismatch | Stop before payment; do not delete unrelated contents; present reconciliation/support path. |
| Cart prepare times out after mutation | `MUTATION_UNKNOWN`; inspect authoritative retailer state before any retry. |
| Payment refused/cancelled/OTP required | Retailer-owned result; no payment secret retained. Keep order pending/failed according to evidence, allow user-directed continuation. |
| Submit timeout/order ID absent | `SUBMISSION_UNKNOWN`, reconcile before retry. Not “placed.” |
| Partial multi-retailer outcome | Show each confirmed/prepared/failed suborder separately; preserve completed work; never claim a single complete order. |
| Tracker unreachable or stale | Show last verified event and timestamp with stale state, not a fabricated current status. |
| Database/worker failure | Durable job/run remains resumable; no duplicate external mutation; surface safe retry/support ID. |

Each result includes stable code, user-safe message, affected item/retailer/order, retryability, required user action, evidence/freshness, and correlation IDs. Unexpected programming failures are observable internally but not returned as stack traces.

## 17. Migration from Current Cartel

### Retain

- Canonical Product/ProductVariant identity contracts, evidence references, governance/review workflow, catalog snapshots, and the distinction between canonical, platform listing, retailer product, cart, and cart-line identity.
- Normalization and immutable ingestion/acquisition provenance contracts.
- Deterministic candidate generation/matching, quantity semantics, candidate allocation, deterministic plan IDs/tie-breaking, explicit feasibility, and optimizer ranking semantics.
- Money/evidence contracts, checkout observation/ECE pipeline, typed unavailable/fail-closed results, strict Blinkit identity parser, and deterministic fixture tests (fixtures remain test-only).
- API integration tests and security/failure regression tests; frontend layout/components where product-state and accessibility review passes.

### Refactor and extend

- `backend/app/data_ingestion`, `product_intelligence`, catalog, observation, and artifact stores: preserve schemas/IDs/provenance; add PostgreSQL repositories behind existing interfaces and a one-way verified importer.
- `cart_optimization` and `cost_intelligence`: preserve deterministic contracts; make runs/list revision/quote freshness durable and tenant-scoped; add policy evolution only through reviewed versions.
- `scrapers`: evolve Blinkit-specific scraper toward the capability adapter contract; add retailer integrations only after permission and evidence tests. Do not generalize unproven Blinkit behavior into universal cart semantics.
- `api/routes`, `main.py`, `core/security.py`: retain V1 compatibility; add V2 identity/list/run/order APIs and authorization dependencies. Replace configured end-user token lookup with session principal, preserving separately scoped operator/service auth.
- `frontend/app`, `services`, `types`, `store`, `lib/apiClient.ts`: keep useful views, add product resolution/approval/orders, migrate browser cart to server list revisions, and replace sessionStorage bearer auth with secure session flow.
- `backend/app/db`, `alembic.ini`: turn empty SQLAlchemy/Alembic scaffolds into tested metadata/session/migrations. Current `postgres_*` and `redis_url` settings are not evidence of an active database runtime.

### Replace or deprecate

- Replace filesystem stores as the authoritative mutable user/application database after verified import and cutover. Retain immutable raw artifacts in a governed object store or retention-managed archive. Never delete source data before digest/count/identity reconciliation and rollback window completion.
- Deprecate browser-local Zustand cart as authoritative saved state; keep it as an offline/UI cache only.
- Deprecate static `AUTH_TOKENS` as consumer authentication. Keep a separate break-glass admin/service mechanism with rotation and audit.
- Retire manual/demo scripts as production workflows after operational tooling exists. Keep fixtures and demos clearly test-only.
- Retire `/api/v1` only after clients, operators, and any integrations migrate with usage evidence and a published deprecation window.

### Data cutover sequence

1. Define import schemas and catalog/observation/artifact manifests; snapshot and checksum current filesystem state.
2. Create PostgreSQL migrations, tenant/global ownership rules, and a read-only importer. Preserve original IDs, timestamps, evidence references, policy versions, and artifact digests.
3. Reconcile entity/association/observation counts and deterministic lookup/serialization results; reject conflicts instead of selecting a winner.
4. Cut new writes to PostgreSQL once comparison gates pass. Avoid indefinite dual-write; if temporary shadow writes are used, make one store authoritative and reconcile every mismatch.
5. Keep source filesystem read-only for an agreed rollback period; document rollback and migration compatibility. Do not import current admin tokens as verified users.
6. Backfill users only through verified signup/invitation. Global canonical catalog remains distinct from user-owned shopping data.

## 18. Phased Implementation Roadmap

Prioritize a small, real product journey over generic platform infrastructure. Each phase ends with a user-observable capability and live/evidence acceptance; do not start order automation before a retailer is legitimately operable.

### Phase 0 — Product and retailer capability gate

- Select launch geography, supported categories, retailer shortlist, retailer-account assumptions, and initial user cohort.
- Obtain written clarity on official API/automation permissions, login, cart, checkout handoff, order confirmation, rate limits, and data rules for each target.
- Run a capability proof for at least one retailer in the launch zone. If no lawful, stable path reaches cart/checkout, adjust launch promise before building deeper execution.
- Define exact-variant policy, allowed substitutions, delivery/savings baseline, freshness TTLs, max split orders, and partial-fill defaults.

### Phase 1 — Real accounts and durable lists

- PostgreSQL/Alembic foundation, tenant auth/session model, signup/verification/recovery, authorization tests, server-owned lists/revisions.
- Migrate governed global catalog/observation data with reconciled provenance.
- Deliver: a real account can save/edit a list, sign in on another device, revoke a session, and recover access.

### Phase 2 — Search and exact product resolution

- Search indexed catalog plus permitted retailer discovery; support free-text intent, exact variant pack/quantity, user confirmation, and unresolved review.
- Add a focused resolution UX and measurable labeled evaluation set; instrument correction rates.
- Deliver: a list contains confirmed canonical variants with no inferred pack substitutions.

### Phase 3 — Live retailer offers

- Integrate the first retailer's permitted search, product identity, zone availability, price, and freshness capabilities. Add a second retailer only after comparable data quality.
- Build quote snapshots, offer provenance, and stale-state refresh. Distinguish acquisition from cart/checkout support.
- Deliver: user sees real, sourced offers for exact variants in the chosen location; unsupported capabilities remain visible.

### Phase 4 — Governed optimization

- Preserve optimizer contracts while adding current quote constraints, same-currency comparisons, split limits, and reproducible savings baseline.
- Evaluate fixtures in CI, then acceptance against real quotes; no fixture in production.
- Deliver: recommendation is deterministic, explainable, fully covers the list or clearly states partial coverage, and exposes quote expiry.

### Phase 5 — Approval and cart preparation

- Implement durable approval snapshots, one retailer adapter cart flow, ownership/line verification, idempotency, reconciliation, and recovery UI.
- Test mutation timeouts, unexpected pre-existing items, price changes, worker restart, and user cancellation against retailer-authorized sandbox/live conditions.
- Deliver: explicit user approval prepares an exact retailer cart; no payment/order is claimed and ambiguous state cannot proceed.

### Phase 6 — Checkout handoff and retailer-confirmed orders

- Add legitimate checkout preparation and retailer-native user authorization/payment handoff; only then order submission/confirmation where permitted.
- Persist per-retailer order groups, unknown-submit reconciliation, status events, and partial outcomes.
- Deliver: user completes retailer authorization; Cartel records only retailer-confirmed orders and supports return-to-history.

### Phase 7 — Multi-retailer orchestration and tracking

- Enable multiple retailer suborders, bounded parallel preparation, independent completion/failure, retailer webhooks or permitted polling, notifications, cancellation and support workflows.
- Deliver the north-star one-list orchestration without requiring users to recreate items in multiple apps.

### Phase 8 — Operational hardening by evidence

- Improve observability, backup/restore drills, privacy operations, rate budgets, capacity, accessibility, support tooling, and incident response based on actual usage and failure rates.
- Scale/introduce Redis or service decomposition only when measured bottlenecks justify the added operational cost.

## 19. Consumer MVP and Definition of Done

The first meaningful consumer MVP is not merely login plus optimizer API. In one supported launch zone:

- A person can sign up with at least email verification and one OAuth/phone alternative selected for launch; sign in, reset/recover, sign out, and manage/revoke sessions.
- Their shopping lists persist across devices and are isolated from all other users.
- They can search/create list lines and confirm exact canonical variants and requested quantity/pack; ambiguity and no-match are handled in-product.
- Cartel retrieves fresh, retailer-originated, zone-scoped offers from at least two authorized retailers for supported products, with explicit timestamps and unsupported states.
- Cartel computes a deterministic feasible allocation across supported retailer checkouts; every displayed total/savings comparison has valid, comparable evidence and an explained baseline. Unknown checkout values do not rank as zero.
- User reviews exact products, quantities, split, delivery/fees/discounts, freshness, and total, then approves an immutable plan snapshot.
- Cartel prepares the exact retailer carts through legitimate supported mechanisms, verifies exact lines/quantities and ownership, and stops safely on mismatch or access denial.
- User authorizes/pays through each legitimate retailer flow without sharing payment secrets with Cartel. The UI never implies authorization or purchase occurred before retailer confirmation.
- Cartel records retailer-confirmed order IDs/status and lets the user return later to see per-retailer orders and last verified tracking state.
- Multi-retailer partial failures, stale price/stock, unknown mutation outcomes, payment refusal, and tracking outage are explicit and recoverable. No duplicate order is produced on replay/retry.
- Cross-user isolation, auditability, secret redaction, rate limits, data export/deletion policy, backup/restore, and production health/incident ownership have acceptance evidence.

Before claiming the north star, execute an end-to-end acceptance with real authorized retailer evidence and a consenting test account. Fixture tests prove architecture only. A retailer that does not support legitimate Cartel-mediated cart/payment handoff cannot count toward the two-retailer execution claim.

## 20. Risks and Decisions Requiring Owners

| Risk / decision | Why it matters | Required decision/evidence |
|---|---|---|
| Retailer permission and anti-automation policy | Access denial or policy changes can stop the core promise and put accounts at risk. | Legal/product approval and per-capability written integration basis before enablement. |
| Cartel access to retailer accounts | Shared browser sessions can expose orders/address across users. | Decide OAuth/API connection versus user-assisted handoff; never share a profile. |
| Real checkout totals and fees | Listing prices cannot prove payable cost or savings. | Per-retailer evidence schema, field completeness, freshness TTL, and total reconciliation rules. |
| Price/stock drift after approval | User may pay more or find an item unavailable. | Maximum change tolerance, mandatory reapproval rules, and replacement/partial-plan UX. |
| Product/variant matching errors | Wrong pack/allergen/form can harm users and destroy trust. | Launch-category critical attributes, confidence calibration set, human confirmation thresholds. |
| Multiple retailer payments | No universal atomic payment/order across retailers. | Confirm user accepts separate retailer authorizations and partial order outcomes. |
| Browser session and credential retention | Retailer credentials/cookies are highly sensitive. | Retention, KMS/key ownership, user revocation, incident response, and policy compliance. |
| Address and purchase history privacy | Data is sensitive even without payment credentials. | Data jurisdiction, retention/deletion/export, subprocessors, and breach response. |
| Cashback, memberships, and rewards | Deferred/conditional value can distort comparisons. | Report immediate payable cost separately; approve treatment and membership consent semantics. |
| Delivery, substitutions, cancellation, refunds | These vary by retailer and post-purchase state. | Capability matrix and support responsibility for each launch retailer. |
| Operational support and liability | Cartel coordinates third-party transactions but may not control fulfillment. | Clarify support routing, order confirmation source, disclaimers, and escalation ownership. |
| Launch retailer/geography | Product quality depends on local coverage, assortment, language, and delivery-zone resolution. | Choose one initial metro/zone and categories using measured catalog/availability coverage. |
| Database and job availability | Orders and mutations need durable state; filesystem prototype is single-instance. | Postgres migration/backup, outbox recovery, worker leases, and restore acceptance before order execution. |

## 21. Architecture Decision Rules

1. Retailer evidence is the authority for retailer identity, availability, checkout, and order state; Cartel is authority for user intent, canonical governance, policy, approval, and orchestration history.
2. Canonical identity is governed separately from retailer identity. Exact variant means identity-critical attributes match; any exception is user-visible and consented.
3. A plan is not an order. An approved plan is not payment. A prepared cart is not a submitted order. A submit request is not a retailer-confirmed order.
4. Unknown is represented as unknown. Never default unavailable fees, stock, quantity, currency, cart identity, or final total to a success-shaped value.
5. External side effects are reconciled and idempotent where possible. Ambiguous outcome blocks mutation retries until state is known.
6. Test evidence, fixture:// provenance, and deterministic adapters cannot be selected by production configuration or become live retailer evidence.
7. Every retailer capability is individually permissioned, scoped, observable, and revocable. One blocked adapter does not falsify other verified retailer results.
8. Start with the smallest coherent modular monolith and one supported geography; invest in queue, cache, and deployment complexity only to satisfy concrete user-visible reliability needs.

---

This document describes the intended Cartel product. It does not claim that signup, multi-user persistence, PostgreSQL domain storage, multiple live retailer integrations, automatic order placement, payment, or order tracking currently exist. Each becomes a product claim only after its phase acceptance criteria pass with real authorized evidence.
