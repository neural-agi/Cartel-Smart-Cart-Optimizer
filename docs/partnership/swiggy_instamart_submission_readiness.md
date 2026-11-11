# Swiggy Instamart Submission Readiness

**Status:** Internal audit and readiness report. **Do not submit this file.**

**Assessment date:** 2026-11-09
**Branch:** `feat/cartel-production-foundation`
**Prepared for:** manual submission by the Cartel owner.

---

## 1. Executive decision

**Verdict: `READY_WITH_OWNER_INPUT`.**

**Rule applied:** The official Swiggy submission route was verified by fetching official pages on 2026-11-09; the package documents do not contradict each other; no unsupported certification, KMS/HSM, partnership, approval, or authorization claim remains; and the zero-budget requirement is stated as a hard constraint without softening. The only remaining gaps are (a) owner-supplied identity, contact, URL, redirect, IP, traffic, privacy, retention, and acknowledgement fields, and (b) externally unverifiable facts that Swiggy has not published (Enterprise/Startup form labels are auth-gated; production pricing and zero-cost production terms are not published).

This is **not** an approval, a partnership, or an authorization. It means the owner can manually submit an accurate package once the owner-input register is completed.

| Readiness gate | Result |
|---|---|
| Official route verified by fetching | Pass (2026-11-09) |
| Cross-document contradictions | None found |
| Unsupported claims reintroduced | None found (see §3) |
| Zero-budget requirement softened | No (see §6) |
| Every application field verified or owner-marked | Yes (13 topics; 20 owner-input IDs) |
| Every external link validates | Yes; enterprise form returns HTTP 401 by design (auth-gated) |
| `OWNER_INPUT_REQUIRED` count | 20 unique IDs / 31 markers |
| `NOT_VERIFIED` external unknowns | Enterprise form labels; production pricing / zero-cost terms |

---

## 2. Verified official submission route

Starting point: `https://mcp.swiggy.com/builders/access/`. All pages below were fetched on **2026-11-09**. "Final URL" is the URL after redirects.

| Page | URL | Final URL | HTTP | What was visible / exact text relied on |
|---|---|---|---|---|
| Production access / application | `https://mcp.swiggy.com/builders/access/` | same | 200 | 12 application inputs; review stages; operating rules. Under **"Not Allowed Restricted"**, item 05: **"Using the APIs for competitive intelligence or benchmarking"**; item 02: **"Building aggregation layers that hide Swiggy's brand or confuse users"**. Links to developer and Enterprise/Startup forms; `builders@swiggy.in`. |
| Access & onboarding | `https://mcp.swiggy.com/builders/docs/operate/access/` | same | 200 | **"Swiggy MCP is invite-based in v1."**; **"Production access once staging has been green for ≥ 48 hours."**; **"Expected volume - rough estimate of orders/day and tool calls/day."**; **"Primary technical contact - email that reaches an engineer."**; enterprise: **"security attestations available (SOC 2, ISO 27001), expected peak QPS, surfaces (voice/chat/app), end-user geography."**; **"typically 4+ weeks because commercial terms are negotiated per-partner."** |
| Docs index | `https://mcp.swiggy.com/builders/docs/` | same | 200 | **"No access needed until prod."**; **"Wire Swiggy MCP into your agent on `http://localhost`"**; four MCP servers (Food, Instamart, Dineout, Scenes). |
| Developers | `https://mcp.swiggy.com/builders/developers/` | same | 200 | **"No approval needed to start. Build locally for free, then apply only when you're ready to go live in production."** |
| Enterprises | `https://mcp.swiggy.com/builders/enterprises/` | same | 200 | **"No metered quotas today. Share your expected traffic and we plan capacity together for production scale."** Link to Enterprise form; `builders@swiggy.in`. No pricing, cost, or "free production" statement. |
| Instamart reference | `https://mcp.swiggy.com/builders/docs/reference/instamart/` | same | 200 | 16 Instamart tools (address, search, cart, payment, order, tracking). |
| Authenticate | `https://mcp.swiggy.com/builders/docs/start/authenticate/` | same | 200 | **"OAuth 2.1 with PKCE"**; **"HTTPS required (except `http://localhost` for local development)"**; **"Exact-match allowlist - no wildcards"**; access token 5 days, refresh 30 days. |
| Delegated auth | `https://mcp.swiggy.com/builders/docs/start/enterprise/delegated-auth/` | same | 200 | OAuth 2.1 on-behalf-of flow for multi-tenant platforms serving end users. |
| Data & compliance | `https://mcp.swiggy.com/builders/docs/operate/data-and-compliance/` | same | 200 | **"Swiggy is the Data Fiduciary"**; **"Your integration acts as a Data Processor operating within the scope Swiggy permits."**; **"Do not persist user PII longer than needed"**; certifications **"Available on request under NDA"**; `security@swiggy.in`. |
| Rate limits | `https://mcp.swiggy.com/builders/docs/operate/rate-limits/` | same | 200 | **"Exact caps aren't published here and may change."**; gateway `429` with `Retry-After`. |
| SLA & uptime | `https://mcp.swiggy.com/builders/docs/operate/sla/` | same | 200 | **"Numbers below are v1 targets, not contractual commitments."** |
| Ship to production | `https://mcp.swiggy.com/builders/docs/build/ship-to-production/` | same | 200 | Technical production checklist. |
| Developer form | `https://forms.gle/4vkeKyqm15Qb6fnJA` | `https://docs.google.com/forms/d/e/1FAIpQLSfUhtaGOQjnxS0o8uHFZwZGNxJhJzyYhxiYVotlqdBCpizpUw/viewform?usp=send_form` | 200 | **Public.** Full field list visible (see §7). |
| Enterprise / Startup form | `https://forms.gle/U6hYGYLYWQPHWY826` | `https://docs.google.com/forms/d/e/1FAIpQLSf6oRHfUa2QFMsCE1Pteh7fnuAnAU5H1JlTr_M7t6MmreT8TA/viewform?usp=send_form` | 401 | **Auth-gated. No fields visible.** Enterprise form labels are **not verified**. |

