# Demo journey fixture dataset

This directory is a deterministic, governed **fixture** dataset used only by the
consumer-journey browser test and local demo mode. It is not live retailer
evidence and must never be presented as live.

## Provenance

Generated with the existing development seed path:

```bash
DATA_DIR=backend/tests/fixtures/demo_journey \
APP_ENV=development \
python -m app.dev.seed_demo_cart
```

The seed writes through the existing filesystem catalog, listing-association,
and observation registries. Every observation is marked with
`demo-`/`development-seed` provenance and a `fixture://` source reference, so
the normal consumer evidence gate (`has_supported_retailer_evidence`) rejects
it. Only an application started with `DEMO_FIXTURES_ENABLED=true` exposes it,
and it does so with `evidence_state: "demo_fixture"`.

## Contents

| Canonical product | Variant | Listings | Availability | Purpose |
| --- | --- | --- | --- | --- |
| `demo-product-a` | `demo-variant-a` | `demo-a-1` (INR 100), `demo-a-2` (INR 110) | available | exact variant selection and two-listing comparison |
| `demo-product-b` | `demo-variant-b` | `demo-b-1` (INR 100), `demo-b-2` (INR 110) | unavailable / unknown | honest unavailable state |
| `demo-product-c` | `demo-variant-c` | none | n/a | explicit unresolved/ambiguous request case |

There are no checkout captures or correlated ECE records in this dataset. A
demo optimization therefore returns `unresolved`/`unavailable` with no offers
and no optimizer result; it never asserts savings, a checkout total, or a
payable amount.

## Reproducing the browser journey

From the repository root:

```bash
python3 scripts/e2e/run_consumer_journey.py
```

The harness builds the current frontend, starts a disposable Redis/API/frontend
stack on the isolated Docker network against `cartel_test`, and runs
`backend/tests/e2e/test_consumer_journey_browser.py`. It reads the test password
from `$HOME/.cartel-test-secrets/cartel-test-secret` by default and never targets
the `cartel` database. Pass `--skip-frontend-build` to reuse an existing
`cartel-e2e-frontend:local` image.
