# Cartel Production Readiness Gap

## Executive Summary

Cartel has a substantial deterministic backend foundation, but it is not yet a
usable live application. The repository contains tested contracts and local
filesystem-backed execution paths for observation ingestion, Product
Intelligence, candidate discovery, planning, Cost Intelligence, and cart
optimization. Those paths are primarily exercised with persisted fixtures or
caller-supplied planning context.

The real user journey now reaches a governed search endpoint, but the default
application catalog is not populated by a user-facing catalog workflow. The
optimization flow still stops after cart resolution and candidate discovery.
It never calls the planning endpoint or displays an optimization result. A manually constructed API
request can exercise more of the backend, but it must supply canonical
identities, candidate context, plan IDs, feasibility, policy values, checkout
groups, and effective-cost inputs that a real user cannot currently provide.

There is one operational scraper implementation, Blinkit, but no production
catalog/search workflow that turns its observations into an authoritative
user-facing product inventory. BigBasket and Zepto packages are placeholders.
Checkout capture is unavailable by default, so true checkout-derived effective
cost cannot be produced for a newly generated live plan.

The repository is therefore a deterministic implementation foundation, not a
live grocery optimization product. The most important work is now product
integration and production authority, not another internal optimizer
refactor.

## Current User Journey

The intended user workflow is: choose grocery items, build a cart, compare
retailer-specific candidates and checkout costs, inspect the explanation, and
act on the recommended cart.

What actually happens today:

1. `/` serves a marketing landing page. The working application views are
   under the grouped app routes rather than the root experience.
2. `/search` calls the governed `/api/v1/products/search` endpoint. Results are
   available only for active canonical variants with persisted associations and
   registered observations. A clean default data directory returns no results.
3. The cart can store a canonical frontend `Product` returned by that endpoint
   when the catalog is populated.
4. `/optimize` calls `/api/v1/cart/resolve`, then
   `/api/v1/cart/candidates`. It does not call `/api/v1/cart/plan`.
5. `/results` displays resolved identities and persisted candidates. It can
   also render a structured optimization result if one is supplied to the
   frontend store, but the current user flow does not produce that result.
6. The planning API can execute only when the caller supplies a complete
   `CartPlanningRequest`, including canonical candidate context and supplied
   plans. This is an internal/test-shaped contract, not a user-facing cart
   submission.
7. Checkout capture is wired to an unavailable adapter by default. No normal
   user flow reaches a live checkout observation or checkout action.

The first real-user break is the absence of a populated, continuously managed
catalog/search authority. If that is bypassed with a
crafted request, the next break is automatic planning input production; after
that, live checkout evidence and effective-cost generation remain unavailable.

## Production Readiness Score

**32% for a real-user live application.**

This is not a test-count score. It is an operational capability estimate using
six weighted gates:

| Gate | Weight | Verified capability | Contribution |
|---|---:|---|---:|
| Deterministic domain/core backend | 25% | Strong contracts and local execution, but supplied-input dependent | 22.5% |
| Real data and catalog authority | 20% | One fragile acquisition path; no user-facing authoritative catalog/search | 2% |
| Automatic planning and true cost | 20% | Core services exist; producer and checkout inputs are missing | 3% |
| Frontend user workflow | 15% | UI shell and cart state exist; search and optimization are not connected | 2.25% |
| Persistence and deployability | 10% | Local filesystem stores and container scaffolding; no production planning/database lifecycle | 1% |
| Security, reliability, and operations | 10% | Basic config/logging and tests; no production access or observability controls | 1% |
| **Total** | **100%** |  | **31.75%, rounded to 32%** |

The deterministic backend core is valuable and substantially implemented. It
does not make the product live because the missing capabilities are at the
user, data-authority, checkout, and operations boundaries.

## Component Status

