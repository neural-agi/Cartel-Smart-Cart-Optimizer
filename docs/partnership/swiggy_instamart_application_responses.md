# Swiggy Instamart Application Responses (Copy-Ready)

**Status:** Prepared for manual owner review and manual submission. **Not submitted.**

**Purpose:** Provide copy-ready answers keyed to the topics Swiggy's published application route asks about, with an explicit verification label on every answer.

## How to use this file

- The **Answer (copy-ready)** text is written for external submission and contains no internal filesystem paths, credentials, private addresses, or unnecessary implementation detail.
- The **Verification** line is an internal annotation. Do not paste it into the application form.
- `OWNER_INPUT_REQUIRED (OI-xx)` means the owner must supply the value. Every such marker appears in `swiggy_instamart_owner_input_register.md`.
- Do not submit until every marker is resolved and the owner has reviewed the cross-retailer disclosure and the zero-budget statement.

## Verification labels

| Label | Meaning |
|---|---|
| `VERIFIED` | The statement is supported by repository evidence or an official Swiggy page cited in this file. |
| `OWNER_INPUT_REQUIRED` | Cartel cannot truthfully answer without owner-supplied information. |
| `NOT_VERIFIED` | The requirement or field is unknown because Swiggy has not published it or the form is auth-gated. |

## Form-field verification status

| Route | URL | Status on 2026-11-09 | What was visible |
|---|---|---|---|
| Official access page | `https://mcp.swiggy.com/builders/access/` | Public, HTTP 200 | 12 published application inputs, 5 review stages, operating restrictions, both track links, `builders@swiggy.in`. |
| Enterprise / Startup form | `https://forms.gle/U6hYGYLYWQPHWY826` → `https://docs.google.com/forms/d/e/1FAIpQLSf6oRHfUa2QFMsCE1Pteh7fnuAnAU5H1JlTr_M7t6MmreT8TA/viewform?usp=send_form` | Auth-gated, HTTP 401 | No fields visible. **Enterprise form fields are not verified.** |
| Developer form | `https://forms.gle/4vkeKyqm15Qb6fnJA` → `https://docs.google.com/forms/d/e/1FAIpQLSfUhtaGOQjnxS0o8uHFZwZGNxJhJzyYhxiYVotlqdBCpizpUw/viewform?usp=send_form` | Public, HTTP 200 | Full field list visible (reproduced below). |
| Onboarding documentation | `https://mcp.swiggy.com/builders/docs/operate/access/` | Public, HTTP 200 | What Swiggy looks for, what applicants provide, turnaround, staging/production sequence. |

Because the Enterprise/Startup form is auth-gated, the enterprise response set below is keyed to the topics published on the official access and onboarding pages. It is labelled **"form fields not verified"** where the exact field labels are unknown. The owner will see the actual form at submission time.

---

## Topic-keyed responses

### 1. Product name and description

**Answer (copy-ready):**

Product name: **Cartel Smart Cart Optimizer**.

Cartel is a consumer grocery comparison and basket-optimization product. A user describes a shopping need; Cartel resolves the exact governed product and pack configuration, compares attributable retailer observations for the user's delivery context, and produces an explainable basket allocation. Cartel is explicitly cross-retailer and may display comparative product, price, availability, and serviceability information, subject to each retailer's written authorization and data-use terms.

Cartel does not claim to be a Swiggy partner and does not have Instamart access. Any Instamart integration would require written permission for comparative display, catalog aggregation, storage/caching, derived recommendations, delegated authorization, and any future cart or checkout handoff.

**Verification:** `VERIFIED` — product name and description are supported by the repository README and the existing partnership brief; the absence of Swiggy authorization is supported by the repository state and by the fact that no Instamart adapter, credentials, or API call exists.

**Evidence:** `README.md` (project title); `docs/partnership/swiggy_instamart_partnership_brief.md:9`; `docs/partnership/swiggy_instamart_partnership_brief.md:24`.

