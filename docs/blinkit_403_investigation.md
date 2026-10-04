# Blinkit HTTP 403 Investigation

**Status:** repository-only investigation, 2026-10-03. No retailer request was made during this investigation.

## Finding

The exact policy that produced the reported HTTP `403` cannot be determined from the retained evidence. Classify the technical root cause as **unknown (D)**. Operationally, treat it as a retailer access-control boundary unless Blinkit supplies an authorized integration path. Do not retry, transfer the request to another acquisition channel after a 403, or attempt to evade the denial.

## Confirmed request and code behavior

The direct search path constructs one `GET https://blinkit.com/s/` with the search phrase in the `q` query parameter. `AsyncHttpClient` follows redirects. The configured headers are:

- `user-agent`: the `SCRAPER_USER_AGENT` setting (repository default identifies Chrome 126 on Windows);
- `accept`: the Blinkit scraper's HTML-oriented accept value;
- `accept-language`: `en-IN,en;q=0.9`;
- `referer`: `https://blinkit.com`.

The direct HTTP client is newly constructed for acquisition and receives no browser storage state or explicit cookies. No locality ID, latitude, or longitude is sent as a query parameter or request header on that path. HTTPX may use proxy environment configuration by default; no proxy variables were present in the environment inspected for this report, which does not prove what was set when the historical request ran.

An HTTP `403` is not retried. `BlinkitScraper` classifies `401`, `403`, `406`, and `429` as access denied and deliberately does not fall back to Playwright. This is fail-closed and must remain so. The browser path, when independently selected for other failures, uses a Playwright context, loads configured storage state only if that file exists, configures locale/timezone/geolocation, and establishes delivery location through Blinkit's visible UI. There is no explicit proxy configured in the scraper/browser code.

## Retained evidence and limits

The repository contains a saved browser `milk` location-failure HTML artifact dated 2026-09-06. A bounded marker scan found Cloudflare, access-denial, blocked, and CAPTCHA-related text in that artifact. Its associated screenshot also exists. The HTML is a page artifact from a location/readiness failure; it is **not** a structured response capture. It does not establish that this page was the body of the reported direct HTTP 403.

No matching structured HTTP response artifact or log was found. The HTTP exception retains only the status code; response headers, response body, final URL, and redirect history are discarded when `raise_for_status()` fails. Therefore the exact responding layer, redirect sequence, challenge reason, and trigger are unavailable. The persisted browser artifact does not record the navigation response status. The inspected environment also had no configured Blinkit session-state file; that does not establish whether a different path or session was present during the earlier attempt.

## Causes

**Confirmed:** the direct request is stateless with respect to Blinkit browser cookies and location, and the code stops on `403`. The preserved browser location-failure page contains Cloudflare/block/challenge markers.

**Likely, not proven:** the request was rejected at a retailer/CDN access-control boundary. The browser page is consistent with an anti-bot/access-denial response. The missing session/location context on the direct HTTP request may correlate with denial, but there is no evidence that supplying it would be permitted or would resolve the response.

**Unverified:** whether the cause was client/session context, IP or network reputation, request rate, user-agent inconsistency, geolocation, a retailer policy rule, or another edge decision. No captured response headers or status-linked body can distinguish these possibilities.

## Authorized integration requirement

Do not change acquisition to route a denied request through browser automation, replay cookies, spoof browser characteristics, rotate network identity, or call guessed endpoints. The preferred production interface is a Blinkit-documented API or retailer-approved partner/catalog feed with explicit permission, documented authentication, rate limits, location semantics, and product/availability fields. Whether such access is available to Cartel is not established here.

Until authorized access is granted, keep live acquisition unavailable on access denial. The existing operator evidence importer can accept a legitimately obtained, policy-compliant, sanitized artifact; it must preserve source, capture time, parser version, and evidence references, and it must not promote incomplete identity to an exact canonical match.