| Component | Status | What Works | What Is Missing | Blocking? |
|---|---|---|---|---|
| Frontend application shell | PARTIAL | Next.js routes, cart state, loading/error UI in some flows | Connected product search, real optimization flow, result explanation and action | Yes |
| Product search/catalog UX | PARTIAL | Governed search API and frontend search-to-cart mapping | Populated/managed catalog authority and complete ambiguity workflow | Yes |
| FastAPI application/API | PARTIAL | Versioned routes, Pydantic validation, planning/candidate/cost routes | User-shaped planning endpoint, auth, readiness, production error/operation controls | Yes |
| Configuration/startup | PARTIAL | Settings validation, environment fields, Docker startup | Production secret management, dependency startup/readiness, migration/config discipline | Yes for deployment |
| Retailer acquisition | EXPERIMENTAL | Blinkit Playwright/browser acquisition with location/session handling | Stable supported production integration, monitoring, legal approval, more retailers | Yes |
| Observation normalization/registry | PARTIAL | Immutable normalized models, provenance, filesystem registry, replay tests | Durable multi-instance storage and operational freshness/cleanup policy | Yes at scale |
| Product Intelligence | PARTIAL | Deterministic matching, review, assertions, evidence and audit artifacts | Automatic catalog authority and user-facing ambiguous-resolution workflow | Yes |
| Candidate discovery | PARTIAL | Discovers persisted canonical listing associations and validates typed prices | Search-to-canonical resolution and automatic candidate production for arbitrary cart input | Yes |
| Retailer identity authority | BLOCKED | Explicit provider seam and caller-supplied values | Authoritative application source for stable retailer IDs | Yes |
| Checkout-group authority | BLOCKED | Explicit supplied group context and membership validation | Source for groups/membership during automatic planning | Yes |
| Feasibility/policy producers | BLOCKED | Frozen validation and fail-closed provider seams | Automatic feasibility evidence, inconvenience policy, retailer preference | Yes |
| CandidatePlan construction | PARTIAL | Deterministic enumeration, identity, provenance, fulfillment and group validation | Automatic producer of complete supplied plans | Yes |
| Cost Context | PARTIAL | Immutable deterministic wrapper around checkout observations | No live checkout source in default application path | Downstream dependency |
| Offer/Fee/Membership evaluators | EXPERIMENTAL | Deterministic value-object evaluators and orchestration | Full real-world fee/offer semantics and source coverage | Yes for true cost |
| Effective Cost Evaluation | PARTIAL | Immutable effective-cost contract and pipeline integration | Authoritative checkout prices, fees, promotions, membership/payment context | Yes |
| Cart Optimization | PARTIAL | Deterministic optimizer, tie-breaking, result invariants and tests | Complete real candidate/ECE inputs and user-facing explanation/action | Yes |
| Planning persistence | PARTIAL | Deterministic request/result serialization and independent filesystem repositories | Frozen lifecycle/relationship contract, durable DB, retrieval/ownership/retention | Yes for production |
| Checkout execution | MISSING | Capture contracts and unavailable adapter | Cart mutation, checkout navigation, payment/order boundary | No for a read-only MVP; yes for execution product |
| Security | PARTIAL | Input validation, explicit CORS configuration, request IDs, secure headers and production config checks | Authentication, authorization, rate limiting and secret management | Yes for public launch |
| Reliability | PARTIAL | Local retries/timeouts and fail-closed service behavior | Job scheduling, distributed coordination, circuit breaking, recovery | Yes for live data |
| Testing | PARTIAL | 556 backend tests and integration fixtures | Frontend/build/E2E/real-provider and production-failure coverage | Yes |
| Deployment | EXPERIMENTAL | Docker Compose, readiness healthcheck and browser runtime installation | Production topology, persistent volumes, migrations, HTTPS and operations | Yes |
| Observability | PARTIAL | Structured logs, request correlation, liveness and readiness endpoints | Metrics, traces, provider dashboards and alerting | Yes |

## End-to-End Reality Check

The strongest verified backend path is:

`ScrapeJob` -> Blinkit acquisition/parser -> raw artifact -> normalized
observation -> observation registry -> canonical association -> Product
Intelligence execution -> persisted association -> candidate discovery ->
explicit enrichment/context -> supplied `CandidatePlan` -> ECE from supplied
checkout observation or precomputed result -> `CartOptimizationResult`.

This path is deterministic and covered with repository-owned fixtures. It is
not the path a real user can initiate. The application has no connected search
that supplies canonical product/variant IDs, and no automatic planning service
that creates all required candidate contexts and plan policy inputs. A normal
API caller must already know internal identifiers and provide values that
should be produced by upstream application authorities.