---

### 2. Organization / developer profile

**Answer (copy-ready):**

Legal entity name: `OWNER_INPUT_REQUIRED (OI-01)`.

Entity type and jurisdiction: `OWNER_INPUT_REQUIRED (OI-02)`.

Company address and country: `OWNER_INPUT_REQUIRED (OI-19)`.

Registration or tax identifier, if applicable: `OWNER_INPUT_REQUIRED (OI-03)`.

Public product or company URL: `OWNER_INPUT_REQUIRED (OI-06)`.

Business email: `OWNER_INPUT_REQUIRED (OI-05)`.

Authorized signatory name and role: `OWNER_INPUT_REQUIRED (OI-04)`.

Application track: `OWNER_INPUT_REQUIRED (OI-15)` — the owner must choose Enterprise/Startup or Developer. The Enterprise/Startup route appears appropriate because Cartel is a product integrating Swiggy commerce into a consumer application, but the choice is the owner's.

**Verification:** `OWNER_INPUT_REQUIRED` for every item above. None of these values exists in the repository, and none may be guessed or filled with development-machine details.

**Evidence:** `docs/partnership/swiggy_instamart_application_fields.md:10-11` already records these as owner-supplied.

---

### 3. Product stage

**Answer (copy-ready):**

Cartel is in active, early-stage repository development. The backend and frontend foundations are implemented and exercised by local automated tests. Cartel does **not** claim production deployment, production traffic, live customers, revenue, funding, or external security certification. Instamart integration is not implemented and will not begin before written authorization.

**Verification:** `VERIFIED` — the repository contains the implementation and tests, and the production-readiness documentation explicitly records that the project is not yet a live production application.

**Evidence:** `README.md` (status: active development); `docs/architecture/production_readiness_gap.md:5-29` (internal readiness assessment); `backend/tests/` (unit/integration suites).

---

### 4. Intended use case

**Answer (copy-ready):**

Cartel's intended use case is commercial cross-retailer grocery comparison and basket optimization. The user states a shopping need; Cartel resolves exact products and packs, collects permitted retailer observations for the user's delivery context, compares attributable facts across authorized retailers, and recommends a basket allocation. Cartel would display Instamart information beside information from other authorized retailers and would derive product-equivalence and basket-allocation recommendations. It is not an Instamart-only shopping assistant.

Cartel acknowledges Swiggy's published restriction on "Using the APIs for competitive intelligence or benchmarking" and is requesting an explicit written determination or negotiated exception before building anything. Cartel will follow Swiggy's attribution and branding requirements, including the requirement not to build "aggregation layers that hide Swiggy's brand or confuse users."

**Verification:** `VERIFIED` for the product model and the quoted restriction (official access page, accessed 2026-11-09). `OWNER_INPUT_REQUIRED (OI-17)` for the owner's written acceptance of Swiggy's attribution/branding terms.

**Evidence:** `https://mcp.swiggy.com/builders/access/` (section "02 / Operating Boundaries — The Ground Rules — Not Allowed"); `docs/partnership/swiggy_instamart_partnership_brief.md:24`; `docs/partnership/swiggy_instamart_authorization_inquiry.md:11`.

---

### 5. Architecture

**Answer (copy-ready):**

Cartel uses a Next.js consumer frontend with a same-origin/server proxy path and a FastAPI backend. PostgreSQL stores users, sessions, retailer connections, lists, jobs, outbox events, and governed metadata. Redis provides distributed request-rate state and is not the application source of truth. Retailer integrations use provider-neutral capability adapters with lifecycle authorization, credential resolution, and a server-side Credential Vault. Cartel separates canonical Product/Variant identity from retailer-native listing and observation identity. Governed ingestion preserves immutable artifact references and provenance; unresolved, stale, unavailable, or conflicting evidence is excluded from consumer eligibility. A background worker/outbox handles durable asynchronous work. Observability is basic JSON logging, request correlation, metrics, and health/readiness checks.

