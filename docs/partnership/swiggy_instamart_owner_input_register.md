# Swiggy Instamart Owner-Input Register

**Status:** Internal working document. **Do not submit this file.**

**Purpose:** Every value Cartel cannot truthfully supply from the repository is recorded here. Each entry states where it is needed, why it is needed, whether it blocks submission, and where the owner supplies it.

## Register

| ID | Field | Where needed (document and section) | Why it is needed | Blocking? | Where the owner supplies it |
|---|---|---|---|---|---|
| OI-01 | Legal entity name | `swiggy_instamart_application_responses.md` §2; Enterprise/Startup form | Identifies the applicant and contracting party. | Yes | Owner completes the application form and this register. |
| OI-02 | Entity type and jurisdiction | `swiggy_instamart_application_responses.md` §2 | Determines contracting entity and applicable law. | Yes | Owner completes the application form. |
| OI-03 | Registration or tax identifier, if applicable | `swiggy_instamart_application_responses.md` §2 | Swiggy may require business registration details. | Conditional | Owner supplies only if the entity has one and the form asks. |
| OI-04 | Authorized signatory name and role | `swiggy_instamart_final_inquiry_email.md` signature; `swiggy_instamart_application_responses.md` §2; developer form "Full Name" | Identifies the person authorized to send the inquiry and sign the application. | Yes | Owner writes the name and role into the email signature and form. |
| OI-05 | Business email | `swiggy_instamart_final_inquiry_email.md` signature; `swiggy_instamart_application_responses.md` §2; developer form "Email" | Swiggy's reply channel and applicant contact. | Yes | Owner supplies a monitored business email; do not use a personal or development address without approval. |
| OI-06 | Public product or company URL | `swiggy_instamart_application_responses.md` §2 | Lets Swiggy verify the applicant and product. | Yes | Owner supplies a public HTTPS URL. |
| OI-07 | Production HTTPS redirect URI(s) | `swiggy_instamart_application_responses.md` §6 and §11; developer form "Production Redirect URI(s)" | Required for OAuth redirect allowlisting. Must be exact-match HTTPS; no localhost in the production field. | Yes for production access | Owner supplies after the production callback route is deployed. |
| OI-08 | Static IP ranges or gateway IP(s) | `swiggy_instamart_application_responses.md` §11 | Swiggy's access page lists this as an application input. | Conditional | Owner supplies only if Swiggy requires it for the chosen deployment; no value exists in the repository. |
| OI-09 | Primary technical contact name and email | `swiggy_instamart_application_responses.md` §12 | Swiggy requires an email that reaches an engineer. | Yes | Owner names the engineer and supplies the email. |
| OI-10 | Security contact name and email | `swiggy_instamart_application_responses.md` §13 | Swiggy's access page lists a security contact as an application input. | Yes | Owner names the security contact and supplies the email. |
| OI-11 | Expected launch users, orders/day, Instamart tool calls/day, peak QPS | `swiggy_instamart_application_responses.md` §10; developer form "Expected request volume" | Swiggy uses volume for capacity planning; fabricated numbers are prohibited. | Yes | Owner supplies a documented planning estimate with assumptions. |
| OI-12 | Launch geography | `swiggy_instamart_application_responses.md` §10 | Enterprise applications may ask for end-user geography. | Yes | Owner confirms the launch geography; the current product intent is India. |
| OI-13 | Privacy-policy URL | `swiggy_instamart_application_responses.md` §9 | Swiggy requires a data-handling and privacy declaration. | Yes | Owner supplies a public privacy-policy URL. |
| OI-14 | Working demo video link | `swiggy_instamart_application_responses.md` developer-track table | The public developer form requires a viewable demo video. | Conditional (developer track) | Owner records a short screen capture and supplies a public YouTube/Loom/Drive link. |
| OI-15 | Application track choice | `swiggy_instamart_application_responses.md` §2 and developer-track table | Determines which official form the owner submits. | Yes | Owner chooses Enterprise/Startup or Developer. |
| OI-16 | Swiggy MCP integration-terms acknowledgement | `swiggy_instamart_application_responses.md` developer-track table | The form requires the applicant to accept Swiggy's terms. | Yes | Owner reads and accepts the terms in the form. |
| OI-17 | Attribution and branding acceptance | `swiggy_instamart_application_responses.md` §4 | Swiggy restricts aggregation that hides its brand; Cartel must accept attribution terms. | Yes | Owner confirms acceptance of Swiggy's brand guidelines. |
| OI-18 | Retention period for Instamart-originated observations | `swiggy_instamart_application_responses.md` §9 | The data-handling declaration must state a retention period. | Yes | Owner/legal decides the period; Swiggy's written terms may override it. |
| OI-19 | Company address and country | `swiggy_instamart_application_responses.md` §2 | Applicant identity and contracting details. | Yes | Owner supplies the registered address. |
| OI-20 | LinkedIn, GitHub, or portfolio URL | `swiggy_instamart_application_responses.md` developer-track table | The public developer form asks for GitHub/portfolio and LinkedIn. | Conditional (developer track) | Owner supplies the relevant public profiles. |

## Reconciliation

The package uses the exact marker `OWNER_INPUT_REQUIRED (OI-xx)`. The register is reconciled in both directions:

- Every `OWNER_INPUT_REQUIRED (OI-xx)` marker in the package must resolve to a row above.
- Every row above must be referenced by at least one marker in the package.

Commands used:

```sh
# Markers in the package (excluding this register)
grep -rhoE "OWNER_INPUT_REQUIRED \(OI-[0-9]{2}\)" docs/partnership/swiggy_instamart_final_inquiry_email.md docs/partnership/swiggy_instamart_application_responses.md docs/partnership/swiggy_instamart_technical_attachments.md docs/partnership/swiggy_instamart_submission_readiness.md | sort | uniq -c

# Register IDs
grep -oE "OI-[0-9]{2}" docs/partnership/swiggy_instamart_owner_input_register.md | sort -u
```

Results are recorded in `swiggy_instamart_submission_readiness.md` §6.