The frontend stops earlier still: it resolves and displays persisted identity
and candidates but never submits a planning request. The default checkout
capture adapter is unavailable, so a newly generated plan cannot obtain live
checkout evidence from the configured application.

There is no final user action boundary. Cartel does not add items to a retailer
cart, navigate a real checkout, accept payment, or place an order.

## Frontend Gaps

- `frontend/services/productSearch.ts` is an explicit unwired boundary and
  always returns an empty list.
- The frontend has no product-search API contract, no canonical product
  selection flow, and no handling for ambiguous product/variant matching.
- `OptimizePage` invokes resolution and candidate discovery only. It does not
  construct or submit `CartPlanningRequest` and therefore cannot obtain an
  optimization result.
- `ResultsPage` now has a structured optimization-result view for selected
  plans, alternatives, allocations, retailer/group counts, feasibility,
  rationale, unknowns and provenance references.
- The frontend cannot show an effective-cost amount or savings because
  `CartOptimizationResult` carries only an ECE reference, and the current
  user flow never produces a linked result.
- No frontend path displays a complete price breakdown by retailer or checkout
  group.
- No frontend path lets a user resolve review cases or correct ambiguous
  product/variant matches.
- No frontend path performs or links to a supported checkout action.
- Cart state is in-memory Zustand client state. There is no authenticated user
  cart, server-side cart persistence, resume flow, or cross-device state.
- The root route is marketing content rather than the usable cart workflow.
- Frontend tests are not part of the backend validation baseline. A frontend
  build/lint must be run in an environment with the Node dependencies installed;
  this audit did not claim a successful frontend build from the Python suite.

## Backend/API Gaps

- `/api/v1/cart/resolve` and `/api/v1/cart/candidates` are useful internal
  boundary endpoints, but they require canonical identities that the frontend
  cannot currently obtain.
- `/api/v1/cart/plan` accepts a complete internal `CartPlanningRequest`; it is
  not a user cart submission API. The request includes candidate contexts,
  supplied plans, feasibility, checkout groups, policy values and ECE inputs.
- `/api/v1/cost-intelligence/evaluate` accepts a caller-supplied checkout
  observation and optimization request. It is not a live checkout-price
  acquisition path.
- `/api/v1/cart/checkout-capture` is expected to return unavailable with the
  default `UnavailableCheckoutCaptureAdapter`.
- API route dependencies are stored on `app.state` and some routes discover
  them with `getattr`; this is workable locally but weakens explicit
  dependency and startup guarantees.
- `/health` is a liveness response and `/ready` now checks core application
  wiring and data-directory availability. It does not prove retailer/browser
  or checkout-provider availability.
- No authentication or authorization boundary is present for cart data,
  observations, planning requests, or future user records.
- CORS origins are now explicit configuration, but rate limiting and abuse
  controls remain absent.
- Error mapping exists for several known domain failures, but there is no
  consistent public error envelope or request-correlated operational error
  reporting.
- API versioning exists at `/api/v1`, but no stable user-facing planning
  response contract or retrieval/status contract is defined.

## Data Source Gaps

The supported acquisition loop is operator-triggerable through `POST /api/v1/scrape`
or `scripts/acquire_mvp_observations.py`. It persists raw artifacts and normalized
observations and reports canonical association status. A fresh deployment still
does not become searchable from acquisition alone: the canonical catalog requires
approved Product and ProductVariant identities, and unresolved observations remain
unresolved rather than being auto-approved. This is an intentional fail-closed
boundary, not a fixture-seeding step.

- Blinkit is the only concrete acquisition path in `backend/app/scrapers`.
  It uses Playwright/browser session state and location context; direct HTTP is
  known to be blocked in the repository research.
- BigBasket and Zepto packages contain no equivalent production adapter. Other
  retailer names in README/research are not implemented integrations.
- The repository contains cleaned/raw Blinkit data and deterministic fixtures,
  but fixtures are not a continuously refreshed production catalog.
- No scheduled ingestion worker, queue-backed job runner, production retry
  scheduler, or multi-instance coordination is configured.
- Browser/session dependencies, location setup, platform DOM drift, rate
  limits, and scraper compliance are not operated as production services.
- Stock/availability and price changes are represented at observation level,
  but there is no live freshness policy that guarantees a user's optimization
  is based on current checkout facts.

## Product Intelligence Gaps