No Instamart adapter, credentials, endpoint configuration, or live integration exists. The Instamart edge is future-only and would be built only after written authorization.

**Verification:** `VERIFIED` for the implemented architecture, with the limitation that production deployment and scale are not verified. `VERIFIED` that no Instamart integration exists.

**Evidence:** `backend/app/main.py` (FastAPI application); `backend/app/db/models/__init__.py` (PostgreSQL models); `backend/app/core/rate_limit.py:31` (`RedisRateLimiter`); `backend/app/retailer_adapters/enforcement.py:87` (`RetailerAdapterExecutor`); `backend/app/credential_vault/crypto.py:22` (`ALGORITHM = "AES_256_GCM"`); `backend/app/data_ingestion/types.py:125,209,464` (parsed observation, raw artifact, normalized observation); `backend/app/product_intelligence/catalog/resolution.py:61` (canonical resolver); `backend/app/services/product_search.py:258` (`ProductSearchService`); `backend/app/services/cart_candidate_discovery.py:84` (`CartCandidateDiscoveryService`); `backend/app/cart_optimization/service.py:39` (optimizer); `docs/observability.md`.

---

### 6. OAuth / delegated authorization

**Answer (copy-ready):**

Cartel would use Swiggy's documented OAuth 2.1 with PKCE and delegated-access flow only after written approval. Swiggy's documentation states that access is scoped at the user level, that redirect URIs must be HTTPS and exact-match (with `http://localhost` allowed for local development), and that production access follows a working staging integration. Cartel would store any provider token or refresh material server-side, scoped to the owning Cartel user and retailer connection, and would support user-initiated disconnection/revocation. Cartel does not have an Instamart OAuth client, redirect allowlist, or credentials today.

Production HTTPS redirect URI(s): `OWNER_INPUT_REQUIRED (OI-07)`. No Instamart callback exists in the repository.

**Verification:** `VERIFIED` for Swiggy's published OAuth requirements. `VERIFIED` that Cartel has no Instamart OAuth client. `OWNER_INPUT_REQUIRED` for the redirect URI(s).

**Evidence:** `https://mcp.swiggy.com/builders/docs/start/authenticate/` (OAuth 2.1/PKCE, redirect rules, token lifecycle); `https://mcp.swiggy.com/builders/docs/start/enterprise/delegated-auth/` (per-user delegated flow, token storage); `backend/app/auth/service.py:223` (`begin_oauth`); `backend/app/auth/providers.py` (server-side OAuth verifiers).

---

### 7. Data collection and storage

**Answer (copy-ready):**

Subject to written Swiggy authorization, Cartel proposes to collect only the minimum data needed for the user's selected delivery context:

- stable retailer-native product identity;
- product title, brand, pack size, quantity, and variant attributes;
- location/address or coordinate context needed for serviceability;
- observed price and currency;
- explicit availability/inventory state;
- capture timestamp or freshness metadata;
- permitted retailer URL/reference;
- structured unavailable/error results.

Cartel would preserve source and capture provenance, keep retailer-native identity separate from canonical identity, and exclude unresolved or conflicting evidence from consumer eligibility. Cartel would not store retailer passwords, OTPs, payment credentials, or UPI PINs. No Swiggy authorization currently covers any of these activities for Cartel.

**Verification:** `VERIFIED` for the existing governed observation model and its provenance fields. The Instamart-specific schema, freshness semantics, and serviceability mapping are `NOT_VERIFIED` because Swiggy has not provided them and no Instamart integration exists.

**Evidence:** `docs/partnership/swiggy_instamart_partnership_brief.md:109-133`; `docs/retailer_data_provider_architecture.md:18-25`; `backend/app/data_ingestion/types.py:125,209,464`.

---

### 8. Security controls

**Answer (copy-ready):**

Implemented controls:

