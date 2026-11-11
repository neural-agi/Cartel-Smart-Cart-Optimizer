# Swiggy Instamart Application Field Preparation

**Status:** Preparation sheet. Not submitted.

## Applicant Identity

| Field | Prepared answer | Verification status |
|---|---|---|
| Product name | Cartel Smart Cart Optimizer | Repository evidence |
| Organization/legal entity | To be supplied by Cartel owner | UNKNOWN |
| Registration details | To be supplied if applicable | UNKNOWN |
| Product stage | Early-stage development; local authenticated and consumer-flow tests exist in the repository, with no claim of production deployment | Repository evidence |
| Customers/users/revenue/funding | Do not claim without separately verified evidence | NOT PROVIDED |
| Application track | Enterprise / Startup partnership route appears appropriate | Human decision required |

## Product and Use Case

Cartel is a consumer grocery comparison and basket-optimization product. Users express shopping intent, select exact governed products, compare permitted retailer observations, and receive an explainable basket allocation. Cartel may support multiple retailer accounts, but each retailer connection, observation, and checkout authorization remains separately governed.

Cartel must disclose that cross-retailer comparison and commercial comparative display are central to the product. It must not describe itself only as an Instamart assistant.

## Architecture Inputs

- Frontend: Next.js consumer application and same-origin backend proxy.
- Backend: FastAPI modular application.
- Persistence: PostgreSQL for mutable application state and governed metadata.
- Background work: PostgreSQL-backed worker/outbox foundation.
- Rate limiting: Redis-backed distributed limiter; Redis is not application source of truth.
- Retailer integration: provider-neutral capability adapters with lifecycle authorization and Credential Vault.
- Identity: exact Product/Variant governance separated from retailer-native product/listing identity.
- Evidence: immutable artifacts and provenance-aware observations; unresolved evidence is excluded from consumer eligibility.
- Security: server-managed sessions, CSRF, Argon2id password hashing, owner-scoped retailer connections, AES-256-GCM vault encryption.

## Application Information to Supply

Swiggy's published access requirements identify these inputs:

- organization/integration name;
- redirect URIs;
- Instamart server selection;
- expected traffic and tool-call volume;
- use-case narrative;
- primary technical contact;
- static IP ranges or gateway IPs where requested;
- security contact;
- data-handling and privacy declaration;
- infrastructure/environment details;
- optional security audit, SOC 2, or ISO information only if actually available.

Source: [Swiggy production access](https://mcp.swiggy.com/builders/access/) and [access and onboarding](https://mcp.swiggy.com/builders/docs/operate/access/).

## Security Questionnaire Position

### Can state as implemented

- Server-managed Cartel sessions.
- CSRF protection for state-changing requests.
- Argon2id password hashing.
- OAuth provider tokens handled server-side.
- Owner-scoped retailer connection records and lifecycle checks.
- AES-256-GCM encrypted credential vault with associated-data binding.
- Redacted audit/logging boundaries.
- Evidence provenance and fail-closed consumer eligibility.

### Must state as incomplete or planned

- Production KMS/HSM integration.
- Instamart-specific OAuth client and credential lifecycle.
- Formal data-processing agreement and retention schedule.
- External security audit or certification.
- Production disaster recovery and key-rotation evidence.
- Instamart-specific serviceability, freshness, and schema qualification.

## Commercial Questions to Attach

Attach the questions from [the authorization inquiry](swiggy_instamart_authorization_inquiry.md), especially the questions on benchmarking, comparative display, storage/caching, derived recommendations, checkout handoff, and sustainable zero-cost production.

## Prohibited Claims

Do not state that Cartel:

- is a Swiggy partner;
- has production Instamart access;
- has received authorization;
- has customers, revenue, funding, certifications, or audits unless independently verified;
- has validated Instamart price or inventory behavior;
- can offer Swiggy data commercially;
- has a zero-cost production agreement.