- Normalization, evidence preservation, deterministic matching, review, audit,
  and assertion services are implemented and well tested as pipeline stages.
- Canonical catalog and listing associations are filesystem-backed and require
  authoritative pre-existing catalog state. The runtime does not turn an
  arbitrary user text query into a governed canonical product/variant.
- Product-family and variant ambiguity can be represented, but there is no
  user-facing review workflow connected to the frontend.
- Catalog population, canonical identity approval, association ownership and
  long-term revision operations remain operationally incomplete.
- The system is conservative about evidence, which is correct; it means the
  product cannot promise coverage for arbitrary grocery input until catalog
  authority and review throughput exist.

## Candidate Discovery Gaps

- Discovery reads persisted canonical listing associations and matching
  observations. It does not search retailer catalogs or generate associations.
- It preserves listing and observation provenance and performs typed-price
  readiness checks, but only after canonical product and variant identity are
  already known.
- No frontend or user-facing service translates text/product selection into
  `CartCandidateDiscoveryRequest` with authoritative canonical IDs.
- Candidate readiness can be `candidates_not_ready` or `no_candidates`; there
  is no user workflow that explains and resolves those states beyond the
  current development UI.

## Retailer/Checkout Authority Gaps

- Retailer identity is not derived from platform, URL, listing ID, or ordering;
  the architecture correctly requires an explicit authoritative source.
  Current planning contexts supply `retailer_id` manually, and unavailable
  provider seams fail closed.
- Checkout groups are validated when supplied, but automatic group derivation
  is not available. The application has no source that authoritatively assigns
  a listing/allocation to a checkout group for generated plans.
- Inconvenience penalty and retailer preference are supplied in `SuppliedPlan`;
  no user/profile/configuration authority currently produces them for a real
  request.
- Feasibility is validated at construction time with evidence supplied by the
  caller. Missing producer authority remains unresolved rather than being
  treated as feasible.
- These are not values the frontend can safely guess. The missing authorities
  block automatic planning.

## Planning Gaps

- Candidate enumeration, fulfillment validation, allocation provenance,
  checkout-group membership, deterministic plan identity, and optimizer result
  invariants are implemented for governed inputs.
- `CartPlanningService` still expects explicit `SuppliedPlan` records. It does
  not automatically create plan IDs, policy values, feasibility/evidence,
  checkout groups, or complete ECE inputs.
- Plan persistence currently has independent request/result repositories and
  deterministic serialization. `docs/architecture/planning_persistence_contract_gap.md`
  explicitly leaves lifecycle, request/result relationship, retries,
  retention, ownership, retrieval, and API persistence undefined.
- There is no user-facing planning status, result retrieval, or resume flow.
- Allocation-free and supplied-plan compatibility semantics are intentionally
  frozen in the backend; they do not remove the need for upstream producers.

## ECE Gaps

- Cost Intelligence has immutable context, offer, fee, membership, effective
  cost contracts and deterministic orchestration.
- Evaluation consumes `CheckoutObservation`; it does not create checkout
  truth from a listing observation or displayed listing price.
- The planning path supports precomputed ECE, caller-supplied checkout
  observations, and a registry/provider-backed observation lookup. The default
  application configuration uses unavailable checkout capture/provider
  behavior.
- Real delivery, handling, platform, membership, coupon, cashback, payment
  method and threshold semantics require authoritative checkout observations.
  They are not made trustworthy by the existence of evaluator classes.
- Currency/money value objects and deterministic arithmetic exist, but live
  multi-retailer fee/offer coverage and stale-observation handling are not a
  production guarantee.

## Optimization Gaps

- The optimizer can deterministically select among valid, fully supplied plans
  using effective cost, feasibility, penalties/preferences and frozen
  tie-breaking rules.
- It is useful as a decision engine for governed inputs, not yet as an
  automatic cart optimizer for arbitrary users.
- Retailer preferences, inconvenience penalties, checkout groups and ECE are
  not sourced automatically.
- Substitution and unavailable-product UX are not connected to the frontend.
- Explanations are available in structured backend artifacts/contracts, but no
  complete result explanation is rendered for users.
- No action is taken on the selected plan: there is no cart mutation, checkout
  navigation, payment, or order placement boundary.