- Argon2id password hashing; plaintext passwords are not stored.
- Server-managed sessions with opaque token material stored as hashes.
- CSRF protection for state-changing authenticated requests.
- Server-side Google/GitHub OAuth token handling; Apple is not enabled.
- Owner-scoped retailer connections with a durable lifecycle.
- AES-256-GCM Credential Vault with associated-data binding to owner, connection, retailer, secret type, version, and reference.
- Vault access fails closed when a key provider is unavailable.
- Audit and structured logging paths exclude passwords, OTPs, cookies, and token material from ordinary payloads.
- Evidence preserves source/artifact/provenance metadata and fails closed on missing or conflicting authority.
- Historical Blinkit evidence is retained for audit but excluded from consumer eligibility.

Incomplete or planned controls:

- Production KMS/HSM or external secret-manager key custody. Cartel does **not** claim production KMS/HSM integration today.
- Instamart-specific OAuth client, token, refresh, and revocation lifecycle.
- Formal data-processing agreement and retention/deletion schedule for Instamart.
- Privacy impact assessment for addresses, coordinates, serviceability, and delegated retailer access.
- External security audit or certification. Cartel does **not** claim SOC 2, ISO 27001, penetration-test completion, or regulatory approval.
- Production deployment-specific key rotation, backup, disaster recovery, and incident-response evidence.

**Verification:** `VERIFIED` for each implemented control, with the explicit limitation that production key custody and external certification are absent. `NOT_VERIFIED` for Instamart-specific controls that do not exist yet.

**Evidence:** `backend/app/auth/service.py:24` (`PasswordHasher(... type=Type.ID)`); `backend/app/auth/service.py:69` (`csrf_token_for_session`); `backend/app/db/models/__init__.py:54-63` (`AuthSession.token_hash`, `csrf_hash`); `backend/app/credential_vault/crypto.py:22` (`AES_256_GCM`); `backend/app/credential_vault/service.py:171` (`CredentialVault`); `backend/app/retailer_connections/lifecycle.py:29` (connection states); `docs/observability.md` (logging exclusions); `docs/phase_j1_1_blinkit_lockdown.md`.

---

### 9. Privacy and retention

**Answer (copy-ready):**

Cartel would act as a data processor for Swiggy-originated data within the scope Swiggy permits, while Swiggy remains the data fiduciary under India's DPDP Act, 2023. Cartel would collect only the minimum fields needed for the user's selected delivery context, avoid using Swiggy-originated data for analytics, advertising, or model training without separate lawful basis and consent, hash or avoid persisting user identifiers where possible, and honour deletion requests. Cartel would retain Instamart-originated observations only for the period and purpose Swiggy authorizes.

Privacy-policy URL: `OWNER_INPUT_REQUIRED (OI-13)`.

Proposed retention period for Instamart-originated observations: `OWNER_INPUT_REQUIRED (OI-18)` — the owner/legal decision must be recorded before submission.

Formal data-processing agreement and final retention schedule: not yet in place; to be negotiated with Swiggy.

**Verification:** `VERIFIED` for Swiggy's published DPDP/data-processor posture. `OWNER_INPUT_REQUIRED` for Cartel's privacy-policy URL and retention period. `NOT_VERIFIED` for the final Swiggy-specific DPA terms.

**Evidence:** `https://mcp.swiggy.com/builders/docs/operate/data-and-compliance/` (DPDP 2023, data fiduciary/processor roles, retention guidance); `docs/partnership/swiggy_instamart_partnership_brief.md:152-159`.

---

### 10. Expected API traffic

**Answer (copy-ready):**

Cartel will not invent traffic numbers. The following are owner-supplied planning values and are not observed production traffic:

