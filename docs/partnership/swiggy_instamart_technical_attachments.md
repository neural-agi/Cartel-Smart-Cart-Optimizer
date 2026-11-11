# Swiggy Instamart Technical Attachment Checklist

**Status:** Internal review sheet for the owner. **Not submitted.**

**Purpose:** Identify which repository documents can be attached to the Swiggy application, which need sanitization, which must not be shared, and which do not exist yet.

**Rule applied:** A document is called `SHAREABLE AS-IS` only after it was actually read for this review and scanned for paths, internal hostnames, private IPs, `localhost`, secret patterns, and email addresses. A partial document is not presented as a complete attachment.

## Classification summary

| Candidate attachment | Path | Classification | Reason |
|---|---|---|---|
| Architecture overview — product-intelligence domain boundaries | `docs/product_intelligence_design.md` | `SHAREABLE AS-IS` | Read in full. Explains canonical Product/Variant vs. retailer listing/observation separation. No paths, hosts, IPs, secrets, or personal data. Partial system scope only. |
| Architecture overview — full system | `docs/architecture/README.md` | `DOES NOT EXIST YET` | The file is a 3-line placeholder ("Architecture notes placeholder"). It is not an architecture overview. |
| Data-flow diagram | `docs/partnership/swiggy_instamart_partnership_brief.md` lines 87–107 | `NEEDS SANITIZATION` | The Mermaid diagram itself is usable, but the surrounding brief is an internal readiness document. Extract only the diagram into a standalone attachment; remove internal status, evidence matrix, and Blinkit lines. |
| Security summary — operational controls | `docs/observability.md` | `SHAREABLE AS-IS` | Read in full. Describes logging, metrics, health/readiness, and explicitly lists what is not implemented. No paths, hosts, IPs, secrets, or personal data. |
| Security summary — application controls | `docs/partnership/swiggy_instamart_application_responses.md` §8 | `SHAREABLE AS-IS` after owner review | Copy-ready implemented vs. incomplete controls. Do not copy the internal evidence annotations. |
| Data-handling declaration | `docs/partnership/swiggy_instamart_application_responses.md` §7 and §9 | `SHAREABLE AS-IS` after owner review | Copy-ready collection, storage, retention, and DPDP posture. Do not copy internal evidence annotations. |
| Use-case description | `docs/partnership/swiggy_instamart_application_responses.md` §1 and §4 | `SHAREABLE AS-IS` after owner review | Copy-ready cross-retailer disclosure and competitive-intelligence acknowledgement. |
| Traffic assumptions | `docs/partnership/swiggy_instamart_application_responses.md` §10 | `DOES NOT EXIST YET` | All traffic values are `OWNER_INPUT_REQUIRED`. No traffic numbers exist and none may be invented. |
| Known limitations | `docs/architecture/production_readiness_gap.md` | `DO NOT SHARE` | Internal candid assessment, including a 32% readiness score, Blinkit scraper references, and internal gap language. It would need substantial rewriting; not suitable as-is. |
| Retailer data-provider architecture | `docs/retailer_data_provider_architecture.md` | `DO NOT SHARE` | Blinkit/QuickCommerce-specific provider modes, environment-variable names, and an operator script path. Not Instamart-relevant and reveals Blinkit workaround history. |
| Blinkit lockdown | `docs/phase_j1_1_blinkit_lockdown.md` | `DO NOT SHARE` | Blinkit-specific competitor policy and internal enforcement detail. Not relevant to Swiggy and could invite unrelated questions. |
| Deployment README | `README.md` | `DO NOT SHARE` | Contains `127.0.0.1`, Docker Compose topology, deployment commands, and internal operational detail. |
| Partnership brief | `docs/partnership/swiggy_instamart_partnership_brief.md` | `NEEDS SANITIZATION` | Internal status ("PARTIALLY READY", "Ready for internal review only"), evidence matrix, and Blinkit lines. Useful as a source, not as an external document. |
| Authorization inquiry draft | `docs/partnership/swiggy_instamart_authorization_inquiry.md` | `NEEDS SANITIZATION` / superseded | Header says "Draft only. Do not send without human review." Superseded by `swiggy_instamart_final_inquiry_email.md`. |
| Application field preparation | `docs/partnership/swiggy_instamart_application_fields.md` | `NEEDS SANITIZATION` / superseded | Internal "Prohibited Claims" section and `UNKNOWN` statuses. Superseded by `swiggy_instamart_application_responses.md`. |
| Existing submission package | `docs/partnership/swiggy_instamart_submission_package.md` | `NEEDS SANITIZATION` / superseded | Uses `TBD` placeholders and internal readiness status. Superseded by the new package files. |
| Final inquiry email | `docs/partnership/swiggy_instamart_final_inquiry_email.md` | `SHAREABLE AS-IS` after owner input | External email body; fill owner markers before sending. |
| Application responses | `docs/partnership/swiggy_instamart_application_responses.md` | `SHAREABLE AS-IS` after owner input | Copy-ready answers; do not paste internal evidence annotations. |
| Owner-input register | `docs/partnership/swiggy_instamart_owner_input_register.md` | `DO NOT SHARE` | Internal tracking document. |
| Submission-readiness report | `docs/partnership/swiggy_instamart_submission_readiness.md` | `DO NOT SHARE` | Internal audit trail. |