- Performance has local limits and deterministic combination caps, but no
  production-scale load profile or queueing strategy has been demonstrated.

## Persistence Gaps

- Raw artifacts, observations, catalog/associations, evidence, checkout
  correlations, and planning request/result payloads have local filesystem
  stores.
- Filesystem repositories provide deterministic JSON, model validation,
  idempotent identical writes, conflict rejection, missing-record behavior,
  and atomic replacement where implemented.
- This is not a production persistence architecture for multiple API
  instances: no database-backed planning/catalog workflow, migrations,
  ownership/access control, lifecycle, retention, deletion, request/result
  atomicity, backups, restore, or operational locking policy is defined.
- Docker Compose starts PostgreSQL and Redis, but current application wiring
  does not make them the authoritative planning/catalog persistence boundary.
- Browser/session and raw evidence files may contain sensitive or operationally
  important state and need storage/retention controls before deployment.

## Security Gaps

Concrete repository-supported gaps are:

- no authentication or authorization middleware for API routes;
- no user/tenant isolation for future cart and planning data;
- no rate limiting or abuse protection around scraping and planning endpoints;
- no explicit production CORS configuration;
- development credentials/defaults exist in configuration and Compose, with
  only partial production validation and no secret-manager integration;
- local browser storage state is persisted under `data/sessions` and needs
  protected handling if it contains authenticated retailer state;
- filesystem-backed API-controlled data paths require deployment-level
  permission and path isolation review;
- broad exception handling in Cost Intelligence returns a generic 500 without
  a durable, correlated diagnostic contract.

No evidence was found of payment handling or of an implemented order-placement
surface; those boundaries are absent rather than accidentally exposed.

## Reliability Gaps

- Scraper-level timeouts/retries exist, but no durable scheduler, queue,
  distributed retry ownership, circuit breaker, or provider health policy is
  present.
- A default checkout capture provider is intentionally unavailable.
- Filesystem state is not sufficient for concurrent horizontally scaled API
  instances without a defined shared storage/locking architecture.
- There is no production freshness monitor or automated invalidation path for
  stale listing/checkout observations.
- Partial ingestion and association failures can be represented in local
  runtime results, but there is no operator workflow for retry/dead-letter
  resolution.
- Deterministic replay is strong for identical governed inputs; it does not
  guarantee that external retailer pages, prices, stock, or checkout behavior
  will remain the same without captured immutable artifacts.

## Testing Gaps

The backend suite currently reports **556 passed and 8 warnings**. It provides
strong unit and fixture-driven integration coverage for deterministic domain
behavior, but it is not evidence that the live application works.

Missing or insufficient coverage includes:

- frontend unit, component, build, lint, and browser E2E tests;
- real browser/API deployment smoke tests;
- a true user-shaped cart submission through frontend to optimization result;
- live retailer/provider contract tests and availability monitoring;
- production persistence concurrency, backup/restore, migration and recovery
  tests;
- authentication/authorization, CORS, rate limiting and abuse tests;
- load, latency, timeout, retry and provider-outage tests;
- stale-price/checkout freshness acceptance tests;
- observability/alert verification;
- complete explanation rendering and error-state tests.

The passing backend count validates many internal invariants. It does not
validate user usefulness, data coverage, or deployment readiness.

## Deployment Gaps

The supported MVP deployment topology is now a Next.js frontend and FastAPI
backend sharing a Docker Compose network. The frontend proxies `/api/*` to the
backend internally, so browser clients do not require a public backend URL.
The backend stores governed artifacts under the mounted `./data:/app/data`
volume. PostgreSQL and Redis are not runtime dependencies of the current
filesystem-backed implementation and are intentionally excluded from the MVP
Compose startup path.

- Docker Compose is development-oriented and includes PostgreSQL/Redis, but
  there is no production topology, secret injection, migration execution,
  persistent storage policy, backup plan, or reverse proxy configuration.
- `backend/Dockerfile` starts Uvicorn but does not establish a production
  worker/timeout model or install/verify the Playwright browser runtime needed
  by the Blinkit path.
- No frontend deployment service/configuration is present in Compose or infra.
- NGINX, monitoring, Docker infrastructure and Terraform directories are
  placeholders.
- No HTTPS/domain/certificate configuration, readiness probe, autoscaling,
  rolling deployment, or persistent volume design is present.