| Metric | Value |
|---|---|
| Expected launch users | `OWNER_INPUT_REQUIRED (OI-11)` |
| Expected orders per day | `OWNER_INPUT_REQUIRED (OI-11)` |
| Expected Instamart tool calls per day | `OWNER_INPUT_REQUIRED (OI-11)` |
| Expected peak QPS | `OWNER_INPUT_REQUIRED (OI-11)` |
| Launch geography | `OWNER_INPUT_REQUIRED (OI-12)` — product intent is India, subject to Swiggy coverage and approval |

Swiggy's onboarding page asks for a rough estimate of orders/day and tool calls/day, and enterprise applicants may be asked for expected peak QPS and end-user geography.

**Verification:** `OWNER_INPUT_REQUIRED` for all values. `VERIFIED` for the fact that Swiggy asks for these estimates.

**Evidence:** `https://mcp.swiggy.com/builders/docs/operate/access/` ("Expected volume — rough estimate of orders/day and tool calls/day"; enterprise: "expected peak QPS, surfaces, end-user geography"); `https://mcp.swiggy.com/builders/access/` (input 12: "Expected traffic and scaling plan (Optional)").

---

### 11. Production requirements

**Answer (copy-ready):**

Cartel understands Swiggy's published sequence: local development can begin without approval; staging access follows OAuth redirect allowlisting during application review; production access follows a working staging integration that has been green for at least 48 hours; enterprise commercial terms are negotiated per partner. Cartel will provide exact-match HTTPS redirect URIs, the servers it will call (`instamart`), a primary technical contact, a security contact, a data-handling/privacy declaration, and environment/infrastructure details.

Static IP ranges or gateway IP(s), if Swiggy requires them for production: `OWNER_INPUT_REQUIRED (OI-08)`. No production deployment value exists in the repository.

Zero-cost requirement: Cartel cannot accept mandatory API credits, platform fees, subscriptions, minimum commitments, paid data licences, or mandatory usage charges. Cartel requests a sustainable zero-cost production arrangement. Swiggy has not published production pricing or a zero-cost production commitment; the enterprise page states "No metered quotas today" but that is a capacity statement, not a pricing or zero-cost commitment. If Swiggy cannot offer a qualifying zero-cost production arrangement, Cartel records the integration as commercially infeasible under its current constraint.

**Verification:** `VERIFIED` for the published access sequence and for the absence of published production pricing. `OWNER_INPUT_REQUIRED` for static IP/gateway values. `NOT_VERIFIED` for Swiggy's actual production pricing and any zero-cost production terms.

**Evidence:** `https://mcp.swiggy.com/builders/docs/operate/access/`; `https://mcp.swiggy.com/builders/enterprises/` ("No metered quotas today"); `https://mcp.swiggy.com/builders/access/` (static IP input; optional traffic/scaling plan).

---

### 12. Technical contact

**Answer (copy-ready):**

Primary technical contact name and email: `OWNER_INPUT_REQUIRED (OI-09)`.

**Verification:** `OWNER_INPUT_REQUIRED` — no technical-contact identity exists in the repository.

**Evidence:** `https://mcp.swiggy.com/builders/docs/operate/access/` ("Primary technical contact — email that reaches an engineer").

---

### 13. Security contact

**Answer (copy-ready):**

Cartel security contact name and email: `OWNER_INPUT_REQUIRED (OI-10)`.

**Verification:** `OWNER_INPUT_REQUIRED` — no Cartel security-contact identity exists in the repository. Swiggy's own security contact (`security@swiggy.in`) is published on Swiggy's data-and-compliance page and is not a substitute for Cartel's contact.