### Review stages and timeline (as published)

The access page lists the review stages: **Security Check, Compliance Review, Use Case Fit, Gradual Rollout, Ongoing Partnership**. The onboarding page states that platform/enterprise onboarding is **"typically 4+ weeks because commercial terms are negotiated per-partner."** These are Swiggy's published statements, not Cartel estimates.

### What was not visible / not published

- **Enterprise/Startup form fields:** the form returned HTTP 401 (Google sign-in required). Cartel did not sign in and did not reconstruct hidden fields. The enterprise response set is keyed to the topics Swiggy publishes on the access and onboarding pages and is labelled **"form fields not verified."**
- **Production pricing / zero-cost production terms:** not published on any official page fetched. The enterprise page's **"No metered quotas today"** is a capacity statement, not a pricing or zero-cost commitment.
- **Swiggy consumer terms / privacy policy:** `https://www.swiggy.com/terms-and-conditions` and `https://www.swiggy.com/privacy-policy` returned HTTP 200 but rendered no readable text via fetch (JS-rendered). They were **not used** as a source for any claim in the package.
- **Cartel authorization:** no page, account, credential, or written communication exists. The package states this explicitly.

---

## 3. J.2.3 corrections-preserved checklist

Every correction below is preserved in substance. Line numbers refer to the current files.

| # | J.2.3 correction | `swiggy_instamart_partnership_brief.md` | `swiggy_instamart_authorization_inquiry.md` | `swiggy_instamart_application_fields.md` | New package |
|---|---|---|---|---|---|
| 1 | Implemented vs. planned capabilities are distinguished | 30, 53–67, 71, 78 | absent: the inquiry is a request, not a capability matrix | 54, 65 | `application_responses.md` 160, 173; `technical_attachments.md` 17 |
| 2 | Security limitations are disclosed | 54–66 (limitation column), 152–159 | absent: not a security document | 65–72 | `application_responses.md` 173–182; `technical_attachments.md` 16–17 |
| 3 | Production KMS/HSM integration is missing and not claimed | 57, 74, 82, 154 | absent: no security inventory | 67 | `application_responses.md` 175, 322 |
| 4 | No external security certification is claimed | 69, 85, 157 | absent: no certification claim | 48, 70, 85 | `application_responses.md` 83, 179, 305, 318, 322 |
| 5 | Competitive-intelligence/benchmarking restriction is explicit | 26, 182, 230 | 22, 27 | 76 | `final_inquiry_email.md` 28, 53, 68; `application_responses.md` 97 |
| 6 | Cross-retailer comparison is disclosed | 24, 171 | 11, 26, 29 | 20 | `final_inquiry_email.md` 17, 21, 52; `application_responses.md` 43, 95 |
| 7 | Zero-budget production requirement is stated | 9, 203, 232, 242 | 5 | 76, 88 | `final_inquiry_email.md` 34, 36, 57; `application_responses.md` 236, 238, 321 |
| 8 | Production pricing is unknown / not published | 9, 203, 232 | absent: the inquiry requests terms without asserting a price | absent: the field sheet defers to the brief; it makes no pricing claim | `application_responses.md` 236, 238 |
| 9 | Absence of Swiggy authorization is stated | 9, 76, 107 | 13 | 84 | `final_inquiry_email.md` 38; `application_responses.md` 47, 111 |