## What does not exist yet

- A standalone, externally formatted architecture overview covering the whole system.
- A standalone data-flow diagram file (the diagram exists only inside the internal brief).
- A standalone security summary document (the copy-ready summary is a section of the application responses).
- A standalone data-handling declaration (the copy-ready declaration is a section of the application responses).
- A traffic-assumptions worksheet with owner values.
- A sanitized known-limitations document.
- A demo video.
- Any Instamart-specific design, schema, or integration document.

## Leak scan

Command pattern used (run from the repository root on 2026-11-09):

```sh
grep -nE "/Users/|C:\\\\|/home/|/private/var/" <file>
grep -nE "(^|[^0-9])(10\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+)([^0-9]|$)" <file>
grep -nE "localhost|127\.0\.0\.1" <file>
grep -nE -- "-----BEGIN|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{16,}|password[[:space:]]*=|secret[[:space:]]*=|api[_-]?key[[:space:]]*=" <file>
grep -coE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" <file>
```

Results:

| File | Absolute paths | Private IPs | localhost / 127.0.0.1 | Secret patterns | Email addresses |
|---|---:|---:|---:|---:|---:|
| `docs/product_intelligence_design.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/observability.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/runtime_rate_limiting.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/retailer_data_provider_architecture.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/phase_j1_1_blinkit_lockdown.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/architecture/production_readiness_gap.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/architecture/README.md` | 0 | 0 | 0 | 0 | 0 |
| `README.md` | 0 | 0 | **6** | 0 | 0 |
| `docs/partnership/swiggy_instamart_partnership_brief.md` | 0 | 0 | 0 | 0 | 1 (official `builders@swiggy.in`) |
| `docs/partnership/swiggy_instamart_authorization_inquiry.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/partnership/swiggy_instamart_application_fields.md` | 0 | 0 | 0 | 0 | 0 |
| `docs/partnership/swiggy_instamart_submission_package.md` | 0 | 0 | **1** (quoted Swiggy `localhost` allowance) | 0 | 1 (official `builders@swiggy.in`) |
| `docs/partnership/swiggy_instamart_final_inquiry_email.md` | 0 | 0 | 0 | 0 | 1 (official `builders@swiggy.in`) |
| `docs/partnership/swiggy_instamart_application_responses.md` | 0 | 0 | **2** (quoted Swiggy `localhost` allowance) | 0 | 3 (official Swiggy addresses) |

Findings:

- `README.md` contains six `127.0.0.1` references in deployment instructions. It is classified `DO NOT SHARE`.
- The `localhost` hits in the partnership documents are quotations of Swiggy's published rule that `http://localhost` is allowed for local development. They are not Cartel internal addresses and are safe in context.
- No absolute filesystem paths, private IP addresses, secret-like strings, or personal email addresses were found in the candidate documents.
- The only email addresses are official Swiggy contacts (`builders@swiggy.in`, `security@swiggy.in`) and must not be replaced with personal addresses.

## Attachment decision

Attach only:

1. `docs/product_intelligence_design.md` (architecture domain boundaries).
2. `docs/observability.md` (operational security summary).
3. A sanitized copy of the data-flow diagram extracted from the brief.
4. The copy-ready application responses, with internal annotations removed.

Do not attach the internal readiness report, the Blinkit documents, the deployment README, or any document marked `DO NOT SHARE`.