**Evidence:** `https://mcp.swiggy.com/builders/access/` (input 6: "Security contact for your team"); `https://mcp.swiggy.com/builders/docs/operate/data-and-compliance/` (Swiggy's own `security@swiggy.in`).

---

## Developer-track form fields (verified from the public form)

The developer form is public. These are the actual visible fields and their prepared answers.

| Form field | Prepared answer | Label |
|---|---|---|
| Email | `OWNER_INPUT_REQUIRED (OI-05)` | `OWNER_INPUT_REQUIRED` |
| Full Name | `OWNER_INPUT_REQUIRED (OI-04)` | `OWNER_INPUT_REQUIRED` |
| Applying as | `OWNER_INPUT_REQUIRED (OI-15)` — options include Individual Developer, Small Team (2–5), Startup | `OWNER_INPUT_REQUIRED` |
| Team / Project Name | Cartel Smart Cart Optimizer | `VERIFIED` |
| GitHub or Portfolio URL | `OWNER_INPUT_REQUIRED (OI-20)` | `OWNER_INPUT_REQUIRED` |
| LinkedIn | `OWNER_INPUT_REQUIRED (OI-20)` | `OWNER_INPUT_REQUIRED` |
| What are you building? | Use the Topic 1 product description. | `VERIFIED` (text) |
| Which MCP servers do you need? | Swiggy Instamart | `VERIFIED` (intended server) |
| What type of integration is this? | Web App | `VERIFIED` (Next.js web application) |
| Tech stack & architecture overview | Use the Topic 5 architecture summary. | `VERIFIED` (text) |
| Production Redirect URI(s) for Authentication | `OWNER_INPUT_REQUIRED (OI-07)` — production HTTPS callback only; do not enter localhost | `OWNER_INPUT_REQUIRED` |
| Expected request volume | `OWNER_INPUT_REQUIRED (OI-11)` — choose the band only after owner traffic planning | `OWNER_INPUT_REQUIRED` |
| Working Demo Video Link | `OWNER_INPUT_REQUIRED (OI-14)` — no demo video exists yet | `OWNER_INPUT_REQUIRED` |
| I acknowledge Swiggy's MCP integration terms | `OWNER_INPUT_REQUIRED (OI-16)` — the owner must read and accept the terms | `OWNER_INPUT_REQUIRED` |

**Form source:** `https://forms.gle/4vkeKyqm15Qb6fnJA`, final URL `https://docs.google.com/forms/d/e/1FAIpQLSfUhtaGOQjnxS0o8uHFZwZGNxJhJzyYhxiYVotlqdBCpizpUw/viewform?usp=send_form`, HTTP 200, accessed 2026-11-09.

## Enterprise / Startup track (form fields not verified)

The Enterprise/Startup form returned HTTP 401 on 2026-11-09. Its exact field labels are **not verified**. The owner will see the form after opening the official link while signed in. Use the 13 topic-keyed answers above; they cover the inputs Swiggy publishes on the access and onboarding pages:

1. company details or individual developer profile;
2. use case;
3. architecture overview;
4. redirect URI(s);
5. static IP ranges or gateway IP(s);
6. security contact;
7. data handling and privacy declaration;
8. environment and infrastructure details;
9. acknowledgement of Swiggy MCP terms;
10. optional security audit summary;
11. optional SOC 2 / ISO certification (only if actually available — Cartel has none);
12. optional expected traffic and scaling plan;
13. enterprise-specific security attestations, expected peak QPS, surfaces, and end-user geography where requested.

**Enterprise form source:** `https://forms.gle/U6hYGYLYWQPHWY826`, final URL `https://docs.google.com/forms/d/e/1FAIpQLSf6oRHfUa2QFMsCE1Pteh7fnuAnAU5H1JlTr_M7t6MmreT8TA/viewform?usp=send_form`, HTTP 401, accessed 2026-11-09.

## Prohibited claims (do not add to any submission)

Do not state that Cartel:

- is a Swiggy partner or has an existing partnership;
- has production Instamart access, credentials, or authorization;
- has received approval or an exception;
- has customers, revenue, funding, certifications, or audits unless independently verified;
- has validated Instamart price, inventory, or serviceability behavior;
- can offer Swiggy data commercially;
- has a zero-cost production agreement;
- has production KMS/HSM integration or external security certification;
- will build an Instamart integration before written approval.