### Removed-claims grep (any hit is a finding)

Commands run from the repository root on 2026-11-09 against the four new package files:

```sh
grep -rniE "official integration|production-ready|production ready" <package>
grep -rniE "\bpartner\b" <package>
grep -rniE "\bapproved\b" <package>
grep -rniE "\bauthorized\b" <package>
grep -rniE "certification|certified|SOC 2|ISO 27001|KMS|HSM" <package>
```

| Pattern | Hits | Assessment |
|---|---|---|
| `official integration` | 0 | Pass |
| `production-ready` / `production ready` | 0 | Pass |
| `\bpartner\b` | 3 | All safe: "does not claim to be a Swiggy partner" (responses 45), "negotiated per partner" (responses 232, Swiggy's own process), "is a Swiggy partner or has an existing partnership" in the prohibited-claims list (responses 315). |
| `\bapproved\b` | 0 | Pass |
| `\bauthorized\b` | 5 | All refer to "other authorized retailers", "Authorized signatory", or "authorized to send"; none claims Swiggy authorized Cartel. |
| `certification` / `certified` / `SOC 2` / `ISO 27001` / `KMS` / `HSM` | 9 | All are negations, planned/incomplete labels, optional form inputs, or prohibited claims. Examples: "does **not** claim ... external security certification" (responses 83); "Cartel does **not** claim production KMS/HSM integration today" (responses 175); "only if actually available — Cartel has none" (responses 305). |

No unsupported claim was reintroduced.

---

## 4. Cross-document consistency table

Facts were extracted from the three scoped documents and the new package. No contradiction was found, so no scoped document was edited.

| Fact | Brief | Inquiry | Field sheet | New package | Result |
|---|---|---|---|---|---|
| Retailers covered | 24 | 11 | 20 | email 17, 21; responses 43, 95 | Consistent: cross-retailer, Instamart plus other authorized retailers |
| Comparison model | 24 | 11, 26, 29 | 20 | email 17, 21; responses 43, 95 | Consistent: comparative display plus derived basket allocation |
| Data collected | 109–131 | not detailed | 18 | responses §7 (133–150) | Consistent: minimum delivery-context fields |
| Retention | 128, 155, 241 | not detailed | 69 | email 32; responses §9 (186–205) | Consistent: Swiggy-authorized period; Cartel retention is owner/legal input |
| Security controls | 35–39, 53–67, 137–159 | not detailed | 32, 52–72 | responses 160–182 | Consistent |
| Implemented vs. planned | 30, 71, 78 | n/a | 54, 65 | responses 160, 173 | Consistent |
| Zero-budget stance | 9, 203, 232, 242 | 5 | 76, 88 | email 34, 36; responses 236, 321 | Consistent: hard constraint |
| Pricing status | 203, 232 (UNKNOWN) | absent (asks) | absent | responses 236, 238 (NOT_VERIFIED) | Consistent: no document claims a price or a zero-cost commitment |
| Traffic assumptions | 218 (lists Swiggy inputs, no numbers) | none | 41 (lists input, no numbers) | responses §10: all `OWNER_INPUT_REQUIRED` | Consistent: no invented traffic |
| Swiggy contacts | 216 (`builders@swiggy.in`) | none | none | email To `builders@swiggy.in`; responses `builders@` / `security@` | Consistent: official Swiggy addresses only |
| Cartel contacts | owner input | none | owner input | owner input (OI-04, OI-05, OI-09, OI-10) | Consistent: never invented |

**Mismatches found:** none. No scoped-doc edit was necessary.

---

## 5. Claim-to-evidence table

Every technical claim in the package maps to repository code (`file:symbol`) or a cited document. Labels are `IMPLEMENTED`, `PLANNED`, or `NOT PRESENT/VERIFIED`.

| Claim | Evidence | Label |
|---|---|---|
| FastAPI backend | `backend/app/main.py:FastAPI` (136) | IMPLEMENTED |
| Next.js frontend | `frontend/package.json` (`"next": "16.3.8"`) | IMPLEMENTED |
| PostgreSQL persistence models | `backend/app/db/models/__init__.py` (AuthSession 54, BackgroundJob 137, EmailOutboxEvent 172) | IMPLEMENTED |
| Server-managed sessions with hashed token material | `backend/app/auth/service.py:csrf_token_for_session` (69); `backend/app/db/models/__init__.py:AuthSession.token_hash` (60), `csrf_hash` (61) | IMPLEMENTED |
| CSRF protection | `backend/app/auth/service.py:csrf_token_for_session` (69) | IMPLEMENTED |
| Argon2id password hashing | `backend/app/auth/service.py:PASSWORD_HASHER` (24, `type=Type.ID`) | IMPLEMENTED |
| Server-side Google/GitHub OAuth handling | `backend/app/auth/service.py:begin_oauth` (223), `authenticate_external` (252); `backend/app/auth/providers.py` | IMPLEMENTED (no live provider credentials verified) |
| AES-256-GCM Credential Vault with AAD binding | `backend/app/credential_vault/crypto.py:ALGORITHM` (22); `backend/app/credential_vault/service.py:CredentialVault` (171) | IMPLEMENTED (development key provider only) |
| Vault fails closed when key provider unavailable | `backend/app/credential_vault/service.py` (`VaultKeyUnavailable` path) | IMPLEMENTED |
| Owner-scoped retailer connection lifecycle | `backend/app/retailer_connections/lifecycle.py:RetailerConnectionStatus` (29) | IMPLEMENTED |
| Adapter capability/lifecycle enforcement | `backend/app/retailer_adapters/enforcement.py:RetailerAdapterExecutor` (87) | IMPLEMENTED |
| Blinkit deny-by-default policy boundary | `backend/app/retailer_policy.py:is_blinkit`, `ensure_retailer_allowed`, `blinkit_consumer_eligible`; `backend/app/services/product_search.py` (131–133); `backend/app/services/cart_candidate_discovery.py` (121) | IMPLEMENTED |
| Governed ingestion and provenance | `backend/app/data_ingestion/types.py:ParsedRetailObservation` (125), `RawArtifactReference` (209), `NormalizedObservation` (464) | IMPLEMENTED |
| Exact Product/Variant resolution | `backend/app/product_intelligence/catalog/resolution.py:DeterministicCanonicalListingResolver` (61) | IMPLEMENTED |
| Consumer product search | `backend/app/services/product_search.py:ProductSearchService` (258) | IMPLEMENTED |
| Candidate discovery | `backend/app/services/cart_candidate_discovery.py:CartCandidateDiscoveryService` (84) | IMPLEMENTED |
| Basket optimization | `backend/app/cart_optimization/service.py:optimize` (39) | IMPLEMENTED |
| Redis distributed rate limiting | `backend/app/core/rate_limit.py:RedisRateLimiter` (31); `docs/runtime_rate_limiting.md` | IMPLEMENTED |
| Durable background jobs/outbox | `backend/app/db/models/__init__.py:BackgroundJob` (137), `EmailOutboxEvent` (172) | IMPLEMENTED |
| Basic observability (JSON logs, request IDs, metrics, health) | `docs/observability.md` | IMPLEMENTED (no Prometheus/Grafana/OTel collector/alert routing) |
| Production KMS/HSM or external secret manager | no code; explicitly absent | PLANNED |
| Instamart adapter / OAuth client / credentials | no code; explicitly absent | PLANNED |
| External security audit or certification | no evidence | NOT PRESENT |
| Production deployment, scale, DR, key rotation | no evidence | NOT VERIFIED |
| Swiggy authorization / partnership / approval | no evidence | NOT PRESENT |

The email's technical statements (cross-retailer model, no adapter, no credentials, zero-cost constraint, no integration before approval) match the application responses.

---

## 6. Zero-budget confirmation

### Exact wording used

**Email** (`swiggy_instamart_final_inquiry_email.md:36`):

> "On cost: Cartel cannot accept mandatory API credits, platform fees, subscriptions, minimum commitments, paid data licences, or mandatory usage charges. Free local development is not the constraint; Cartel needs a sustainable zero-cost production arrangement. If Swiggy cannot offer a qualifying zero-cost production arrangement, we will record the integration as commercially infeasible under our current constraint rather than proceed."

**Application responses** (`swiggy_instamart_application_responses.md:236`):

> "Zero-cost requirement: Cartel cannot accept mandatory API credits, platform fees, subscriptions, minimum commitments, paid data licences, or mandatory usage charges. Cartel requests a sustainable zero-cost production arrangement. Swiggy has not published production pricing or a zero-cost production commitment; the enterprise page states 'No metered quotas today' but that is a capacity statement, not a pricing or zero-cost commitment. If Swiggy cannot offer a qualifying zero-cost production arrangement, Cartel records the integration as commercially infeasible under its current constraint."

### What Cartel cannot accept

- Mandatory API credits or prepaid usage.
- Platform fees.
- Subscriptions.
- Minimum commitments or minimum spend.
- Paid data licences.
- Mandatory per-call or usage charges.

### Local development vs. sustainable production

- **Local development:** Swiggy publishes that local development is free and needs no approval (`developers` page; onboarding page). This is **not** the constraint and is not treated as satisfying the requirement.
- **Sustainable production:** no official page publishes production pricing, a zero-cost production tier, or a zero-cost production commitment. This remains `NOT_VERIFIED` and is requested in writing in the email.
- **Consequence:** if Swiggy cannot offer a qualifying zero-cost production arrangement, the integration is recorded as **commercially infeasible under Cartel's current constraint**. Cartel does not proceed.

### Softening grep

Command:

```sh
grep -rniF "<term>" docs/partnership/swiggy_instamart_final_inquiry_email.md \
  docs/partnership/swiggy_instamart_application_responses.md \
  docs/partnership/swiggy_instamart_technical_attachments.md \
  docs/partnership/swiggy_instamart_owner_input_register.md
```

| Term | Hits |
|---|---|
| `flexible on pricing` | 0 |
| `open to a pilot fee` | 0 |
| `initial credits` | 0 |
| `nominal` | 0 |

Broader grep for `pilot|discount|waive|free tier|concession` found **one** hit: "We are not asking you to waive that rule by implication" (`final_inquiry_email.md:28`) — a negation, not a softening. No hit softens the zero-budget position.

---

## 7. Application responses (summary of labels)

Full copy-ready text is in `swiggy_instamart_application_responses.md`. Every topic carries a verification label.

| # | Topic | Label(s) |
|---|---|---|
| 1 | Product name and description | `VERIFIED` |
| 2 | Organization / developer profile | `OWNER_INPUT_REQUIRED` (OI-01, 02, 03, 04, 05, 06, 15, 19) |
| 3 | Product stage | `VERIFIED` |
| 4 | Intended use case | `VERIFIED` + `OWNER_INPUT_REQUIRED` (OI-17) |
| 5 | Architecture | `VERIFIED` (production scale not verified) |
| 6 | OAuth / delegated authorization | `VERIFIED` + `OWNER_INPUT_REQUIRED` (OI-07) |
| 7 | Data collection and storage | `VERIFIED` + `NOT_VERIFIED` (Instamart schema) |
| 8 | Security controls | `VERIFIED` + `NOT_VERIFIED` (Instamart-specific controls) |
| 9 | Privacy and retention | `VERIFIED` + `OWNER_INPUT_REQUIRED` (OI-13, OI-18) + `NOT_VERIFIED` (DPA terms) |
| 10 | Expected API traffic | `OWNER_INPUT_REQUIRED` (OI-11, OI-12) |
| 11 | Production requirements | `VERIFIED` + `OWNER_INPUT_REQUIRED` (OI-08) + `NOT_VERIFIED` (pricing) |
| 12 | Technical contact | `OWNER_INPUT_REQUIRED` (OI-09) |
| 13 | Security contact | `OWNER_INPUT_REQUIRED` (OI-10) |

### Developer form (verified public fields)

The developer form's visible fields are: Email, Full Name, Applying as (Individual Developer / Small Team 2–5 / Startup), Team/Project Name, GitHub or Portfolio URL, LinkedIn, What are you building?, Which MCP servers, Integration type, Tech stack & architecture, Production Redirect URI(s), Expected request volume, Working Demo Video Link, terms acknowledgement. Prepared answers are in the responses file.

### Enterprise / Startup form

**Form fields not verified.** The form returned HTTP 401. The responses file uses the 13 topics above, which cover every input Swiggy publishes on the access and onboarding pages.

---

## 8. Technical attachment checklist (summary)

Full detail is in `swiggy_instamart_technical_attachments.md`.

| Candidate | Classification | Key reason |
|---|---|---|
| `docs/product_intelligence_design.md` | `SHAREABLE AS-IS` | Read in full; domain-boundary architecture; no leaks |
| `docs/observability.md` | `SHAREABLE AS-IS` | Read in full; states what is not implemented |
| `docs/architecture/README.md` | `DOES NOT EXIST YET` | 3-line placeholder |
| Data-flow diagram | `NEEDS SANITIZATION` | Extract the Mermaid diagram from the brief; remove internal status/evidence/Blinkit lines |
| `docs/architecture/production_readiness_gap.md` | `DO NOT SHARE` | Internal candid gap assessment; Blinkit and readiness-score detail |
| `docs/retailer_data_provider_architecture.md` | `DO NOT SHARE` | Blinkit/QuickCommerce provider detail and internal script paths |
| `docs/phase_j1_1_blinkit_lockdown.md` | `DO NOT SHARE` | Blinkit-specific competitor policy |
| `README.md` | `DO NOT SHARE` | Contains `127.0.0.1`, Compose topology, deployment commands |
| Existing brief / inquiry / field sheet / submission package | `NEEDS SANITIZATION` / superseded | Internal status and `TBD`/`UNKNOWN` markers |
| Traffic assumptions | `DOES NOT EXIST YET` | All values are owner input |
| Demo video | `DOES NOT EXIST YET` | Owner input (OI-14) |

### Attachment scan results

Scan patterns: absolute paths (`/Users/`, `C:\`, `/home/`, `/private/var/`), private IPs, `localhost`/`127.0.0.1`, secret patterns, and email addresses.

- No absolute paths, private IPs, or secret-like strings in any candidate document.
- `README.md`: 6 `127.0.0.1` hits → `DO NOT SHARE`.
- `localhost` hits in partnership files are quotations of Swiggy's published local-development allowance, not Cartel addresses.
- Email addresses found are official Swiggy contacts only (`builders@swiggy.in`, `security@swiggy.in`).

---

## 9. Link validation

Every external link in the three scoped documents and the four new package files was fetched on 2026-11-09.

| URL | HTTP | Final URL | Note |
|---|---|---|---|
| `https://mcp.swiggy.com/builders/access/` | 200 | same | Official access page |
| `https://mcp.swiggy.com/builders/developers/` | 200 | same | Official developer page |
| `https://mcp.swiggy.com/builders/docs/` | 200 | same | Official docs index |
| `https://mcp.swiggy.com/builders/docs/operate/` | 200 | same | Official operate index |
| `https://mcp.swiggy.com/builders/docs/operate/access/` | 200 | same | Official onboarding |
| `https://mcp.swiggy.com/builders/docs/operate/data-and-compliance/` | 200 | same | Official compliance |
| `https://mcp.swiggy.com/builders/docs/reference/instamart/` | 200 | same | Official Instamart reference |
| `https://mcp.swiggy.com/builders/docs/start/authenticate/` | 200 | same | Official auth docs |
| `https://mcp.swiggy.com/builders/docs/start/enterprise/delegated-auth/` | 200 | same | Official delegated auth |
| `https://mcp.swiggy.com/builders/enterprises/` | 200 | same | Official enterprise page |
| `https://forms.gle/4vkeKyqm15Qb6fnJA` | 200 | `https://docs.google.com/forms/d/e/1FAIpQLSfUhtaGOQjnxS0o8uHFZwZGNxJhJzyYhxiYVotlqdBCpizpUw/viewform?usp=send_form` | Official developer form; redirect is expected (Google Forms) |
| `https://forms.gle/U6hYGYLYWQPHWY826` | 401 | `https://docs.google.com/forms/d/e/1FAIpQLSf6oRHfUa2QFMsCE1Pteh7fnuAnAU5H1JlTr_M7t6MmreT8TA/viewform?usp=send_form` | Official enterprise form; **auth-gated by design** |
| `http://localhost` | n/a | n/a | Not an external link; a quoted Swiggy local-development allowance |

No 404s, no non-official domains, and no placeholder or example URLs remain. The only non-200 is the enterprise form's expected 401.

---

## 10. Whole-package leak scan

Command pattern (run from the repository root, 2026-11-09):

```sh
grep -nE "/Users/|C:\\\\|/home/|/private/var/" <file>
grep -nE "(^|[^0-9])(10\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+)([^0-9]|$)" <file>
grep -nE "localhost|127\.0\.0\.1" <file>
grep -nE -- "-----BEGIN|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{16,}|password[[:space:]]*=|secret[[:space:]]*=|api[_-]?key[[:space:]]*=" <file>
grep -coE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" <file>
```

Raw grep counts for every package file (including this report). Counts are literal pattern matches; the "Nature of hits" column classifies them.

| File | Paths | Private IPs | localhost | Secrets | Emails | Nature of hits |
|---|---:|---:|---:|---:|---:|---|
| `final_inquiry_email.md` | 0 | 0 | 0 | 0 | 1 | Official `builders@swiggy.in` |
| `application_responses.md` | 0 | 0 | 2 | 0 | 3 | Two quotations of Swiggy's `http://localhost` local-dev allowance; official Swiggy addresses |
| `technical_attachments.md` | 1 | 0 | 8 | 1 | 4 | **Self-referential only:** the documented scan commands (`/Users/`, `-----BEGIN|...|password=`, `localhost`) and quoted Swiggy `localhost`/`127.0.0.1` text; official Swiggy addresses |
| `owner_input_register.md` | 0 | 0 | 1 | 0 | 0 | The instruction "no localhost in the production field" |
| `submission_readiness.md` (this file) | 2 | 0 | 10 | 1 | 7 | **Self-referential only:** the documented scan commands, quoted Swiggy `localhost` text, and official Swiggy addresses |
| `partnership_brief.md` | 0 | 0 | 0 | 0 | 1 | Official `builders@swiggy.in` |
| `authorization_inquiry.md` | 0 | 0 | 0 | 0 | 0 | None |
| `application_fields.md` | 0 | 0 | 0 | 0 | 0 | None |

**Verified classification:** no owner name, personal email, credential, absolute filesystem path, internal hostname, or private infrastructure address appears as an actual value in any package file. Every path/secret/localhost hit in `technical_attachments.md` and `submission_readiness.md` is either (a) the scan command written out as documentation, or (b) a quotation of Swiggy's published `http://localhost` local-development allowance. The only email addresses are official Swiggy contacts (`builders@swiggy.in`, `security@swiggy.in`). The `owner_input_register.md` hit is an instruction, not an address.

---

## 11. Owner-input register reconciliation

The register is `swiggy_instamart_owner_input_register.md` (OI-01 through OI-20).

Commands:

```sh
grep -rhoE "OWNER_INPUT_REQUIRED \(OI-[0-9]{2}\)" \
  docs/partnership/swiggy_instamart_final_inquiry_email.md \
  docs/partnership/swiggy_instamart_application_responses.md \
  docs/partnership/swiggy_instamart_technical_attachments.md | sort | uniq -c

grep -oE "OI-[0-9]{2}" docs/partnership/swiggy_instamart_owner_input_register.md | sort -u
```

| Check | Count |
|---|---|
| Total `OWNER_INPUT_REQUIRED (OI-xx)` markers in the package | 31 |
| Unique marker IDs | 20 (OI-01 … OI-20) |
| Register IDs | 20 (OI-01 … OI-20) |
| Markers without a register row | 0 |
| Register rows without a marker | 0 |

Both directions reconcile exactly.

### Blocking classification

- **Blocking:** OI-01, 02, 04, 05, 06, 09, 10, 11, 12, 13, 15, 16, 17, 18, 19.
- **Conditional:** OI-03 (if a registration ID exists), OI-08 (if Swiggy requires static IPs), OI-14 and OI-20 (developer track only).

---

## 12. Remaining blockers

1. **Owner-supplied identity and contact fields** — OI-01 to OI-06, OI-09, OI-10, OI-19. Cannot be invented.
2. **Owner-supplied production redirect URI(s)** — OI-07. No production callback exists in the repository.
3. **Owner-supplied traffic and geography** — OI-11, OI-12. No traffic numbers may be invented.
4. **Owner/legal privacy inputs** — OI-13 (privacy-policy URL), OI-18 (retention period).
5. **Owner acknowledgements** — OI-15 (track), OI-16 (terms), OI-17 (branding).
6. **Developer-track extras** — OI-14 (demo video), OI-20 (GitHub/LinkedIn).
7. **External unknown: enterprise form fields** — HTTP 401; labels not verified.
8. **External unknown: production pricing / zero-cost terms** — not published; requested in writing.
9. **No written Swiggy authorization** — the package requests it; none exists.
10. **No Instamart adapter or credentials** — intentionally absent; will not be built before written approval.

None of these is a contradiction or an unsupported claim. They are owner inputs or documented external unknowns, which is why the verdict is `READY_WITH_OWNER_INPUT`, not `NOT_READY`.

---

## 13. Verified vs. inferred

### Verified (fetched or repository-read on 2026-11-09)

- All official Swiggy URLs and quotes in §2.
- The competitive-intelligence and aggregation restrictions, quoted verbatim from the access page.
- The developer form's public field list; the enterprise form's HTTP 401 gate.
- The absence of published production pricing / zero-cost production terms.
- Every repository symbol in §5 (read from the listed files).
- Owner-input marker/register reconciliation (§11).
- Link statuses (§9) and leak-scan results (§10).

### Inferred or owner-dependent (not asserted as fact)

- That the Enterprise/Startup route is the better fit for a consumer product integrating Swiggy commerce. This is a recommendation; the owner chooses (OI-15).
- That Swiggy may require static IPs for Cartel's deployment. The access page lists static IPs as an input; whether they apply is not published for Cartel's case (OI-08).
- The appropriate retention period for Instamart-originated data. Owner/legal decision (OI-18), subject to Swiggy's written terms.
- The exact Enterprise form field labels. **Not verified** (auth-gated).
- Swiggy's production pricing and any zero-cost production arrangement. **Not published / not verified.**

---

## 14. Git preservation

**Before (recorded at start):**

- Branch: `feat/cartel-production-foundation`
- HEAD: `59560b9dcab78c82c8bd3b0c47f8d7d33508a821`
- Staged: 0 files
- Many pre-existing modified and untracked files outside `docs/partnership/` were present and were left untouched.

**After:**

- No `git add`, `commit`, `push`, `pull`, `reset`, `clean`, `stash`, `checkout`, or discard was run.
- Changes are confined to `docs/partnership/` (the directory is untracked as a whole, so `git diff --stat -- docs/partnership/` is empty; `git status --short -- docs/partnership/` shows `?? docs/partnership/`).
- Pre-existing work outside `docs/partnership/` is unchanged.

---

## 15. Package file index

| File | Purpose | External use |
|---|---|---|
| `swiggy_instamart_final_inquiry_email.md` | Final email, 392-word body, element checklist, source quote | Send manually after owner input |
| `swiggy_instamart_application_responses.md` | 13 topic-keyed copy-ready answers with labels; developer fields; enterprise caveat | Paste into forms after removing internal annotations |
| `swiggy_instamart_technical_attachments.md` | Attachment classification, sanitization, scan results | Internal review |
| `swiggy_instamart_owner_input_register.md` | OI-01–OI-20 register and reconciliation | Internal only |
| `swiggy_instamart_submission_readiness.md` | This report | Internal only |
| `swiggy_instamart_partnership_brief.md` | Existing internal brief (superseded as submission source) | Internal |
| `swiggy_instamart_authorization_inquiry.md` | Existing draft inquiry (superseded by the final email) | Internal |
| `swiggy_instamart_application_fields.md` | Existing field prep (superseded by the responses file) | Internal |
| `swiggy_instamart_submission_package.md` | Existing package using `TBD` (superseded; not edited) | Internal / historical |