- Scheduled ingestion and browser-worker deployment are not defined.
- No migration command is connected to startup, and the DB package does not
  currently provide the application's authoritative persistence path.

## Observability Gaps

- Structured logging is configured and some services emit useful stage logs.
- Only liveness-style health is exposed; dependency readiness is not.
- No metrics for request rate, planning latency, candidate coverage, provider
  errors, freshness, checkout capture, or selected outcomes were found.
- No distributed tracing or correlation propagation is established across
  ingestion, planning, Cost Intelligence and API calls.
- No error-reporting integration, dashboards, alert rules, or operator runbook
  exists.
- An operator cannot reliably answer which retailer provider is failing, where
  a user's cart stopped, or whether optimization results are based on fresh
  checkout evidence.

## Legal/External Dependencies

- Blinkit acquisition uses browser automation and persisted session/location
  state. The repository research explicitly calls out platform blocking,
  rate-limit, session and compliance concerns. Terms-of-service and permitted
  access must be reviewed before operating this as a public service.
- Additional retailer APIs/scrapers require separate technical and legal
  approval; README references are not integration authority.
- If user accounts, saved carts, location, retailer session state or purchase
  history are introduced, privacy and retention requirements must be reviewed
  externally.
- Cartel does not currently process payment or order placement, so those legal
  and security obligations are outside the current code boundary but would
  become mandatory if execution is added.

## Hard Blockers

These prevent a real user from successfully using the current repository as a
live cart optimizer:

1. No populated, continuously managed product catalog/search authority for a
   normal user.
2. No automatic user-cart API path that turns selected products into complete
   planning inputs.
3. No authoritative automatic retailer identity source.
4. No authoritative checkout-group source for generated allocations.
5. No automatic feasibility/evidence, penalty, or retailer-preference
   producers.
6. No reliable live checkout observation/capture path for generated plans, so
   true effective cost is unavailable by default.
7. Only one experimental retailer acquisition path, with no stable supported
   multi-retailer data coverage or catalog lifecycle.
8. Frontend does not submit planning or render optimization results.
9. No production-grade persistence/lifecycle/retrieval architecture for user
   planning data.
10. No authentication, public API abuse controls, production readiness checks,
    deployment topology, or operational monitoring.

## Non-Blocking Improvements

- Additional retailer integrations after one supported retailer is reliable.
- Richer offer, membership and promotion stacking semantics after checkout
  evidence is available.
- Advanced substitution UX and review prioritization.
- Optimization performance tuning beyond current deterministic caps.
- Purchase history, wrapped views, saved preferences, notifications and
  personalization.
- Cart execution, payment and order placement.
- Advanced tracing and analytics after the basic operational telemetry exists.

## MVP Definition

The smallest genuinely usable Cartel MVP should be deliberately narrow:

- **Retailer:** one legally approved retailer integration, initially Blinkit,
  in one supported location scope.
- **Product input:** user searches/selects products from a governed catalog;
  arbitrary free-text products that cannot be canonically resolved are shown
  as unsupported or sent to review, never guessed.
- **Cart:** user builds a cart with exact supported quantities and sees
  unresolved/missing variants explicitly.
- **Data:** a scheduled or operator-triggered ingestion process produces
  immutable raw artifacts, normalized observations, canonical associations and
  freshness metadata for the supported scope.
- **Planning:** one automatic application path creates complete candidate
  context, plan identity, checkout group, feasibility evidence and policy
  inputs under a frozen MVP policy. Missing authority fails closed.
- **Cost:** checkout capture or a clearly bounded supported checkout-observation
  source supplies actual checkout facts. Displayed listing prices alone must
  not be presented as effective cost.
- **Optimization:** deterministic selection among supported plans, with an
  item/retailer/group/price/fee breakdown and explicit unresolved reasons.
- **Frontend:** search, cart, optimize, loading/error/empty states, result
  explanation, provenance/freshness display and a read-only next action such
  as opening the retailer link. No payment or order placement is required for
  the first read-only MVP.
- **Backend:** user-shaped cart submission, automatic planning orchestration,
  stable response models, structured errors and readiness checks.
- **Persistence:** a shared production store for catalog, observations,
  requests/results and user/cart records, with the lifecycle and ownership
  contracts frozen first.
- **Operations:** HTTPS, secrets, auth, rate limits, logs, metrics, alerts,
  backups and a supported deployment for the one-retailer scope.

## Path to Live

### Phase A: Must Have Before First Real User

1. Freeze the one-retailer MVP scope, catalog authority, retailer/group/policy
   sources, and user-shaped planning request contract.
2. Implement governed product search/catalog selection and connect it to the
   frontend cart.
3. Implement automatic planning-input production from selected canonical
   products, using explicit fail-closed authorities.
4. Establish a supported checkout-observation capture path or explicitly limit
   the MVP claim to a non-ECE comparison product.
5. Connect frontend optimize -> planning -> result and render effective-cost
   explanations.
6. Add API authentication/user isolation, production CORS/rate limits,
   readiness checks and structured public errors.
7. Replace local-only critical persistence with a shared durable store and
   freeze lifecycle/retention/ownership semantics.

### Phase B: Must Have Before Public Launch

1. Operate scheduled ingestion with provider health, retries, freshness
   monitoring and a manual recovery path.
2. Validate browser/runtime deployment and legal access for the supported
   retailer.
3. Add frontend/API E2E, load, outage, stale-data, security and restore tests.
4. Deploy HTTPS, secrets management, migrations, backups, monitoring,
   alerting, dashboards and an operator runbook.
5. Add a second retailer only after the first retailer's data/checkout path is
   reliable and its authority boundaries are explicit.

### Phase C: Post-Launch Improvements

1. More retailers, richer promotion/membership semantics and better review
   throughput.
2. Substitution recommendations, preferences, history and personalization.
3. Cart execution/checkout integration, only with separate security and legal
   approval.
4. Scale optimization, distributed workers, richer analytics and automated
   catalog maintenance.

## Remaining Work Estimate

| Area | Remaining effort | Reason |
|---|---|---|
| Backend user-facing planning/search | Very High | Missing producer authorities and user-shaped API path |
| Frontend | Very High | Search, planning submission, result explanation and E2E workflow are incomplete |
| Data integrations | Very High | One experimental browser path; no operational multi-retailer coverage |
| Infrastructure/persistence | High | Shared durable state, migrations, backups, lifecycle and deployment topology missing |
| Testing | High | Frontend, live-provider, security, load, recovery and E2E gaps |
| Security | High | Auth, isolation, CORS, abuse controls and secret operations absent |
| Operations/observability | High | Readiness, metrics, tracing, alerts and runbooks absent |

## Explicitly Out of Scope

The first genuinely usable read-only MVP does not require payment processing,
order placement, automated retailer-cart mutation, a broad retailer fleet,
personalized loyalty optimization, purchase history, mobile native clients,
ML-based matching, or a full public marketplace.

## Next 10 Implementation Batches

### 1. Freeze One-Retailer MVP Authority

**Why it matters:** The current system cannot safely create automatic plans
without authoritative retailer, group, feasibility and policy inputs.

**Dependencies:** Existing Cart Optimization and Product Intelligence
contracts; one approved retailer/data source.

**Implement:** Freeze the supported retailer/location scope, catalog authority,
checkout-group source, feasibility evidence source, and policy defaults only
where product authority exists.

**Acceptance criteria:** A complete user-shaped planning request can be
specified without guessing or caller-supplied internal-only fields.

### 2. Governed Product Catalog Population and Search

**Why it matters:** Product search is the first live-user break.

**Dependencies:** Authoritative canonical catalog and association state.

**Implement:** Populate and maintain governed catalog/association state, then
use the existing backend search/read contract with canonical product/variant
selection, deterministic ordering and explicit empty/ambiguous states.

**Acceptance criteria:** A user can search supported products and add a
canonical item/variant to a cart through a tested API/frontend path.

### 3. Automatic Planning Input Producer

**Why it matters:** It removes the current requirement for users/callers to
supply `SuppliedPlan` internals.

**Dependencies:** Batch 1 authorities, Batch 2 canonical selection, existing
discovery/enrichment/construction services.

**Implement:** Explicit application orchestration for candidate context,
retailer/group, plan ID, feasibility/evidence and policy values.

**Acceptance criteria:** A supported cart produces validated CandidatePlans
without manual internal plan payloads; missing authority fails closed.

### 4. Supported Checkout Observation Capture

**Why it matters:** Effective cost is Cartel's distinguishing product claim and
the current default capture adapter is unavailable.

**Dependencies:** Retailer-approved checkout evidence source and legal review.

**Implement:** One supported capture/provider path, freshness/error semantics,
correlation to request and plan, and operator-visible failures.

**Acceptance criteria:** A generated supported plan obtains a real governed
checkout observation and deterministic ECE, or the UI explicitly says cost is
unavailable.

### 5. Frontend Planning and Result Workflow

**Why it matters:** The current frontend stops after discovery.

**Dependencies:** Batches 2-4 and stable user-shaped API contracts.

**Implement:** Submit cart for planning, render chosen plan, alternatives,
cost breakdown, feasibility, provenance, freshness and failures.

**Acceptance criteria:** Browser E2E covers search -> cart -> optimize -> result
with no internal IDs manually entered.

### 6. Production Planning Persistence Contract

**Why it matters:** Filesystem repositories are not a safe shared-user store.

**Dependencies:** Existing persistence gap decisions in
`planning_persistence_contract_gap.md`; product decisions on lifecycle,
ownership, retention and retrieval.

**Implement:** Freeze and implement shared storage, request/result relationship,
status/replay/retrieval semantics, migrations and round-trip/concurrency tests.

**Acceptance criteria:** Multiple application instances can safely persist and
retrieve user planning requests/results with deterministic conflict behavior.

### 7. Authentication and Tenant Isolation

**Why it matters:** Real carts, location and retailer session state cannot be
publicly addressable without identity and access control.

**Dependencies:** User/account ownership decision and persistence.

**Implement:** Authenticated API boundary, authorization checks, CORS policy,
secret management and rate limiting.

**Acceptance criteria:** Users can access only their own cart/planning data and
abuse controls are tested.

### 8. Ingestion Operations for the MVP Retailer

**Why it matters:** A one-time Blinkit corpus is not current product data.

**Dependencies:** Retailer access approval, shared persistence, Batch 4
checkout source.

**Implement:** Scheduling, retries, freshness monitoring, browser worker
runtime, artifact retention and manual recovery.

**Acceptance criteria:** Supported location data refreshes predictably, stale
or failed data is visible and never silently treated as current.

### 9. Production Deployment and Observability

**Why it matters:** The current Docker/infra directories are scaffolding.

**Dependencies:** Shared persistence, auth, ingestion worker, frontend/API
contracts.

**Implement:** Production containers, HTTPS/reverse proxy, migrations,
health/readiness, metrics, traces, logs, alerts, backups and runbooks.

**Acceptance criteria:** An operator can deploy, detect, diagnose and recover
from API, storage, ingestion and checkout-provider failures.

### 10. Read-Only Retailer Action Boundary

**Why it matters:** A result is useful only if the user can act on it, while
keeping payment/order execution out of the first MVP.

**Dependencies:** Stable result/provenance contract and frontend result view.

**Implement:** Safe retailer deep links or explicit handoff for selected
listings, with no credential or payment handling.

**Acceptance criteria:** A user can open the recommended retailer/listing
context and understand what to add, without Cartel claiming checkout completion.

## Audit methodology

This audit inspected the current committed repository rather than relying on
previous status reports. It covered:

- frontend routes, services, store and package configuration;
- FastAPI application startup, routes, request/response models and config;
- Product Intelligence ingestion, catalog, evidence, matching, review and
  assertion boundaries;
- candidate discovery, enrichment, planning, CandidatePlan construction,
  optimization, ECE and persistence code;
- Blinkit acquisition/parser/session code and retailer package inventory;
- filesystem artifact/observation/catalog/planning stores;
- Docker Compose, backend Dockerfile, database scaffolding and infra
  placeholders;
- repository README, research, architecture and persistence gap documents;
- backend tests and integration fixtures.

The validation baseline for this audit is:

```text
PYTHONPATH=backend python3 -m pytest backend/tests -q
556 passed, 8 warnings
PYTHONPATH=backend python3 -m compileall -q backend/app backend/tests
passed
git diff --check
passed
```

Passing tests were treated as evidence of covered deterministic behavior, not
as evidence of live data availability, user workflow completeness, security,
operability, or production deployment readiness.
